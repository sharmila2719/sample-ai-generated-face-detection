"""pytest configuration and shared fixtures."""

import os
import pytest

# Provide dummy environment variables so modules can be imported without real AWS credentials
os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")
os.environ.setdefault("AWS_ACCESS_KEY_ID", "test-key-id")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "test-secret")
os.environ.setdefault("DYNAMODB_DETECTION_TABLE", "ai-detection-results")
os.environ.setdefault("DYNAMODB_RATE_LIMIT_TABLE", "generation-rate-limits")
os.environ.setdefault("S3_INTAKE_BUCKET_NAME", "test-intake-bucket")
os.environ.setdefault("SNS_TOPIC_ARN", "arn:aws:sns:us-east-1:123456789012:ai-detection-alerts")
os.environ.setdefault("SAGEMAKER_ENDPOINT_NAME", "ai-image-detector")
os.environ.setdefault("USE_AGENT", "true")
os.environ.setdefault("BEDROCK_GUARDRAIL_ID", "test-guardrail")
os.environ.setdefault("KMS_SIGNING_KEY_ARN", "arn:aws:kms:us-east-1:123456789012:key/test")
