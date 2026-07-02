"""Shared EXIF extractor — parses image metadata from raw bytes."""

from __future__ import annotations

import base64
import io
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

try:
    from PIL import Image
    from PIL.ExifTags import TAGS
    _PIL_AVAILABLE = True
except ImportError:
    _PIL_AVAILABLE = False


@dataclass
class ExifInfo:
    """Structured representation of image EXIF metadata."""

    make: Optional[str] = None
    model: Optional[str] = None
    datetime_original: Optional[datetime] = None
    software: Optional[str] = None
    gps_present: bool = False
    is_recent_exif: bool = False


def extract_exif(image_bytes_b64: str) -> ExifInfo:
    """Decode a base64 image and extract EXIF metadata.

    Returns an :class:`ExifInfo` with ``is_recent_exif=True`` only when
    the image carries camera Make + Model metadata AND a DateTimeOriginal
    within the last 10 years.
    """
    if not _PIL_AVAILABLE:
        return ExifInfo()

    try:
        raw = base64.b64decode(image_bytes_b64, validate=False)
        img = Image.open(io.BytesIO(raw))
        exif_data = img._getexif()  # type: ignore[attr-defined]
    except Exception:
        return ExifInfo()

    if not exif_data:
        return ExifInfo()

    decoded = {TAGS.get(k, k): v for k, v in exif_data.items()}

    make = decoded.get("Make")
    model = decoded.get("Model")
    software = decoded.get("Software")
    dt_str = decoded.get("DateTimeOriginal")
    gps = decoded.get("GPSInfo") is not None

    dt_original: Optional[datetime] = None
    if dt_str:
        try:
            dt_original = datetime.strptime(dt_str, "%Y:%m:%d %H:%M:%S").replace(
                tzinfo=timezone.utc
            )
        except ValueError:
            pass

    now = datetime.now(tz=timezone.utc)
    recent = (
        bool(make)
        and bool(model)
        and dt_original is not None
        and (now - dt_original).days < 365 * 10
    )

    return ExifInfo(
        make=make,
        model=model,
        datetime_original=dt_original,
        software=software,
        gps_present=gps,
        is_recent_exif=recent,
    )
