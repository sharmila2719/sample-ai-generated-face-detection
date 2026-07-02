"""Unit tests for the detection Lambda handler."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch


def _make_event(body: dict, path: str = "/api/detect", method: str = "POST") -> dict:
    return {
        "httpMethod": method,
        "path": path,
        "headers": {"X-Tenant-ID": "test-tenant", "Content-Type": "application/json"},
        "body": json.dumps(body),
    }


class TestDetectionHandler:

    @patch("lambda_handlers.detection_handler._pick_pipeline")
    def test_missing_s3_bucket_returns_400(self, mock_pick):
        from lambda_handlers.detection_handler import lambda_handler

        event = _make_event({"s3_key": "some/key.jpg"})
        resp = lambda_handler(event, None)
        assert resp["statusCode"] == 400
        body = json.loads(resp["body"])
        assert body["error_code"] == "VALIDATION_ERROR"

    @patch("lambda_handlers.detection_handler._pick_pipeline")
    def test_options_returns_204(self, mock_pick):
        from lambda_handlers.detection_handler import lambda_handler

        event = {
            "httpMethod": "OPTIONS",
            "path": "/api/detect",
            "headers": {},
            "body": "",
        }
        resp = lambda_handler(event, None)
        assert resp["statusCode"] == 204

    @patch("lambda_handlers.detection_handler._pick_pipeline")
    def test_invalid_json_returns_400(self, mock_pick):
        from lambda_handlers.detection_handler import lambda_handler

        event = {
            "httpMethod": "POST",
            "path": "/api/detect",
            "headers": {},
            "body": "not-json{{{",
        }
        resp = lambda_handler(event, None)
        assert resp["statusCode"] == 400
        assert "INVALID_JSON" in resp["body"]

    @patch("lambda_handlers.detection_handler._pick_pipeline")
    def test_successful_detection(self, mock_pick):
        from lambda_handlers.detection_handler import lambda_handler

        mock_result = MagicMock()
        mock_result.to_dict.return_value = {
            "image_id": "img-1",
            "tenant_id": "test-tenant",
            "classification": "NATURAL",
            "probability_score": 0.05,
            "evidence": [],
            "signals_consulted": ["exif_check"],
            "reasoning": "Test",
            "model_ids_used": [],
            "composite_analysis": {},
            "composite_signal": {},
            "celebrities": [],
            "cache_hit": False,
        }

        mock_pipeline = MagicMock()
        mock_pipeline.detect_image = AsyncMock(return_value=mock_result)
        mock_pick.return_value = mock_pipeline

        event = _make_event({"s3_bucket": "test-bucket", "s3_key": "test.jpg"})
        resp = lambda_handler(event, None)
        assert resp["statusCode"] == 200
        body = json.loads(resp["body"])
        assert body["classification"] == "NATURAL"
