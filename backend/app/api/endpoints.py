import logging
from fastapi import APIRouter, Request
from app.schemas.routing import RouteRequest, RouteResponse, RoutingDecision, TokenStats, CostStats
from app.router.router_service import RouterService
from app.schemas.data_contracts import InferenceRequest

router = APIRouter()
logger = logging.getLogger(__name__)
router_service = RouterService()

@router.get("/health")
async def health_check():
    """
    Returns the health status of the TERA service.
    """
    return {
        "status": "ok"
    }

@router.get("/ready")
async def ready_check():
    """
    Returns the readiness status of the TERA service.
    """
    return {
        "status": "ok"
    }

@router.post("/route", response_model=RouteResponse)
async def route_prompt(route_request: RouteRequest, request: Request):
    """
    Ingests a prompt, executes the TERAOrchestrator V2 pipeline, and returns 
    the response and routing metrics conforming to the RouteResponse schema.
    """
    logger.info(f"Received routing request for prompt length: {len(route_request.prompt)}")
    
    # 1. Access the global TERAOrchestrator from app state
    orchestrator = request.app.state.orchestrator
    
    # 2. Build V2 InferenceRequest
    context = route_request.context or {}
    raw_task_id = context.get("task_id") or "task_0_default"
    # Clean task ID to satisfy strict Pydantic pattern constraint: ^task_\d+_[a-zA-Z0-9]+$
    cleaned_id = "".join(c for c in str(raw_task_id) if c.isalnum())
    if not cleaned_id:
        cleaned_id = "default"
    conforming_task_id = f"task_0_{cleaned_id}"
    
    c2 = float(context.get("c2", 10.0))
    c3 = float(context.get("c3", 100.0))
    lambda_coeff = float(context.get("lambda_coeff", 0.5))
    alpha_dense = float(context.get("alpha_dense", 0.9))
    schema_type = str(context.get("schema_type", "none")).lower()
    regex_pattern = context.get("regex_pattern")
    
    inf_req = InferenceRequest(
        prompt=route_request.prompt,
        task_id=conforming_task_id,
        c2=c2,
        c3=c3,
        lambda_coeff=lambda_coeff,
        alpha_dense=alpha_dense,
        schema_type=schema_type,
        regex_pattern=regex_pattern
    )
    
    # 3. Process via TERAOrchestrator
    v2_res = await orchestrator.process_request_async(inf_req)
    
    # 4. Map V2 InferenceResponse to V1 RouteResponse
    selected_model = "local_llm" if v2_res.route_taken == "local_llm" else "remote_fallback"
    confidence = v2_res.verification.calibrated_confidence if (v2_res.verification and hasattr(v2_res.verification, "calibrated_confidence")) else 1.0
    if confidence is None:
        confidence = 1.0
        
    decision = RoutingDecision(
        selected_model=selected_model,
        confidence=float(confidence),
        route=v2_res.route_taken,
        rationale=f"Processed via V2 TERA pipeline: {v2_res.route_taken}"
    )
    
    input_tokens = len(route_request.prompt) // 4
    output_tokens = v2_res.tokens_consumed
    total_tokens = input_tokens + output_tokens
    
    # Calculate savings
    saved_tokens = max(0, (input_tokens + output_tokens) - total_tokens) if v2_res.route_taken == "local_llm" else 0
    
    tokens_stats = TokenStats(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
        saved_tokens=saved_tokens
    )
    
    # Cost calculations
    actual_cost = (input_tokens * 0.15) / 1e6 + (output_tokens * 0.60) / 1e6 if v2_res.route_taken == "local_llm" else (input_tokens * 1.5) / 1e6 + (output_tokens * 5.0) / 1e6
    saved_cost = max(0.0, ((input_tokens * 1.5) / 1e6 + (output_tokens * 5.0) / 1e6) - actual_cost) if v2_res.route_taken == "local_llm" else 0.0
    
    cost_stats = CostStats(
        estimated_cost_usd=float(actual_cost),
        saved_cost_usd=float(saved_cost)
    )
    
    return RouteResponse(
        response=v2_res.final_response,
        routing_decision=decision,
        tokens=tokens_stats,
        cost=cost_stats
    )
