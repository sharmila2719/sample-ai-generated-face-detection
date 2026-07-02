"""Legacy SageMaker-only detection pipeline (USE_AGENT=false path).

This is the non-agentic fallback. It calls the SageMaker pixel-detector
endpoint directly, skipping all Bedrock vision models. Retained for
backward compatibility; the production path uses the agentic orchestrator.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from src.aws_clients import sagemaker_runtime
from src.config import Config
from src.exceptions import ModelInvocationError
from src.logger import get_logger
from src.storage import get_original_format, image_to_b64, read_image_from_s3

logger = get_logger(__name__)


@dataclass
class DetectionResult:
    """Result object returned by the legacy pipeline."""

    image_id: str
    tenant_id: str
    classification: str = "UNCERTAIN"
    probability_score: float = 0.5
    evidence: List[str] = field(default_factory=list)
    signals_consulted: List[str] = field(default_factory=list)
    reasoning: str = ""
    model_ids_used: List[str] = field(default_factory=list)
    composite_analysis: Dict[str, Any] = field(
        default_factory=lambda: {
            "has_composite_elements": False,
            "regions": [],
            "layers_consulted": [],
        }
    )
    celebrities: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "image_id": self.image_id,
            "tenant_id": self.tenant_id,
            "classification": self.classification,
            "probability_score": self.probability_score,
            "evidence": self.evidence,
            "signals_consulted": self.signals_consulted,
            "reasoning": self.reasoning,
            "model_ids_used": self.model_ids_used,
            "composite_analysis": self.composite_analysis,
            "celebrities": self.celebrities,
        }


class DetectionPipeline:
    """Legacy single-model detection via SageMaker pixel detector."""

    async def detect_image(
        self,
        s3_bucket: str,
        s3_key: str,
        image_id: Optional[str] = None,
        tenant_id: str = "default",
        request_id: str = "",
        force_fresh: bool = False,
        deep_analysis: bool = False,
        fast_mode: bool = False,
    ) -> DetectionResult:
        raw_bytes, content_hash = read_image_from_s3(s3_bucket, s3_key)
        image_bytes_b64 = image_to_b64(raw_bytes)
        img_id = image_id or content_hash[:16]

        try:
            resp = sagemaker_runtime().invoke_endpoint(
                EndpointName=Config.SAGEMAKER_ENDPOINT_NAME,
                ContentType="application/json",
                Body=json.dumps({"image_b64": image_bytes_b64}),
            )
            result = json.loads(resp["Body"].read())
            score = float(result.get("probability_score", 0.5))
        except Exception as exc:
            logger.error("detection.sagemaker_failed", extra={"error": str(exc)})
            score = 0.5

        if score < 0.40:
            classification = "NATURAL"
        elif score > 0.65:
            classification = "AI_GENERATED"
        else:
            classification = "UNCERTAIN"

        return DetectionResult(
            image_id=img_id,
            tenant_id=tenant_id,
            classification=classification,
            probability_score=score,
            evidence=[f"SageMaker pixel detector score: {score:.3f}"],
            signals_consulted=["sagemaker_pixel_check"],
            reasoning="Legacy SageMaker pipeline (USE_AGENT=false).",
            model_ids_used=[Config.SAGEMAKER_ENDPOINT_NAME],
        )

    async def detect_batch(
        self,
        images: List[Dict[str, Any]],
        tenant_id: str = "default",
        request_id: str = "",
    ) -> List[DetectionResult]:
        tasks = [
            self.detect_image(
                s3_bucket=img["s3_bucket"],
                s3_key=img["s3_key"],
                image_id=img.get("image_id"),
                tenant_id=tenant_id,
                request_id=request_id,
            )
            for img in images
        ]
        return list(await asyncio.gather(*tasks))
