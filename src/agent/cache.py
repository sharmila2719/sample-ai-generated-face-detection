"""Content-hash idempotency cache lookup (Req 15)."""

from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Optional

from src.aws_clients import dynamodb
from src.config import Config
from src.logger import get_logger

logger = get_logger(__name__)


class DetectionCacheLookup:
    """Look up a prior detection result by content-hash + tenant."""

    def __init__(self, table_name: str = Config.DYNAMODB_DETECTION_TABLE) -> None:
        self._table = table_name

    def lookup(self, tenant_id: str, content_hash: str) -> Optional[Dict[str, Any]]:
        """Query the by-tenant-content-hash GSI.

        Returns the most recent matching row (within the cache window) or
        ``None`` when no cached result exists.
        """
        pk = f"{tenant_id}#{content_hash}"
        cutoff = (
            datetime.now(tz=timezone.utc) - timedelta(hours=Config.CACHE_TTL_HOURS)
        ).isoformat()

        try:
            resp = dynamodb().query(
                TableName=self._table,
                IndexName="by-tenant-content-hash",
                KeyConditionExpression=(
                    "content_hash_pk = :pk AND detection_timestamp >= :cutoff"
                ),
                ExpressionAttributeValues={
                    ":pk": {"S": pk},
                    ":cutoff": {"S": cutoff},
                },
                ScanIndexForward=False,  # newest first
                Limit=1,
            )
            items = resp.get("Items", [])
            if not items:
                return None
            row = items[0]
            return self._deserialise(row)
        except Exception as exc:
            logger.warning("cache.lookup_failed", extra={"error": str(exc)})
            return None

    @staticmethod
    def _deserialise(row: Dict[str, Any]) -> Dict[str, Any]:
        """Convert DynamoDB attribute-value map to a plain dict."""

        def _val(attr: Dict[str, Any]) -> Any:
            if "S" in attr:
                return attr["S"]
            if "N" in attr:
                return float(attr["N"])
            if "BOOL" in attr:
                return attr["BOOL"]
            return None

        result = {k: _val(v) for k, v in row.items()}
        for json_key in ("evidence", "signals_consulted", "model_ids_used",
                         "composite_analysis", "composite_signal", "celebrities"):
            if json_key in result and isinstance(result[json_key], str):
                try:
                    result[json_key] = json.loads(result[json_key])
                except json.JSONDecodeError:
                    pass
        return result
