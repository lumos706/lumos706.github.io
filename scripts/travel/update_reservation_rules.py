#!/usr/bin/env python3
"""Refresh actionable attraction reservation rules through last30days-cn.

This script is an orchestrator, not a crawler. It calls the officially
installed last30days-cn skill, accepts only explicit booking language from the
returned JSON, and keeps the previous known-good rule when evidence is weak.
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


@dataclass(frozen=True)
class ReservationSpec:
    key: str
    name: str
    topic: str
    required_terms: tuple[str, ...]
    required: bool
    planning_lead_days: int
    channel: str
    fallback_note: str

    def query(self) -> QuerySpec:
        return QuerySpec(
            key=self.key,
            label=self.name,
            topic=self.topic,
            sources="xiaohongshu,douyin,zhihu,bilibili,baidu",
            group="attraction",
            required_terms=self.required_terms,
        )


RESERVATIONS = (
    ReservationSpec(
        key="qinghaiLake",
        name="青海湖",
        topic="青海湖 二郎剑 门票 预约 提前几天",
        required_terms=("青海湖", "二郎剑"),
        required=False,
        planning_lead_days=1,
        channel="青海湖景区官方平台或现场售票窗口",
        fallback_note="二郎剑等正规收费景区可实名购票；只走合法入口，不进入未确认价格的私人牧场。",
    ),
    ReservationSpec(
        key="chakaSaltLake",
        name="茶卡盐湖",
        topic="茶卡盐湖 门票 预约 提前几天",
        required_terms=("茶卡盐湖", "茶卡", "盐湖"),
        required=False,
        planning_lead_days=1,
        channel="茶卡盐湖景区官方平台或现场售票窗口",
        fallback_note="普通门票通常可当天实名购买；暑期提前购票更方便同时确认小火车套票与入园时段。",
    ),
    ReservationSpec(
        key="dachaidan",
        name="大柴旦",
        topic="大柴旦 翡翠湖 水上雅丹 门票 预约",
        required_terms=("大柴旦", "翡翠湖", "水上雅丹"),
        required=False,
        planning_lead_days=1,
        channel="翡翠湖或水上雅丹景区官方平台",
        fallback_note="翡翠湖和水上雅丹是两个独立景区，决定二选一后再购买对应门票。",
    ),
    ReservationSpec(
        key="mogaoCaves",
        name="莫高窟",
        topic="莫高窟 门票 预约 提前几天 攻略",
        required_terms=("莫高窟",),
        required=True,
        planning_lead_days=15,
        channel="“莫高窟参观预约网”公众号或微信小程序",
        fallback_note="至少提前15天开始处理；放票后应立即下单，15天不是有票保证。",
    ),
    ReservationSpec(
        key="mingshaMountain",
        name="鸣沙山月牙泉",
        topic="鸣沙山 月牙泉 门票 预约 提前几天",
        required_terms=("鸣沙山", "月牙泉"),
        required=False,
        planning_lead_days=1,
        channel="鸣沙山月牙泉景区官方平台或现场售票窗口",
        fallback_note="普通门票可实名购买；暑期日落前客流集中，提前购票可以减少现场排队。",
    ),
    ReservationSpec(
        key="jiayuPass",
        name="嘉峪关",
        topic="嘉峪关 关城 门票 预约 提前几天",
        required_terms=("嘉峪关", "关城"),
        required=False,
        planning_lead_days=1,
        channel="嘉峪关文物景区官方平台或现场售票窗口",
        fallback_note="关城普通票通常可当天实名购买；先看清单景点票与套票范围。",
    ),
    ReservationSpec(
        key="zhangyeDanxia",
        name="张掖七彩丹霞",
        topic="张掖 七彩丹霞 门票 预约 提前几天",
        required_terms=("张掖", "七彩丹霞", "丹霞"),
        required=False,
        planning_lead_days=1,
        channel="张掖七彩丹霞景区官方平台或现场售票窗口",
        fallback_note="普通游览票通常可当天购买；日出、深度游等特殊产品必须按官方场次单独确认。",
    ),
)


DAY_PATTERNS = (
    re.compile(r"提前\s*(\d{1,2})\s*(?:天|日)"),
    re.compile(r"(\d{1,2})\s*(?:天|日)前"),
)
BOOKING_TERMS = re.compile(r"预约|订票|购票|放票|实名制|门票")
REQUIRED_TERMS = re.compile(r"必须预约|务必提前|需要提前|需提前|实名预约")
NOT_REQUIRED_TERMS = re.compile(r"无需预约|不用预约|不需要预约|无需提前预约|现场购票|当天购票")
ATTRACTION_TERMS = (
    "青海湖",
    "二郎剑",
    "茶卡盐湖",
    "茶卡",
    "大柴旦",
    "翡翠湖",
    "水上雅丹",
    "莫高窟",
    "鸣沙山",
    "月牙泉",
    "嘉峪关",
    "关城",
    "张掖七彩丹霞",
    "七彩丹霞",
)
PARSER_VERSION = 2


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Refresh attraction reservation rules")
    parser.add_argument("--skill-dir", type=Path)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("src/data/travel/reservations.json"),
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


def mentions_target_near(text: str, start: int, end: int, terms: tuple[str, ...]) -> bool:
    candidates: list[tuple[int, str]] = []
    for term in ATTRACTION_TERMS:
        before = text.rfind(term, max(0, start - 64), start)
        if before >= 0:
            candidates.append((start - (before + len(term)), term))
        after = text.find(term, end, min(len(text), end + 28))
        if after >= 0:
            candidates.append((after - end, term))
    if not candidates:
        return False
    _, closest = min(candidates, key=lambda item: item[0])
    return closest in terms


def explicit_days(text: str, terms: tuple[str, ...]) -> list[int]:
    days: list[int] = []
    for pattern in DAY_PATTERNS:
        for match in pattern.finditer(text):
            if mentions_target_near(text, match.start(), match.end(), terms):
                days.append(int(match.group(1)))
    named_periods = (
        (re.compile(r"提前半个月"), 15),
        (re.compile(r"提前\s*(?:一|1)\s*个?月"), 30),
        (re.compile(r"提前一周"), 7),
        (re.compile(r"提前两周"), 14),
    )
    for pattern, value in named_periods:
        for match in pattern.finditer(text):
            if mentions_target_near(text, match.start(), match.end(), terms):
                days.append(value)
    return [value for value in days if 0 < value <= 60]


def targeted_vote(pattern: re.Pattern[str], text: str, terms: tuple[str, ...]) -> bool:
    return any(
        mentions_target_near(text, match.start(), match.end(), terms)
        for match in pattern.finditer(text)
    )


def source_rule(
    spec: ReservationSpec,
    evidence: list[dict[str, Any]],
    prior: dict[str, Any],
    checked_at: str,
) -> dict[str, Any]:
    booking_evidence: list[dict[str, Any]] = []
    day_values: list[int] = []
    required_votes = 0
    not_required_votes = 0

    for item in evidence:
        text = f"{item.get('title', '')} {item.get('snippet', '')}"
        if not BOOKING_TERMS.search(text):
            continue
        days = explicit_days(text, spec.required_terms)
        required_vote = targeted_vote(REQUIRED_TERMS, text, spec.required_terms)
        not_required_vote = targeted_vote(NOT_REQUIRED_TERMS, text, spec.required_terms)
        required_votes += int(required_vote)
        not_required_votes += int(not_required_vote)
        if days or required_vote or not_required_vote:
            booking_evidence.append(item)
            day_values.extend(days)

    compatible_prior = prior if prior.get("parserVersion") == PARSER_VERSION else {}
    prior_required = (
        compatible_prior.get("required")
        if isinstance(compatible_prior.get("required"), bool)
        else spec.required
    )
    required = spec.required or prior_required
    if not spec.required and required_votes >= 1 and day_values:
        required = True
    elif not spec.required and not_required_votes >= 1:
        required = False

    observed_window = (
        max(day_values)
        if day_values
        else compatible_prior.get("observedBookingWindowDays")
    )
    if not isinstance(observed_window, int) or not 0 < observed_window <= 60:
        observed_window = 30 if spec.key == "mogaoCaves" else None

    if required:
        lead_days = (
            spec.planning_lead_days
            if spec.required
            else max(spec.planning_lead_days, min(observed_window or spec.planning_lead_days, 30))
        )
        lead_time = f"至少提前 {lead_days} 天"
        status_label = "需要提前预约"
    else:
        recommendation = spec.planning_lead_days
        if day_values:
            recommendation = max(recommendation, min(max(day_values), 7))
        lead_days = recommendation
        lead_time = f"当天可买；暑期建议提前 {recommendation} 天"
        status_label = "不需要提前预约"

    note = spec.fallback_note
    if required and observed_window:
        prefix = (
            "本次公开信息出现"
            if booking_evidence
            else "当前保留的稳妥值按"
        )
        note = f"{prefix}约提前{observed_window}天的预约或放票窗口。{spec.fallback_note}"

    return {
        "name": spec.name,
        "required": required,
        "statusLabel": status_label,
        "leadDays": lead_days,
        "leadTime": lead_time,
        "observedBookingWindowDays": observed_window,
        "channel": spec.channel,
        "note": note,
        "checkedAt": checked_at,
        "lastEvidenceAt": checked_at if booking_evidence else compatible_prior.get("lastEvidenceAt"),
        "sourceStatus": "confirmed" if booking_evidence else "fallback",
        "evidence": booking_evidence[:3],
        "parserVersion": PARSER_VERSION,
    }


def main() -> int:
    args = parse_args()
    skill_dir = discover_skill_dir(args.skill_dir)
    skill_script = skill_dir / "scripts" / "last30days.py"
    output = args.output.resolve()
    prior = previous_snapshot(output)
    prior_attractions = prior.get("attractions") if isinstance(prior.get("attractions"), dict) else {}
    env = skill_environment(args.no_browser, args.allow_credentials)
    now = datetime.now(timezone.utc)
    checked_at = now.isoformat()
    attractions: dict[str, Any] = {}
    failures: list[dict[str, str]] = []
    active_sources: set[str] = set()

    for index, spec in enumerate(RESERVATIONS):
        old_rule = prior_attractions.get(spec.key) if isinstance(prior_attractions.get(spec.key), dict) else {}
        try:
            payload = run_skill(
                skill_script,
                spec.query(),
                days=args.days,
                timeout=args.timeout,
                quick=args.quick,
                env=env,
            )
            evidence = normalize_evidence(payload, spec.query(), limit=8)
            rule = source_rule(spec, evidence, old_rule, checked_at)
            rule["sourceErrors"] = {
                key.removesuffix("_error"): value
                for key, value in payload.items()
                if key.endswith("_error") and isinstance(value, str)
            }
            attractions[spec.key] = rule
            active_sources.update(item.get("platform") for item in evidence if item.get("platform"))
        except (OSError, subprocess.SubprocessError, ValueError) as exc:
            failures.append({"key": spec.key, "message": str(exc)})
            if old_rule:
                attractions[spec.key] = {
                    **old_rule,
                    "checkedAt": checked_at,
                    "sourceStatus": "stale",
                    "lastError": str(exc),
                }
            else:
                attractions[spec.key] = source_rule(spec, [], {}, checked_at)
                attractions[spec.key]["sourceStatus"] = "fallback"
                attractions[spec.key]["lastError"] = str(exc)
        if index < len(RESERVATIONS) - 1 and args.pause > 0:
            time.sleep(args.pause)

    status = "partial" if failures else "ok"
    snapshot = {
        "schemaVersion": 1,
        "generatedAt": checked_at,
        "expiresAt": (now + timedelta(hours=30)).isoformat(),
        "status": status,
        "schedule": "21:17/22:17/23:17 Asia/Shanghai",
        "skill": {
            "name": SKILL_NAME,
            "version": SKILL_VERSION,
            "repository": "https://github.com/Jesseovo/last30days-skill-cn",
        },
        "activeSources": sorted(active_sources),
        "attractions": attractions,
        "collection": {
            "mode": "browser-plus-optional-credentials" if args.allow_credentials else "no-api-browser",
            "failures": failures,
        },
    }
    write_atomic(output, snapshot)
    print(
        json.dumps(
            {
                "output": str(output),
                "status": status,
                "rules": len(attractions),
                "failures": failures,
            },
            ensure_ascii=False,
        )
    )
    return 0 if attractions else 1


if __name__ == "__main__":
    raise SystemExit(main())
