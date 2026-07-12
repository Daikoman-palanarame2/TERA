from dataclasses import dataclass
from typing import List, Optional, Any
from app.router.route_types import RouteOption, RoutingDecision
from app.verification.verification_types import SchemaType, VerificationResult

"""
This module defines the request, response, and output structures
used across the TERA end-to-end inference coordination pipeline.
"""

@dataclass(frozen=True)
class InferenceRequest:
    """
    Purpose:
        Carries prompt text, cost parameters, Lagrangian multiplier lambda,
        and ROVL validation constraints.
    """
    prompt: str
    c2: float
    c3: float
    lambda_coeff: float
    alpha_dense: float
    schema_type: SchemaType = SchemaType.NONE
    regex_pattern: Optional[str] = None
    min_chars: Optional[int] = None
    max_chars: Optional[int] = None


@dataclass(frozen=True)
class ModelOutput:
    """
    Purpose:
        A generic, provider-agnostic data wrapper returned by any LLM adapter.
    """
    text: str
    token_probs: Optional[List[float]] = None
    metadata: Optional[dict[str, Any]] = None


@dataclass(frozen=True)
class InferenceResponse:
    """
    Purpose:
        Carries the final response text, selected route, router decision metrics,
        validation metrics, escalation status, and comprehensive telemetry metadata.
    """
    final_response: str
    selected_route: RouteOption
    routing_decision: RoutingDecision
    verification_result: Optional[VerificationResult]
    escalated: bool
    metadata: Optional[dict[str, Any]] = None
