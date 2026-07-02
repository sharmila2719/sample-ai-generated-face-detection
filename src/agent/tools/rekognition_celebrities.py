"""Tool: rekognition_celebrities — identifies public figures in the image."""

from __future__ import annotations

import base64
from typing import Any, Dict, List

from src.agent.tools._timing import timed
from src.aws_clients import rekognition

# Minimum Rekognition confidence to include a celebrity match
_CONFIDENCE_THRESHOLD: int = 85


@timed("rekognition_celebrities")
def rekognition_celebrities(image_bytes_b64: str, *, request_id: str = "") -> Dict[str, Any]:
    """Call Rekognition RecognizeCelebrities.

    Returns ``{"celebrities": [{name, confidence, urls}]}`` or an
    empty list when no public figures are detected above the threshold.
    """
    raw = base64.b64decode(image_bytes_b64, validate=False)
    resp = rekognition().recognize_celebrities(Image={"Bytes": raw})

    matches: List[Dict[str, Any]] = []
    for face in resp.get("CelebrityFaces", []):
        confidence = float(face.get("MatchConfidence", 0))
        if confidence >= _CONFIDENCE_THRESHOLD:
            matches.append(
                {
                    "name": face.get("Name", "Unknown"),
                    "confidence": confidence,
                    "urls": face.get("Urls", []),
                }
            )

    return {"celebrities": matches}
