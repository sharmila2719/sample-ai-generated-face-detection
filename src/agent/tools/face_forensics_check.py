"""Tool: face_forensics_check — Rekognition DetectFaces gate + AIGC SageMaker endpoint."""

from __future__ import annotations

import base64
import json
from typing import Any, Dict, List

from src.agent.tools._timing import timed
from src.aws_clients import rekognition, sagemaker_runtime
from src.config import Config


@timed("face_forensics_check")
def face_forensics_check(image_bytes_b64: str, *, request_id: str = "") -> Dict[str, Any]:
    """Detect faces, then run the AIGC ensemble model on the whole image.

    Flow:
    1. Rekognition DetectFaces — if no faces are found, return early with
       ``has_faces=False`` so the caller can skip face-swap detection.
    2. If faces are present, invoke the AIGC SageMaker endpoint on the
       full image bytes.

    Returns:
        has_faces: bool
        face_count: int
        max_face_probability: float  (AIGC score for most AI-like face region)
        faces: list of {bbox, confidence}
    """
    raw = base64.b64decode(image_bytes_b64, validate=False)

    # Gate 1: does the image contain any faces?
    rek_resp = rekognition().detect_faces(
        Image={"Bytes": raw},
        Attributes=["DEFAULT"],
    )
    face_details = rek_resp.get("FaceDetails", [])
    if not face_details:
        return {
            "has_faces": False,
            "face_count": 0,
            "max_face_probability": 0.0,
            "faces": [],
        }

    faces: List[Dict[str, Any]] = []
    for face in face_details:
        box = face.get("BoundingBox", {})
        faces.append(
            {
                "bbox": [
                    float(box.get("Left", 0)),
                    float(box.get("Top", 0)),
                    float(box.get("Width", 0)),
                    float(box.get("Height", 0)),
                ],
                "confidence": float(face.get("Confidence", 0)),
            }
        )

    # Gate 2: AIGC ensemble on the full image
    endpoint_name = Config.FACE_FORENSICS_ENDPOINT_NAME
    try:
        sm_resp = sagemaker_runtime().invoke_endpoint(
            EndpointName=endpoint_name,
            ContentType="application/json",
            Body=json.dumps({"image_b64": image_bytes_b64}),
        )
        aigc_result: Dict[str, Any] = json.loads(sm_resp["Body"].read())
        max_prob = float(aigc_result.get("max_face_probability", 0.0))
    except Exception:
        max_prob = 0.0

    return {
        "has_faces": True,
        "face_count": len(faces),
        "max_face_probability": max_prob,
        "faces": faces,
    }
