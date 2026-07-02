"""Tool: combine_evidence — merges all tool outputs into the final verdict and persists to DynamoDB."""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from src.agent.tools._timing import timed
from src.alerts import publish_alert
from src.aws_clients import dynamodb
from src.config import Config
from src.logger import get_logger

logger = get_logger(__name__)

# Classification thresholds (must match inline_orchestrator.py)
_NATURAL_THRESHOLD: float = 0.40
_AI_THRESHOLD: float = 0.65
_PIXEL_BLEND_WEIGHT: float = 0.20

# Face-forensics upgrade thresholds
_FACE_FORENSICS_AI_THRESHOLD: float = 0.85
_FACE_FORENSICS_UNCERTAIN_THRESHOLD: float = 0.60


def _score_or_default(result: Optional[Dict[str, Any]], default: float = 0.5) -> float:
    if not isinstance(result, dict) or "error_code" in result:
        return default
    return float(result.get("probability_score", default))


@timed("combine_evidence")
def combine_evidence(
    *,
    image_id: str,
    tenant_id: str,
    request_id: str,
    exif: Optional[Dict[str, Any]] = None,
    c2pa: Optional[Dict[str, Any]] = None,
    pixel: Optional[Dict[str, Any]] = None,
    nova: Optional[Dict[str, Any]] = None,
    claude: Optional[Dict[str, Any]] = None,
    face_forensics: Optional[Dict[str, Any]] = None,
    content_hash: Optional[str] = None,
    extra_regions: Optional[List[Dict[str, Any]]] = None,
    force_fresh: bool = False,
    deep_analysis: bool = False,
    celebrities: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Combine all tool outputs, classify the image, persist to DynamoDB."""

    signals_consulted: List[str] = []
    evidence: List[str] = []
    model_ids_used: List[str] = []
    all_regions: List[Dict[str, Any]] = []

    # --- Gather vision scores ---
    vision_scores: List[float] = []
    for tool_result, label in [(nova, "haiku_vision"), (claude, "sonnet_vision")]:
        if isinstance(tool_result, dict) and "error_code" not in tool_result:
            score = float(tool_result.get("probability_score", 0.5))
            vision_scores.append(score)
            signals_consulted.append(label)
            rationale = tool_result.get("rationale", "")
            if rationale:
                evidence.append(f"{label}: {rationale}")
            model_id = tool_result.get("model_id", "")
            if model_id:
                model_ids_used.append(model_id)
            regions = tool_result.get("regions") or []
            all_regions.extend(r for r in regions if isinstance(r, dict))

    # --- Pixel score ---
    pixel_score = _score_or_default(pixel)
    if isinstance(pixel, dict) and "error_code" not in pixel:
        signals_consulted.append("sagemaker_pixel_check")

    # --- Vision mean ---
    vision_mean = sum(vision_scores) / len(vision_scores) if vision_scores else 0.5

    # --- Blended probability ---
    if vision_scores:
        blended = (1 - _PIXEL_BLEND_WEIGHT) * vision_mean + _PIXEL_BLEND_WEIGHT * pixel_score
    else:
        blended = pixel_score

    # --- EXIF signal ---
    exif_short_circuit = False
    if isinstance(exif, dict) and "error_code" not in exif:
        signals_consulted.append("exif_check")
        if exif.get("is_recent_exif"):
            exif_short_circuit = True
            evidence.append(
                f"EXIF: Recent camera photo ({exif.get('make')} {exif.get('model')})"
            )

    # --- Face-forensics composite signal ---
    has_ai_face_with_real_context = False
    face_forensics_score = 0.0
    face_count = 0

    if isinstance(face_forensics, dict) and "error_code" not in face_forensics:
        signals_consulted.append("face_forensics_check")
        face_count = int(face_forensics.get("face_count", 0))
        face_forensics_score = float(face_forensics.get("max_face_probability", 0.0))
        if face_forensics_score >= _FACE_FORENSICS_AI_THRESHOLD:
            if vision_mean < 0.40 and pixel_score < 0.40:
                has_ai_face_with_real_context = True
                evidence.append(
                    f"Face forensics: AI-generated face detected (score {face_forensics_score:.2f})"
                )

    # --- Extra regions from Phase B/C ---
    if extra_regions:
        all_regions.extend(extra_regions)

    # --- Final classification ---
    if exif_short_circuit and not deep_analysis:
        classification = "NATURAL"
        probability_score = min(blended, _NATURAL_THRESHOLD - 0.01)
    elif has_ai_face_with_real_context:
        classification = "AI_GENERATED"  # face-swap composite
        probability_score = max(blended, _FACE_FORENSICS_AI_THRESHOLD)
    elif blended < _NATURAL_THRESHOLD:
        classification = "NATURAL"
        probability_score = blended
    elif blended > _AI_THRESHOLD:
        classification = "AI_GENERATED"
        probability_score = blended
    else:
        classification = "UNCERTAIN"
        probability_score = blended

    probability_score = max(0.0, min(1.0, probability_score))

    # --- Build composite analysis ---
    composite_signal = {
        "has_ai_face_with_real_context": has_ai_face_with_real_context,
        "face_forensics_ai_score": face_forensics_score,
        "face_count": face_count,
        "vision_mean": vision_mean,
        "pixel_score": pixel_score,
    }
    composite_analysis = {
        "has_composite_elements": bool(all_regions),
        "regions": all_regions,
        "layers_consulted": list(set(signals_consulted)),
    }

    # --- Confidence and recommendation ---
    distance_from_05 = abs(probability_score - 0.5) * 2  # [0,1]
    overall_confidence = round(distance_from_05, 3)
    if classification == "NATURAL":
        recommendation = "ACCEPT"
    elif classification == "AI_GENERATED":
        recommendation = "REJECT"
    else:
        recommendation = "REVIEW"

    # --- Build reasoning string ---
    reasoning = (
        f"Classification: {classification} (score {probability_score:.3f}). "
        f"Vision mean: {vision_mean:.3f}. Pixel: {pixel_score:.3f}. "
        f"Signals: {', '.join(signals_consulted) or 'none'}."
    )

    # --- Persist to DynamoDB ---
    now_iso = datetime.now(tz=timezone.utc).isoformat()
    ttl = int(time.time()) + Config.DETECTION_RETENTION_DAYS * 86400
    ch_pk = f"{tenant_id}#{content_hash}" if content_hash else f"{tenant_id}#none"

    item = {
        "image_id": {"S": image_id},
        "tenant_id": {"S": tenant_id},
        "detection_timestamp": {"S": now_iso},
        "content_hash": {"S": content_hash or ""},
        "content_hash_pk": {"S": ch_pk},
        "classification": {"S": classification},
        "probability_score": {"N": str(probability_score)},
        "evidence": {"S": json.dumps(evidence)},
        "signals_consulted": {"S": json.dumps(signals_consulted)},
        "reasoning": {"S": reasoning},
        "model_ids_used": {"S": json.dumps(model_ids_used)},
        "composite_analysis": {"S": json.dumps(composite_analysis)},
        "composite_signal": {"S": json.dumps(composite_signal)},
        "celebrities": {"S": json.dumps(celebrities or [])},
        "overall_confidence": {"N": str(overall_confidence)},
        "recommendation": {"S": recommendation},
        "ttl": {"N": str(ttl)},
        "alert_published": {"BOOL": False},
    }

    try:
        dynamodb().put_item(
            TableName=Config.DYNAMODB_DETECTION_TABLE,
            Item=item,
        )
    except Exception as exc:
        logger.error("combine_evidence.dynamo_write_failed", extra={"error": str(exc)})

    # --- Publish SNS alert on high-confidence AI detection ---
    if probability_score > Config.ALERT_THRESHOLD:
        try:
            publish_alert(
                subject=f"AI Image Alert: {classification} ({probability_score:.2f})",
                payload={
                    "image_id": image_id,
                    "tenant_id": tenant_id,
                    "classification": classification,
                    "probability_score": probability_score,
                    "celebrities": celebrities or [],
                },
            )
        except Exception:
            pass

    return {
        "classification": classification,
        "probability_score": probability_score,
        "evidence": evidence,
        "signals_consulted": signals_consulted,
        "reasoning": reasoning,
        "model_ids_used": model_ids_used,
        "composite_analysis": composite_analysis,
        "composite_signal": composite_signal,
        "celebrities": celebrities or [],
        "recommendation": recommendation,
        "overall_confidence": overall_confidence,
    }
