"""S3 image reader and DynamoDB detection-result writer."""

from __future__ import annotations

import base64
import hashlib
from typing import Any, Dict, Optional, Tuple

from src.aws_clients import dynamodb, s3
from src.config import Config
from src.exceptions import StorageError
from src.logger import get_logger

logger = get_logger(__name__)


def read_image_from_s3(bucket: str, key: str) -> Tuple[bytes, str]:
    """Download an image from S3 and return ``(raw_bytes, content_hash)``.

    Raises :class:`~src.exceptions.StorageError` on any S3 failure.
    """
    try:
        resp = s3().get_object(Bucket=bucket, Key=key)
        body: bytes = resp["Body"].read()
        content_hash = hashlib.sha256(body).hexdigest()
        return body, content_hash
    except Exception as exc:
        raise StorageError(f"S3 read failed for s3://{bucket}/{key}: {exc}") from exc


def image_to_b64(raw_bytes: bytes) -> str:
    """Encode raw image bytes to a base64 ASCII string."""
    return base64.b64encode(raw_bytes).decode("ascii")


def get_original_format(raw_bytes: bytes) -> str:
    """Sniff the image format from the first magic bytes."""
    if raw_bytes[:8] == b"\x89PNG\r\n\x1a\n":
        return "PNG"
    if raw_bytes[:3] == b"\xff\xd8\xff":
        return "JPEG"
    if raw_bytes[:4] in (b"RIFF", b"WEBP"):
        return "WEBP"
    if raw_bytes[:4] == b"GIF8":
        return "GIF"
    return "UNKNOWN"
