import os
import re
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, Dict, Any

from app.core.config import settings
from app.verification.rovl import ROVL
from app.schemas.data_contracts import InferenceRequest
from app.core.orchestrator import TERAOrchestrator
from app.inference.local_client import LocalModelClient
from app.inference.local_power_client import LocalPowerModelClient
from app.cache.semantic_cache import SemanticCache
from app.solvers.solver_registry import SolverRegistry
from app.solvers.plugins.arithmetic_solver import ArithmeticSolver
from app.solvers.plugins.logic_solver import LogicSolver
from app.solvers.plugins.text_counter_solver import TextCounterSolver
from app.solvers.plugins.word_problem_solver import WordProblemSolver
from app.parser.intent_parser import IntentParser
from app.router.regex_patterns import DEFAULT_PATTERNS

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
async def inspect_route(request: InspectorRequest, fastapi_req: Request) -> Dict[str, Any]:
    """Executes TERA V2 inference pipeline for diagnostics prompt and returns telemetry metrics."""
    if not request.prompt or not request.prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt must not be empty.")

    try:
        try:
            orchestrator = fastapi_req.app.state.orchestrator
        except AttributeError:
            # Fallback transient initialization for offline environments
            cache = SemanticCache(
                cache_dir=settings.tera_cache_dir,
                embedding_model_path=settings.tera_onnx_model_path
            )
            registry = SolverRegistry()
            registry.register_solver(ArithmeticSolver())
            registry.register_solver(LogicSolver())
            registry.register_solver(TextCounterSolver())
            registry.register_solver(WordProblemSolver())
            registry.lock()
            parser = IntentParser(registry)
            
            cheap_model = LocalModelClient(
                endpoint_url=settings.tera_local_inference_url,
                model_name=settings.tera_local_model_name,
                timeout_sec=settings.tera_model_timeout_sec,
            )
            dense_model = LocalPowerModelClient(
                endpoint_url=settings.tera_power_inference_url,
                model_name=settings.tera_power_model_name,
                timeout_sec=settings.tera_model_timeout_sec,
            )
                
            rovl = ROVL(entropy_threshold=settings.entropy_threshold)
            orchestrator = TERAOrchestrator(
                cache=cache,
                parser=parser,
                registry=registry,
                local_client=cheap_model,
                remote_client=dense_model,
                rovl=rovl,
                settings=settings
            )

        # 2. Parse request payload
        schema_type = str(request.schema_type or "none").lower()
        c2 = float(request.c2 if request.c2 is not None else 10.0)
        c3 = float(request.c3 if request.c3 is not None else 100.0)
        lambda_coeff = float(request.lambda_coeff if request.lambda_coeff is not None else 0.5)
        alpha_dense = float(request.alpha_dense if request.alpha_dense is not None else 0.9)

        # 3. Create InferenceRequest
        inf_req = InferenceRequest(
            prompt=request.prompt,
            task_id="task_0_diagnostic",
            c2=c2,
            c3=c3,
            lambda_coeff=lambda_coeff,
            alpha_dense=alpha_dense,
            schema_type=schema_type,
            regex_pattern=request.regex_pattern
        )

        # 4. Execute Orchestrator Inference
        response = await orchestrator.process_request_async(inf_req)
        
        # 5. Extract Feature Vector (V1 compatibility fallback)
        try:
            from app.router.feature_extractor import FeatureExtractor
            models_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../models"))
            fe = FeatureExtractor(models_dir)
            features = fe.extract(request.prompt)
            code_matched = bool(DEFAULT_PATTERNS["code"].search(request.prompt))
            math_matched = bool(DEFAULT_PATTERNS["calculate"].search(request.prompt))
            reasoning_count = sum(1 for _ in re.finditer(r"\b(because|therefore|since|logical|conclude|consequence|reason|why|how)\b", request.prompt, re.IGNORECASE))
            numeric_density = sum(1 for c in request.prompt if c.isdigit()) / max(1, len(request.prompt))
            
            raw_features = {
                "length": features.length,
                "symbol_ratio": float(features.symbol_ratio),
                "regex_density": int(features.regex_density),
                "bm25_score": float(features.bm25_score),
                "code_detected": code_matched,
                "math_detected": math_matched,
                "reasoning_count": reasoning_count,
                "numeric_density": float(numeric_density)
            }
        except Exception:
            raw_features = {
                "length": len(request.prompt),
                "symbol_ratio": 0.0,
                "regex_density": 0,
                "bm25_score": 0.0,
                "code_detected": False,
                "math_detected": False,
                "reasoning_count": 0,
                "numeric_density": 0.0
            }

        # 6. Build route and utility fallback structures
        router_route = "cheap" if response.route_taken in {"cache", "solver", "local_llm"} else "dense"
        
        router_data = {
            "raw_probability": 0.0 if router_route == "cheap" else 1.0,
            "calibrated_probability": 1.0,
            "selected_route": router_route
        }
        
        utilities_data = {
            "cheap": 1.0 if router_route == "cheap" else 0.0,
            "dense": 1.0 if router_route == "dense" else 0.0,
            "cascade": 0.0
        }

        # 7. Verification results mapping
        verification_data = {
            "accepted": response.verification.passed if response.verification else True,
            "confidence": 1.0,
            "entropy": float(response.verification.sequence_entropy) if (response.verification and response.verification.sequence_entropy is not None) else None,
            "escalated": response.route_taken == "remote_fallback",
            "reason": ", ".join(response.verification.failed_validators) if (response.verification and response.verification.failed_validators) else None
        }

        # 8. Token and Cost calculation
        prompt_tokens = len(request.prompt) // 4
        completion_tokens = response.tokens_consumed
        total_tokens = prompt_tokens + completion_tokens
        
        telemetry_data = {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "model_name": "local_llm" if response.route_taken == "local_llm" else "remote_fallback",
            "latency_ms": response.latency_ms
        }

        dense_baseline_cost = (prompt_tokens * 1.5) / 1e6 + (completion_tokens * 5.0) / 1e6
        if response.route_taken == "local_llm":
            actual_cost = (prompt_tokens * 0.15) / 1e6 + (completion_tokens * 0.60) / 1e6
            token_savings = total_tokens
            cost_savings_usd = max(0.0, dense_baseline_cost - actual_cost)
            cost_savings_percentage = (cost_savings_usd / dense_baseline_cost * 100.0) if dense_baseline_cost > 0 else 0.0
        else:
            actual_cost = dense_baseline_cost
            token_savings = 0
            cost_savings_usd = 0.0
            cost_savings_percentage = 0.0

        savings_data = {
            "dense_baseline_cost": float(dense_baseline_cost),
            "actual_cost": float(actual_cost),
            "cost_savings_usd": float(cost_savings_usd),
            "cost_savings_percentage": float(cost_savings_percentage),
            "token_savings": int(token_savings)
        }

        return {
            "prompt": request.prompt,
            "features": raw_features,
            "router": router_data,
            "utilities": utilities_data,
            "verification": verification_data,
            "telemetry": telemetry_data,
            "savings": savings_data,
            "answer": response.final_response,
            "metadata": {
                "route_taken": response.route_taken,
                "tokens_consumed": response.tokens_consumed,
                "latency_ms": response.latency_ms
            }
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
