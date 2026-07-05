"""Tests for cold-start tier detection and graceful fingerprint degradation."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from memory_shield.cold_start import (
    TIER_EMPTY,
    TIER_ESTABLISHED,
    TIER_WARMING,
    classify_tier,
    filter_patterns,
    genre_summary_for_tier,
    needs_declared_niche,
    patterns_enabled,
)
from memory_shield.fingerprint import build_fingerprint


def _mock_corpus(live: list[dict], handle: str = "@newcreator") -> dict:
    return {
        "creator": {"handle": handle, "title": "New Creator", "subscribers": 1200},
        "holdout_cutoff": "2026-04-01",
        "live": live,
        "holdout": [],
        "competitors": {
            "@comp1": [
                {
                    "video_id": "c1",
                    "title": "Slow living morning routine",
                    "views": 50000,
                    "published": "2026-01-15",
                    "topics": ["slow living", "morning routine"],
                    "format": "vlog",
                }
            ],
        },
        "trends": {},
    }


def _video(i: int) -> dict:
    return {
        "video_id": f"v{i}",
        "title": f"Personal essay {i}",
        "published": f"2026-0{(i % 3) + 1}-15",
        "views": 1000 * i,
        "topics": ["self improvement", "personal essay"],
        "format": "personal-essay",
    }


class TestColdStartTiers(unittest.TestCase):
    def test_classify_tiers(self):
        self.assertEqual(classify_tier(0), TIER_EMPTY)
        self.assertEqual(classify_tier(3), TIER_WARMING)
        self.assertEqual(classify_tier(9), TIER_WARMING)
        self.assertEqual(classify_tier(10), TIER_ESTABLISHED)
        self.assertEqual(classify_tier(80), TIER_ESTABLISHED)

    def test_patterns_gated_for_thin_catalog(self):
        sample = [
            {
                "kind": "Hook",
                "label": "question (2.1× CTR, n=5)",
                "confidence": "validated",
                "support_n": 5,
            }
        ]
        self.assertEqual(filter_patterns(sample, TIER_EMPTY), [])
        self.assertEqual(filter_patterns(sample, TIER_WARMING), [])
        self.assertEqual(filter_patterns(sample, TIER_ESTABLISHED), sample)
        self.assertFalse(patterns_enabled(TIER_WARMING))
        self.assertTrue(patterns_enabled(TIER_ESTABLISHED))

    def test_needs_declared_niche_only_for_empty(self):
        self.assertTrue(needs_declared_niche(TIER_EMPTY, ""))
        self.assertFalse(needs_declared_niche(TIER_EMPTY, "slow living vlogs"))
        self.assertFalse(needs_declared_niche(TIER_WARMING, ""))


class TestFingerprintColdStart(unittest.TestCase):
    @patch("memory_shield.fingerprint.get_preferences")
    @patch("memory_shield.fingerprint.load_analytics")
    @patch("memory_shield.fingerprint._persist_fingerprint")
    def test_zero_videos_honest_summary(self, _persist, _analytics, prefs):
        _analytics.return_value = {"per_video": {}, "baselines": {}}
        prefs.return_value = {"declared_niche": "mindful productivity for students"}

        fp = build_fingerprint(
            _mock_corpus([]),
            declared_niche="mindful productivity for students",
            tier=TIER_EMPTY,
            uid="test-empty",
        )

        summary = fp["genre"]["summary"]
        self.assertIn("don't have any of your videos", summary.lower())
        self.assertNotIn("last 40 videos", summary.lower())
        self.assertNotIn("2.1×", summary)
        self.assertEqual(fp["cold_start"]["tier"], TIER_EMPTY)
        self.assertFalse(fp["cold_start"]["patterns_enabled"])

    @patch("memory_shield.fingerprint.get_preferences")
    @patch("memory_shield.fingerprint.load_analytics")
    @patch("memory_shield.fingerprint._persist_fingerprint")
    def test_three_videos_warming_summary(self, _persist, _analytics, prefs):
        _analytics.return_value = {"per_video": {}, "baselines": {}}
        prefs.return_value = {"declared_niche": ""}

        live = [_video(1), _video(2), _video(3)]
        fp = build_fingerprint(_mock_corpus(live), tier=TIER_WARMING, uid="test-warming")

        summary = fp["genre"]["summary"]
        self.assertIn("don't have enough", summary.lower())
        self.assertIn("3 video", summary.lower())
        self.assertNotIn("last 40 videos", summary.lower())
        self.assertNotIn("vulnerable personal essays convert best", summary)
        self.assertEqual(fp["cold_start"]["tier"], TIER_WARMING)
        self.assertFalse(fp["cold_start"]["patterns_enabled"])

    @patch("memory_shield.fingerprint.get_preferences")
    @patch("memory_shield.fingerprint.load_analytics")
    @patch("memory_shield.fingerprint._persist_fingerprint")
    def test_established_unchanged_tone(self, _persist, _analytics, prefs):
        _analytics.return_value = {"per_video": {}, "baselines": {}}
        prefs.return_value = {"declared_niche": ""}

        live = [_video(i) for i in range(1, 12)]
        fp = build_fingerprint(_mock_corpus(live), tier=TIER_ESTABLISHED, uid="test-full")

        summary = fp["genre"]["summary"]
        self.assertIn("Your last 11 videos", summary)
        self.assertTrue(fp["cold_start"]["patterns_enabled"])


if __name__ == "__main__":
    unittest.main()
