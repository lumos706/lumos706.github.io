#!/usr/bin/env python3
"""Refresh local transport evidence through last30days-cn.

This module does not crawl any platform itself. It asks the officially
installed last30days-cn skill for low-frequency public evidence, then attaches
that evidence to conservative, hand-reviewed transport baselines. Route numbers
and timetables are deliberately not inferred from a single user post because
seasonal services change often.
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

DRIVE_SIGNAL = re.compile(r"自驾|租车|停车|高速|国道|加油|路况|驾驶|还车")
PUBLIC_SIGNAL = re.compile(
    r"公交|直通车|大巴|客运|班车|火车|动车|高铁|打车|出租车|网约车|"
    r"接驳|专线|拼车|包车|旅游集散|怎么去|交通"
)


@dataclass(frozen=True)
class ModeBaseline:
    headline: str
    route: str
    note: str


@dataclass(frozen=True)
class TransportSpec:
    key: str
    name: str
    topic: str
    required_terms: tuple[str, ...]
    drive: ModeBaseline
    public: ModeBaseline

    def query(self) -> QuerySpec:
        return QuerySpec(
            key=self.key,
            label=self.name,
            topic=self.topic,
            sources="xiaohongshu,douyin,bilibili,zhihu,baidu",
            group="transport",
            required_terms=self.required_terms,
        )


TRANSPORT_GUIDES = (
    TransportSpec(
        key="qinghaiLake",
        name="青海湖",
        topic="青海湖 二郎剑 西宁 自驾 公交 直通车 攻略",
        required_terms=("青海湖", "二郎剑"),
        drive=ModeBaseline(
            headline="西宁 → 二郎剑约 150 km，预留 2.5–3 小时",
            route="西宁早出发 → 青海湖南岸正规入口 → 景区停车场",
            note="暑期把拥堵、停车和天气余量算进去；不在公路路肩停车，也不临时驶入未明码标价的私人牧场。",
        ),
        public=ModeBaseline(
            headline="优先选择西宁往返二郎剑的正规旅游直通车",
            route="西宁官方旅游集散点 → 二郎剑景区 → 按约定时间原车返回",
            note="班次会随季节和成团情况调整；付款前确认集合点、返程时间、是否含门票及是否有购物安排。",
        ),
    ),
    TransportSpec(
        key="chakaSaltLake",
        name="茶卡盐湖",
        topic="茶卡盐湖 西宁 自驾 火车 大巴 打车 攻略",
        required_terms=("茶卡", "盐湖"),
        drive=ModeBaseline(
            headline="青海湖 → 茶卡约 150 km，日落前完成入住",
            route="二郎剑一带 → 橡皮山方向 → 茶卡镇 / 景区停车场",
            note="高原天气和路况变化快，不为追日落安排夜间赶路；进景区前先确认停车场与预约入口。",
        ),
        public=ModeBaseline(
            headline="先到茶卡镇，再用正规打车补景区最后一段",
            route="西宁乘当日可售铁路或客运班次 → 茶卡镇 → 景区入口",
            note="铁路和客运班次并非每天、每季都相同；先锁定去回两程再订住宿，不把返程航班接在同一天。",
        ),
    ),
    TransportSpec(
        key="dachaidan",
        name="大柴旦",
        topic="大柴旦 翡翠湖 水上雅丹 自驾 拼车 交通攻略",
        required_terms=("大柴旦", "翡翠湖", "水上雅丹"),
        drive=ModeBaseline(
            headline="茶卡 → 大柴旦是长距离高原路段",
            route="茶卡 → 德令哈补给 → 大柴旦镇 → 翡翠湖或水上雅丹二选一",
            note="出发前加满油并下载离线地图，至少两人轮换驾驶；翡翠湖和水上雅丹不要塞进同一个下午。",
        ),
        public=ModeBaseline(
            headline="常规公共交通覆盖弱，七日不自驾方案建议跳过",
            route="若坚持前往：先到大柴旦镇，再预订可核验资质的当地接驳",
            note="镇区到翡翠湖、水上雅丹仍有明显最后一公里问题；不要到站后再临时接受陌生人揽客包车。",
        ),
    ),
    TransportSpec(
        key="mogaoCaves",
        name="莫高窟",
        topic="莫高窟 敦煌市区 公交 直通车 打车 攻略",
        required_terms=("莫高窟", "数字展示中心"),
        drive=ModeBaseline(
            headline="按票面报到时间直达数字展示中心停车场",
            route="敦煌市区 → 莫高窟数字展示中心 → 统一乘景区接驳前往洞窟",
            note="导航目的地应是数字展示中心而不是直接开往洞窟；旺季停车、取票和安检都要另留时间。",
        ),
        public=ModeBaseline(
            headline="市区先到数字展示中心，再乘景区统一接驳",
            route="敦煌市区 → 当日官方直通车 / 公交 / 正规打车 → 数字展示中心",
            note="市区公交与直通车可能季节性调整，因此不凭旧攻略写死线路号；出发前一天用官方通知和地图实时公交复核。",
        ),
    ),
    TransportSpec(
        key="mingshaMountain",
        name="鸣沙山月牙泉",
        topic="鸣沙山 月牙泉 敦煌市区 公交 打车 日落返程",
        required_terms=("鸣沙山", "月牙泉"),
        drive=ModeBaseline(
            headline="敦煌市区短途前往，先确认景区停车入口",
            route="酒店休息 → 景区正规停车场 → 日落后按现场导流离场",
            note="日落散场车辆集中，不把车停在非正规路边；把骑骆驼和滑沙当可选项，不影响离场时间。",
        ),
        public=ModeBaseline(
            headline="市区公交去、散场后四人打车回更稳",
            route="敦煌市区 → 当日可用公交 / 正规打车 → 鸣沙山月牙泉入口",
            note="晚间公交班次可能减少，去程就准备正规打车备选；上车前核对车牌和平台订单。",
        ),
    ),
    TransportSpec(
        key="jiayuPass",
        name="嘉峪关",
        topic="嘉峪关 关城 公交 打车 自驾 攻略",
        required_terms=("嘉峪关", "关城"),
        drive=ModeBaseline(
            headline="市区短途到关城，只保留一个核心景点",
            route="市区 / 酒店 → 关城景区停车场 → 原路返回",
            note="先看清单景点票与套票范围；七日线不再串悬壁长城等外围点，避免挤压下一段动车。",
        ),
        public=ModeBaseline(
            headline="从到达站用公交或四人打车分摊前往关城",
            route="嘉峪关站 / 嘉峪关南站 → 市区寄存行李 → 关城景区",
            note="两个铁路站与市区距离不同；买票后按实际到达站重新查路线，不套用另一车站的公交攻略。",
        ),
    ),
    TransportSpec(
        key="zhangyeDanxia",
        name="张掖七彩丹霞",
        topic="张掖 七彩丹霞 直通车 公交 自驾 日落返程",
        required_terms=("张掖", "七彩丹霞", "丹霞"),
        drive=ModeBaseline(
            headline="市区 → 北入口约 40 km，早场更容易控时",
            route="张掖市区 → 七彩丹霞北入口停车场 → 按景区接驳环线游览",
            note="进景区后服从内部接驳顺序；日落场散场集中，返兰州当天优先选择早场。",
        ),
        public=ModeBaseline(
            headline="用当日景区专线或四人正规打车往返",
            route="张掖市区 / 张掖西站 → 旅游集散点或正规打车 → 北入口",
            note="日落时间可能晚于末班公共接驳，去程前必须确认返程；无法确认就改早场，不在景区外临时找黑车。",
        ),
    ),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Refresh local transport evidence")
    parser.add_argument("--skill-dir", type=Path)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("src/data/travel/transport.json"),
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


def transport_evidence(evidence: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        item
        for item in evidence
        if DRIVE_SIGNAL.search(f"{item.get('title', '')} {item.get('snippet', '')}")
        or PUBLIC_SIGNAL.search(f"{item.get('title', '')} {item.get('snippet', '')}")
    ]


def mode_payload(
    baseline: ModeBaseline,
    evidence: list[dict[str, Any]],
    signal: re.Pattern[str],
    prior: dict[str, Any],
    checked_at: str,
) -> dict[str, Any]:
    matched = [
        item
        for item in evidence
        if signal.search(f"{item.get('title', '')} {item.get('snippet', '')}")
    ]
    return {
        "headline": baseline.headline,
        "route": baseline.route,
        "note": baseline.note,
        "checkedAt": checked_at,
        "lastEvidenceAt": checked_at if matched else prior.get("lastEvidenceAt"),
        "sourceStatus": "confirmed" if matched else "fallback",
        "evidence": matched[:3],
    }


def main() -> int:
    args = parse_args()
    skill_dir = discover_skill_dir(args.skill_dir)
    skill_script = skill_dir / "scripts" / "last30days.py"
    output = args.output.resolve()
    previous = previous_snapshot(output)
    previous_attractions = (
        previous.get("attractions") if isinstance(previous.get("attractions"), dict) else {}
    )
    env = skill_environment(args.no_browser, args.allow_credentials)
    now = datetime.now(timezone.utc)
    checked_at = now.isoformat()
    attractions: dict[str, Any] = {}
    failures: list[dict[str, str]] = []
    active_sources: set[str] = set()

    for index, spec in enumerate(TRANSPORT_GUIDES):
        prior = previous_attractions.get(spec.key)
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
            evidence = transport_evidence(normalized)
            attractions[spec.key] = {
                "name": spec.name,
                "drive": mode_payload(
                    spec.drive,
                    evidence,
                    DRIVE_SIGNAL,
                    prior.get("drive", {}) if isinstance(prior.get("drive"), dict) else {},
                    checked_at,
                ),
                "public": mode_payload(
                    spec.public,
                    evidence,
                    PUBLIC_SIGNAL,
                    prior.get("public", {}) if isinstance(prior.get("public"), dict) else {},
                    checked_at,
                ),
                "sourceErrors": {
                    key.removesuffix("_error"): value
                    for key, value in payload.items()
                    if key.endswith("_error") and isinstance(value, str)
                },
            }
            active_sources.update(
                item.get("platform") for item in evidence if item.get("platform")
            )
        except (OSError, subprocess.SubprocessError, ValueError) as exc:
            failures.append({"key": spec.key, "message": str(exc)})
            if prior:
                attractions[spec.key] = {
                    **prior,
                    "checkedAt": checked_at,
                    "sourceStatus": "stale",
                    "lastError": str(exc),
                }
            else:
                attractions[spec.key] = {
                    "name": spec.name,
                    "drive": mode_payload(spec.drive, [], DRIVE_SIGNAL, {}, checked_at),
                    "public": mode_payload(spec.public, [], PUBLIC_SIGNAL, {}, checked_at),
                    "lastError": str(exc),
                }
        if index < len(TRANSPORT_GUIDES) - 1 and args.pause > 0:
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
        "attractions": attractions,
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
                "guides": len(attractions),
                "failures": failures,
            },
            ensure_ascii=False,
        )
    )
    return 0 if attractions else 1


if __name__ == "__main__":
    raise SystemExit(main())
