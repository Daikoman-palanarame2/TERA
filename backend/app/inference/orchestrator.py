import time
from typing import Optional

from app.router.route_types import RouteOption
from app.router.runtime_router import RuntimeRouter
from app.verification.verification_types import VerificationStatus, FailureReason
from app.verification.rovl import ROVL
from app.inference.model_interface import ModelInterface
from app.inference.inference_types import InferenceRequest, InferenceResponse

class InferenceOrchestrator:
    """
    Purpose:
        Coordinates the end-to-end TERA runtime execution flow:
        1. Requests a routing decision from the RuntimeRouter.
        2. Routes to the Dense model directly, OR routes to the Cheap model.
        3. If Cheap model is chosen, runs ROVL validation.
        4. If validation passes, returns cheap model generation.
        5. If validation fails, triggers automatic escalation, running the Dense model.
        6. Measures and returns telemetry performance indicators.
        
    Time Complexity:
        Overhead is dominated by model execution times; TERA routing and verification 
        calculations execute in microsecond scales (< 0.2 ms cumulative on CPU).
        
    Memory Complexity:
        O(L) to hold text completions and model structures in memory.
    """

    def __init__(
        self,
        router: RuntimeRouter,
        cheap_model: ModelInterface,
        dense_model: ModelInterface,
        rovl: ROVL
    ) -> None:
        """
        Purpose:
            Initializes the orchestrator with dependency-injected routing, model, and ROVL providers.
            
        Inputs:
            router: RuntimeRouter instance.
            cheap_model: ModelInterface implementation representing the cheap model lane.
            dense_model: ModelInterface implementation representing the dense model lane.
            rovl: ROVL validation orchestrator instance.
            
        Outputs:
            None
        """
        self.router = router
        self.cheap_model = cheap_model
        self.dense_model = dense_model
        self.rovl = rovl

    def run(self, request: InferenceRequest) -> InferenceResponse:
        """
        Purpose:
            Executes the TERA routing and inference pipeline for a request.
            
        Inputs:
            request: InferenceRequest containing prompt, hyperparameters, and constraints.
            
        Outputs:
            An InferenceResponse carrying the final output, metadata, and routing metrics.
            
        Time/Memory Complexity:
            O(L + T + Q * log(N)) + model latency.
        """
        # 1. Obtain routing decision
        decision = self.router.route(
            prompt=request.prompt,
            c2=request.c2,
            c3=request.c3,
            lambda_coeff=request.lambda_coeff,
            alpha_dense=request.alpha_dense
        )
        
        route = decision.selected_route
        
        # 2. Invoke appropriate path
        if route == RouteOption.DENSE:
            # Direct Dense Path
            dense_t0 = time.perf_counter()
            output = self.dense_model.generate(request.prompt)
            dense_time_ms = (time.perf_counter() - dense_t0) * 1000.0
            
            metadata = {
                "router_probability": decision.calibrated_probability,
                "cheap_utility": decision.cheap_utility,
                "dense_utility": decision.dense_utility,
                "cascade_utility": decision.cascade_utility,
                "verification_time_ms": 0.0,
                "inference_time_ms": float(dense_time_ms),
                "escalation_reason": None,
                "model_metadata": output.metadata
            }
            
            return InferenceResponse(
                final_response=output.text,
                selected_route=RouteOption.DENSE,
                routing_decision=decision,
                verification_result=None,
                escalated=False,
                metadata=metadata
            )
            
        else:
            # CHEAP or CASCADE model lane execution
            cheap_t0 = time.perf_counter()
            output = self.cheap_model.generate(request.prompt)
            cheap_time_ms = (time.perf_counter() - cheap_t0) * 1000.0
            
            # Run output verification check
            ver_t0 = time.perf_counter()
            ver_res = self.rovl.verify(
                text=output.text,
                token_probs=output.token_probs,
                schema_type=request.schema_type,
                regex_pattern=request.regex_pattern,
                min_chars=request.min_chars,
                max_chars=request.max_chars
            )
            ver_time_ms = (time.perf_counter() - ver_t0) * 1000.0
            
            # Check validation status
            if ver_res.status == VerificationStatus.PASS:
                metadata = {
                    "router_probability": decision.calibrated_probability,
                    "cheap_utility": decision.cheap_utility,
                    "dense_utility": decision.dense_utility,
                    "cascade_utility": decision.cascade_utility,
                    "verification_time_ms": float(ver_time_ms),
                    "inference_time_ms": float(cheap_time_ms),
                    "escalation_reason": None,
                    "model_metadata": output.metadata
                }
                
                return InferenceResponse(
                    final_response=output.text,
                    selected_route=route,
                    routing_decision=decision,
                    verification_result=ver_res,
                    escalated=False,
                    metadata=metadata
                )
            else:
                # Verification failed - trigger automatic escalation to M3
                dense_t0 = time.perf_counter()
                escalated_output = self.dense_model.generate(request.prompt)
                dense_time_ms = (time.perf_counter() - dense_t0) * 1000.0
                
                total_inference_time_ms = cheap_time_ms + dense_time_ms
                escalation_reason = ", ".join(r.value for r in ver_res.failure_reasons)
                
                metadata = {
                    "router_probability": decision.calibrated_probability,
                    "cheap_utility": decision.cheap_utility,
                    "dense_utility": decision.dense_utility,
                    "cascade_utility": decision.cascade_utility,
                    "verification_time_ms": float(ver_time_ms),
                    "inference_time_ms": float(total_inference_time_ms),
                    "escalation_reason": escalation_reason,
                    "model_metadata": escalated_output.metadata
                }
                
                return InferenceResponse(
                    final_response=escalated_output.text,
                    selected_route=route,
                    routing_decision=decision,
                    verification_result=ver_res,
                    escalated=True,
                    metadata=metadata
                )

    async def run_async(self, request: InferenceRequest) -> InferenceResponse:
        """
        Purpose:
            Executes the TERA routing and inference pipeline for a request asynchronously.
            Decisions, validation checks, calibration, utilities, and outputs remain identical.
            
        Inputs:
            request: InferenceRequest containing prompt, hyperparameters, and constraints.
            
        Outputs:
            An InferenceResponse carrying the final output, metadata, and routing metrics.
        """
        # 1. Obtain routing decision
        decision = self.router.route(
            prompt=request.prompt,
            c2=request.c2,
            c3=request.c3,
            lambda_coeff=request.lambda_coeff,
            alpha_dense=request.alpha_dense
        )
        
        route = decision.selected_route
        
        # 2. Invoke appropriate path
        if route == RouteOption.DENSE:
            # Direct Dense Path
            dense_t0 = time.perf_counter()
            output = await self.dense_model.generate_async(request.prompt)
            dense_time_ms = (time.perf_counter() - dense_t0) * 1000.0
            
            metadata = {
                "router_probability": decision.calibrated_probability,
                "cheap_utility": decision.cheap_utility,
                "dense_utility": decision.dense_utility,
                "cascade_utility": decision.cascade_utility,
                "verification_time_ms": 0.0,
                "inference_time_ms": float(dense_time_ms),
                "escalation_reason": None,
                "model_metadata": output.metadata
            }
            
            return InferenceResponse(
                final_response=output.text,
                selected_route=RouteOption.DENSE,
                routing_decision=decision,
                verification_result=None,
                escalated=False,
                metadata=metadata
            )
            
        else:
            # CHEAP or CASCADE model lane execution
            cheap_t0 = time.perf_counter()
            try:
                output = await self.cheap_model.generate_async(request.prompt)
                cheap_time_ms = (time.perf_counter() - cheap_t0) * 1000.0
                
                # Run output verification check
                ver_t0 = time.perf_counter()
                ver_res = self.rovl.verify(
                    text=output.text,
                    token_probs=output.token_probs,
                    schema_type=request.schema_type,
                    regex_pattern=request.regex_pattern,
                    min_chars=request.min_chars,
                    max_chars=request.max_chars
                )
                ver_time_ms = (time.perf_counter() - ver_t0) * 1000.0
            except Exception as cheap_err:
                # If cheap model fails completely, trigger automatic escalation to Dense
                # (This guarantees reliability and fallback when the cheap model endpoint goes down).
                cheap_time_ms = (time.perf_counter() - cheap_t0) * 1000.0
                ver_time_ms = 0.0
                
                from app.verification.verification_types import VerificationResult
                ver_res = VerificationResult(
                    status=VerificationStatus.FAIL,
                    failure_reasons=[FailureReason.ENTROPY],
                    output_entropy=None,
                    schema_passed=False,
                    length_passed=False,
                    stop_token_passed=False,
                    entropy_passed=False
                )
                
                # Escalation to Dense
                dense_t0 = time.perf_counter()
                escalated_output = await self.dense_model.generate_async(request.prompt)
                dense_time_ms = (time.perf_counter() - dense_t0) * 1000.0
                
                total_inference_time_ms = cheap_time_ms + dense_time_ms
                
                metadata = {
                    "router_probability": decision.calibrated_probability,
                    "cheap_utility": decision.cheap_utility,
                    "dense_utility": decision.dense_utility,
                    "cascade_utility": decision.cascade_utility,
                    "verification_time_ms": float(ver_time_ms),
                    "inference_time_ms": float(total_inference_time_ms),
                    "escalation_reason": f"cheap_model_failure: {cheap_err}",
                    "model_metadata": escalated_output.metadata
                }
                
                return InferenceResponse(
                    final_response=escalated_output.text,
                    selected_route=route,
                    routing_decision=decision,
                    verification_result=ver_res,
                    escalated=True,
                    metadata=metadata
                )
            
            # Check validation status
            if ver_res.status == VerificationStatus.PASS:
                metadata = {
                    "router_probability": decision.calibrated_probability,
                    "cheap_utility": decision.cheap_utility,
                    "dense_utility": decision.dense_utility,
                    "cascade_utility": decision.cascade_utility,
                    "verification_time_ms": float(ver_time_ms),
                    "inference_time_ms": float(cheap_time_ms),
                    "escalation_reason": None,
                    "model_metadata": output.metadata
                }
                
                return InferenceResponse(
                    final_response=output.text,
                    selected_route=route,
                    routing_decision=decision,
                    verification_result=ver_res,
                    escalated=False,
                    metadata=metadata
                )
            else:
                # Verification failed - trigger automatic escalation to M3
                dense_t0 = time.perf_counter()
                escalated_output = await self.dense_model.generate_async(request.prompt)
                dense_time_ms = (time.perf_counter() - dense_t0) * 1000.0
                
                total_inference_time_ms = cheap_time_ms + dense_time_ms
                escalation_reason = ", ".join(r.value for r in ver_res.failure_reasons)
                
                metadata = {
                    "router_probability": decision.calibrated_probability,
                    "cheap_utility": decision.cheap_utility,
                    "dense_utility": decision.dense_utility,
                    "cascade_utility": decision.cascade_utility,
                    "verification_time_ms": float(ver_time_ms),
                    "inference_time_ms": float(total_inference_time_ms),
                    "escalation_reason": escalation_reason,
                    "model_metadata": escalated_output.metadata
                }
                
                return InferenceResponse(
                    final_response=escalated_output.text,
                    selected_route=route,
                    routing_decision=decision,
                    verification_result=ver_res,
                    escalated=True,
                    metadata=metadata
                )
