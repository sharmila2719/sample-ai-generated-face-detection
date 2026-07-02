"""Tool: exif_check — extracts EXIF metadata and returns a fast-path signal."""

from __future__ import annotations

from typing import Any, Dict

from src.agent.tools._timing import timed
from src.exif import extract_exif


@timed("exif_check")
def exif_check(image_bytes_b64: str, *, request_id: str = "") -> Dict[str, Any]:
    """Parse EXIF data and determine if the image is a recent camera photo.

    Returns:
        is_recent_exif: True when Make + Model + recent DateTimeOriginal present.
        make, model, software, gps_present, datetime_original (ISO string).
    """
    info = extract_exif(image_bytes_b64)
    return {
        "is_recent_exif": info.is_recent_exif,
        "make": info.make,
        "model": info.model,
        "software": info.software,
        "gps_present": info.gps_present,
        "datetime_original": (
            info.datetime_original.isoformat() if info.datetime_original else None
        ),
    }
