"""Lambda handler for POST /api/upload-url — returns a pre-signed S3 PUT URL."""

from __future__ import annotations

import json
import uuid
from typing import Any, Dict

import boto3

from src.config import Config
from src.logger import get_logger

logger = get_logger(__name__)

_CORS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type,X-Tenant-ID",
    "Access-Control-Allow-Methods": "POST,OPTIONS",
}

# Pre-signed URL expiry (seconds)
_URL_EXPIRY = 300

# Allowed image MIME types
_ALLOWED_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/gif",
}


def lambda_handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    if (event.get("httpMethod") or "") == "OPTIONS":
        return {"statusCode": 204, "headers": _CORS, "body": ""}

    try:
        body = json.loads(event.get("body") or "{}")
        content_type = body.get("content_type", "image/jpeg")
        filename = body.get("filename", f"{uuid.uuid4()}.jpg")

        if content_type not in _ALLOWED_CONTENT_TYPES:
            return {
                "statusCode": 400,
                "headers": {"Content-Type": "application/json", **_CORS},
                "body": json.dumps({"error": f"Unsupported content type: {content_type}"}),
            }

        s3_key = f"uploads/{uuid.uuid4()}/{filename}"
        bucket = Config.S3_INTAKE_BUCKET_NAME

        s3_client = boto3.client("s3", region_name=Config.AWS_REGION)
        presigned_url = s3_client.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": bucket,
                "Key": s3_key,
                "ContentType": content_type,
            },
            ExpiresIn=_URL_EXPIRY,
        )

        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json", **_CORS},
            "body": json.dumps({
                "upload_url": presigned_url,
                "s3_bucket": bucket,
                "s3_key": s3_key,
                "expires_in": _URL_EXPIRY,
            }),
        }

    except Exception as exc:  # noqa: BLE001
        logger.error("upload_url.error", extra={"error": str(exc)})
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json", **_CORS},
            "body": json.dumps({"error": "Failed to generate upload URL"}),
        }
