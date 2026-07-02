"""Tool: claude_opus_tiebreaker — Claude Opus 4.7 tiebreaker / composite-zoom."""

from __future__ import annotations

import json
import re
from typing import Any, Dict, Optional

from src.agent.tools._prompts import OPUS_COMPOSITE_PROMPT, OPUS_TIEBREAKER_PROMPT
from src.agent.tools._timing import timed
from src.aws_clients import bedrock_runtime

OPUS_MODEL_ID = "us.anthropic.claude-opus-4-7-20251001-v1:0"


def _parse(raw: str) -> Dict[str, Any]:
    cleaned = re.sub(r"```(?:json)?", "", raw).strip().strip("`").strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return {
            "probability_score": 0.5,
            "classification": "UNCERTAIN",
            "rationale": raw[:200],
            "regions": [],
        }


@timed("claude_opus_tiebreaker")
def claude_opus_tiebreaker(
    image_bytes_b64: str,
    *,
    request_id: str = "",
    mode: str = "tiebreaker",
    nova_score: float = 0.5,
    claude_score: float = 0.5,
) -> Dict[str, Any]:
    """Invoke Claude Opus 4.7 as tiebreaker or composite-zoom analyser.

    Args:
        mode: ``"tiebreaker"`` or ``"composite_zoom"``
        nova_score: Haiku probability (forwarded for context in the prompt)
        claude_score: Sonnet probability
    """
    system_prompt = (
        OPUS_COMPOSITE_PROMPT if mode == "composite_zoom" else OPUS_TIEBREAKER_PROMPT
    )
    context = (
        f"First-pass vision score: {nova_score:.2f}. "
        f"Second-pass score: {claude_score:.2f}. "
        f"Mode: {mode}."
    )

    body = json.dumps(
        {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1024,
            "system": system_prompt,
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
                        {"type": "text", "text": context + "\nReturn JSON only."},
                    ],
                }
            ],
        }
    )

    client = bedrock_runtime()
    resp = client.invoke_model(
        modelId=OPUS_MODEL_ID,
        contentType="application/json",
        accept="application/json",
        body=body,
    )
    response_body: Dict[str, Any] = json.loads(resp["body"].read())
    text = response_body["content"][0]["text"]
    parsed = _parse(text)

    return {
        "probability_score": float(parsed.get("probability_score", 0.5)),
        "classification": parsed.get("classification", "UNCERTAIN"),
        "rationale": parsed.get("rationale", ""),
        "regions": parsed.get("regions") or [],
        "model_id": OPUS_MODEL_ID,
        "mode": mode,
    }
