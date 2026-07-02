"""Singleton configuration — reads environment variables once at module load."""

from __future__ import annotations

import os


class Config:
    """Application-wide configuration read from environment variables."""

    # AWS region where the stack is deployed
    AWS_REGION: str = os.getenv("AWS_REGION_OVERRIDE", "us-east-1")

    # Bedrock region (Global Inference Profiles live here)
    BEDROCK_REGION: str = os.getenv("BEDROCK_REGION", "eu-west-1")

    # SageMaker endpoints
    SAGEMAKER_ENDPOINT_NAME: str = os.getenv("SAGEMAKER_ENDPOINT_NAME", "ai-image-detector")
    FACE_FORENSICS_ENDPOINT_NAME: str = os.getenv(
        "FACE_FORENSICS_ENDPOINT_NAME", "ai-aigc-ensemble"
    )
    COMPOSITE_SPECIALIST_ENDPOINT_NAME: str = os.getenv(
        "COMPOSITE_SPECIALIST_ENDPOINT_NAME", "ai-composite-specialist"
    )

    # DynamoDB
    DYNAMODB_DETECTION_TABLE: str = os.getenv(
        "DYNAMODB_DETECTION_TABLE", "ai-detection-results"
    )
    DYNAMODB_RATE_LIMIT_TABLE: str = os.getenv(
        "DYNAMODB_RATE_LIMIT_TABLE", "generation-rate-limits"
    )

    # S3
    S3_INTAKE_BUCKET_NAME: str = os.getenv("S3_INTAKE_BUCKET_NAME", "")

    # SNS
    SNS_TOPIC_ARN: str = os.getenv("SNS_TOPIC_ARN", "")

    # KMS
    KMS_SIGNING_KEY_ARN: str = os.getenv("KMS_SIGNING_KEY_ARN", "")

    # Bedrock guardrail (must be set post-deploy)
    BEDROCK_GUARDRAIL_ID: str = os.getenv("BEDROCK_GUARDRAIL_ID", "REPLACE_ME")

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # Feature flags
    USE_AGENT: bool = os.getenv("USE_AGENT", "false").lower() == "true"
    AGENTCORE_RUNTIME_ARN: str = os.getenv("AGENTCORE_RUNTIME_ARN", "")

    # Alert threshold — publish SNS when probability_score exceeds this
    ALERT_THRESHOLD: float = float(os.getenv("ALERT_THRESHOLD", "0.85"))

    # Detection result retention (DynamoDB TTL)
    DETECTION_RETENTION_DAYS: int = int(os.getenv("DETECTION_RETENTION_DAYS", "180"))

    # Cache window for content-hash idempotency (hours)
    CACHE_TTL_HOURS: int = int(os.getenv("CACHE_TTL_HOURS", "24"))
