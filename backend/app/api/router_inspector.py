import os
import re
import time
import pickle
import numpy as np
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any

from app.core.settings import settings
from app.router.runtime_router import RuntimeRouter
from app.router.regex_patterns import DEFAULT_PATTERNS
from app.verification.verification_types import SchemaType
from app.verification.rovl import ROVL
from app.inference.inference_types import InferenceRequest, InferenceResponse
from app.inference.orchestrator import InferenceOrchestrator
from app.inference.cheap_model import CheapModel
from app.inference.dense_model import DenseModel
from app.inference.fireworks_model import FireworksModel

router = APIRouter()

# Request model
class InspectorRequest(BaseModel):
    prompt: str
    c2: Optional[float] = 10.0
    c3: Optional[float] = 100.0
    lambda_coeff: Optional[float] = 0.5
    alpha_dense: Optional[float] = 0.9
    schema_type: Optional[str] = "none"
    regex_pattern: Optional[str] = None
    min_chars: Optional[int] = None
    max_chars: Optional[int] = None

@router.post("/router-inspector")
async def inspect_route(request: InspectorRequest):
    """
    Executes TERA inference pipeline for a developer diagnostics prompt
    and returns feature, router, validation, and final output data.
    """
    if not request.prompt or not request.prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt must not be empty.")

    try:
        # 1. Initialize TERA runtime modules
        models_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../models"))
        router_instance = RuntimeRouter(models_dir)
        
        # Determine adapter modes (mock fallback if no Fireworks API key is set)
        if settings.fireworks_api_key:
            cheap_model = FireworksModel(model_name=settings.cheap_model)
            dense_model = FireworksModel(model_name=settings.dense_model)
        else:
            cheap_model = CheapModel()
            dense_model = DenseModel()
            
        rovl = ROVL(entropy_threshold=settings.entropy_threshold)
        orchestrator = InferenceOrchestrator(router_instance, cheap_model, dense_model, rovl)

        # 2. Parse SchemaType String
        schema_map = {
            "none": SchemaType.NONE,
            "json": SchemaType.JSON,
            "regex": SchemaType.REGEX
        }
        schema_enum = schema_map.get(request.schema_type.lower(), SchemaType.NONE)

        # 3. Create InferenceRequest
        inf_req = InferenceRequest(
            prompt=request.prompt,
            c2=request.c2,
            c3=request.c3,
            lambda_coeff=request.lambda_coeff,
            alpha_dense=request.alpha_dense,
            schema_type=schema_enum,
            regex_pattern=request.regex_pattern,
            min_chars=request.min_chars,
            max_chars=request.max_chars
        )

        # 4. Execute Orchestrator Inference
        response = await orchestrator.run_async(inf_req)
        
        # 5. Extract Feature Vector and compute auxiliary features
        decision = response.routing_decision
        features = decision.feature_vector
        
        features_arr = np.array([[
            features.length, 
            features.symbol_ratio, 
            features.regex_density, 
            features.bm25_score
        ]])
        
        # Load raw probability from pickle object
        raw_prob = float(router_instance.probability_estimator.logistic_model.predict_proba(features_arr)[0, 1])

        # Auxiliary keyword counts
        code_matched = bool(DEFAULT_PATTERNS["code"].search(request.prompt))
        math_matched = bool(DEFAULT_PATTERNS["calculate"].search(request.prompt))
        reasoning_count = sum(1 for _ in re.finditer(r"\b(because|therefore|since|logical|conclude|consequence|reason|why|how)\b", request.prompt, re.IGNORECASE))
        numeric_density = sum(1 for c in request.prompt if c.isdigit()) / max(1, len(request.prompt))

        # 6. Build structured inspector payload
        return {
            "prompt": request.prompt,
            "features": {
                "length": features.length,
                "symbol_ratio": float(features.symbol_ratio),
                "regex_density": int(features.regex_density),
                "bm25_score": float(features.bm25_score),
                "code_detected": code_matched,
                "math_detected": math_matched,
                "reasoning_count": reasoning_count,
                "numeric_density": float(numeric_density)
            },
            "router": {
                "raw_probability": raw_prob,
                "calibrated_probability": float(decision.calibrated_probability),
                "selected_route": decision.selected_route.value
            },
            "utilities": {
                "cheap": float(decision.cheap_utility),
                "dense": float(decision.dense_utility),
                "cascade": float(decision.cascade_utility)
            },
            "verification": {
                "accepted": response.verification_result.status.value == "pass" if response.verification_result else True,
                "confidence": float(decision.calibrated_probability),
                "entropy": float(response.verification_result.output_entropy) if (response.verification_result and response.verification_result.output_entropy is not None) else None,
                "escalated": response.escalated,
                "reason": response.metadata.get("escalation_reason") if response.metadata else None
            },
            "answer": response.final_response,
            "metadata": response.metadata
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
