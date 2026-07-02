"""Tool: nova_pro_vision — retained as a one-line fallback (not scheduled by live orchestrator)."""

from __future__ import annotations

import json
import re
from typing import Any, Dict

from src.agent.tools._timing import timed
from src.aws_clients import bedrock_runtime

NOVA_PRO_MODEL_ID = "us.amazon.nova-pro-v1:0"


@timed("nova_pro_vision")
def nova_pro_vision(image_bytes_b64: str, *, request_id: str = "") -> Dict[str, Any]:
    """Invoke Amazon Nova Pro for AI-image detection (fallback path only)."""
    body = json.dumps(
        {
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "image": {
                                "format": "jpeg",
                                "source": {"bytes": image_bytes_b64},
                            }
                        },
                        {
                            "text": (
                                "Is this image AI-generated or a real photo? "
                                "Return JSON: {probability_score, classification, rationale, regions}"
                            )
                        },
                    ],
                }
            ]
        }
    )
    client = bedrock_runtime()
    resp = client.invoke_model(
        modelId=NOVA_PRO_MODEL_ID,
        contentType="application/json",
        accept="application/json",
        body=body,
    )
    response_body: Dict[str, Any] = json.loads(resp["body"].read())
    raw = response_body.get("output", {}).get("message", {}).get("content", [{}])[0].get("text", "")
    cleaned = re.sub(r"```(?:json)?", "", raw).strip().strip("`").strip()
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        parsed = {"probability_score": 0.5, "classification": "UNCERTAIN", "rationale": raw[:200], "regions": []}

    return {
        "probability_score": float(parsed.get("probability_score", 0.5)),
        "classification": parsed.get("classification", "UNCERTAIN"),
        "rationale": parsed.get("rationale", ""),
        "regions": parsed.get("regions") or [],
        "model_id": NOVA_PRO_MODEL_ID,
    }
