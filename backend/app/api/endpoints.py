import logging
from fastapi import APIRouter, HTTPException
from app.schemas.routing import RouteRequest, RouteResponse, RoutingDecision, TokenStats, CostStats
from app.router.router_service import RouterService

router = APIRouter()
logger = logging.getLogger(__name__)
router_service = RouterService()

@router.get("/health")
async def health_check():
    """
    Returns the health status and current version of the TERA service.
    """
    return {
        "status": "healthy",
        "version": "1.0.0"
    }

@router.post("/route", response_model=RouteResponse)
async def route_prompt(request: RouteRequest):
    """
    Ingests a prompt, executes the ML routing decision, and returns the response 
    and routing metrics. Currently handles the placeholder NotImplementedError 
    gracefully by returning mock values.
    """
    logger.info(f"Received routing request for prompt length: {len(request.prompt)}")
    
    try:
        # Call the router service (will raise NotImplementedError in Phase 1)
        await router_service.route(request.prompt)
        
        # If it doesn't raise, raise an exception as it's not expected in Phase 1
        raise HTTPException(
            status_code=500, 
            detail="Unexpected success from routing service skeleton."
        )
    except NotImplementedError as e:
        logger.warning(f"RouterService.route called but raised exception: {e}")
        # Return a graceful placeholder response as requested
        return RouteResponse(
            response=(
                "[Placeholder Response] The TERA ML Router is in skeleton mode (Phase 1). "
                "Once Phase 2 is complete, this will execute the dynamically routed model."
            ),
            routing_decision=RoutingDecision(
                selected_model="skeleton-model",
                confidence=0.0,
                route="skeleton",
                rationale="Fallback to skeleton response because ML Router is not yet implemented."
            ),
            tokens=TokenStats(
                input_tokens=len(request.prompt) // 4,
                output_tokens=30,
                total_tokens=(len(request.prompt) // 4) + 30,
                saved_tokens=0
            ),
            cost=CostStats(
                estimated_cost_usd=0.0,
                saved_cost_usd=0.0
            )
        )
