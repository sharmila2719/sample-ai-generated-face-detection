"""Inline agent orchestrator — runs all MCP tools directly without AgentCore Runtime.

This is the default path when AGENTCORE_RUNTIME_ARN is not set.
The decision tree is encoded in Python control flow for determinism and
to avoid Docker/ECR/AgentCore setup requirements.

Detection cascade order:
  0. rekognition_celebrities (always, before any short-circuit)
  1. exif_check             (EXIF fast-path)
  2. sagemaker_pixel_check  (pixel-level CNN)
  3. claude_haiku_vision + claude_vision (parallel on deep_analysis)
  4. claude_opus_tiebreaker (when needed)
  5. face_forensics_check
  6. Phase B composite cascade (rekognition_regions + per-crop Haiku)
  7. Phase C specialist (specialist_composite_check)
  8. combine_evidence (always last)
"""

from __future__ import annotations

import base64
import binascii
import io
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional

from src.agent.tools import (
    claude_opus_tiebreaker,
    claude_vision,
    combine_evidence,
    exif_check,
    face_forensics_check,
    rekognition_celebrities,
)
from src.agent.tools.claude_haiku_vision import claude_haiku_vision
from src.agent.tools.rekognition_regions import rekognition_regions
from src.agent.tools.sagemaker_pixel_check import (
    PIXEL_AI_THRESHOLD,
    PIXEL_NATURAL_THRESHOLD,
    sagemaker_pixel_check,
)
from src.agent.tools.specialist_composite_check import specialist_composite_check
from src.logger import get_logger

logger = get_logger(__name__)

# Band thresholds for the uncertain escalation gate
_NATURAL_THRESHOLD = 0.40
_AI_THRESHOLD = 0.65

# Phase B / C composite cascade thresholds
_PHASE_B_REGION_TRIGGER = 0.60
_PHASE_C_CROP_TRIGGER = 0.85

_MAX_CROPS = 3
_MIN_CROP_PIXELS = 64


def _is_error(tool_result: Optional[Dict[str, Any]]) -> bool:
    return isinstance(tool_result, dict) and "error_code" in tool_result


def _is_success(tool_result: Optional[Dict[str, Any]]) -> bool:
    return isinstance(tool_result, dict) and "error_code" not in tool_result


