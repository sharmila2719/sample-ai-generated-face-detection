"""Per-tenant rate limiting using DynamoDB atomic counters."""

from __future__ import annotations

import time
from typing import Optional

from src.aws_clients import dynamodb
from src.config import Config
from src.logger import get_logger

logger = get_logger(__name__)

# Default quota: 100 requests per minute per tenant
DEFAULT_QUOTA = int(100)
WINDOW_SECONDS = 60


def check_rate_limit(tenant_id: str, quota: int = DEFAULT_QUOTA) -> bool:
    """Atomically increment the per-tenant counter and check against ``quota``.

    Returns ``True`` if the request is allowed, ``False`` if quota exceeded.
    Uses a 1-minute sliding window keyed on ``{tenant_id}#{window_epoch}``.
    """
    window = int(time.time()) // WINDOW_SECONDS
    pk = f"{tenant_id}#{window}"
    table = Config.DYNAMODB_RATE_LIMIT_TABLE

    try:
        resp = dynamodb().update_item(
            TableName=table,
            Key={"rate_pk": {"S": pk}},
            UpdateExpression="ADD request_count :one SET #ttl = if_not_exists(#ttl, :exp)",
            ExpressionAttributeNames={"#ttl": "ttl"},
            ExpressionAttributeValues={
                ":one": {"N": "1"},
                ":exp": {"N": str(int(time.time()) + WINDOW_SECONDS * 2)},
            },
            ReturnValues="UPDATED_NEW",
        )
        count = int(resp["Attributes"]["request_count"]["N"])
        allowed = count <= quota
        if not allowed:
            logger.warning(
                "rate_limit.exceeded",
                extra={"tenant_id": tenant_id, "count": count, "quota": quota},
            )
        return allowed
    except Exception as exc:  # noqa: BLE001
        # On DDB failure, allow the request (fail open) and log the error.
        logger.error("rate_limit.check_failed", extra={"error": str(exc)})
        return True
