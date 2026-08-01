#!/usr/bin/env python3
"""Shared weekly-refresh and retention policy for Douyin travel evidence.

Collection remains the responsibility of the official last30days-cn skill.
This module only decides whether a query may include Douyin, preserves the
latest successful Douyin evidence on other days, and records honest freshness
metadata for the static site and the workflow health check.
"""

from __future__ import annotations

import copy
import os
from collections.abc import Iterable, Mapping
from typing import Any


DOUYIN_REFRESH_ENV = "TRAVEL_DOUYIN_REFRESH"
DOUYIN_SCHEDULE = "每周一 09:00 Asia/Shanghai"
DOUYIN_POLICY = "weekly-monday"


def env_flag(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def douyin_refresh_requested(env: Mapping[str, str] | None = None) -> bool:
    source = os.environ if env is None else env
    return env_flag(source.get(DOUYIN_REFRESH_ENV))


def query_sources(
    sources: str,
    *,
    representative: bool,
    refresh_requested: bool,
) -> str:
    """Include Douyin only for the file's representative weekly query."""
    values = [source.strip() for source in sources.split(",") if source.strip()]
    if representative and refresh_requested:
        return ",".join(values)
    return ",".join(source for source in values if source != "douyin")


def is_douyin_evidence(value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    platform = str(value.get("platform") or "").lower()
    url = str(value.get("url") or "")
    return platform == "douyin" and "douyin.com/video/" in url


def douyin_urls(value: Any, *, state: str | None = None) -> set[str]:
    matches: set[str] = set()
    if isinstance(value, dict):
        if is_douyin_evidence(value):
            item_state = str(value.get("douyinState") or "")
            if state is None or item_state == state:
                matches.add(str(value["url"]))
        for child in value.values():
            matches.update(douyin_urls(child, state=state))
    elif isinstance(value, list):
        for child in value:
            matches.update(douyin_urls(child, state=state))
    return matches


def evidence_platforms(value: Any) -> set[str]:
    platforms: set[str] = set()
    if isinstance(value, dict):
        platform = value.get("platform")
        url = value.get("url")
        if isinstance(platform, str) and isinstance(url, str) and url:
            platforms.add(platform)
        for child in value.values():
            platforms.update(evidence_platforms(child))
    elif isinstance(value, list):
        for child in value:
            platforms.update(evidence_platforms(child))
    return platforms


def _contains_douyin(value: Any) -> bool:
    return bool(douyin_urls(value))


def _looks_like_evidence_list(current: list[Any], previous: list[Any]) -> bool:
    return any(
        isinstance(item, dict) and "platform" in item and "url" in item
        for item in (*current, *previous)
    )


def _container_identity(value: Any) -> tuple[str, str] | None:
    if not isinstance(value, dict):
        return None
    for key in ("key", "name", "code"):
        candidate = value.get(key)
        if isinstance(candidate, (str, int)) and str(candidate):
            return key, str(candidate)
    return None


def _retained_item(item: dict[str, Any], prior_success_at: str | None) -> dict[str, Any]:
    retained = copy.deepcopy(item)
    retained["douyinState"] = "retained"
    retained["douyinLastSuccessfulAt"] = (
        retained.get("douyinLastSuccessfulAt") or prior_success_at
    )
    return retained


def _fresh_or_retained_item(
    item: dict[str, Any],
    *,
    refresh_requested: bool,
    fresh_urls: set[str],
    checked_at: str,
    prior_success_at: str | None,
) -> dict[str, Any]:
    url = str(item.get("url") or "")
    if refresh_requested and url in fresh_urls:
        fresh = copy.deepcopy(item)
        fresh["douyinState"] = "fresh"
        fresh["douyinLastSuccessfulAt"] = checked_at
        return fresh
    return _retained_item(item, prior_success_at)


def _dedupe_evidence(items: list[Any]) -> list[Any]:
    result: list[Any] = []
    seen_urls: set[str] = set()
    for item in items:
        if isinstance(item, dict):
            url = str(item.get("url") or "")
            if url:
                if url in seen_urls:
                    continue
                seen_urls.add(url)
        result.append(item)
    return result


def _merge_evidence_list(
    current: list[Any],
    previous: list[Any],
    *,
    refresh_requested: bool,
    fresh_urls: set[str],
    checked_at: str,
    prior_success_at: str | None,
) -> list[Any]:
    current_douyin = [item for item in current if is_douyin_evidence(item)]
    merged: list[Any] = []
    for item in current:
        if is_douyin_evidence(item):
            merged.append(
                _fresh_or_retained_item(
                    item,
                    refresh_requested=refresh_requested,
                    fresh_urls=fresh_urls,
                    checked_at=checked_at,
                    prior_success_at=prior_success_at,
                )
            )
        else:
            merged.append(copy.deepcopy(item))

    if not current_douyin:
        merged.extend(
            _retained_item(item, prior_success_at)
            for item in previous
            if is_douyin_evidence(item)
        )
    return _dedupe_evidence(merged)


def _mark_retained_tree(value: Any, prior_success_at: str | None) -> Any:
    if is_douyin_evidence(value):
        return _retained_item(value, prior_success_at)
    if isinstance(value, dict):
        return {
            key: _mark_retained_tree(child, prior_success_at)
            for key, child in value.items()
        }
    if isinstance(value, list):
        return [_mark_retained_tree(child, prior_success_at) for child in value]
    return copy.deepcopy(value)


def _merge_node(
    current: Any,
    previous: Any,
    *,
    refresh_requested: bool,
    fresh_urls: set[str],
    checked_at: str,
    prior_success_at: str | None,
) -> Any:
    if isinstance(current, dict):
        prior_dict = previous if isinstance(previous, dict) else {}
        merged = {
            key: _merge_node(
                child,
                prior_dict.get(key),
                refresh_requested=refresh_requested,
                fresh_urls=fresh_urls,
                checked_at=checked_at,
                prior_success_at=prior_success_at,
            )
            for key, child in current.items()
        }
        for key, child in prior_dict.items():
            if key not in merged and _contains_douyin(child):
                merged[key] = _mark_retained_tree(child, prior_success_at)
        evidence = merged.get("evidence")
        if isinstance(evidence, list) and isinstance(merged.get("evidenceCount"), int):
            merged["evidenceCount"] = len(evidence)
        if (
            isinstance(evidence, list)
            and evidence
            and merged.get("sourceStatus") in {"fallback", "stale"}
            and any(is_douyin_evidence(item) for item in evidence)
        ):
            merged["sourceStatus"] = "retained"
        return merged

    if isinstance(current, list):
        prior_list = previous if isinstance(previous, list) else []
        if _looks_like_evidence_list(current, prior_list):
            return _merge_evidence_list(
                current,
                prior_list,
                refresh_requested=refresh_requested,
                fresh_urls=fresh_urls,
                checked_at=checked_at,
                prior_success_at=prior_success_at,
            )

        prior_by_identity = {
            identity: item
            for item in prior_list
            if (identity := _container_identity(item)) is not None
        }
        matched: set[tuple[str, str]] = set()
        merged_items: list[Any] = []
        for index, item in enumerate(current):
            identity = _container_identity(item)
            if identity is not None and identity in prior_by_identity:
                prior_item = prior_by_identity[identity]
                matched.add(identity)
            elif index < len(prior_list):
                prior_item = prior_list[index]
            else:
                prior_item = None
            merged_items.append(
                _merge_node(
                    item,
                    prior_item,
                    refresh_requested=refresh_requested,
                    fresh_urls=fresh_urls,
                    checked_at=checked_at,
                    prior_success_at=prior_success_at,
                )
            )

        for item in prior_list:
            identity = _container_identity(item)
            if identity is not None and identity in matched:
                continue
            if _contains_douyin(item):
                merged_items.append(_mark_retained_tree(item, prior_success_at))
        return merged_items

    return copy.deepcopy(current)


def _latest_timestamp(values: Iterable[Any]) -> str | None:
    candidates = sorted(
        str(value)
        for value in values
        if isinstance(value, str) and value.strip()
    )
    return candidates[-1] if candidates else None


def _prior_success_at(previous: dict[str, Any]) -> str | None:
    metadata = previous.get("douyin") if isinstance(previous.get("douyin"), dict) else {}
    item_dates: list[str] = []

    def collect(value: Any) -> None:
        if isinstance(value, dict):
            if is_douyin_evidence(value):
                item_date = value.get("douyinLastSuccessfulAt")
                if isinstance(item_date, str):
                    item_dates.append(item_date)
            for child in value.values():
                collect(child)
        elif isinstance(value, list):
            for child in value:
                collect(child)

    collect(previous)
    explicit = metadata.get("lastSuccessfulAt")
    inferred = previous.get("generatedAt") if douyin_urls(previous) else None
    return _latest_timestamp([explicit, inferred, *item_dates])


def merge_douyin_snapshot(
    snapshot: dict[str, Any],
    previous: dict[str, Any] | None,
    *,
    refresh_requested: bool,
    checked_at: str,
    fresh_urls: Iterable[str],
) -> dict[str, Any]:
    """Merge source-specific evidence and attach file-level policy metadata."""
    previous = previous if isinstance(previous, dict) else {}
    fresh_url_set = {str(url) for url in fresh_urls if str(url)}
    prior_success_at = _prior_success_at(previous)
    previous_metadata = (
        previous.get("douyin") if isinstance(previous.get("douyin"), dict) else {}
    )

    merged = _merge_node(
        snapshot,
        previous,
        refresh_requested=refresh_requested,
        fresh_urls=fresh_url_set,
        checked_at=checked_at,
        prior_success_at=prior_success_at,
    )
    snapshot.clear()
    snapshot.update(merged)

    fresh_present = douyin_urls(snapshot, state="fresh")
    retained_present = douyin_urls(snapshot, state="retained") - fresh_present
    all_present = fresh_present | retained_present
    last_successful_at = checked_at if fresh_present else prior_success_at
    prior_attempt = previous_metadata.get("lastAttemptAt") or prior_success_at
    last_attempt_at = checked_at if refresh_requested else prior_attempt
    if fresh_present:
        refresh_status = "fresh"
    elif all_present:
        refresh_status = "retained-after-empty" if refresh_requested else "retained"
    else:
        refresh_status = "unavailable" if refresh_requested else "not-collected"

    metadata = {
        "schemaVersion": 1,
        "policy": DOUYIN_POLICY,
        "schedule": DOUYIN_SCHEDULE,
        "refreshRequested": refresh_requested,
        "refreshStatus": refresh_status,
        "lastAttemptAt": last_attempt_at,
        "lastSuccessfulAt": last_successful_at,
        "evidenceCount": len(all_present),
        "freshEvidenceCount": len(fresh_present),
        "retainedEvidenceCount": len(retained_present),
    }
    snapshot["douyin"] = metadata
    return metadata
