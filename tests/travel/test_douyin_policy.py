from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "travel"))

from check_douyin_evidence import build_report  # noqa: E402
from douyin_policy import merge_douyin_snapshot, query_sources  # noqa: E402


def douyin(url: str) -> dict[str, str]:
    return {"platform": "douyin", "title": "攻略", "url": url}


class DouyinPolicyTests(unittest.TestCase):
    def test_nonweekly_refresh_excludes_douyin_and_retains_prior_source(self) -> None:
        current = {
            "generatedAt": "2026-08-02T01:00:00+00:00",
            "attractions": {
                "lake": {
                    "evidence": [
                        {
                            "platform": "xiaohongshu",
                            "title": "新攻略",
                            "url": "https://www.xiaohongshu.com/explore/new",
                        }
                    ]
                }
            },
        }
        previous = {
            "generatedAt": "2026-07-30T05:00:00+00:00",
            "attractions": {
                "lake": {
                    "evidence": [douyin("https://www.douyin.com/video/123")]
                }
            },
        }

        metadata = merge_douyin_snapshot(
            current,
            previous,
            refresh_requested=False,
            checked_at=current["generatedAt"],
            fresh_urls=(),
        )

        evidence = current["attractions"]["lake"]["evidence"]
        retained = next(item for item in evidence if item["platform"] == "douyin")
        self.assertEqual(retained["douyinState"], "retained")
        self.assertEqual(
            retained["douyinLastSuccessfulAt"], "2026-07-30T05:00:00+00:00"
        )
        self.assertEqual(metadata["refreshStatus"], "retained")
        self.assertEqual(metadata["freshEvidenceCount"], 0)
        self.assertEqual(metadata["retainedEvidenceCount"], 1)
        self.assertNotIn(
            "douyin",
            query_sources(
                "xiaohongshu,douyin,zhihu",
                representative=True,
                refresh_requested=False,
            ).split(","),
        )

    def test_weekly_fresh_result_replaces_prior_douyin_for_that_list(self) -> None:
        fresh_url = "https://www.douyin.com/video/456"
        current = {
            "generatedAt": "2026-08-03T01:00:00+00:00",
            "evidence": [douyin(fresh_url)],
        }
        previous = {
            "generatedAt": "2026-07-30T05:00:00+00:00",
            "evidence": [douyin("https://www.douyin.com/video/old")],
        }

        metadata = merge_douyin_snapshot(
            current,
            previous,
            refresh_requested=True,
            checked_at=current["generatedAt"],
            fresh_urls=(fresh_url,),
        )

        self.assertEqual([item["url"] for item in current["evidence"]], [fresh_url])
        self.assertEqual(current["evidence"][0]["douyinState"], "fresh")
        self.assertEqual(metadata["refreshStatus"], "fresh")
        self.assertEqual(metadata["lastSuccessfulAt"], current["generatedAt"])

    def test_checker_requires_fresh_evidence_in_two_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths: list[Path] = []
            for index, state in enumerate(("fresh", "retained", "fresh", "retained")):
                path = root / f"snapshot-{index}.json"
                item = douyin(f"https://www.douyin.com/video/{index}")
                item["douyinState"] = state
                payload = {
                    "generatedAt": "2026-08-03T01:00:00+00:00",
                    "douyin": {
                        "refreshRequested": True,
                        "refreshStatus": "fresh" if state == "fresh" else "retained-after-empty",
                    },
                    "evidence": [item],
                }
                path.write_text(json.dumps(payload), encoding="utf-8")
                paths.append(path)

            report = build_report(paths)
            self.assertEqual(report["status"], "healthy")
            self.assertEqual(report["filesWithFreshEvidence"], 2)

            retained_only = json.loads(paths[2].read_text(encoding="utf-8"))
            retained_only["evidence"][0]["douyinState"] = "retained"
            retained_only["douyin"]["refreshStatus"] = "retained-after-empty"
            paths[2].write_text(json.dumps(retained_only), encoding="utf-8")
            report = build_report(paths)
            self.assertEqual(report["status"], "attention")
            self.assertEqual(report["filesWithFreshEvidence"], 1)


if __name__ == "__main__":
    unittest.main()
