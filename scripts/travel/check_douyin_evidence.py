#!/usr/bin/env python3
"""Report whether the weekly run obtained newly refreshed Douyin evidence.

This helper never visits the web. Collection remains the responsibility of the
official last30days-cn skill. Retained links keep the website useful between
weekly runs, but they never count as a successful new collection attempt.
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
    all_urls: set[str] = set()
    fresh_urls: set[str] = set()
    retained_urls: set[str] = set()
    for path in paths:
        payload = load_json(path)
        items = valid_douyin_items(payload)
        urls = {
            str(item.get("url"))
            for item in items
            if isinstance(item.get("url"), str) and item.get("url")
        }
        metadata = payload.get("douyin") if isinstance(payload.get("douyin"), dict) else {}
        file_fresh_urls = {
            str(item.get("url"))
            for item in items
            if item.get("douyinState") == "fresh"
            and metadata.get("refreshRequested") is True
            and metadata.get("refreshStatus") == "fresh"
        }
        file_retained_urls = urls - file_fresh_urls
        all_urls.update(urls)
        fresh_urls.update(file_fresh_urls)
        retained_urls.update(file_retained_urls)
        files.append(
            {
                "path": path.as_posix(),
                "generatedAt": payload.get("generatedAt"),
                "evidenceCount": len(urls),
                "freshEvidenceCount": len(file_fresh_urls),
                "retainedEvidenceCount": len(file_retained_urls),
                "refreshStatus": metadata.get("refreshStatus"),
                "lastSuccessfulAt": metadata.get("lastSuccessfulAt"),
            }
        )

    files_with_evidence = sum(1 for item in files if item["evidenceCount"] > 0)
    files_with_fresh_evidence = sum(
        1 for item in files if item["freshEvidenceCount"] > 0
    )
    status = "healthy" if files_with_fresh_evidence >= 2 else "attention"
    return {
        "schemaVersion": 2,
        "checkedAt": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "evidenceCount": len(all_urls),
        "freshEvidenceCount": len(fresh_urls),
        "retainedEvidenceCount": len(retained_urls - fresh_urls),
        "filesWithEvidence": files_with_evidence,
        "filesWithFreshEvidence": files_with_fresh_evidence,
        "files": files,
    }


def markdown(report: dict[str, Any], *, issue: bool = False) -> str:
    label = "本周刷新成功" if report["status"] == "healthy" else "本周需要验证"
    heading = "# 抖音旅游数据需要验证" if issue else "## 抖音每周刷新检查"
    lines = [
        heading,
        "",
        f"- 检查时间：{report['checkedAt']}",
        f"- 状态：**{label}**",
        f"- 本轮新取得抖音链接：{report['freshEvidenceCount']} 条",
        f"- 本轮取得新依据的数据文件：{report['filesWithFreshEvidence']} / {len(report['files'])}",
        f"- 仍保留的历史抖音链接：{report['retainedEvidenceCount']} 条",
    ]
    if report["status"] != "healthy":
        lines.extend(
            [
                "",
                "> 抖音只在每周一 09:00 尝试刷新。无 API 浏览器路径可能遇到验证码或风控页；其他来源仍会每日更新，最近一次成功的抖音依据会保留并显示真实日期。",
                "",
                "### 需要处理",
                "",
                "1. 在本机通过 last30days-cn 的 Playwright 窗口完成抖音验证；若页面要求登录，再扫码登录。",
                "2. 将浏览器 Cookie 加密更新到仓库 Secret `LAST30DAYS_DOUYIN_COOKIES_B64`。",
                "3. 不要把 Cookie 粘贴到 Issue、聊天或代码中。",
                "4. 更新后可以自行关闭本 Issue；系统会在下周一重新核验。若要提前核验，手动运行工作流时需勾选“同时刷新抖音”。",
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
        handle.write(f"fresh_evidence_count={report['freshEvidenceCount']}\n")


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
