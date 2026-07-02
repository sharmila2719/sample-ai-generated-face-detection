"""SNS alert publisher."""

from __future__ import annotations

import json
from typing import Any, Dict

from src.aws_clients import sns
from src.config import Config
from src.logger import get_logger

logger = get_logger(__name__)


def publish_alert(subject: str, payload: Dict[str, Any]) -> None:
    """Publish a detection alert to the SNS topic.

    Silently logs on failure so a broken SNS topic never crashes the
    detection response.
    """
    topic_arn = Config.SNS_TOPIC_ARN
    if not topic_arn:
        logger.warning("alerts.sns_topic_not_configured")
        return
    try:
        sns().publish(
            TopicArn=topic_arn,
            Subject=subject[:100],
            Message=json.dumps(payload, default=str),
        )
        logger.info("alerts.published", extra={"subject": subject})
    except Exception as exc:  # noqa: BLE001
        logger.error("alerts.publish_failed", extra={"error": str(exc)})
