"""Lambda handler for POST /api/detect and /api/detect/batch."""

from __future__ import annotations

import asyncio
import json
import os
from typing import Any, Dict

from src.agent.pipeline import AgentDetectionPipeline
from src.agent.runtime_client import AgentInvocationError, AgentRuntimeClient
from src.config import Config
from src.detection import DetectionPipeline
from src.exceptions import PipelineException, ValidationError
from src.logger import ContextLogger, get_logger
from src.utils import RequestTracer

logger = get_logger(__name__, Config.LOG_LEVEL)
context_logger = ContextLogger(logger)

_CORS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type,X-Tenant-ID,X-Request-ID",
    "Access-Control-Allow-Methods": "POST,OPTIONS",
    "Access-Control-Max-Age": "300",
}

_AGENT_ERROR_STATUS: Dict[str, int] = {
    "AGENT_TIMEOUT": 504,
    "AGENT_RESPONSE_MALFORMED": 502,
    "AGENT_THROTTLED": 429,
    "AGENT_INVOCATION_FAILED": 502,
}


def _pick_pipeline():
    """Select the detection pipeline based on USE_AGENT environment variable."""
    if os.getenv("USE_AGENT", "false").lower() != "true":
        return DetectionPipeline()

    if os.getenv("AGENTCORE_RUNTIME_ARN"):
        return AgentDetectionPipeline(AgentRuntimeClient.from_env())

    from src.agent.inline_orchestrator import InlineAgentOrchestrator
    return AgentDetectionPipeline(InlineAgentOrchestrator.from_env())


def lambda_handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    method = (
        event.get("httpMethod")
        or event.get("requestContext", {}).get("http", {}).get("method")
    )
    if method == "OPTIONS":
        return {"statusCode": 204, "headers": _CORS, "body": ""}

    request_id = RequestTracer.get_request_id_from_headers(event.get("headers", {}))
    context_logger.set_context(request_id=request_id)

    try:
        body = json.loads(event.get("body") or "{}")
        headers = event.get("headers") or {}
        tenant_id = (
            headers.get("X-Tenant-ID")
            or headers.get("x-tenant-id")
            or "default"
        )
        pipeline = _pick_pipeline()
        path = event.get("rawPath") or event.get("path") or ""
        is_batch = bool(body.get("batch_mode")) or path.endswith("/batch")

        if is_batch:
            images = body.get("images")
            if not isinstance(images, list):
                raise ValidationError("'images' must be a list for batch mode", field="images")
            results = asyncio.run(pipeline.detect_batch(images, tenant_id, request_id))
            return _ok(request_id, {"results": [r.to_dict() for r in results]})

        s3_bucket = body.get("s3_bucket")
        s3_key = body.get("s3_key")
        if not s3_bucket or not s3_key:
            raise ValidationError("s3_bucket and s3_key are required")

        force_fresh = bool(body.get("force_fresh")) or _header_bool(headers, "X-Force-Fresh")
        deep_analysis = bool(body.get("deep_analysis")) or _header_bool(headers, "X-Deep-Analysis")
        fast_mode = bool(body.get("fast_mode")) or _header_bool(headers, "X-Fast-Mode")

        response = asyncio.run(
            pipeline.detect_image(
                s3_bucket=s3_bucket,
                s3_key=s3_key,
                image_id=body.get("image_id"),
                tenant_id=tenant_id,
                request_id=request_id,
                force_fresh=force_fresh,
                deep_analysis=deep_analysis,
                fast_mode=fast_mode,
            )
        )
        return _ok(request_id, response.to_dict())

    except PipelineException as exc:
        context_logger.error(f"Pipeline error: {exc.message}")
        return _error(exc.http_status, request_id, exc.to_dict(request_id))
    except AgentInvocationError as exc:
        code = exc.error_code or "AGENT_INVOCATION_FAILED"
        status = _AGENT_ERROR_STATUS.get(code, 502)
        context_logger.error(f"Agent error [{code}]: {exc}")
        return _error(status, request_id, {"error_code": code, "error_message": str(exc), "request_id": request_id})
    except json.JSONDecodeError:
        return _error(400, request_id, {"error_code": "INVALID_JSON", "error_message": "Request body is not valid JSON", "request_id": request_id})
    except Exception as exc:  # noqa: BLE001
        context_logger.error(f"Unexpected error: {exc}")
        return _error(500, request_id, {"error_code": "INTERNAL_SERVER_ERROR", "error_message": "An unexpected error occurred", "request_id": request_id})


def _header_bool(headers: Dict[str, str], name: str) -> bool:
    return str(headers.get(name) or headers.get(name.lower()) or "").lower() == "true"


def _ok(request_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json", "X-Request-ID": request_id, **_CORS},
        "body": json.dumps(payload, default=str),
    }


def _error(status: int, request_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json", "X-Request-ID": request_id, **_CORS},
        "body": json.dumps(payload),
    }
