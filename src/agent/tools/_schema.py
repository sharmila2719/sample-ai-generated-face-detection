"""JSON schema helpers for tool return shapes."""

from __future__ import annotations

from typing import Any, Dict, List, Optional


def make_vision_result(
    probability_score: float,
    classification: str,
    rationale: str,
    regions: Optional[List[Dict[str, Any]]] = None,
    tool_name: str = "",
    duration_ms: int = 0,
    model_id: str = "",
) -> Dict[str, Any]:
    """Build a canonical vision-tool return dict."""
    return {
        "tool_name": tool_name,
        "duration_ms": duration_ms,
        "probability_score": float(probability_score),
        "classification": classification,
        "rationale": rationale,
        "regions": regions or [],
        "model_id": model_id,
    }


def make_error(tool_name: str, error_code: str, error_message: str, duration_ms: int = 0) -> Dict[str, Any]:
    return {
        "tool_name": tool_name,
        "duration_ms": duration_ms,
        "error_code": error_code,
        "error_message": error_message,
    }
