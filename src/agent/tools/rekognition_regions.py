"""Tool: rekognition_regions — detect bounding boxes for Phase B composite cascade."""

from __future__ import annotations

import base64
from typing import Any, Dict, List

from src.agent.tools._timing import timed
from src.aws_clients import rekognition


@timed("rekognition_regions")
def rekognition_regions(image_bytes_b64: str, *, request_id: str = "") -> Dict[str, Any]:
    """Call Rekognition DetectLabels to get object bounding boxes.

    Returns ``{"regions": [{label, bbox:[x,y,w,h]}]}`` where bbox values
    are normalised to [0,1]. Only labels with bounding boxes are included.
    Capped at the top-3 largest boxes by area.
    """
    raw = base64.b64decode(image_bytes_b64, validate=False)
    resp = rekognition().detect_labels(
        Image={"Bytes": raw},
        MaxLabels=20,
        MinConfidence=70,
    )

    regions: List[Dict[str, Any]] = []
    for label in resp.get("Labels", []):
        for instance in label.get("Instances", []):
            box = instance.get("BoundingBox", {})
            if not box:
                continue
            left = float(box.get("Left", 0))
            top = float(box.get("Top", 0))
            width = float(box.get("Width", 0))
            height = float(box.get("Height", 0))
            regions.append(
                {
                    "label": label.get("Name", "object"),
                    "bbox": [left, top, width, height],
                    "area": width * height,
                }
            )

    # Sort by area descending and take the top 3
    regions.sort(key=lambda r: r["area"], reverse=True)
    top3 = [{"label": r["label"], "bbox": r["bbox"]} for r in regions[:3]]

    return {"regions": top3}
