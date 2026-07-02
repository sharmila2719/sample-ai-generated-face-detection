"""boto3 singleton factory — one client per service per region."""

from __future__ import annotations

import threading
from typing import Any, Dict, Optional

import boto3

from src.config import Config

_lock = threading.Lock()
_clients: Dict[str, Any] = {}


def get_client(service: str, region: Optional[str] = None) -> Any:
    """Return a cached boto3 client for ``service`` in ``region``."""
    region = region or Config.AWS_REGION
    key = f"{service}:{region}"
    if key not in _clients:
        with _lock:
            if key not in _clients:
                _clients[key] = boto3.client(service, region_name=region)
    return _clients[key]


def s3() -> Any:
    return get_client("s3")


def dynamodb() -> Any:
    return get_client("dynamodb")


def rekognition() -> Any:
    return get_client("rekognition")


def sagemaker_runtime() -> Any:
    return get_client("sagemaker-runtime")


def bedrock_runtime() -> Any:
    return get_client("bedrock-runtime", region=Config.BEDROCK_REGION)


def sns() -> Any:
    return get_client("sns")


def secretsmanager() -> Any:
    return get_client("secretsmanager")


def kms() -> Any:
    return get_client("kms")
