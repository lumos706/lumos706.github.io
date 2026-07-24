#!/usr/bin/env python3
"""Apply a narrow Douyin compatibility shim to last30days-cn v3.2.0.

Douyin's current search page renders a skeleton when opened directly and only
loads its video grid after the populated search field submits once. The skill's
current DOM fallback also targets older card class names. This script keeps all
collection inside the officially installed skill while adapting those two
browser interactions. Anchor checks make the rewrite idempotent and fail-safe.
"""

from __future__ import annotations

from pathlib import Path

from update_travel_data import discover_skill_dir


MARKER = "LUMOS_DOUYIN_BROWSER_COMPAT_V1"

SUBMIT_BLOCK = r'''
            # LUMOS_DOUYIN_BROWSER_COMPAT_V1: submit the populated search field
            # once; direct navigation currently leaves Douyin on a skeleton.
            try:
                search_input = page.locator("input").first
                search_input.wait_for(state="visible", timeout=5000)
                page.wait_for_timeout(2500)
                search_input.press("Enter")
            except Exception:
                pass

'''

MODERN_DOM_BLOCK = r'''
            # LUMOS_DOUYIN_BROWSER_COMPAT_V1: generated card class names are
            # unstable, while canonical /video/ links remain usable.
            if not any(item.get("url") for item in items):
                items = []
                seen_links = set()
                for link_el in page.query_selector_all("a[href*='/video/']"):
                    try:
                        href = link_el.get_attribute("href") or ""
                        if href.startswith("/"):
                            href = f"https://www.douyin.com{href}"
                        if not href or href in seen_links:
                            continue

                        title = _clean_text(link_el.inner_text())
                        if len(title) < 6:
                            title = _clean_text(
                                link_el.evaluate(
                                    """element => {
                                        let node = element;
                                        for (let depth = 0; depth < 5 && node; depth += 1) {
                                            const value = (node.innerText || '').trim();
                                            if (value.length >= 8) return value;
                                            node = node.parentElement;
                                        }
                                        return '';
                                    }"""
                                )
                            )
                        if not title:
                            continue

                        seen_links.add(href)
                        items.append({
                            "text": title[:600],
                            "url": href,
                            "author_name": "",
                            "author_id": "",
                            "date": None,
                            "engagement": {
                                "views": 0,
                                "likes": 0,
                                "comments": 0,
                                "shares": 0,
                            },
                            "hashtags": [],
                            "duration": 0,
                            "source": "crawler-dom-compatible",
                        })
                        if len(items) >= limit:
                            break
                    except Exception:
                        continue

'''


def patch_bridge(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    if MARKER in text:
        return "already-patched"

    start = text.find("def crawl_douyin(")
    end = text.find("\ndef crawl_bilibili(", start)
    if start < 0 or end < 0:
        raise RuntimeError(f"Douyin bridge function was not found in {path}")

    function = text[start:end]
    wait_anchor = "            for _ in range(5):\n"
    if function.count(wait_anchor) != 1:
        raise RuntimeError(f"Expected Douyin wait loop was not found exactly once in {path}")
    function = function.replace(
        wait_anchor,
        SUBMIT_BLOCK + "            for _ in range(12):\n",
        1,
    )

    outer_except = function.rfind("\n    except Exception as e:")
    if outer_except < 0:
        raise RuntimeError(f"Expected Douyin exception handler was not found in {path}")
    function = function[:outer_except] + MODERN_DOM_BLOCK + function[outer_except:]

    path.write_text(text[:start] + function + text[end:], encoding="utf-8")
    return "patched"


def main() -> int:
    skill_dir = discover_skill_dir(None)
    candidates = (
        skill_dir / "scripts" / "lib" / "crawler_bridge.py",
        skill_dir / "skills" / "last30days" / "scripts" / "lib" / "crawler_bridge.py",
    )
    existing = tuple(dict.fromkeys(path.resolve() for path in candidates if path.is_file()))
    if not existing:
        raise FileNotFoundError(f"No crawler_bridge.py found below {skill_dir}")

    for path in existing:
        print(f"{patch_bridge(path)}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
