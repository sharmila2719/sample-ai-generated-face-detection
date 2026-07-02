"""Lambda handler for S3 ObjectCreated events — triggers async detection."""

from __future__ import annotations

import asyncio
import json
import os
import urllib.parse
from typing import Any, Dict

from src.agent.inline_orchestrator import InlineAgentOrchestrator
from src.agent.pipeline import AgentDetectionPipeline
from src.detection import DetectionPipeline
from src.logger import get_logger

logger = get_logger(__name__)


def _pick_pipeline():
    if os.getenv("USE_AGENT", "false").lower() != "true":
        return DetectionPipeline()
    return AgentDetectionPipeline(InlineAgentOrchestrator.from_env())


def lambda_handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    """Process each S3 ObjectCreated record."""
    pipeline = _pick_pipeline()
    results = []

    for record in event.get("Records", []):
        bucket = record["s3"]["bucket"]["name"]
        key = urllib.parse.unquote_plus(record["s3"]["object"]["key"])

        logger.info("s3_event.processing", extra={"bucket": bucket, "key": key})
        try:
            result = asyncio.run(
                pipeline.detect_image(
                    s3_bucket=bucket,
                    s3_key=key,
                    tenant_id="s3-event",
                    deep_analysis=True,  # full cascade — no API Gateway timeout
                    fast_mode=False,
                )
            )
            results.append(
                {
                    "s3_key": key,
                    "classification": result.to_dict().get("classification"),
                    "probability_score": result.to_dict().get("probability_score"),
                }
            )
            logger.info(
                "s3_event.completed",
                extra={
                    "key": key,
                    "classification": result.to_dict().get("classification"),
                },
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("s3_event.failed", extra={"key": key, "error": str(exc)})
            results.append({"s3_key": key, "error": str(exc)})

    return {"statusCode": 200, "body": json.dumps({"results": results})}
