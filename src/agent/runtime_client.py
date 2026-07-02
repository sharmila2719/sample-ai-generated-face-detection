"""AgentCore Runtime client (dormant — requires Docker / ECR deployment).

When ``AGENTCORE_RUNTIME_ARN`` is set, the detection handler routes
through this client instead of the inline orchestrator. The inline path
is used in production today.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict

from src.aws_clients import get_client
from src.logger import get_logger

logger = get_logger(__name__)

_ALLOWED_RESPONSE_KEYS = {
    "classification",
    "probability_score",
    "evidence",
    "signals_consulted",
    "reasoning",
    "model_ids_used",
    "composite_analysis",
    "composite_signal",
    "celebrities",
}


class AgentInvocationError(Exception):
    """Raised when the AgentCore Runtime call fails."""

    def __init__(self, message: str, error_code: str = "AGENT_INVOCATION_FAILED") -> None:
        super().__init__(message)
        self.error_code = error_code


class AgentRuntimeClient:
    """Thin wrapper around Bedrock AgentCore Runtime InvokeAgentRuntime."""

    def __init__(self, runtime_arn: str) -> None:
        self._arn = runtime_arn
        self._client = get_client("bedrock-agentcore", region="us-east-1")

    @classmethod
    def from_env(cls) -> "AgentRuntimeClient":
        arn = os.getenv("AGENTCORE_RUNTIME_ARN", "")
        if not arn:
            raise AgentInvocationError(
                "AGENTCORE_RUNTIME_ARN is not set", error_code="AGENT_INVOCATION_FAILED"
            )
        return cls(arn)

    def invoke(self, payload: Dict[str, Any], *, request_id: str) -> Dict[str, Any]:
        """Invoke the AgentCore Runtime and return the parsed response."""
        try:
            resp = self._client.invoke_agent_runtime(
                agentRuntimeArn=self._arn,
                requestBody=json.dumps(payload),
            )
            body = json.loads(resp["responseBody"])
        except Exception as exc:
            raise AgentInvocationError(str(exc)) from exc

        # Strict parse — only pass through allowed keys
        result = {k: v for k, v in body.items() if k in _ALLOWED_RESPONSE_KEYS}
        if "classification" not in result:
            raise AgentInvocationError(
                "Agent response missing 'classification'",
                error_code="AGENT_RESPONSE_MALFORMED",
            )
        return result
