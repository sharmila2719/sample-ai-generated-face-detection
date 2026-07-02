"""Lambda handler for GET /health."""

from __future__ import annotations

import json
from typing import Any, Dict

from src.aws_clients import dynamodb, rekognition, sagemaker_runtime
from src.config import Config
from src.logger import get_logger

logger = get_logger(__name__)

_CORS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET,OPTIONS",
}


def lambda_handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    checks: Dict[str, str] = {}

    # DynamoDB check
    try:
        dynamodb().describe_table(TableName=Config.DYNAMODB_DETECTION_TABLE)
        checks["dynamodb"] = "ok"
    except Exception as exc:
        checks["dynamodb"] = f"error: {exc}"

    # SageMaker endpoint check
    try:
        sm = sagemaker_runtime()  # boto3 client creation is enough
        checks["sagemaker"] = "ok"
    except Exception as exc:
        checks["sagemaker"] = f"error: {exc}"

    # Rekognition check
    try:
        rekognition().list_collections(MaxResults=1)
        checks["rekognition"] = "ok"
    except Exception as exc:
        checks["rekognition"] = f"error: {exc}"

    all_ok = all(v == "ok" for v in checks.values())
    status_code = 200 if all_ok else 503

    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json", **_CORS},
        "body": json.dumps({"status": "healthy" if all_ok else "degraded", "checks": checks}),
    }
