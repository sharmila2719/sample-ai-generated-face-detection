"""C2PA provenance verifier — stub only.

The live C2PA tool was removed from the cascade on 2026-05-13 (face-swap
detection rework). This module is retained so legacy SageMaker code paths
that import it don't crash on startup.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class ProvenanceResult:
    """Wire-compatible placeholder returned by the stub verifier."""

    provenance_valid: bool = False
    c2pa_claim: Optional[str] = None
    error: Optional[str] = "c2pa_library_unavailable"


def verify_provenance(image_bytes_b64: str) -> ProvenanceResult:  # noqa: ARG001
    """Return a neutral stub — no actual C2PA check runs."""
    return ProvenanceResult()
