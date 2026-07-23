#!/usr/bin/env python3
"""Refresh departure-preparation evidence through last30days-cn.

This is an orchestration layer, not a crawler. The packing and health guidance
below is a conservative, hand-reviewed baseline for four adults travelling from
Shenyang to Qinghai and Gansu in early August. The official last30days-cn skill
is called at low frequency to refresh supporting public evidence every day.
Weak or empty runs never rewrite medical advice and never erase the previous
known-good evidence.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from update_travel_data import (
    QuerySpec,
    discover_skill_dir,
    normalize_evidence,
    run_skill,
    skill_environment,
    write_atomic,
)


SKILL_NAME = "last30days-cn"
SKILL_VERSION = "3.2.0-cn"
PARSER_VERSION = 1


@dataclass(frozen=True)
class PreparationItem:
    key: str
    title: str
    detail: str
    scope: str
    priority: str


@dataclass(frozen=True)
class PreparationSpec:
    key: str
    code: str
    title: str
    summary: str
    topic: str
    required_terms: tuple[str, ...]
    signal: re.Pattern[str]
    transport: str
    items: tuple[PreparationItem, ...]

    def query(self) -> QuerySpec:
        return QuerySpec(
            key=self.key,
            label=self.title,
            topic=self.topic,
            sources="xiaohongshu,douyin,zhihu,bilibili,baidu",
            group="preparation",
            required_terms=self.required_terms,
        )


PREPARATIONS = (
    PreparationSpec(
        key="health",
        code="HEALTH / 01",
        title="药品与高原健康",
        summary="先照顾每个人原有的身体情况，再准备通用小药包；不要把网红药单当处方。",
        topic="青甘旅游 高原反应 药品 氧气 出发准备",
        required_terms=("青海", "甘肃", "高原", "高反", "药品", "氧气"),
        signal=re.compile(r"高反|高原|药|氧气|头痛|血氧|医院|急救|晕车|肠胃|止痛"),
        transport="all",
        items=(
            PreparationItem(
                key="personal-medicine",
                title="每个人的处方药和用药清单",
                detail="保留原包装，按全程用量再多带 2 天；写清药名、剂量、过敏史和紧急联系人。慢性心肺疾病、严重贫血、妊娠或近期身体不适者，出发前先问医生是否适合进入高海拔地区。",
                scope="每人一份",
                priority="必带",
            ),
            PreparationItem(
                key="shared-first-aid",
                title="四人共用基础小药包",
                detail="结合个人禁忌，在医生或药师指导下准备晕车药、肠胃药、退热止痛药，以及创可贴、消毒棉片和纱布；处方药不要互相分着吃。",
                scope="四人共用",
                priority="建议",
            ),
            PreparationItem(
                key="altitude-plan",
                title="把“休息、下撤、就医”写进计划",
                detail="抵达高海拔后的第一天放慢节奏，少酒、避免剧烈运动。症状持续加重，或出现静息呼吸困难、意识异常、走路不稳等情况时，停止继续上升，尽快下撤并就医。",
                scope="全员知晓",
                priority="必看",
            ),
        ),
    ),
    PreparationSpec(
        key="weather",
        code="WEATHER / 02",
        title="衣物、防晒与天气",
        summary="八月也不能只带短袖：高原紫外线强，早晚、风口和下雨后的体感差很多。",
        topic="青甘大环线 8月 穿衣 防晒 雨具 出发准备",
        required_terms=("青甘", "青海", "甘肃", "8月", "防晒", "衣物", "温差"),
        signal=re.compile(r"防晒|紫外线|墨镜|帽|冲锋衣|羽绒|外套|温差|雨|鞋|保暖|风"),
        transport="all",
        items=(
            PreparationItem(
                key="layered-clothes",
                title="分层穿衣，不押注一件厚外套",
                detail="每人准备速干内层、保暖中层和防风防雨外层；茶卡、大柴旦、青海湖日出日落时再加轻薄羽绒或抓绒。当天看预报决定穿哪层。",
                scope="每人一套",
                priority="必带",
            ),
            PreparationItem(
                key="sun-protection",
                title="防晒霜、墨镜、帽子和润唇",
                detail="选择适合自己的高倍广谱防晒并按说明补涂；带有 UV 防护的墨镜、遮阳帽、润唇膏和保湿用品，长时间在户外时优先用衣物做物理遮挡。",
                scope="每人一套",
                priority="必带",
            ),
            PreparationItem(
                key="walking-gear",
                title="防滑鞋、备用袜和轻便雨具",
                detail="盐湖、戈壁和景区接驳会走不少路，鞋底要防滑且提前穿合脚；雨衣比大伞更适合风大的路段。",
                scope="每人一套",
                priority="建议",
            ),
        ),
    ),
    PreparationSpec(
        key="documents",
        code="DOCS / 03",
        title="证件、订单与应急信息",
        summary="手机没信号或临时没电时，仍要能证明身份、找到酒店并联系同行人。",
        topic="青甘大环线 身份证 驾驶证 保险 预约 清单",
        required_terms=("青甘", "青海", "甘肃", "身份证", "驾驶证", "预约", "订单"),
        signal=re.compile(r"身份证|驾照|驾驶证|订单|预约|证件|保险|保单|门票|酒店|航班|紧急"),
        transport="all",
        items=(
            PreparationItem(
                key="identity-documents",
                title="身份证原件和必要驾驶证件",
                detail="四人分别保管身份证原件；自驾司机另带有效驾驶证。证件照片只作应急备份，不能替代现场要求的原件。",
                scope="每人保管",
                priority="必带",
            ),
            PreparationItem(
                key="offline-orders",
                title="把关键订单离线保存",
                detail="保存航班、酒店、租车、莫高窟及其他景区预约截图，标出日期、报到地点和退改规则；四人群里放一份，另给一位同行人离线备份。",
                scope="两人备份",
                priority="必做",
            ),
            PreparationItem(
                key="insurance-contacts",
                title="旅行保险、紧急联系人和简短病史",
                detail="核对保障范围是否覆盖高原旅行和自驾；记录保险报案电话、租车救援电话、紧急联系人及每个人的重要病史和过敏信息。",
                scope="四人共享",
                priority="建议",
            ),
        ),
    ),
    PreparationSpec(
        key="flightTech",
        code="CABIN / 04",
        title="乘机、充电与离线导航",
        summary="从沈阳飞过去，行李规则比“带不带”更重要；易变规定每天只做提醒，最终看航司和机场。",
        topic="飞机 行李 充电宝 3C 药品 托运 规定",
        required_terms=("民航", "乘机", "充电宝", "3C", "氧气瓶", "托运", "随身"),
        signal=re.compile(r"民航|飞机|乘机|充电宝|3C|电池|氧气|托运|随身|行李|药品"),
        transport="all",
        items=(
            PreparationItem(
                key="power-bank",
                title="标识清楚的合规充电宝",
                detail="容量和 3C 等标识必须清晰，放随身行李，不托运；出发当天再次核对承运航司和机场的最新要求，不按旧攻略判断。",
                scope="每人确认",
                priority="出发前确认",
            ),
            PreparationItem(
                key="oxygen-flight",
                title="不要把一次性氧气罐直接装进行李",
                detail="压缩气体通常受航空运输限制；如确有需要，到达后在正规渠道购买或租用，并先咨询航司、机场及医生，不自行携带登机。",
                scope="全员知晓",
                priority="必看",
            ),
            PreparationItem(
                key="offline-kit",
                title="离线地图、充电线和车载电源",
                detail="提前下载青海、甘肃离线地图和关键订单；四人至少准备两套充电线与电源。自驾方案另带车充，公共交通方案把充电宝放进随身小包。",
                scope="四人共用",
                priority="必带",
            ),
        ),
    ),
    PreparationSpec(
        key="driveKit",
        code="DRIVE / 05",
        title="自驾专用准备",
        summary="租车不是拿到钥匙就走：先留证据、确认保险，再把长路段拆给两位司机。",
        topic="青甘大环线 自驾 租车 驾驶证 保险 加油 准备",
        required_terms=("青甘", "自驾", "租车", "驾驶证", "验车", "保险", "加油"),
        signal=re.compile(r"自驾|租车|驾驶证|验车|车况|轮胎|保险|加油|离线地图|驾驶|救援"),
        transport="drive",
        items=(
            PreparationItem(
                key="rental-check",
                title="取还车合同、保险和全车视频",
                detail="确认驾驶人、押金、里程、异地还车、保险免赔和道路救援；取车时连续拍摄车身、玻璃、轮胎、油表和仪表告警。",
                scope="两位司机",
                priority="必做",
            ),
            PreparationItem(
                key="route-safety",
                title="两位司机轮换，长路段提前加油",
                detail="茶卡—德令哈—大柴旦等长路段先下载离线地图、查加油点和天气；不疲劳驾驶、不为赶日落夜间赶路，遇封路以交警和道路通知为准。",
                scope="驾驶组",
                priority="必做",
            ),
            PreparationItem(
                key="shared-car-supplies",
                title="水、易保存零食、纸巾和垃圾袋",
                detail="按当天路线补给，不把车内堆满；水和食物避免长时间暴晒，垃圾带到有处理条件的地方再丢。",
                scope="四人共用",
                priority="建议",
            ),
        ),
    ),
    PreparationSpec(
        key="publicKit",
        code="TRANSIT / 05",
        title="公共交通专用准备",
        summary="动车、客运、公交和打车之间要频繁换乘，轻装和时间余量比多塞一件衣服更有用。",
        topic="青甘旅游 公共交通 动车 公交 打车 行李 准备",
        required_terms=("青海", "甘肃", "公共交通", "动车", "客运", "公交", "换乘", "行李"),
        signal=re.compile(r"公共交通|动车|高铁|客运|公交|打车|换乘|行李|寄存|车站|班次"),
        transport="public",
        items=(
            PreparationItem(
                key="light-luggage",
                title="每人一只好移动的行李和随身小包",
                detail="减少需要两个人抬的箱子；身份证、药品、充电宝、雨具和当天车票放随身小包，行李加姓名与联系电话。",
                scope="每人整理",
                priority="建议",
            ),
            PreparationItem(
                key="transfer-buffer",
                title="换乘预留余量，保存车站全名",
                detail="保存“嘉峪关站 / 嘉峪关南站”等完整站名和地址；动车、客运与景区接驳之间不做极限衔接，末班车前准备正规打车备选。",
                scope="行程负责人",
                priority="必做",
            ),
            PreparationItem(
                key="shared-arrival-note",
                title="四人共享住宿地址和到达方案",
                detail="把酒店中文地址、电话、百度地图链接及夜间到达方式放进群公告；打车时核对平台订单和车牌。",
                scope="四人共享",
                priority="必做",
            ),
        ),
    ),
)


CONTEXT_SIGNALS: dict[str, re.Pattern[str]] = {
    "health": re.compile(r"高反|高原|药|健康|安全|急救|氧气"),
    "weather": re.compile(r"天气|穿搭|衣|防晒|温差|紫外线|保暖|冲锋|羽绒|雨具"),
    "documents": re.compile(r"证件|身份证|驾驶证|订单|门票|预约|保险|酒店|航班"),
    "flightTech": re.compile(r"中国|国内|民航|3C|机场|航空"),
    "driveKit": re.compile(r"租车|准备|攻略|避坑|验车|保险|轮胎|加油|救援"),
    "publicKit": re.compile(
        r"青海|甘肃|青甘|西宁|敦煌|张掖|嘉峪关|青海湖|茶卡|莫高窟"
    ),
}

EXCLUDE_SIGNALS: dict[str, re.Pattern[str]] = {
    "health": re.compile(r"神药|刚需抗高反药品|闭眼买|照着买"),
    "flightTech": re.compile(
        r"榜单|推荐|三合一|耐用充电宝|品牌排行|神器|大容量|快充|高铁|购买"
    ),
    "publicKit": re.compile(r"随机换乘|挑战|公交迷|报站"),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Refresh departure preparation evidence")
    parser.add_argument("--skill-dir", type=Path)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("src/data/travel/preparations.json"),
    )
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--pause", type=float, default=8.0)
    parser.add_argument("--quick", action="store_true")
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--allow-credentials", action="store_true")
    return parser.parse_args()


def previous_snapshot(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def serialized_items(items: tuple[PreparationItem, ...]) -> list[dict[str, str]]:
    return [
        {
            "key": item.key,
            "title": item.title,
            "detail": item.detail,
            "scope": item.scope,
            "priority": item.priority,
        }
        for item in items
    ]


def category_payload(
    spec: PreparationSpec,
    evidence: list[dict[str, Any]],
    prior: dict[str, Any],
    checked_at: str,
) -> dict[str, Any]:
    context_signal = CONTEXT_SIGNALS.get(spec.key)
    exclude_signal = EXCLUDE_SIGNALS.get(spec.key)

    def matches(item: dict[str, Any]) -> bool:
        text = f"{item.get('title', '')} {item.get('snippet', '')}"
        return (
            bool(spec.signal.search(text))
            and (context_signal is None or bool(context_signal.search(text)))
            and (exclude_signal is None or not exclude_signal.search(text))
        )

    matched = [
        item
        for item in evidence
        if matches(item)
    ][:4]
    prior_evidence = prior.get("evidence") if isinstance(prior.get("evidence"), list) else []
    retained = [
        item for item in prior_evidence if isinstance(item, dict) and matches(item)
    ][:4]
    visible_evidence = matched or retained
    if matched:
        source_status = "confirmed"
    elif retained:
        source_status = "retained"
    else:
        source_status = "fallback"
    return {
        "key": spec.key,
        "code": spec.code,
        "title": spec.title,
        "summary": spec.summary,
        "transport": spec.transport,
        "items": serialized_items(spec.items),
        "checkedAt": checked_at,
        "lastEvidenceAt": checked_at if matched else prior.get("lastEvidenceAt"),
        "sourceStatus": source_status,
        "evidence": visible_evidence,
    }


def main() -> int:
    args = parse_args()
    skill_dir = discover_skill_dir(args.skill_dir)
    skill_script = skill_dir / "scripts" / "last30days.py"
    output = args.output.resolve()
    previous = previous_snapshot(output)
    previous_categories = (
        previous.get("categories") if isinstance(previous.get("categories"), dict) else {}
    )
    env = skill_environment(args.no_browser, args.allow_credentials)
    now = datetime.now(timezone.utc)
    checked_at = now.isoformat()
    categories: dict[str, Any] = {}
    failures: list[dict[str, str]] = []
    active_sources: set[str] = set()

    for index, spec in enumerate(PREPARATIONS):
        prior = previous_categories.get(spec.key)
        if not isinstance(prior, dict):
            prior = {}
        try:
            payload = run_skill(
                skill_script,
                spec.query(),
                days=args.days,
                timeout=args.timeout,
                quick=args.quick,
                env=env,
            )
            normalized = normalize_evidence(payload, spec.query(), limit=10)
            category = category_payload(spec, normalized, prior, checked_at)
            category["sourceErrors"] = {
                key.removesuffix("_error"): value
                for key, value in payload.items()
                if key.endswith("_error") and isinstance(value, str)
            }
            categories[spec.key] = category
            active_sources.update(
                item.get("platform")
                for item in category["evidence"]
                if item.get("platform")
            )
        except (OSError, subprocess.SubprocessError, ValueError) as exc:
            failures.append({"key": spec.key, "message": str(exc)})
            categories[spec.key] = category_payload(spec, [], prior, checked_at)
            categories[spec.key]["sourceStatus"] = "stale" if prior else "fallback"
            categories[spec.key]["lastError"] = str(exc)
        if index < len(PREPARATIONS) - 1 and args.pause > 0:
            time.sleep(args.pause)

    snapshot = {
        "schemaVersion": 1,
        "parserVersion": PARSER_VERSION,
        "generatedAt": checked_at,
        "expiresAt": (now + timedelta(hours=30)).isoformat(),
        "status": "partial" if failures else "ok",
        "schedule": "21:00 Asia/Shanghai",
        "skill": {
            "name": SKILL_NAME,
            "version": SKILL_VERSION,
            "repository": "https://github.com/Jesseovo/last30days-skill-cn",
        },
        "activeSources": sorted(active_sources),
        "categories": categories,
        "medicalNotice": (
            "药品与高原健康内容仅用于一般旅行准备，不替代医生诊断或个体化用药建议；"
            "如有基础疾病、孕期、近期不适或高原经历不佳，请在出发前咨询医生。"
        ),
        "collection": {
            "mode": "browser-plus-optional-credentials"
            if args.allow_credentials
            else "no-api-browser",
            "failures": failures,
        },
    }
    write_atomic(output, snapshot)
    print(
        json.dumps(
            {
                "output": str(output),
                "status": snapshot["status"],
                "categories": len(categories),
                "activeSources": snapshot["activeSources"],
                "failures": failures,
            },
            ensure_ascii=False,
        )
    )
    return 0 if categories else 1


if __name__ == "__main__":
    raise SystemExit(main())
