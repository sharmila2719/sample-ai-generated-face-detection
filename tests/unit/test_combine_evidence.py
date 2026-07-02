"""Unit tests for combine_evidence classification logic."""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch


def _make_vision_result(score: float) -> dict:
    return {
        "probability_score": score,
        "classification": "NATURAL" if score < 0.40 else ("AI_GENERATED" if score > 0.65 else "UNCERTAIN"),
        "rationale": f"score={score}",
        "regions": [],
        "model_id": "test-model",
    }


@patch("src.agent.tools.combine_evidence.dynamodb")
@patch("src.agent.tools.combine_evidence.publish_alert")
class TestCombineEvidence:
    """Tests for the combine_evidence tool."""

    def test_natural_classification_low_score(self, mock_alert, mock_ddb):
        """Score below 0.40 → NATURAL."""
        mock_ddb.return_value.put_item.return_value = {}
        from src.agent.tools.combine_evidence import combine_evidence

        result = combine_evidence(
            image_id="img-1",
            tenant_id="test",
            request_id="req-1",
            nova=_make_vision_result(0.10),
            pixel={"probability_score": 0.12, "classification": "NATURAL", "model_id": "sm"},
        )
        assert result["classification"] == "NATURAL"
        assert result["probability_score"] < 0.40

    def test_ai_generated_classification_high_score(self, mock_alert, mock_ddb):
        """Score above 0.65 → AI_GENERATED."""
        mock_ddb.return_value.put_item.return_value = {}
        from src.agent.tools.combine_evidence import combine_evidence

        result = combine_evidence(
            image_id="img-2",
            tenant_id="test",
            request_id="req-2",
            nova=_make_vision_result(0.90),
            pixel={"probability_score": 0.88, "classification": "AI_GENERATED", "model_id": "sm"},
        )
        assert result["classification"] == "AI_GENERATED"
        assert result["probability_score"] > 0.65

    def test_uncertain_band(self, mock_alert, mock_ddb):
        """Score in [0.40, 0.65] → UNCERTAIN."""
        mock_ddb.return_value.put_item.return_value = {}
        from src.agent.tools.combine_evidence import combine_evidence

        result = combine_evidence(
            image_id="img-3",
            tenant_id="test",
            request_id="req-3",
            nova=_make_vision_result(0.52),
        )
        assert result["classification"] == "UNCERTAIN"

    def test_probability_score_clamped(self, mock_alert, mock_ddb):
        """probability_score is always in [0, 1]."""
        mock_ddb.return_value.put_item.return_value = {}
        from src.agent.tools.combine_evidence import combine_evidence

        result = combine_evidence(
            image_id="img-4",
            tenant_id="test",
            request_id="req-4",
            nova=_make_vision_result(0.0),
        )
        assert 0.0 <= result["probability_score"] <= 1.0

    def test_exif_short_circuit_sets_natural(self, mock_alert, mock_ddb):
        """Recent EXIF without deep_analysis → NATURAL."""
        mock_ddb.return_value.put_item.return_value = {}
        from src.agent.tools.combine_evidence import combine_evidence

        exif = {
            "is_recent_exif": True,
            "make": "Apple",
            "model": "iPhone 15",
            "software": None,
            "gps_present": True,
            "datetime_original": "2025-01-01T10:00:00+00:00",
        }
        result = combine_evidence(
            image_id="img-5",
            tenant_id="test",
            request_id="req-5",
            exif=exif,
            deep_analysis=False,
        )
        assert result["classification"] == "NATURAL"

    def test_face_forensics_elevates_to_composite(self, mock_alert, mock_ddb):
        """Face-forensics ≥ 0.85 on a real image → composite AI-face result."""
        mock_ddb.return_value.put_item.return_value = {}
        from src.agent.tools.combine_evidence import combine_evidence

        result = combine_evidence(
            image_id="img-6",
            tenant_id="test",
            request_id="req-6",
            nova=_make_vision_result(0.10),   # vision says real
            pixel={"probability_score": 0.10, "classification": "NATURAL", "model_id": "sm"},
            face_forensics={
                "has_faces": True,
                "face_count": 1,
                "max_face_probability": 0.92,
                "faces": [],
            },
        )
        assert result["composite_signal"]["has_ai_face_with_real_context"] is True

    def test_celebrities_pass_through(self, mock_alert, mock_ddb):
        """Celebrity list is included in the result."""
        mock_ddb.return_value.put_item.return_value = {}
        from src.agent.tools.combine_evidence import combine_evidence

        result = combine_evidence(
            image_id="img-7",
            tenant_id="test",
            request_id="req-7",
            celebrities=[{"name": "Alice", "confidence": 92.0, "urls": []}],
        )
        assert len(result["celebrities"]) == 1
        assert result["celebrities"][0]["name"] == "Alice"
