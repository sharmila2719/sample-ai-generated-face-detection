"""AgentDetectionPipeline — wraps the inline orchestrator or AgentCore runtime client."""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union

from src.agent.cache import DetectionCacheLookup
from src.logger import get_logger
from src.storage import get_original_format, image_to_b64, read_image_from_s3

logger = get_logger(__name__)


@dataclass
class AgentDetectionResult:
    """Result object returned by the agent pipeline."""

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
    composite_signal: Dict[str, Any] = field(
        default_factory=lambda: {
            "has_ai_face_with_real_context": False,
            "face_forensics_ai_score": 0.0,
            "face_count": 0,
            "vision_mean": 0.5,
            "pixel_score": 0.5,
        }
    )
    celebrities: List[Dict[str, Any]] = field(default_factory=list)
    cache_hit: bool = False

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
            "composite_signal": self.composite_signal,
            "celebrities": self.celebrities,
            "cache_hit": self.cache_hit,
        }


class AgentDetectionPipeline:
    """Orchestrates image detection via the inline orchestrator or AgentCore runtime."""

    def __init__(self, orchestrator: Any) -> None:
        self._orchestrator = orchestrator
        self._cache = DetectionCacheLookup()

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
    ) -> AgentDetectionResult:
        """Download from S3, check cache, run detection cascade."""
        raw_bytes, content_hash = read_image_from_s3(s3_bucket, s3_key)
        img_id = image_id or str(uuid.uuid4())

        # Cache lookup (Req 15) — skip when force_fresh=True
        if not force_fresh:
            cached = self._cache.lookup(tenant_id, content_hash)
            if cached:
                logger.info(
                    "pipeline.cache_hit",
                    extra={"image_id": img_id, "content_hash": content_hash},
                )
                return AgentDetectionResult(
                    image_id=img_id,
                    tenant_id=tenant_id,
                    classification=cached.get("classification", "UNCERTAIN"),
                    probability_score=float(cached.get("probability_score", 0.5)),
                    evidence=["Cache hit — result reused from prior analysis"]
                    + (cached.get("evidence") or []),
                    signals_consulted=cached.get("signals_consulted") or [],
                    reasoning=cached.get("reasoning", ""),
                    model_ids_used=cached.get("model_ids_used") or [],
                    composite_analysis=cached.get("composite_analysis") or {},
                    composite_signal=cached.get("composite_signal") or {},
                    celebrities=cached.get("celebrities") or [],
                    cache_hit=True,
                )

        image_bytes_b64 = image_to_b64(raw_bytes)
        original_format = get_original_format(raw_bytes)

        payload = {
            "image_bytes_b64": image_bytes_b64,
            "tenant_id": tenant_id,
            "image_id": img_id,
            "request_id": request_id,
            "content_hash": content_hash,
            "force_fresh": force_fresh,
            "deep_analysis": deep_analysis,
            "fast_mode": fast_mode,
            "original_format": original_format,
        }

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: self._orchestrator.invoke(payload, request_id=request_id),
        )

        return AgentDetectionResult(
            image_id=img_id,
            tenant_id=tenant_id,
            classification=result.get("classification", "UNCERTAIN"),
            probability_score=float(result.get("probability_score", 0.5)),
            evidence=result.get("evidence") or [],
            signals_consulted=result.get("signals_consulted") or [],
            reasoning=result.get("reasoning", ""),
            model_ids_used=result.get("model_ids_used") or [],
            composite_analysis=result.get("composite_analysis") or {},
            composite_signal=result.get("composite_signal") or {},
            celebrities=result.get("celebrities") or [],
        )

    async def detect_batch(
        self,
        images: List[Dict[str, Any]],
        tenant_id: str = "default",
        request_id: str = "",
    ) -> List[AgentDetectionResult]:
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
