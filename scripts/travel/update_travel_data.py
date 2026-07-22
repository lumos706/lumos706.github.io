#!/usr/bin/env python3
"""Build the travel snapshot by orchestrating last30days-cn only.

This file is deliberately not a crawler. It invokes the officially installed
last30days-cn skill, normalizes its JSON contract, and writes one static data
file for Astro. No booking API, paid scraping service, or site-specific HTTP
logic is implemented here.
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlparse


SKILL_NAME = "last30days-cn"
SKILL_VERSION = "3.2.0-cn"
PLATFORM_KEYS = (
    "weibo",
    "xiaohongshu",
    "bilibili",
    "zhihu",
    "douyin",
    "wechat",
    "baidu",
    "toutiao",
)
API_ENV_KEYS = (
    "WEIBO_ACCESS_TOKEN",
    "SCRAPECREATORS_API_KEY",
    "ZHIHU_COOKIE",
    "TIKHUB_API_KEY",
    "DOUYIN_API_KEY",
    "WECHAT_API_KEY",
    "BAIDU_API_KEY",
    "BAIDU_SECRET_KEY",
)


@dataclass(frozen=True)
class RestaurantSpec:
    name: str
    specialty: str
    note: str


@dataclass(frozen=True)
class QuerySpec:
    key: str
    label: str
    topic: str
    sources: str
    group: str = "category"
    required_terms: tuple[str, ...] = ()
    min_term_hits: int = 1
    restaurants: tuple[RestaurantSpec, ...] = ()
    min_price: int | None = None
    max_price: int | None = None


QUERIES = (
    QuerySpec(
        key="flights",
        label="机票",
        topic="2026年8月初 沈阳桃仙国际机场 往返 西宁兰州 机票价格 含税",
        sources="xiaohongshu,douyin,zhihu,baidu",
        required_terms=("沈阳", "桃仙", "西宁", "兰州", "机票", "航班"),
        min_term_hits=2,
        min_price=300,
        max_price=5000,
    ),
    QuerySpec(
        key="hotels",
        label="住宿",
        topic="2026年8月 青海甘肃 西宁茶卡大柴旦敦煌张掖 酒店双床房 每晚价格",
        sources="xiaohongshu,douyin,zhihu,baidu",
        required_terms=("西宁", "茶卡", "大柴旦", "敦煌", "张掖", "酒店", "双床房"),
        min_term_hits=2,
        min_price=80,
        max_price=2000,
    ),
    QuerySpec(
        key="tickets",
        label="门票",
        topic="2026年8月 青海湖茶卡盐湖莫高窟鸣沙山七彩丹霞 门票价格 预约",
        sources="xiaohongshu,douyin,zhihu,baidu",
        required_terms=("青海湖", "茶卡", "莫高窟", "鸣沙山", "丹霞", "门票", "预约"),
        min_term_hits=2,
        min_price=20,
        max_price=1000,
    ),
)


ATTRACTION_QUERIES = (
    QuerySpec(
        key="qinghaiLake",
        label="青海湖",
        topic="青海湖 8月 自驾 拍照 门票 避坑 私人牧场 路边停车",
        sources="xiaohongshu,douyin,bilibili,zhihu",
        group="attraction",
        required_terms=("青海湖",),
    ),
    QuerySpec(
        key="chakaSaltLake",
        label="茶卡盐湖",
        topic="茶卡盐湖 8月 小火车 拍照 鞋套 预约 避坑",
        sources="xiaohongshu,douyin,bilibili,zhihu",
        group="attraction",
        required_terms=("茶卡", "盐湖"),
    ),
    QuerySpec(
        key="dachaidan",
        label="大柴旦",
        topic="大柴旦 翡翠湖 水上雅丹 U型公路 自驾 攻略 避坑",
        sources="xiaohongshu,douyin,bilibili,zhihu",
        group="attraction",
        required_terms=("大柴旦", "翡翠湖", "水上雅丹", "U型公路"),
    ),
    QuerySpec(
        key="mogaoCaves",
        label="莫高窟",
        topic="莫高窟 8月 官方预约 A类票 参观 攻略 避坑",
        sources="xiaohongshu,douyin,bilibili,zhihu",
        group="attraction",
        required_terms=("莫高窟",),
    ),
    QuerySpec(
        key="mingshaMountain",
        label="鸣沙山月牙泉",
        topic="鸣沙山 月牙泉 8月 日落 骑骆驼 鞋套 攻略 避坑",
        sources="xiaohongshu,douyin,bilibili,zhihu",
        group="attraction",
        required_terms=("鸣沙山", "月牙泉"),
    ),
    QuerySpec(
        key="jiayuPass",
        label="嘉峪关",
        topic="嘉峪关 关城 8月 门票 游玩顺序 攻略 避坑",
        sources="xiaohongshu,douyin,bilibili,zhihu",
        group="attraction",
        required_terms=("嘉峪关", "关城"),
    ),
    QuerySpec(
        key="zhangyeDanxia",
        label="张掖七彩丹霞",
        topic="张掖 七彩丹霞 8月 日出 日落 观景台 攻略 避坑",
        sources="xiaohongshu,douyin,bilibili,zhihu",
        group="attraction",
        required_terms=("张掖", "七彩丹霞", "丹霞"),
    ),
)


FOOD_QUERIES = (
    QuerySpec(
        key="xining",
        label="西宁",
        topic="西宁 益鑫羊肉手抓馆 德禄酸奶 马忠羊肠面 美食 推荐 避雷",
        sources="xiaohongshu,zhihu",
        group="food",
        required_terms=("西宁", "益鑫", "德禄", "马忠"),
        restaurants=(
            RestaurantSpec("益鑫羊肉手抓馆", "手抓羊肉", "推荐与避雷帖同时存在，四人先点招牌手抓，再决定是否加菜。"),
            RestaurantSpec("德禄酸奶", "青海酸奶", "近期口碑分化，先买小杯试味，不把它当作唯一酸奶选择。"),
            RestaurantSpec("马忠羊肠面", "羊肠面", "早餐或午间去更稳，出发前核对当天营业时间。"),
        ),
    ),
    QuerySpec(
        key="chaka",
        label="茶卡",
        topic="茶卡 应财特色炕锅肉 炕锅羊肉 本地餐厅 推荐 避雷",
        sources="xiaohongshu,zhihu",
        group="food",
        required_terms=("茶卡", "应财", "炕锅"),
        restaurants=(
            RestaurantSpec("应财特色炕锅肉", "炕锅羊肉", "旺季先问清斤价、份量和等位时间，四人不要一次点过量。"),
        ),
    ),
    QuerySpec(
        key="dachaidan",
        label="大柴旦",
        topic="大柴旦 鼎鼎牛干锅牦牛肉 餐厅 推荐 避雷",
        sources="xiaohongshu,zhihu",
        group="food",
        required_terms=("大柴旦", "鼎鼎", "牦牛肉"),
        restaurants=(
            RestaurantSpec("鼎鼎牛干锅牦牛肉", "牦牛肉干锅", "当地近期推荐与避雷内容并存，到店先确认锅底、份量和总价。"),
        ),
    ),
    QuerySpec(
        key="dunhuang",
        label="敦煌",
        topic="敦煌 达记驴肉黄面 靖远尕六美味羊羔肉 夏家合汁 推荐 避雷",
        sources="xiaohongshu,zhihu",
        group="food",
        required_terms=("敦煌", "达记", "尕六", "夏家合汁"),
        restaurants=(
            RestaurantSpec("靖远尕六美味羊羔肉", "羊羔肉", "热门时段可能排队，先取号再决定是否等待。"),
            RestaurantSpec("达记驴肉黄面", "驴肉黄面", "驴肉和黄面可能分开计价，点单前确认套餐内容。"),
            RestaurantSpec("夏家合汁", "敦煌合汁", "更适合早餐，临近中午前先核对是否售罄。"),
        ),
    ),
    QuerySpec(
        key="zhangye",
        label="张掖",
        topic="张掖 孙记炒炮 苗氏卷子鸡 甘州名吃",
        sources="xiaohongshu,zhihu",
        group="food",
        required_terms=("张掖", "孙记", "苗氏", "甘州"),
        restaurants=(
            RestaurantSpec("孙记炒炮", "炒炮", "近期笔记有人反馈偏咸，可在点单时主动要求少盐。"),
            RestaurantSpec("苗氏卷子鸡", "卷子鸡", "有近期避雷反馈，去前先看最新评价并确认份量。"),
            RestaurantSpec("甘州名吃", "张掖小吃", "适合一次尝多种主食，四人先点小份再追加。"),
        ),
    ),
    QuerySpec(
        key="lanzhou",
        label="兰州",
        topic="兰州 马子禄牛肉面 吾穆勒蓬灰牛肉面 杜记甜食 再回首酿皮",
        sources="xiaohongshu,zhihu",
        group="food",
        required_terms=("兰州", "马子禄", "吾穆勒", "杜记", "再回首"),
        restaurants=(
            RestaurantSpec("吾穆勒蓬灰牛肉面", "牛肉面", "尽量放在早餐或午餐，牛肉面店常比晚餐时段更早收档。"),
            RestaurantSpec("马子禄牛肉面", "牛肉面", "按面型、牛肉和小菜分别点，先看现场排队长度。"),
            RestaurantSpec("杜记甜食", "灰豆子、甜醅", "适合多人分食试味，甜度和口感因人而异。"),
            RestaurantSpec("再回首酿皮", "酿皮", "分店体验可能不同，优先核对具体门店近期评价。"),
        ),
    ),
)


ALL_QUERIES = (*QUERIES, *ATTRACTION_QUERIES, *FOOD_QUERIES)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Refresh travel data through last30days-cn")
    parser.add_argument("--skill-dir", type=Path, help="Installed last30days-cn directory")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("src/data/travel/snapshot.json"),
        help="Snapshot JSON destination",
    )
    parser.add_argument("--days", type=int, default=30, help="Public-content lookback window")
    parser.add_argument("--timeout", type=int, default=95, help="Per-query skill timeout in seconds")
    parser.add_argument("--quick", action="store_true", help="Ask the skill to use quick mode")
    parser.add_argument(
        "--pause",
        type=float,
        default=5.0,
        help="Low-frequency pause between skill queries in seconds",
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Force the skill's browserless public-search fallbacks",
    )
    parser.add_argument(
        "--allow-credentials",
        action="store_true",
        help="Allow optional credentials from the official user config or process environment",
    )
    parser.add_argument(
        "--only",
        help="Comma-separated query keys to refresh while preserving all other snapshot groups",
    )
    return parser.parse_args()


def discover_skill_dir(explicit: Path | None) -> Path:
    candidates: list[Path] = []
    if explicit:
        candidates.append(explicit)
    configured = os.environ.get("LAST30DAYS_SKILL_DIR")
    if configured:
        candidates.append(Path(configured))
    candidates.extend(
        [
            Path.home() / ".agents" / "skills" / SKILL_NAME,
            Path.home() / ".codex" / "skills" / SKILL_NAME,
        ]
    )

    for candidate in candidates:
        if (candidate / "scripts" / "last30days.py").is_file():
            return candidate.resolve()

    try:
        result = subprocess.run(
            ["npx", "--yes", "skills", "list", "-g", "--json"],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
        )
        installed = json.loads(result.stdout)
        for item in installed:
            if item.get("name") == SKILL_NAME:
                candidate = Path(item["path"])
                if (candidate / "scripts" / "last30days.py").is_file():
                    return candidate.resolve()
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError, KeyError):
        pass

    searched = ", ".join(str(path) for path in candidates)
    raise FileNotFoundError(
        f"{SKILL_NAME} was not found. Run the official installer first. Searched: {searched}"
    )


def skill_environment(no_browser: bool, allow_credentials: bool) -> dict[str, str]:
    env = os.environ.copy()
    if not allow_credentials:
        for key in API_ENV_KEYS:
            env.pop(key, None)
        # An empty override disables the user's global config file in last30days-cn.
        env["LAST30DAYS_CN_CONFIG_DIR"] = ""
    else:
        env.pop("LAST30DAYS_CN_CONFIG_DIR", None)
    env["PYTHONUTF8"] = "1"
    if no_browser:
        env["LAST30DAYS_DISABLE_BROWSER"] = "1"
    else:
        env.pop("LAST30DAYS_DISABLE_BROWSER", None)
    return env


def extract_json(text: str) -> dict[str, Any]:
    decoder = json.JSONDecoder()
    starts = [match.start() for match in re.finditer(r"(?m)^\s*\{", text)]
    # The skill prints progress lines before one outer JSON document. Iterate
    # from the first line-level opening brace so nested objects near the end do
    # not get mistaken for the payload.
    for start in starts:
        try:
            value, _ = decoder.raw_decode(text[start:].lstrip())
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    raise ValueError("last30days-cn did not emit a JSON object")


def run_skill(
    skill_script: Path,
    spec: QuerySpec,
    *,
    days: int,
    timeout: int,
    quick: bool,
    env: dict[str, str],
) -> dict[str, Any]:
    command = [
        sys.executable,
        str(skill_script),
        spec.topic,
        "--search",
        spec.sources,
        "--days",
        str(days),
        "--refresh",
        "--emit",
        "json",
        "--timeout",
        str(timeout),
    ]
    if quick:
        command.append("--quick")

    completed = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        timeout=timeout + 45,
    )
    output = f"{completed.stdout}\n{completed.stderr}"
    payload = extract_json(output)
    payload["_exit_code"] = completed.returncode
    return payload


def run_diagnose(skill_script: Path, env: dict[str, str], timeout: int) -> dict[str, Any]:
    completed = subprocess.run(
        [sys.executable, str(skill_script), "--diagnose", "--emit", "json"],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        timeout=min(timeout, 75),
    )
    return extract_json(f"{completed.stdout}\n{completed.stderr}")


def relevance_value(item: dict[str, Any]) -> float:
    raw = item.get("relevance")
    if isinstance(raw, (int, float)):
        return float(raw)
    score = item.get("score")
    if isinstance(score, (int, float)):
        return min(1.0, max(0.0, float(score) / 100.0))
    return 0.0


def clean_text(value: Any) -> str:
    text = html.unescape(str(value or ""))
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def platform_from_url(url: str, fallback: str) -> str:
    host = urlparse(url).netloc.lower()
    domain_map = (
        ("xiaohongshu.com", "xiaohongshu"),
        ("douyin.com", "douyin"),
        ("zhihu.com", "zhihu"),
        ("bilibili.com", "bilibili"),
        ("weibo.com", "weibo"),
        ("toutiao.com", "toutiao"),
        ("mp.weixin.qq.com", "wechat"),
    )
    for domain, platform in domain_map:
        if host == domain or host.endswith(f".{domain}"):
            return platform
    return fallback


def engagement_total(item: dict[str, Any]) -> int:
    engagement = item.get("engagement")
    if not isinstance(engagement, dict):
        return 0
    return sum(
        int(value)
        for value in engagement.values()
        if isinstance(value, (int, float)) and value > 0
    )


NEGATIVE_SIGNAL = re.compile(
    r"避雷|踩雷|踩坑|别去|别来|别再推荐|不推荐|受害者|血亏|太咸|偏咸|劝退|失望"
)
POSITIVE_SIGNAL = re.compile(r"推荐|必吃|好吃|宝藏|不踩雷|排队王|值得|首选")


def evidence_signal(title: str, snippet: str) -> str:
    text = f"{title} {snippet}"
    negative = bool(NEGATIVE_SIGNAL.search(text))
    positive = bool(POSITIVE_SIGNAL.search(text))
    if negative and positive:
        return "mixed"
    if negative:
        return "caution"
    if positive:
        return "positive"
    return "neutral"


def normalize_evidence(
    payload: dict[str, Any], spec: QuerySpec, limit: int = 12
) -> list[dict[str, Any]]:
    evidence: list[dict[str, Any]] = []
    seen_urls: set[str] = set()
    for platform in PLATFORM_KEYS:
        items = payload.get(platform)
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict):
                continue
            url = str(item.get("url") or "").strip()
            title = clean_text(item.get("title") or item.get("text"))
            snippet = clean_text(
                item.get("snippet")
                or item.get("excerpt")
                or item.get("desc")
                or item.get("description")
            )
            if not url or not title or url in seen_urls:
                continue
            parsed = urlparse(url)
            if parsed.netloc.lower().endswith(("xiaohongshu.com", "douyin.com")) and parsed.path in ("", "/"):
                continue
            haystack = f"{title} {snippet}".lower()
            hits = sum(1 for term in spec.required_terms if term.lower() in haystack)
            if spec.required_terms and hits < spec.min_term_hits:
                continue
            relevance = relevance_value(item)
            if relevance < 0.12 and hits < 2:
                continue
            seen_urls.add(url)
            evidence.append(
                {
                    "platform": platform_from_url(url, platform),
                    "title": title,
                    "snippet": snippet,
                    "url": url,
                    "date": item.get("date"),
                    "dateConfidence": item.get("date_confidence") or "unknown",
                    "relevance": round(relevance, 3),
                    "score": item.get("score"),
                    "engagement": item.get("engagement") if isinstance(item.get("engagement"), dict) else {},
                    "author": clean_text(
                        item.get("author_name")
                        or item.get("author")
                        or item.get("channel_name")
                    ),
                    "signal": evidence_signal(title, snippet),
                }
            )
    evidence.sort(
        key=lambda item: (
            item["relevance"],
            item.get("score") or 0,
            engagement_total(item),
        ),
        reverse=True,
    )
    return evidence[:limit]


PRICE_PATTERNS = (
    re.compile(r"(?:¥|￥|RMB\s*)(\d{2,5})(?:\.\d{1,2})?", re.IGNORECASE),
    re.compile(r"(?<!\d)(\d{2,5})(?:\.\d{1,2})?\s*(?:元|块(?:钱)?)(?!\d)"),
)


def price_candidates(
    evidence: Iterable[dict[str, Any]], minimum: int, maximum: int
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    seen: set[tuple[str, int]] = set()
    for item in evidence:
        if item["relevance"] < 0.2:
            continue
        haystack = f"{item['title']} {item['snippet']}"
        for pattern in PRICE_PATTERNS:
            for match in pattern.finditer(haystack):
                value = int(match.group(1))
                key = (item["url"], value)
                if minimum <= value <= maximum and key not in seen:
                    seen.add(key)
                    candidates.append(
                        {
                            "value": value,
                            "platform": item["platform"],
                            "title": item["title"],
                            "url": item["url"],
                        }
                    )
    return candidates[:20]


def category_snapshot(spec: QuerySpec, payload: dict[str, Any]) -> dict[str, Any]:
    evidence = normalize_evidence(payload, spec)
    category: dict[str, Any] = {
        "label": spec.label,
        "status": "ok" if evidence else "empty",
        "evidenceCount": len(evidence),
        "evidence": evidence,
        "sourceErrors": {
            key.removesuffix("_error"): value
            for key, value in payload.items()
            if key.endswith("_error") and isinstance(value, str)
        },
    }
    if spec.min_price is None or spec.max_price is None:
        return category

    candidates = price_candidates(evidence, spec.min_price, spec.max_price)
    unique_values = sorted({item["value"] for item in candidates})
    reliable = (
        spec.key != "tickets"
        and len(candidates) >= 2
        and len({item["url"] for item in candidates}) >= 2
    )
    category.update(
        {
            "priceStatus": "reference" if reliable else "insufficient",
            "priceRange": (
                {"min": unique_values[0], "max": unique_values[-1]} if reliable else None
            ),
            "priceSamples": candidates,
        }
    )
    return category


def restaurant_snapshot(
    candidates: tuple[RestaurantSpec, ...], evidence: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    restaurants: list[dict[str, Any]] = []
    for candidate in candidates:
        matches = [
            item
            for item in evidence
            if candidate.name in f"{item['title']} {item['snippet']}"
        ]
        if not matches:
            continue
        has_positive = any(item["signal"] in ("positive", "mixed") for item in matches)
        has_caution = any(item["signal"] in ("caution", "mixed") for item in matches)
        verdict = "mixed" if has_positive and has_caution else ("caution" if has_caution else "candidate")
        restaurants.append(
            {
                "name": candidate.name,
                "specialty": candidate.specialty,
                "note": candidate.note,
                "verdict": verdict,
                "sources": matches[:3],
            }
        )
    return restaurants


def previous_snapshot(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def diagnostic_summary(diagnose: dict[str, Any]) -> dict[str, Any]:
    sources = diagnose.get("sources") if isinstance(diagnose.get("sources"), list) else []
    return {
        "summary": diagnose.get("summary") or {},
        "sources": [
            {
                "source": item.get("source"),
                "label": item.get("label"),
                "status": item.get("status"),
                "available": item.get("available"),
                "reason": item.get("reason"),
            }
            for item in sources
            if isinstance(item, dict)
        ],
        "crawlerEngine": diagnose.get("crawler_engine") or {},
    }


def write_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        newline="\n",
        delete=False,
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
    ) as handle:
        handle.write(serialized)
        temporary = Path(handle.name)
    temporary.replace(path)


def main() -> int:
    args = parse_args()
    skill_dir = discover_skill_dir(args.skill_dir)
    skill_script = skill_dir / "scripts" / "last30days.py"
    output = args.output.resolve()
    prior = previous_snapshot(output)
    env = skill_environment(args.no_browser, args.allow_credentials)
    now = datetime.now(timezone.utc)
    requested_keys = {
        key.strip()
        for key in (args.only or "").split(",")
        if key.strip()
    }
    selected_queries = tuple(
        spec for spec in ALL_QUERIES if not requested_keys or spec.key in requested_keys
    )
    if requested_keys and not selected_queries:
        raise ValueError(f"No query key matched --only: {', '.join(sorted(requested_keys))}")

    failures: list[dict[str, str]] = []
    categories: dict[str, Any] = dict((prior or {}).get("categories") or {}) if requested_keys else {}
    attractions: dict[str, Any] = dict((prior or {}).get("attractions") or {}) if requested_keys else {}
    food: dict[str, Any] = dict((prior or {}).get("food") or {}) if requested_keys else {}
    query_log: list[dict[str, Any]] = list(((prior or {}).get("collection") or {}).get("queries") or []) if requested_keys else []

    try:
        diagnose = run_diagnose(skill_script, env, args.timeout)
    except (OSError, subprocess.SubprocessError, ValueError) as exc:
        diagnose = {}
        failures.append({"key": "diagnose", "message": str(exc)})

    for index, spec in enumerate(selected_queries):
        target = categories if spec.group == "category" else (attractions if spec.group == "attraction" else food)
        try:
            payload = run_skill(
                skill_script,
                spec,
                days=args.days,
                timeout=args.timeout,
                quick=args.quick,
                env=env,
            )
            old_group = {
                "category": "categories",
                "attraction": "attractions",
                "food": "food",
            }[spec.group]
            old_result = ((prior or {}).get(old_group) or {}).get(spec.key)
            result = category_snapshot(spec, payload)
            if spec.group == "food":
                fresh_restaurants = restaurant_snapshot(spec.restaurants, result["evidence"])
                result["restaurants"] = fresh_restaurants
                old_restaurants = (
                    old_result.get("restaurants", [])
                    if isinstance(old_result, dict)
                    and isinstance(old_result.get("restaurants"), list)
                    else []
                )
                # Browser search results can fluctuate even while the login is
                # valid. If a source explicitly failed, retain still-traceable
                # restaurant evidence from the preceding snapshot instead of
                # silently deleting useful candidates after one weak refresh.
                if (
                    len(fresh_restaurants) < len(old_restaurants)
                    and result.get("sourceErrors")
                ):
                    merged = list(fresh_restaurants)
                    seen_names = {item.get("name") for item in merged}
                    merged.extend(
                        item
                        for item in old_restaurants
                        if item.get("name") not in seen_names
                    )
                    result["restaurants"] = merged
                    result["staleRestaurantsPreserved"] = True
                    result["restaurantRefreshAttemptAt"] = now.isoformat()
                    result["lastRestaurantSuccessfulAt"] = (
                        old_result.get("lastRestaurantSuccessfulAt")
                        or (prior or {}).get("generatedAt")
                    )
                elif fresh_restaurants:
                    result["lastRestaurantSuccessfulAt"] = now.isoformat()
            if (
                result.get("evidenceCount", 0) == 0
                and isinstance(old_result, dict)
                and old_result.get("evidenceCount", 0) > 0
            ):
                result = {
                    **old_result,
                    "staleBecauseRefreshEmpty": True,
                    "lastRefreshAttemptAt": now.isoformat(),
                    "lastRefreshSourceErrors": result.get("sourceErrors") or {},
                }
            target[spec.key] = result
            query_log = [item for item in query_log if item.get("key") != spec.key or item.get("group") != spec.group]
            query_log.append(
                {
                    "key": spec.key,
                    "label": spec.label,
                    "group": spec.group,
                    "topic": spec.topic,
                    "sources": spec.sources.split(","),
                    "range": payload.get("range"),
                    "exitCode": payload.get("_exit_code"),
                }
            )
        except (OSError, subprocess.SubprocessError, ValueError) as exc:
            failures.append({"key": spec.key, "message": str(exc)})
            old_group = {
                "category": "categories",
                "attraction": "attractions",
                "food": "food",
            }[spec.group]
            old_category = ((prior or {}).get(old_group) or {}).get(spec.key)
            if isinstance(old_category, dict):
                target[spec.key] = {**old_category, "staleBecauseRefreshFailed": True}
            else:
                target[spec.key] = {
                    "label": spec.label,
                    "status": "error",
                    "evidenceCount": 0,
                    "evidence": [],
                    "priceStatus": "insufficient" if spec.min_price else None,
                    "priceRange": None,
                    "priceSamples": [],
                    "sourceErrors": {},
                }
        if index < len(selected_queries) - 1 and args.pause > 0:
            time.sleep(args.pause)

    all_groups = (*categories.values(), *attractions.values(), *food.values())
    active_sources = sorted(
        {
            evidence["platform"]
            for category in all_groups
            for evidence in category.get("evidence", [])
        }
    )
    source_coverage = {
        platform: sum(
            1
            for category in all_groups
            for evidence in category.get("evidence", [])
            if evidence.get("platform") == platform
        )
        for platform in active_sources
    }
    evidence_total = sum(category.get("evidenceCount", 0) for category in all_groups)
    if failures:
        overall_status = "partial" if evidence_total else "error"
    else:
        overall_status = "ok" if evidence_total else "empty"
    snapshot = {
        "schemaVersion": 2,
        "generatedAt": now.isoformat(),
        "expiresAt": (now + timedelta(hours=36)).isoformat(),
        "status": overall_status,
        "mode": "browser-plus-optional-credentials" if args.allow_credentials else "no-api-browser",
        "skill": {
            "name": SKILL_NAME,
            "version": SKILL_VERSION,
            "repository": "https://github.com/Jesseovo/last30days-skill-cn",
        },
        "tripContext": {
            "origin": "沈阳桃仙国际机场",
            "travelWindow": "2026 年 8 月初",
            "travelers": 4,
            "rooms": 2,
            "roomType": "双床房",
        },
        "notice": "公开内容价格快照与攻略线索，不是实时库存或官方结论；最终价格、余票、营业状态和退改规则以官方页面及商家当日信息为准。",
        "activeSources": active_sources,
        "sourceCoverage": source_coverage,
        "categories": categories,
        "attractions": attractions,
        "food": food,
        "collection": {
            "python": sys.version.split()[0],
            "pythonPrefix": str(Path(sys.prefix)),
            "browserDisabled": args.no_browser,
            "optionalCredentialsEnabled": args.allow_credentials,
            "diagnose": diagnostic_summary(diagnose),
            "queries": query_log,
            "failures": failures,
        },
    }
    write_atomic(output, snapshot)
    print(
        json.dumps(
            {
                "output": str(output),
                "status": overall_status,
                "activeSources": active_sources,
                "failures": failures,
            },
            ensure_ascii=False,
        )
    )
    return 0 if overall_status != "error" else 1


if __name__ == "__main__":
    raise SystemExit(main())
