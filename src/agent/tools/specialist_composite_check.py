"""Tool: specialist_composite_check — SageMaker specialist on high-risk crops."""

from __future__ import annotations

import json
from typing import Any, Dict

from src.agent.tools._timing import timed
from src.aws_clients import sagemaker_runtime
from src.config import Config


@timed("specialist_composite_check")
def specialist_composite_check(image_bytes_b64: str, *, request_id: str = "") -> Dict[str, Any]:
    """Invoke the composite-specialist SageMaker endpoint on a cropped region.

    Returns:
        ai_likelihood: float [0,1]
        rationale: str
    """
    endpoint_name = Config.COMPOSITE_SPECIALIST_ENDPOINT_NAME
    resp = sagemaker_runtime().invoke_endpoint(
        EndpointName=endpoint_name,
        ContentType="application/json",
        Body=json.dumps({"image_b64": image_bytes_b64}),
    )
    result: Dict[str, Any] = json.loads(resp["Body"].read())
    return {
        "ai_likelihood": float(result.get("ai_likelihood", 0.5)),
        "rationale": result.get("rationale", ""),
        "model_id": endpoint_name,
    }
