"""Tool: claude_haiku_vision — first-pass vision using Claude Haiku 4.5."""

from __future__ import annotations

import json
import re
from typing import Any, Dict

from src.agent.tools._prompts import HAIKU_SYSTEM_PROMPT
from src.agent.tools._timing import timed
from src.aws_clients import bedrock_runtime
from src.config import Config

HAIKU_MODEL_ID = "us.anthropic.claude-haiku-4-5-20251001-v1:0"


def _parse_vision_response(raw: str) -> Dict[str, Any]:
    """Extract JSON from the model's text response."""
    # Strip markdown code fences if present
    cleaned = re.sub(r"```(?:json)?", "", raw).strip().strip("`").strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # Fallback: treat as UNCERTAIN
        return {
            "probability_score": 0.5,
            "classification": "UNCERTAIN",
            "rationale": raw[:200],
            "regions": [],
        }


@timed("claude_haiku_vision")
def claude_haiku_vision(image_bytes_b64: str, *, request_id: str = "") -> Dict[str, Any]:
    """Invoke Claude Haiku 4.5 via Bedrock for first-pass AI-image detection."""
    client = bedrock_runtime()

    body = json.dumps(
        {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 512,
            "system": HAIKU_SYSTEM_PROMPT,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
                                "data": image_bytes_b64,
                            },
                        },
                        {
                            "type": "text",
                            "text": "Analyse this image. Return JSON only.",
                        },
                    ],
                }
            ],
        }
    )

    resp = client.invoke_model(
        modelId=HAIKU_MODEL_ID,
        contentType="application/json",
        accept="application/json",
        body=body,
    )
    response_body: Dict[str, Any] = json.loads(resp["body"].read())
    text = response_body["content"][0]["text"]
    parsed = _parse_vision_response(text)

    return {
        "probability_score": float(parsed.get("probability_score", 0.5)),
        "classification": parsed.get("classification", "UNCERTAIN"),
        "rationale": parsed.get("rationale", ""),
        "regions": parsed.get("regions") or [],
        "model_id": HAIKU_MODEL_ID,
    }
