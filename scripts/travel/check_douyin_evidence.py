#!/usr/bin/env python3
"""Report whether the latest travel snapshots contain usable Douyin evidence.

This helper never visits the web. Collection remains the responsibility of the
official last30days-cn skill; this script only verifies its generated JSON so a
scheduled workflow can request a new browser verification when Douyin returns
an empty result after a CAPTCHA or risk-control challenge.
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_SNAPSHOTS = (
    Path("src/data/travel/snapshot.json"),
    Path("src/data/travel/transport.json"),
    Path("src/data/travel/preparations.json"),
    Path("src/data/travel/reservations.json"),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check generated Douyin evidence")
    parser.add_argument("--summary", type=Path, help="Append a Markdown summary")
    parser.add_argument("--issue-body", type=Path, help="Write a safe issue body")
    parser.add_argument("snapshots", nargs="*", type=Path, default=DEFAULT_SNAPSHOTS)
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def valid_douyin_items(value: Any) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    if isinstance(value, dict):
        platform = str(value.get("platform") or "").lower()
        url = str(value.get("url") or "")
        if platform == "douyin" and "douyin.com/video/" in url:
            matches.append(value)
        for child in value.values():
            matches.extend(valid_douyin_items(child))
    elif isinstance(value, list):
        for child in value:
            matches.extend(valid_douyin_items(child))
    return matches


def build_report(paths: list[Path]) -> dict[str, Any]:
    files: list[dict[str, Any]] = []
    seen_urls: set[str] = set()
    for path in paths:
        payload = load_json(path)
        items = valid_douyin_items(payload)
        urls = {
            str(item.get("url"))
            for item in items
            if isinstance(item.get("url"), str) and item.get("url")
        }
        seen_urls.update(urls)
        files.append(
            {
                "path": path.as_posix(),
                "generatedAt": payload.get("generatedAt"),
                "evidenceCount": len(urls),
            }
        )

    files_with_evidence = sum(1 for item in files if item["evidenceCount"] > 0)
    status = "healthy" if seen_urls and files_with_evidence >= 2 else "attention"
    return {
        "schemaVersion": 1,
        "checkedAt": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "evidenceCount": len(seen_urls),
        "filesWithEvidence": files_with_evidence,
        "files": files,
    }


def markdown(report: dict[str, Any], *, issue: bool = False) -> str:
    label = "正常" if report["status"] == "healthy" else "需要验证"
    heading = "# 抖音旅游数据需要验证" if issue else "## 抖音旅游数据刷新检查"
    lines = [
        heading,
        "",
        f"- 检查时间：{report['checkedAt']}",
        f"- 状态：**{label}**",
        f"- 有效抖音链接：{report['evidenceCount']} 条",
        f"- 含抖音依据的数据文件：{report['filesWithEvidence']} / {len(report['files'])}",
    ]
    if report["status"] != "healthy":
        lines.extend(
            [
                "",
                "> 抖音不强制登录，但无 API 浏览器路径可能遇到验证码或风控页。其他来源仍会正常刷新，已有静态行程不会被清空。",
                "",
                "### 需要处理",
                "",
                "1. 在本机通过 last30days-cn 的 Playwright 窗口完成抖音验证；若页面要求登录，再扫码登录。",
                "2. 将浏览器 Cookie 加密更新到仓库 Secret `LAST30DAYS_DOUYIN_COOKIES_B64`。",
                "3. 不要把 Cookie 粘贴到 Issue、聊天或代码中。",
                "4. 手动运行 `Refresh travel data`，成功后本 Issue 会自动关闭。",
            ]
        )
    return "\n".join(lines) + "\n"


def write_outputs(report: dict[str, Any]) -> None:
    output_path = os.environ.get("GITHUB_OUTPUT")
    if not output_path:
        return
    with Path(output_path).open("a", encoding="utf-8") as handle:
        handle.write(f"overall={report['status']}\n")
        handle.write(f"evidence_count={report['evidenceCount']}\n")


def main() -> int:
    args = parse_args()
    report = build_report(list(args.snapshots))
    if args.summary:
        args.summary.parent.mkdir(parents=True, exist_ok=True)
        with args.summary.open("a", encoding="utf-8") as handle:
            handle.write(markdown(report))
    if args.issue_body:
        args.issue_body.parent.mkdir(parents=True, exist_ok=True)
        args.issue_body.write_text(markdown(report, issue=True), encoding="utf-8")
    write_outputs(report)
    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