def _celebrities_from(result: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not isinstance(result, dict) or "error_code" in result:
        return []
    matches = result.get("celebrities") or []
    if not isinstance(matches, list):
        return []
    return [dict(m) for m in matches if isinstance(m, dict)]


def _uncertain_band(score: float) -> bool:
    return _NATURAL_THRESHOLD <= score <= _AI_THRESHOLD


def _max_region_likelihood(tool_result: Optional[Dict[str, Any]]) -> float:
    if not isinstance(tool_result, dict):
        return 0.0
    regions = tool_result.get("regions") or []
    if not isinstance(regions, list):
        return 0.0
    best = 0.0
    for r in regions:
        if not isinstance(r, dict):
            continue
        try:
            val = float(r.get("ai_likelihood", 0.0))
        except (TypeError, ValueError):
            continue
        if val > best:
            best = val
    return best


def _crop_region(image_bytes: bytes, bbox: List[float]) -> Optional[bytes]:
    try:
        from PIL import Image
    except ImportError:
        return None

    try:
        img = Image.open(io.BytesIO(image_bytes))
        img.load()
    except Exception as exc:
        logger.warning("orchestrator.crop_decode_failed", extra={"error": str(exc)})
        return None

    w_px, h_px = img.size
    x, y, w, h = bbox
    left = max(0, int(x * w_px))
    upper = max(0, int(y * h_px))
    right = min(w_px, int((x + w) * w_px))
    lower = min(h_px, int((y + h) * h_px))

    if (right - left) < _MIN_CROP_PIXELS or (lower - upper) < _MIN_CROP_PIXELS:
        return None

    cropped = img.crop((left, upper, right, lower))
    if cropped.mode != "RGB":
        cropped = cropped.convert("RGB")
    buf = io.BytesIO()
    cropped.save(buf, format="JPEG", quality=90)
    return buf.getvalue()


class InlineAgentOrchestrator:
    """Runs the detection decision tree in-process — no Docker required."""

    @classmethod
    def from_env(cls) -> "InlineAgentOrchestrator":
        return cls()

    def invoke(self, payload: Dict[str, Any], *, request_id: str) -> Dict[str, Any]:
        image_bytes_b64: str = payload["image_bytes_b64"]
        tenant_id: str = payload["tenant_id"]
        image_id: str = payload["image_id"]
        content_hash: Optional[str] = payload.get("content_hash")
        force_fresh: bool = bool(payload.get("force_fresh", False))
        deep_analysis: bool = bool(payload.get("deep_analysis", False))
        fast_mode: bool = bool(payload.get("fast_mode", False))

        # Step 0: Celebrity recognition (always before any short-circuit)
        celebrities_result = rekognition_celebrities(
            image_bytes_b64, request_id=request_id
        )

        # Step 1: EXIF check
        exif_result = exif_check(image_bytes_b64, request_id=request_id)
        if isinstance(exif_result, dict) and "error_code" not in exif_result:
            exif_result["image_format"] = payload.get("original_format", "UNKNOWN")

        if (
            not deep_analysis
            and not _is_error(exif_result)
            and exif_result.get("is_recent_exif", False)
        ):
            logger.info("orchestrator.exif_short_circuit", extra={"request_id": request_id})
            return self._call_combine(
                image_id=image_id, tenant_id=tenant_id, request_id=request_id,
                content_hash=content_hash, exif=exif_result, pixel=None,
                nova=None, claude=None, force_fresh=force_fresh,
                deep_analysis=deep_analysis, celebrities=celebrities_result,
                extra_regions=None,
            )

        # Step 2: SageMaker pixel check
        pixel_result = sagemaker_pixel_check(image_bytes_b64, request_id=request_id)

        if not deep_analysis and not _is_error(pixel_result):
            pixel_score = float(pixel_result.get("probability_score", 0.5))
            if pixel_score < PIXEL_NATURAL_THRESHOLD or pixel_score > PIXEL_AI_THRESHOLD:
                logger.info("orchestrator.pixel_short_circuit", extra={"request_id": request_id, "score": pixel_score})
                return self._call_combine(
                    image_id=image_id, tenant_id=tenant_id, request_id=request_id,
                    content_hash=content_hash, exif=exif_result, c2pa=None,
                    pixel=pixel_result, nova=None, claude=None,
                    force_fresh=force_fresh, deep_analysis=deep_analysis,
                    celebrities=celebrities_result, extra_regions=None,
                )

        # Step 3 + 5 (deep): Vision LLMs
        nova_result: Dict[str, Any]
        claude_result: Optional[Dict[str, Any]] = None
        face_forensics_result: Optional[Dict[str, Any]] = None

        if deep_analysis:
            with ThreadPoolExecutor(max_workers=3) as pool:
                haiku_f = pool.submit(claude_haiku_vision, image_bytes_b64, request_id=request_id)
                sonnet_f = pool.submit(claude_vision, image_bytes_b64, request_id=request_id)
                ff_f = pool.submit(face_forensics_check, image_bytes_b64, request_id=request_id)
                nova_result = haiku_f.result()
                claude_result = sonnet_f.result()
                face_forensics_result = ff_f.result()
            nova_score = float(nova_result.get("probability_score", 0.5)) if not _is_error(nova_result) else 0.5
            nova_decisive = not _is_error(nova_result) and not _uncertain_band(nova_score)
        else:
            nova_result = claude_haiku_vision(image_bytes_b64, request_id=request_id)
            nova_score = 0.5
            nova_decisive = False
            if not _is_error(nova_result):
                nova_score = float(nova_result.get("probability_score", 0.5))
                nova_decisive = not _uncertain_band(nova_score)
            if not nova_decisive:
                claude_result = claude_vision(image_bytes_b64, request_id=request_id)
            face_forensics_result = face_forensics_check(image_bytes_b64, request_id=request_id)

        # Step 4: Opus tiebreaker
        opus_result: Optional[Dict[str, Any]] = None
        claude_score = (
            float(claude_result.get("probability_score", 0.5))
            if _is_success(claude_result) else 0.5
        )
        region_trigger_hit = (
            _max_region_likelihood(nova_result) > _PHASE_B_REGION_TRIGGER
            or _max_region_likelihood(claude_result) > _PHASE_B_REGION_TRIGGER
        )
        tiebreaker_needed = (
            _is_success(nova_result) and _is_success(claude_result)
            and _NATURAL_THRESHOLD <= (nova_score + claude_score) / 2 <= _AI_THRESHOLD
        )

        opus_mode: Optional[str] = None
        if region_trigger_hit:
            opus_mode = "composite_zoom"
        elif tiebreaker_needed:
            opus_mode = "tiebreaker"

        if fast_mode:
            opus_mode = None

        if opus_mode is not None:
            opus_result = claude_opus_tiebreaker(
                image_bytes_b64, request_id=request_id,
                mode=opus_mode, nova_score=nova_score, claude_score=claude_score,
            )

        # Collect extra regions
        extra_regions: List[Dict[str, Any]] = []
        if _is_success(opus_result):
            opus_regions = (opus_result or {}).get("regions") or []
            if isinstance(opus_regions, list):
                extra_regions.extend(r for r in opus_regions if isinstance(r, dict))
            if not region_trigger_hit:
                region_trigger_hit = any(
                    isinstance(r, dict)
                    and float(r.get("ai_likelihood", 0)) > _PHASE_B_REGION_TRIGGER
                    for r in extra_regions
                )

        # Phase B / C composite cascade
        if region_trigger_hit and not fast_mode:
            phase_bc = self._run_composite_cascade(
                image_bytes_b64=image_bytes_b64,
                request_id=request_id,
                image_id=image_id,
            )
            extra_regions.extend(phase_bc)

        combine_claude_result = opus_result if _is_success(opus_result) else claude_result

        return self._call_combine(
            image_id=image_id, tenant_id=tenant_id, request_id=request_id,
            content_hash=content_hash, exif=exif_result, c2pa=None,
            pixel=pixel_result, nova=nova_result, claude=combine_claude_result,
            face_forensics=face_forensics_result, force_fresh=force_fresh,
            deep_analysis=deep_analysis, celebrities=celebrities_result,
            extra_regions=extra_regions or None,
        )

    def _run_composite_cascade(
        self, *, image_bytes_b64: str, request_id: str, image_id: str
    ) -> List[Dict[str, Any]]:
        rek = rekognition_regions(image_bytes_b64, request_id=request_id)
        if _is_error(rek) or not rek.get("regions"):
            return []

        try:
            image_bytes = base64.b64decode(image_bytes_b64, validate=False)
        except (binascii.Error, ValueError, TypeError):
            return []

        phase_b: List[Dict[str, Any]] = []
        for rek_region in rek["regions"][:_MAX_CROPS]:
            bbox = rek_region.get("bbox")
            if not bbox or len(bbox) != 4:
                continue
            crop_bytes = _crop_region(image_bytes, bbox)
            if crop_bytes is None:
                continue
            crop_b64 = base64.b64encode(crop_bytes).decode("ascii")
            crop_result = claude_haiku_vision(crop_b64, request_id=request_id)
            if _is_error(crop_result):
                continue
            prob = float(crop_result.get("probability_score", 0.5))
            phase_b.append({
                "label": rek_region.get("label", "region"),
                "bbox": bbox,
                "ai_likelihood": prob,
                "rationale": crop_result.get("rationale", ""),
                "analyzed_by": "claude_haiku_vision (crop)",
            })

        if not phase_b:
            return []

        phase_c_candidates = sorted(
            [r for r in phase_b if r["ai_likelihood"] > _PHASE_C_CROP_TRIGGER],
            key=lambda r: r["ai_likelihood"], reverse=True,
        )[:_MAX_CROPS]

        phase_c: List[Dict[str, Any]] = []
        for candidate in phase_c_candidates:
            crop_bytes = _crop_region(image_bytes, candidate["bbox"])
            if crop_bytes is None:
                continue
            crop_b64 = base64.b64encode(crop_bytes).decode("ascii")
            specialist = specialist_composite_check(crop_b64, request_id=request_id)
            if _is_error(specialist):
                continue
            phase_c.append({
                "label": candidate["label"],
                "bbox": candidate["bbox"],
                "ai_likelihood": float(specialist.get("ai_likelihood", 0.5)),
                "rationale": specialist.get("rationale", ""),
                "analyzed_by": "specialist_composite_check",
            })

        return phase_b + phase_c

    def _call_combine(
        self, *, image_id, tenant_id, request_id, content_hash,
        exif=None, c2pa=None, pixel=None, nova=None, claude=None,
        face_forensics=None, extra_regions=None, force_fresh=False,
        deep_analysis=False, celebrities=None,
    ) -> Dict[str, Any]:
        combiner = combine_evidence(
            image_id=image_id, tenant_id=tenant_id, request_id=request_id,
            exif=exif, c2pa=c2pa, pixel=pixel, nova=nova, claude=claude,
            face_forensics=face_forensics, content_hash=content_hash,
            extra_regions=extra_regions, force_fresh=force_fresh,
            deep_analysis=deep_analysis,
            celebrities=_celebrities_from(celebrities),
        )

        if _is_error(combiner):
            return {
                "classification": "UNCERTAIN", "probability_score": 0.5,
                "evidence": ["combine_evidence failed: " + str(combiner.get("error_message", ""))],
                "signals_consulted": [], "reasoning": "Inline orchestrator fell back to UNCERTAIN.",
                "model_ids_used": [],
                "composite_analysis": {"has_composite_elements": False, "regions": [], "layers_consulted": []},
                "composite_signal": {"has_ai_face_with_real_context": False, "face_forensics_ai_score": 0.0, "face_count": 0, "vision_mean": 0.5, "pixel_score": 0.5},
                "celebrities": _celebrities_from(celebrities),
            }

        return {
            "classification": combiner["classification"],
            "probability_score": combiner["probability_score"],
            "evidence": combiner["evidence"],
            "signals_consulted": combiner["signals_consulted"],
            "reasoning": combiner["reasoning"],
            "model_ids_used": combiner["model_ids_used"],
            "composite_analysis": combiner.get("composite_analysis", {"has_composite_elements": False, "regions": [], "layers_consulted": []}),
            "composite_signal": combiner.get("composite_signal", {"has_ai_face_with_real_context": False, "face_forensics_ai_score": 0.0, "face_count": 0, "vision_mean": 0.5, "pixel_score": 0.5}),
            "celebrities": _celebrities_from(celebrities),
        }


__all__ = ["InlineAgentOrchestrator"]
