#!/usr/bin/env python3
"""Check travel-source login health through the official last30days-cn skill.

This is an orchestration and reporting helper, not a crawler. Every live web
probe is performed by the officially installed last30days-cn CLI. The helper
only inspects the returned source metadata and local cookie expiry fields so a
scheduled GitHub Action can warn when a source falls back to public search.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


SKILL_NAME = "last30days-cn"
PROBE_TOPICS = (
    "青海湖 8月 旅游攻略",
    "敦煌 莫高窟 8月 旅游攻略",
)
XHS_NATIVE_SOURCES = {"crawler", "crawler-xhr", "crawler-dom"}
FALLBACK_SOURCES = {"site-search-fallback", "public-search-fallback"}
XHS_LOGIN_COOKIE_NAMES = {"web_session", "id_token"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check Xiaohongshu and Zhihu access through last30days-cn"
    )
    parser.add_argument("--skill-dir", type=Path, help="Installed skill directory")
    parser.add_argument("--timeout", type=int, default=90, help="Per-probe timeout")
    parser.add_argument("--attempts", type=int, default=2, choices=(1, 2))
    parser.add_argument("--pause", type=float, default=8.0)
    parser.add_argument("--report", type=Path, help="Write machine-readable JSON")
    parser.add_argument("--summary", type=Path, help="Append a Markdown summary")
    parser.add_argument("--issue-body", type=Path, help="Write a safe issue body")
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
    raise FileNotFoundError(
        "last30days-cn was not found; install Jesseovo/last30days-skill-cn first"
    )


def extract_json(text: str) -> dict[str, Any]:
    decoder = json.JSONDecoder()
    for match in re.finditer(r"(?m)^\s*\{", text):
        try:
            value, _ = decoder.raw_decode(text[match.start() :].lstrip())
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    raise ValueError("last30days-cn did not emit a JSON object")


def load_optional_config_value(key: str) -> str:
    value = os.environ.get(key, "").strip()
    if value:
        return value
    config_path = Path.home() / ".config" / "last30days-cn" / ".env"
    if not config_path.is_file():
        return ""
    for raw_line in config_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        candidate, raw_value = line.split("=", 1)
        if candidate.strip() != key:
            continue
        raw_value = raw_value.strip()
        if len(raw_value) >= 2 and raw_value[0] == raw_value[-1] and raw_value[0] in "\"'":
            raw_value = raw_value[1:-1]
        return raw_value
    return ""


def cookie_source(item: dict[str, Any]) -> str:
    source = str(item.get("source") or "").strip().lower()
    if source:
        return source
    why_relevant = str(item.get("why_relevant") or "")
    match = re.search(r"来源\(([^)]+)\)", why_relevant)
    return match.group(1).strip().lower() if match else "native-api"


def xhs_cookie_health() -> dict[str, Any]:
    cookie_path = (
        Path.home()
        / ".config"
        / "last30days-cn"
        / "browser_cookies"
        / "xiaohongshu_cookies.json"
    )
    result: dict[str, Any] = {
        "configured": cookie_path.is_file(),
        "path": str(cookie_path),
        "coreCookiesPresent": [],
        "coreExpiry": None,
        "daysRemaining": None,
        "structuralStatus": "missing",
    }
    if not cookie_path.is_file():
        return result
    try:
        cookies = json.loads(cookie_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        result["structuralStatus"] = "invalid"
        return result
    if not isinstance(cookies, list):
        result["structuralStatus"] = "invalid"
        return result

    now = datetime.now(timezone.utc).timestamp()
    core = [
        cookie
        for cookie in cookies
        if isinstance(cookie, dict)
        and str(cookie.get("name") or "") in XHS_LOGIN_COOKIE_NAMES
    ]
    result["coreCookiesPresent"] = sorted(
        str(cookie.get("name")) for cookie in core if cookie.get("name")
    )
    if not core:
        result["structuralStatus"] = "missing-core-cookie"
        return result

    future_expiries: list[float] = []
    for cookie in core:
        try:
            expiry = float(cookie.get("expires") or 0)
        except (TypeError, ValueError):
            expiry = 0
        if expiry <= 0 or expiry > now:
            if expiry > 0:
                future_expiries.append(expiry)

    expiry_values: list[float] = []
    for cookie in core:
        try:
            expiry_values.append(float(cookie.get("expires") or 0))
        except (TypeError, ValueError):
            expiry_values.append(0)
    if not future_expiries and all(expiry > 0 for expiry in expiry_values):
        result["structuralStatus"] = "expired"
        return result

    if future_expiries:
        expiry = min(future_expiries)
        expiry_dt = datetime.fromtimestamp(expiry, timezone.utc)
        result["coreExpiry"] = expiry_dt.isoformat()
        result["daysRemaining"] = round((expiry - now) / 86400, 1)
        result["structuralStatus"] = (
            "expiring-soon" if expiry - now <= 7 * 86400 else "present"
        )
    else:
        result["structuralStatus"] = "present-session-cookie"
    return result


def run_probe(skill_script: Path, topic: str, timeout: int) -> dict[str, Any]:
    command = [
        sys.executable,
        str(skill_script),
        topic,
        "--search",
        "xiaohongshu,zhihu",
        "--days",
        "30",
        "--refresh",
        "--emit",
        "json",
        "--timeout",
        str(timeout),
    ]
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env.pop("LAST30DAYS_DISABLE_BROWSER", None)
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
    payload = extract_json(f"{completed.stdout}\n{completed.stderr}")
    return {"topic": topic, "exitCode": completed.returncode, "payload": payload}


def source_result(attempts: list[dict[str, Any]], source: str) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    errors: list[str] = []
    for attempt in attempts:
        payload = attempt["payload"]
        raw_items = payload.get(source)
        if isinstance(raw_items, list):
            items.extend(item for item in raw_items if isinstance(item, dict))
        error = payload.get(f"{source}_error")
        if isinstance(error, str) and error.strip():
            errors.append(error.strip())

    sources = sorted({cookie_source(item) for item in items})
    if source == "xiaohongshu":
        native = any(item_source in XHS_NATIVE_SOURCES for item_source in sources)
    else:
        native = bool(items) and any(
            item_source not in FALLBACK_SOURCES for item_source in sources
        )
    fallback_only = bool(items) and not native
    return {
        "itemCount": len(items),
        "resultSources": sources,
        "nativePathUsable": native,
        "fallbackOnly": fallback_only,
        "errors": sorted(set(errors)),
    }


def status_label(status: str) -> str:
    return {
        "healthy": "正常",
        "expiring": "即将到期",
        "degraded": "已降级",
        "missing": "未配置",
        "unknown": "无法确认",
    }.get(status, status)


def build_markdown(report: dict[str, Any], *, issue: bool = False) -> str:
    xhs = report["sources"]["xiaohongshu"]
    zhihu = report["sources"]["zhihu"]
    expiry = xhs["cookie"].get("coreExpiry")
    expiry_text = "无法从 Cookie 元数据确定"
    if expiry:
        china_tz = timezone(timedelta(hours=8), name="UTC+8")
        parsed = datetime.fromisoformat(expiry).astimezone(china_tz)
        expiry_text = f"{parsed:%Y-%m-%d %H:%M %Z}（约 {xhs['cookie']['daysRemaining']} 天）"

    heading = "# 旅游数据登录态需要更新" if issue else "## 旅游数据登录态预检"
    lines = [
        heading,
        "",
        f"- 检查时间：{report['checkedAt']}",
        f"- 小红书：**{status_label(xhs['status'])}**；主采集路径结果 {xhs['probe']['itemCount']} 条",
        f"- 小红书核心登录 Cookie：{expiry_text}",
        f"- 知乎：**{status_label(zhihu['status'])}**；原生/API 路径结果 {zhihu['probe']['itemCount']} 条",
        "- 知乎 Cookie：平台未在复制的 Cookie 请求头中提供可靠到期时间，只能通过实时查询确认可用性",
    ]
    if report.get("runUrl"):
        lines.append(f"- 检查任务：{report['runUrl']}")
    if report["overall"] != "healthy":
        lines.extend(
            [
                "",
                "> 当晚的数据刷新仍会继续，并自动使用公开搜索兜底；已有有效攻略不会因一次空结果被清空。",
                "",
                "### 需要处理",
                "",
                "1. 小红书显示异常时，在本机重新扫码登录并更新仓库 Secret `LAST30DAYS_XHS_COOKIES_B64`。",
                "2. 知乎显示异常时，重新复制已登录浏览器的 Cookie，并更新仓库 Secret `ZHIHU_COOKIE`。",
                "3. 不要把 Cookie 或密钥粘贴到 Issue、聊天或代码中。",
                "4. 更新后手动运行 `Refresh travel data`；预检恢复时本 Issue 会自动关闭。",
            ]
        )
    return "\n".join(lines) + "\n"


def write_github_outputs(report: dict[str, Any]) -> None:
    output_path = os.environ.get("GITHUB_OUTPUT")
    if not output_path:
        return
    values = {
        "overall": report["overall"],
        "xiaohongshu": report["sources"]["xiaohongshu"]["status"],
        "zhihu": report["sources"]["zhihu"]["status"],
    }
    with Path(output_path).open("a", encoding="utf-8") as handle:
        for key, value in values.items():
            handle.write(f"{key}={value}\n")


def main() -> int:
    args = parse_args()
    skill_dir = discover_skill_dir(args.skill_dir)
    skill_script = skill_dir / "scripts" / "last30days.py"
    attempts: list[dict[str, Any]] = []
    probe_failures: list[str] = []

    for index, topic in enumerate(PROBE_TOPICS[: args.attempts]):
        try:
            attempts.append(run_probe(skill_script, topic, args.timeout))
        except (OSError, subprocess.SubprocessError, ValueError) as error:
            probe_failures.append(f"{type(error).__name__}: {error}")
        both_native = (
            source_result(attempts, "xiaohongshu")["nativePathUsable"]
            and source_result(attempts, "zhihu")["nativePathUsable"]
        )
        if both_native:
            break
        if index < args.attempts - 1 and args.pause > 0:
            time.sleep(args.pause)

    xhs_probe = source_result(attempts, "xiaohongshu")
    zhihu_probe = source_result(attempts, "zhihu")
    xhs_cookie = xhs_cookie_health()
    zhihu_cookie_configured = bool(load_optional_config_value("ZHIHU_COOKIE"))

    xhs_cookie_usable = xhs_cookie["structuralStatus"] in {
        "present",
        "present-session-cookie",
        "expiring-soon",
    }
    if xhs_probe["nativePathUsable"] and xhs_cookie["structuralStatus"] == "expiring-soon":
        xhs_status = "expiring"
    elif xhs_probe["nativePathUsable"] and xhs_cookie_usable:
        xhs_status = "healthy"
    elif not xhs_cookie["configured"]:
        xhs_status = "missing"
    elif attempts:
        xhs_status = "degraded"
    else:
        xhs_status = "unknown"

    if zhihu_probe["nativePathUsable"] and zhihu_cookie_configured:
        zhihu_status = "healthy"
    elif not zhihu_cookie_configured:
        zhihu_status = "missing"
    elif attempts:
        zhihu_status = "degraded"
    else:
        zhihu_status = "unknown"

    overall = (
        "healthy"
        if xhs_status == "healthy" and zhihu_status == "healthy"
        else "attention"
    )
    server = os.environ.get("GITHUB_SERVER_URL", "https://github.com")
    repository = os.environ.get("GITHUB_REPOSITORY", "")
    run_id = os.environ.get("GITHUB_RUN_ID", "")
    run_url = f"{server}/{repository}/actions/runs/{run_id}" if repository and run_id else ""
    report = {
        "schemaVersion": 1,
        "checkedAt": datetime.now(timezone.utc).isoformat(),
        "overall": overall,
        "skill": {"name": SKILL_NAME, "path": str(skill_dir)},
        "runUrl": run_url,
        "probeFailures": probe_failures,
        "sources": {
            "xiaohongshu": {
                "status": xhs_status,
                "cookie": xhs_cookie,
                "probe": xhs_probe,
            },
            "zhihu": {
                "status": zhihu_status,
                "cookieConfigured": zhihu_cookie_configured,
                "cookieExpiryKnown": False,
                "probe": zhihu_probe,
            },
        },
    }

    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    if args.summary:
        args.summary.parent.mkdir(parents=True, exist_ok=True)
        with args.summary.open("a", encoding="utf-8") as handle:
            handle.write(build_markdown(report))
    if args.issue_body:
        args.issue_body.parent.mkdir(parents=True, exist_ok=True)
        args.issue_body.write_text(build_markdown(report, issue=True), encoding="utf-8")
    write_github_outputs(report)
    print(
        json.dumps(
            {
                "overall": overall,
                "xiaohongshu": xhs_status,
                "zhihu": zhihu_status,
                "probeFailures": probe_failures,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
