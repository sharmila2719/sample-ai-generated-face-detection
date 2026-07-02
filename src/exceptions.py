"""Typed exceptions for the detection pipeline."""

from __future__ import annotations

from typing import Any, Dict, Optional


class PipelineException(Exception):
    """Base class for all pipeline errors."""

    http_status: int = 500
    error_code: str = "PIPELINE_ERROR"

    def __init__(self, message: str, **kwargs: Any) -> None:
        super().__init__(message)
        self.message = message
        self.extra = kwargs

    def to_dict(self, request_id: Optional[str] = None) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "error_code": self.error_code,
            "error_message": self.message,
        }
        if request_id:
            payload["request_id"] = request_id
        return payload


class ValidationError(PipelineException):
    """Request payload did not pass validation."""

    http_status = 400
    error_code = "VALIDATION_ERROR"

    def __init__(self, message: str, field: Optional[str] = None) -> None:
        super().__init__(message, field=field)
        self.field = field

    def to_dict(self, request_id: Optional[str] = None) -> Dict[str, Any]:
        d = super().to_dict(request_id)
        if self.field:
            d["field"] = self.field
        return d


class StorageError(PipelineException):
    """S3 or DynamoDB operation failed."""

    http_status = 502
    error_code = "STORAGE_ERROR"


class DynamoWriteError(StorageError):
    """DynamoDB write failed after retries."""

    error_code = "DYNAMO_WRITE_ERROR"


class RateLimitExceeded(PipelineException):
    """Tenant exceeded their request quota."""

    http_status = 429
    error_code = "RATE_LIMIT_EXCEEDED"


class ModelInvocationError(PipelineException):
    """Bedrock or SageMaker invocation failed."""

    http_status = 502
    error_code = "MODEL_INVOCATION_ERROR"
