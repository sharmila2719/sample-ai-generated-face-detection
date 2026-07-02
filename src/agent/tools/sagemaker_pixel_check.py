"""Tool: sagemaker_pixel_check — CNN pixel-level AI-image detector."""

from __future__ import annotations

import json
from typing import Any, Dict

from src.agent.tools._timing import timed
from src.aws_clients import sagemaker_runtime
from src.config import Config

# Short-circuit thresholds — scores outside this band are decisive.
PIXEL_NATURAL_THRESHOLD: float = 0.15
PIXEL_AI_THRESHOLD: float = 0.85


@timed("sagemaker_pixel_check")
def sagemaker_pixel_check(image_bytes_b64: str, *, request_id: str = "") -> Dict[str, Any]:
    """Invoke the SageMaker pixel-detector endpoint.

    Returns a dict with ``probability_score`` (float [0,1]) and
    ``classification`` (NATURAL | AI_GENERATED | UNCERTAIN).
    Raises on endpoint errors so the @timed wrapper converts them
    to error dicts automatically.
    """
    payload = json.dumps({"image_b64": image_bytes_b64})
    resp = sagemaker_runtime().invoke_endpoint(
        EndpointName=Config.SAGEMAKER_ENDPOINT_NAME,
        ContentType="application/json",
        Body=payload,
    )
    result: Dict[str, Any] = json.loads(resp["Body"].read())
    score = float(result.get("probability_score", 0.5))

    if score < PIXEL_NATURAL_THRESHOLD:
        classification = "NATURAL"
    elif score > PIXEL_AI_THRESHOLD:
        classification = "AI_GENERATED"
    else:
        classification = "UNCERTAIN"

    return {
        "probability_score": score,
        "classification": classification,
        "model_id": Config.SAGEMAKER_ENDPOINT_NAME,
    }
