"""Unit tests for the InlineAgentOrchestrator."""

from __future__ import annotations

import base64
from unittest.mock import MagicMock, patch


def _dummy_b64() -> str:
    return base64.b64encode(b"fake-image-bytes").decode("ascii")


def _natural_result(score: float = 0.05) -> dict:
    return {"probability_score": score, "classification": "NATURAL", "rationale": "ok", "regions": [], "model_id": "test"}


def _error_result() -> dict:
    return {"tool_name": "test", "duration_ms": 0, "error_code": "TOOL_EXCEPTION", "error_message": "fail"}


class TestInlineOrchestratorShortCircuits:

    @patch("src.agent.inline_orchestrator.combine_evidence")
    @patch("src.agent.inline_orchestrator.rekognition_celebrities")
    @patch("src.agent.inline_orchestrator.exif_check")
    def test_exif_short_circuit(self, mock_exif, mock_celeb, mock_combine):
        """Recent EXIF should short-circuit the cascade."""
        from src.agent.inline_orchestrator import InlineAgentOrchestrator

        mock_celeb.return_value = {"celebrities": []}
        mock_exif.return_value = {"is_recent_exif": True, "make": "Sony", "model": "A7IV"}
        mock_combine.return_value = {
            "classification": "NATURAL", "probability_score": 0.05,
            "evidence": [], "signals_consulted": [], "reasoning": "",
            "model_ids_used": [], "composite_analysis": {}, "composite_signal": {}, "celebrities": [],
        }

        orch = InlineAgentOrchestrator()
        result = orch.invoke(
            {"image_bytes_b64": _dummy_b64(), "tenant_id": "t1", "image_id": "i1",
             "deep_analysis": False, "fast_mode": False, "force_fresh": False},
            request_id="r1",
        )
        assert result["classification"] == "NATURAL"
        mock_combine.assert_called_once()

    @patch("src.agent.inline_orchestrator.combine_evidence")
    @patch("src.agent.inline_orchestrator.sagemaker_pixel_check")
    @patch("src.agent.inline_orchestrator.rekognition_celebrities")
    @patch("src.agent.inline_orchestrator.exif_check")
    def test_pixel_short_circuit_natural(self, mock_exif, mock_celeb, mock_pixel, mock_combine):
        """Pixel score < 0.15 → short circuit to NATURAL."""
        from src.agent.inline_orchestrator import InlineAgentOrchestrator

        mock_celeb.return_value = {"celebrities": []}
        mock_exif.return_value = {"is_recent_exif": False}
        mock_pixel.return_value = {"probability_score": 0.05, "classification": "NATURAL", "model_id": "sm"}
        mock_combine.return_value = {
            "classification": "NATURAL", "probability_score": 0.05,
            "evidence": [], "signals_consulted": [], "reasoning": "",
            "model_ids_used": [], "composite_analysis": {}, "composite_signal": {}, "celebrities": [],
        }

        orch = InlineAgentOrchestrator()
        result = orch.invoke(
            {"image_bytes_b64": _dummy_b64(), "tenant_id": "t1", "image_id": "i2",
             "deep_analysis": False, "fast_mode": False, "force_fresh": False},
            request_id="r2",
        )
        assert result["classification"] == "NATURAL"

    @patch("src.agent.inline_orchestrator.combine_evidence")
    @patch("src.agent.inline_orchestrator.sagemaker_pixel_check")
    @patch("src.agent.inline_orchestrator.rekognition_celebrities")
    @patch("src.agent.inline_orchestrator.exif_check")
    def test_pixel_short_circuit_ai(self, mock_exif, mock_celeb, mock_pixel, mock_combine):
        """Pixel score > 0.85 → short circuit to AI_GENERATED."""
        from src.agent.inline_orchestrator import InlineAgentOrchestrator

        mock_celeb.return_value = {"celebrities": []}
        mock_exif.return_value = {"is_recent_exif": False}
        mock_pixel.return_value = {"probability_score": 0.95, "classification": "AI_GENERATED", "model_id": "sm"}
        mock_combine.return_value = {
            "classification": "AI_GENERATED", "probability_score": 0.95,
            "evidence": [], "signals_consulted": [], "reasoning": "",
            "model_ids_used": [], "composite_analysis": {}, "composite_signal": {}, "celebrities": [],
        }

        orch = InlineAgentOrchestrator()
        result = orch.invoke(
            {"image_bytes_b64": _dummy_b64(), "tenant_id": "t1", "image_id": "i3",
             "deep_analysis": False, "fast_mode": False, "force_fresh": False},
            request_id="r3",
        )
        assert result["classification"] == "AI_GENERATED"
