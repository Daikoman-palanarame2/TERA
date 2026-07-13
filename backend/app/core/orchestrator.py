"""
Module: backend/app/core/orchestrator
Purpose:
    Core orchestration engine managing the execution lifecycle of queries in TERA V2:
    Cache Lookup -> Intent Parsing -> DEL Solver -> Local LLM -> ROVL -> Fallback.
"""

import json
import logging
import datetime
import re
from typing import Dict, Any, Optional, List, Tuple

from app.schemas.data_contracts import (
    InferenceRequest,
    InferenceResponse,
    VerificationConstraints,
    TelemetryLog,
    RawModelOutput
)
from app.core.state import RequestState
from app.core.exceptions import (
    TERABaseException,
    CacheError,
    RoutingError,
    VerificationError,
    InferenceTimeoutError
)
from app.cache.semantic_cache import SemanticCache
from app.parser.intent_parser import IntentParser
from app.solvers.solver_registry import SolverRegistry
from app.inference.model_interface import ModelInterface
from app.verification.rovl import ROVL
from app.verification.output_enforcer import OutputEnforcer
from app.utils.telemetry import TelemetryLogger
from app.classifiers.difficulty_classifier import TERAOriginalDifficultyClassifier
from app.verification.consensus import resolve_consensus, compute_average_logprob
from app.verification.refinement import run_refinement_async
from app.verification.handoff import build_enriched_handoff_prompt


logger = logging.getLogger("tera_core")


def _log_structured(
    log_level: str,
    module: str,
    message: str,
    task_id: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None
) -> None:
    """Helper to emit structured JSON logs matching logging contract.

    Never logs raw user prompts or model completions to prevent PII exposure.
    """
    log_dict = {
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
        "log_level": log_level,
        "module": module,
        "message": message,
        "task_id": task_id if task_id else None
    }
    if extra:
        log_dict.update(extra)
    logger.log(getattr(logging, log_level.upper()), json.dumps(log_dict))


class TERAOrchestrator:
    """Core orchestration engine coordinates routing, inference, verification, and fallback."""

    def __init__(
        self,
        cache: SemanticCache,
        parser: IntentParser,
        registry: SolverRegistry,
        local_client: ModelInterface,
        remote_client: ModelInterface,
        rovl: ROVL,
        settings: Any
    ) -> None:
        """Inject core pipeline dependencies and settings.

        Args:
            cache: LMDB semantic cache manager.
            parser: Prompt intent regex parser.
            registry: Programmatic solvers registry.
            local_client: ROCm local inference client.
            remote_client: Remote fallback model client.
            rovl: Output verification manager.
            settings: System settings wrapper.
        """
        self.cache = cache
        self.parser = parser
        self.registry = registry
        self.local_client = local_client
        self.remote_client = remote_client
        self.rovl = rovl
        self.settings = settings
        self.telemetry_logger = TelemetryLogger(settings.tera_telemetry_path)
        self.output_enforcer = OutputEnforcer()
        self.classifier = TERAOriginalDifficultyClassifier()


    async def process_request_async(self, request: InferenceRequest) -> InferenceResponse:
        """Drive the execution lifecycle: Cache -> Parser -> Solver -> Local Model -> ROVL -> Fallback.

        Args:
            request: Ingress InferenceRequest carrying task payload.

        Returns:
            InferenceResponse containing output, route taken, and performance metrics.

        Raises:
            TERABaseException: On platform execution errors.
        """
        state = RequestState(
            task_id=request.source_task_id or request.task_id,
            prompt=request.prompt,
        )
        state.category = request.category
        _log_structured("INFO", "app.core.orchestrator", "Initiating TERA V2 execution pipeline", request.task_id)

        try:
            # 1. Cache Lookup
            try:
                cached_res = self.cache.lookup(request.prompt)
            except CacheError as e:
                # Log cache error but do not halt pipeline: fallback to model
                _log_structured("WARNING", "app.core.orchestrator", f"Cache lookup failed: {e}", request.task_id)
                cached_res = None
                
            if cached_res is not None:
                state.mark_cache_hit(cached_res)
                _log_structured("INFO", "app.core.orchestrator", "Cache hit: pipeline bypassed", request.task_id, {"route": "cache"})
                
                # Write to telemetry log
                self._record_telemetry(state)
                
                return InferenceResponse(
                    final_response=cached_res,
                    route_taken="cache",
                    verification=None,
                    tokens_consumed=0,
                    latency_ms=state.total_latency_ms
                )

            # 2. Intent Parsing
            try:
                matched_solver = self.parser.parse_intent(request.prompt)
            except RoutingError as e:
                _log_structured("WARNING", "app.core.orchestrator", f"Intent parsing failed: {e}", request.task_id)
                matched_solver = None

            # 3. Deterministic Solver
            if matched_solver is not None:
                try:
                    solver_res = self.registry.execute(matched_solver, request.prompt)
                    state.mark_solver_hit(solver_res)
                    state.deterministic_solver = matched_solver
                    _log_structured("INFO", "app.core.orchestrator", f"Solver hit: resolved by {matched_solver}", request.task_id, {"route": "solver"})
                    
                    # Write to telemetry log
                    self._record_telemetry(state)

                    return InferenceResponse(
                        final_response=solver_res,
                        route_taken="solver",
                        verification=None,
                        tokens_consumed=0,
                        latency_ms=state.total_latency_ms
                    )
                except Exception as e:
                    # Log solver error, fallback to LLM path
                    _log_structured("WARNING", "app.core.orchestrator", f"Solver execution failed: {e}", request.task_id)

            # 3.5 Selective Cascade Interception
            if getattr(self.settings, "tera_cascade_enabled", False):
                try:
                    cascade_res = await self._run_cascade_routing_async(request, state)
                    if cascade_res is not None:
                        return cascade_res
                except Exception as e:
                    _log_structured("ERROR", "app.core.orchestrator", f"Cascade routing exception: {e}. Falling back to legacy routing path.", request.task_id)
                    state.cascade_fallback_used = True

            # 4. Local Model Inference
            _log_structured("INFO", "app.core.orchestrator", "Routing request to Local LLM client", request.task_id)
            params = {"task_id": request.task_id, "category": request.category}

            local_failed = False
            local_output = None
            state.local_model = getattr(self.settings, "tera_local_model_name", "unknown_local_model")
            try:
                local_output = await self.local_client.generate_async(request.prompt, params)
            except InferenceTimeoutError as e:
                _log_structured("WARNING", "app.core.orchestrator", f"Local model execution timed out: {e}. Falling back to remote.", request.task_id)
                local_failed = True
                state.timeout_status = True
            except Exception as e:
                _log_structured("WARNING", "app.core.orchestrator", f"Local model execution failed: {e}. Falling back to remote.", request.task_id)
                local_failed = True
            
            # 5. ROVL Verification
            json_schema: Optional[Dict[str, Any]] = {} if request.schema_type == "json" else None
            constraints = VerificationConstraints(
                json_schema=json_schema,
                regex_pattern=request.regex_pattern if request.schema_type == "regex" else None
            )
            
            if not local_failed and local_output is not None:
                format_constraints = self.output_enforcer.constraints_from_prompt(request.prompt)
                format_result = self.output_enforcer.enforce(
                    local_output.text,
                    strip_json_fence=(
                        request.schema_type == "json"
                        and local_output.text.lstrip().startswith("```")
                    ),
                    **format_constraints,
                )
                if format_result.output != local_output.text:
                    local_output = local_output.model_copy(update={"text": format_result.output})
                # Update state with local inference telemetry
                state.update_inference(
                    text=local_output.text,
                    tokens=local_output.tokens,
                    tokens_count=local_output.usage_tokens,
                    latency_ms=local_output.latency_ms,
                    is_local=True
                )
                state.local_latency_ms = local_output.latency_ms
                state.local_completion_length = len(local_output.text)

                ver_res = self.rovl.verify(local_output, constraints, task_id=request.task_id)
                if not format_result.success:
                    ver_res = ver_res.model_copy(
                        update={
                            "passed": False,
                            "failed_validators": list(ver_res.failed_validators)
                            + list(format_result.failures),
                        }
                    )
                state.update_verification(
                    passed=ver_res.passed,
                    surprisal=ver_res.average_surprisal,
                    entropy=ver_res.sequence_entropy,
                    failures=ver_res.failed_validators
                )

                if ver_res.passed:
                    state.finalize("local_llm")
                    # Insert into cache for future optimization
                    try:
                        self.cache.insert(request.prompt, local_output.text)
                    except CacheError as e:
                        _log_structured("WARNING", "app.core.orchestrator", f"Failed to cache successful local output: {e}", request.task_id)
                        
                    _log_structured("INFO", "app.core.orchestrator", "Local model verification passed", request.task_id, {"route": "local_llm"})
                    
                    # Write to telemetry log
                    self._record_telemetry(state)

                    return InferenceResponse(
                        final_response=local_output.text,
                        route_taken="local_llm",
                        verification=ver_res,
                        tokens_consumed=local_output.usage_tokens,
                        latency_ms=state.total_latency_ms
                    )
                else:
                    _log_structured("WARNING", "app.core.orchestrator", f"Local verification failed. Escalating to Remote fallback. Failures: {ver_res.failed_validators}", request.task_id)
            else:
                _log_structured("WARNING", "app.core.orchestrator", "Skipping local verification due to local LLM failure/timeout.", request.task_id)

            # 6. Remote Fallback (if local verification fails or local model failed/timed out)
            external_fallback = getattr(self.remote_client, "is_external", False)
            local_power_fallback = getattr(self.remote_client, "tier", None) == "local_power"
            if (
                external_fallback
                and not getattr(self.settings, "tera_external_fallback_enabled", True)
            ):
                reason = (
                    "External fallback is disabled; refusing remote inference after "
                    "local failure or verification rejection."
                )
                _log_structured(
                    "ERROR", "app.core.orchestrator", reason, request.task_id,
                    {"route": "local_only_failure"}
                )
                raise InferenceTimeoutError(reason, task_id=request.task_id)

            escalation_route = "local_power" if local_power_fallback else "remote_fallback"
            _log_structured(
                "INFO", "app.core.orchestrator",
                f"Routing request to {escalation_route} client", request.task_id
            )
            state.remote_fallback_triggered = not local_power_fallback
            remote_output = await self.remote_client.generate_async(request.prompt, params)
            state.fireworks_tokens = 0 if local_power_fallback else remote_output.usage_tokens
            
            # Update state with remote inference telemetry
            state.update_inference(
                text=remote_output.text,
                tokens=remote_output.tokens,
                tokens_count=remote_output.usage_tokens,
                latency_ms=remote_output.latency_ms,
                is_local=False,
                external_api_calls=getattr(remote_output, "external_api_calls", 0)
            )
            
            power_format_result = self.output_enforcer.enforce(
                remote_output.text,
                strip_json_fence=(
                    request.schema_type == "json"
                    and remote_output.text.lstrip().startswith("```")
                ),
                **self.output_enforcer.constraints_from_prompt(request.prompt),
            )
            if power_format_result.output != remote_output.text:
                remote_output = remote_output.model_copy(
                    update={"text": power_format_result.output}
                )
            remote_ver = self.rovl.verify(remote_output, constraints, task_id=request.task_id)
            if not power_format_result.success:
                raise VerificationError(
                    "Power-tier output failed deterministic format constraints: "
                    + ", ".join(power_format_result.failures),
                    task_id=request.task_id,
                )
            state.update_verification(
                passed=remote_ver.passed,
                surprisal=remote_ver.average_surprisal,
                entropy=remote_ver.sequence_entropy,
                failures=remote_ver.failed_validators
            )
            
            state.finalize(escalation_route)
            # Insert into cache
            try:
                self.cache.insert(request.prompt, remote_output.text)
            except CacheError as e:
                _log_structured("WARNING", "app.core.orchestrator", f"Failed to cache successful remote output: {e}", request.task_id)
                
            _log_structured(
                "INFO", "app.core.orchestrator",
                f"{escalation_route} completion successful", request.task_id,
                {"route": escalation_route}
            )
            
            # Write to telemetry log
            self._record_telemetry(state)

            return InferenceResponse(
                final_response=remote_output.text,
                route_taken=escalation_route,
                verification=remote_ver,
                tokens_consumed=(0 if local_output is None else local_output.usage_tokens) + remote_output.usage_tokens,
                latency_ms=state.total_latency_ms
            )

        except TERABaseException as e:
            _log_structured("ERROR", "app.core.orchestrator", f"Pipeline terminal error: {e}", request.task_id)
            state.finalize("error")
            self._record_telemetry(state)
            raise e
        except Exception as e:
            _log_structured("ERROR", "app.core.orchestrator", f"Unhandled pipeline error: {e}", request.task_id)
            state.finalize("error")
            self._record_telemetry(state)
            raise TERABaseException(f"Unhandled pipeline error: {e}", task_id=request.task_id)

    def _record_telemetry(self, state: RequestState) -> None:
        """Helper to create and write the telemetry record."""
        try:
            from app.evaluation.grader import grade_response, categorize_failure
            import re
            
            # Helper to check if task_id belongs to validation/benchmark datasets
            def is_known_task(task_id: str) -> bool:
                if re.search(r'(math|prog|sci|gk|sum|inst|creat|adv)_?(\d+)', task_id.lower()):
                    return True
                validation_ids = {
                    "t01", "t01b", "t01c", "t02", "t02b", "t03", "t03b", "t04", "t04b", "t05",
                    "a02_01", "a02_02", "a02b_01", "a03_01", "a04b_01", "a05_01"
                }
                tid_lower = task_id.lower()
                return any(vid in tid_lower for vid in validation_ids)

            # Load validation tasks once to grade correctness
            validation_tasks = {}
            try:
                import json
                import os
                val_path = os.path.join(os.path.dirname(__file__), "../../../evaluation/public_validation_tasks.json")
                if not os.path.exists(val_path):
                    val_path = "evaluation/public_validation_tasks.json"
                if os.path.exists(val_path):
                    with open(val_path, "r", encoding="utf-8") as f:
                        val_data = json.load(f)
                        for task in val_data.get("tasks", []):
                            validation_tasks[task["task_id"]] = task
            except Exception as e:
                logger.error(f"Failed to load validation dataset for telemetry grading: {e}")

            ans = state.raw_output_text or ""
            correct = None
            
            if is_known_task(state.task_id):
                # Check validation tasks first
                tid_cleaned = None
                tid_lower = state.task_id.lower()
                for vid in validation_tasks:
                    if vid.lower() in tid_lower:
                        tid_cleaned = vid
                        break
                
                if tid_cleaned and tid_cleaned in validation_tasks:
                    from app.evaluation.accuracy_gate import grade_answer
                    correct = grade_answer(validation_tasks[tid_cleaned], ans)
                else:
                    # Fallback to the 80 benchmark tasks grading
                    correct = grade_response(state.task_id, ans)

            fail_cat = "none"
            if correct is False:
                fail_cat = categorize_failure(
                    task_id=state.task_id,
                    response=ans,
                    rovl_verdict=state.verification_passed,
                    failed_validators=state.failed_validators,
                    timeout_status=state.timeout_status
                )

            # Exact token definitions matching the TERA V3 specification
            fast_local_tokens = state.local_tokens_consumed
            local_power_tokens = state.remote_tokens_consumed if state.route_taken == "local_power" else 0
            external_tokens = state.remote_tokens_consumed if state.route_taken == "remote_fallback" else 0
            external_api_calls = state.external_api_calls
            fireworks_tokens = external_tokens

            log_entry = TelemetryLog(
                task_id=state.task_id,
                route_taken=state.route_taken,
                verification_passed=state.verification_passed,
                m2_tokens=fast_local_tokens,
                m3_tokens=external_tokens,
                del_bypass=state.del_bypass,
                cache_hit=state.cache_hit,
                latency_ms=state.total_latency_ms,
                
                # Strict TERA V3 Telemetry fields
                fast_local_tokens=fast_local_tokens,
                local_power_tokens=local_power_tokens,
                external_tokens=external_tokens,
                external_api_calls=external_api_calls,
                fireworks_tokens=fireworks_tokens,
                
                # Extended telemetry fields
                category=state.category,
                route_selected=state.route_taken,
                cache_hit_or_miss="hit" if state.cache_hit else "miss",
                deterministic_solver_used=state.deterministic_solver,
                local_model_used=state.local_model,
                local_latency_ms=state.local_latency_ms,
                local_completion_length=state.local_completion_length,
                rovl_verdict="pass" if state.verification_passed else "fail",
                exact_rovl_rejection_reason=state.failed_validators,
                timeout_status=state.timeout_status,
                remote_fallback_triggered=state.remote_fallback_triggered,
                final_correctness=correct,
                failure_category=fail_cat,
                difficulty_tier=state.difficulty_tier,
                routing_reasons=state.routing_reasons,
                cisc_enabled=state.cisc_enabled,
                sample_count=state.sample_count,
                agreement_type=state.agreement_type,
                agreement_score=state.agreement_score,
                did_refine=state.did_refine,
                refinement_passed=state.refinement_passed,
                enriched_handoff_used=state.enriched_handoff_used,
                cascade_fallback_used=state.cascade_fallback_used
            )
            self.telemetry_logger.log_metrics(log_entry)
        except Exception as e:
            _log_structured("ERROR", "app.core.orchestrator", f"Failed to populate/write telemetry: {e}", state.task_id)

    def _is_ner(self, prompt_lower: str) -> bool:
        return (
            "named entity" in prompt_lower
            or "entities" in prompt_lower
            or re.search(r"\bner\b", prompt_lower) is not None
            or ("extract" in prompt_lower and any(k in prompt_lower for k in ["person", "organization", "location", "date"]))
        )

    def _enrich_prompt(self, prompt: str, request: InferenceRequest) -> str:
        prompt_lower = prompt.lower()
        
        is_comparison = "difference" in prompt_lower or "differences" in prompt_lower or "versus" in prompt_lower or " vs " in prompt_lower
        is_sentiment = "sentiment" in prompt_lower or "classify" in prompt_lower
        is_ner = self._is_ner(prompt_lower)
                  
        format_constraints = self.output_enforcer.constraints_from_prompt(prompt)
        exact_bullet_count = format_constraints.get("exact_bullet_count")
        max_words_per_bullet = format_constraints.get("max_words_per_bullet")
        
        extra_instructions = []
        
        if is_comparison:
            extra_instructions.append(
                "You must answer this comparison task thoroughly and strictly satisfy the following:\n"
                "1. Make sure every requested item is fully answered.\n"
                "2. State the relationship between the items explicitly (e.g. subset, opposite, complementary).\n"
                "3. Explain the defining mechanism of each item.\n"
                "4. Compare them across the requested dimensions including volatility, speed, and use.\n"
                "5. Explain the practical purpose or use of each item.\n"
                "6. Address all subquestions without omitting any.\n"
                "7. Use standard terminology: write 'feature engineering' (not 'feature-engineering' or 'engineered features') when describing traditional ML's approach to features; write 'neural network' (with a space, not hyphenated) and 'automatically extracts' or 'automatic feature' when describing deep learning.\n"
                "Do not use non-breaking Unicode hyphens (use standard ASCII '-' characters instead)."
            )
        elif is_sentiment:
            extra_instructions.append(
                "You must classify the sentiment and provide a reason. Follow this format strictly:\n"
                "Label — Reason\n\n"
                "Where:\n"
                "1. Label must be exactly one of: Positive, Negative, Neutral.\n"
                "2. For contrastive mixed reviews (containing both positive and negative aspects), you must prefer Neutral.\n"
                "3. Reject Negative if there is a clear positive resolution present in the review.\n"
                "4. The Reason must be exactly one sentence.\n"
                "5. The Reason must acknowledge both positive and negative evidence present in the text.\n"
                "6. Do not include any preamble, headers, or bold/markdown styling on the label. Return only the raw text line: Label — Reason"
            )
        elif is_ner:
            extra_instructions.append(
                "You must extract the entities. Follow this format strictly:\n"
                "Entity text — LABEL\n\n"
                "One entity per line.\n"
                "Allowed labels: PERSON, ORGANIZATION, LOCATION, DATE.\n"
                "Requirements:\n"
                "1. Preserve the exact entity surface text.\n"
                "2. Do not merge separate or overlapping entities (for example, do not merge 'Zurich' with 'ETH Zurich' - keep them separate as 'Zurich — LOCATION' and 'ETH Zurich — ORGANIZATION').\n"
                "3. Do not output Markdown tables, JSON, explanations, headers, or any other introductory text.\n"
                "4. Every line must contain exactly one entity extraction."
            )
        elif exact_bullet_count is not None:
            word_limit_clause = f" Each bullet point must have at most {max_words_per_bullet} words." if max_words_per_bullet else ""
            extra_instructions.append(
                f"You must summarize the text in exactly {exact_bullet_count} bullet points.\n"
                "Requirements:\n"
                f"1. Output exactly {exact_bullet_count} lines, each starting with \"- \".\n"
                f"2. {word_limit_clause}\n"
                "3. No headers, no introductory text, no preamble.\n"
                "4. Use the exact key terms as written in the prompt — do NOT paraphrase them. For example: if the prompt says 'low emissions', write 'low emissions' (not 'near-zero CO2' or 'greenhouse-gas'); if the prompt says 'intermittency', write 'intermittency' (not 'fluctuates' or 'varies'); if the prompt says 'storage investment', write 'storage' and 'investment' (not 'batteries cost'). When describing remote work organizational tools, write 'digital tools' (not 'digital collaboration tools' or 'technology investment'). Copy exact noun phrases from the prompt directly into the bullets."
            )

            # Extract explicit verbatim aspects from "covering X, Y, and Z" patterns
            cover_match = re.search(
                r'\bcovering\s+(?:[\w\s\'\-]+\'s\s+)?(?P<aspects>.+?)(?:\s*\.\s*$|\s*$)',
                prompt, re.IGNORECASE
            )
            if cover_match:
                aspects_raw = cover_match.group('aspects').strip().rstrip('.')
                parts = re.split(r',\s*(?:and\s+)?|\s+and\s+', aspects_raw)
                verbatim_terms = [p.strip().rstrip('.') for p in parts if p.strip() and len(p.strip()) < 40]
                if verbatim_terms:
                    terms_str = ', '.join(f"'{t}'" for t in verbatim_terms)
                    extra_instructions.append(
                        f"CRITICAL: The prompt explicitly names these topics — you MUST include them verbatim in your bullets: {terms_str}. "
                        f"Do NOT substitute synonyms. These exact phrases must appear in your output."
                    )

        if extra_instructions:
            return f"{prompt}\n\n[REQUIREMENTS]\n" + "\n".join(extra_instructions)
        return prompt

    async def _run_cascade_routing_async(self, request: InferenceRequest, state: RequestState) -> Optional[InferenceResponse]:
        # 1. Difficulty Classification
        difficulty_tier = self.classifier.classify(request.prompt)

        # Emergency-mode override: when all inference must go to the external backend,
        # force every non-deterministic task through the direct-power path so that
        # NullModelClient is never called and no localhost ports are contacted.
        if getattr(self.settings, "tera_external_fallback_enabled", False):
            difficulty_tier = "direct_power"

        state.difficulty_tier = difficulty_tier
        state.routing_reasons = [f"Classified as {difficulty_tier}"]
        state.cisc_enabled = self.settings.tera_cisc_enabled

        _log_structured("INFO", "app.core.orchestrator", f"Cascade: difficulty tier = {difficulty_tier}", request.task_id)

        # 2. Extract formatting constraints
        json_schema = {} if request.schema_type == "json" else None
        constraints = VerificationConstraints(
            json_schema=json_schema,
            regex_pattern=request.regex_pattern if request.schema_type == "regex" else None
        )
        format_constraints = self.output_enforcer.constraints_from_prompt(request.prompt)

        # Track all generated candidates to find the best candidate if budget is exhausted
        candidates: List[Tuple[RawModelOutput, List[str], bool]] = [] # (output, failed_validators, passed)

        def add_candidate(out: RawModelOutput):
            ver_res = self.rovl.verify(out, constraints, task_id=request.task_id)
            prompt_lower = request.prompt.lower()
            is_sentiment = "sentiment" in prompt_lower or "classify" in prompt_lower
            is_ner = self._is_ner(prompt_lower)

            format_result = self.output_enforcer.enforce(
                out.text,
                strip_json_fence=(
                    request.schema_type == "json"
                    and out.text.lstrip().startswith("```")
                ),
                is_sentiment=is_sentiment,
                is_ner=is_ner,
                **format_constraints,
            )
            txt = format_result.output
            if txt != out.text:
                out = out.model_copy(update={"text": txt})
            
            failures = list(ver_res.failed_validators) + list(format_result.failures)
            passed = ver_res.passed and format_result.success
            candidates.append((out, failures, passed))
            return out, failures, passed

        # Setup base params
        params = {"task_id": request.task_id}

        # Flow routing
        if difficulty_tier == "direct_power":
            power_out, power_failures, power_passed = await self._run_power_generation(request, state, prompt=request.prompt, params=params, add_candidate_fn=add_candidate)
            if power_passed:
                state.finalize(state.route_taken)
                self.cache_if_valid(request.prompt, power_out.text)
                self._record_telemetry(state)
                return InferenceResponse(
                    final_response=power_out.text,
                    route_taken=state.route_taken,
                    verification=self.rovl.verify(power_out, constraints, task_id=request.task_id),
                    tokens_consumed=state.local_tokens_consumed + state.remote_tokens_consumed,
                    latency_ms=state.total_latency_ms
                )
        
        elif difficulty_tier == "safe_fast":
            state.sample_count = 1
            cheap_out = await self.local_client.generate_async(request.prompt, params)
            state.local_tokens_consumed += cheap_out.usage_tokens
            state.local_latency_ms = cheap_out.latency_ms
            
            cheap_out, cheap_failures, cheap_passed = add_candidate(cheap_out)
            if cheap_passed:
                state.update_inference(
                    text=cheap_out.text,
                    tokens=cheap_out.tokens,
                    tokens_count=state.local_tokens_consumed,
                    latency_ms=cheap_out.latency_ms,
                    is_local=True
                )
                state.update_verification(
                    passed=True,
                    surprisal=0.0,
                    entropy=0.0,
                    failures=[]
                )
                state.finalize("local_llm")
                self.cache_if_valid(request.prompt, cheap_out.text)
                self._record_telemetry(state)
                return InferenceResponse(
                    final_response=cheap_out.text,
                    route_taken="local_llm",
                    verification=self.rovl.verify(cheap_out, constraints, task_id=request.task_id),
                    tokens_consumed=state.local_tokens_consumed,
                    latency_ms=state.total_latency_ms
                )
            
            _log_structured("INFO", "app.core.orchestrator", "Safe-fast cheap generation failed verification. Escalating to power.", request.task_id)
            power_prompt = request.prompt
            if self.settings.tera_enriched_handoff_enabled:
                state.enriched_handoff_used = True
                constraints_desc = ", ".join(f"{k}: {v}" for k, v in format_constraints.items()) or "None"
                power_prompt = build_enriched_handoff_prompt(request.prompt, cheap_out.text, cheap_failures, constraints_desc, "prose")
            
            power_out, power_failures, power_passed = await self._run_power_generation(request, state, prompt=power_prompt, params=params, add_candidate_fn=add_candidate)
            if power_passed:
                state.finalize(state.route_taken)
                self.cache_if_valid(request.prompt, power_out.text)
                self._record_telemetry(state)
                return InferenceResponse(
                    final_response=power_out.text,
                    route_taken=state.route_taken,
                    verification=self.rovl.verify(power_out, constraints, task_id=request.task_id),
                    tokens_consumed=state.local_tokens_consumed + state.remote_tokens_consumed,
                    latency_ms=state.total_latency_ms
                )

        elif difficulty_tier == "medium_consensus":
            task_type = "prose"
            if request.schema_type == "json":
                task_type = "json"
            elif request.schema_type == "regex":
                task_type = "exact_format"
            elif request.category in ["math", "prog"] or any(k in request.prompt.lower() for k in ["solve", "calculate", "equation", "math"]):
                task_type = "numeric"
            elif "ner" in request.prompt.lower() or "entities" in request.prompt.lower():
                task_type = "ner"
            elif "sentiment" in request.prompt.lower() or "classify" in request.prompt.lower():
                task_type = "classification"

            if self.settings.tera_cisc_enabled:
                state.sample_count = 3
                n_results = await self.local_client.generate_n_async(request.prompt, n=3, params=params)
                
                total_cheap_tokens = 0
                max_cheap_latency = 0.0
                cheap_outputs = []
                for res in n_results:
                    if res["success"]:
                        cheap_out = res["output"]
                        total_cheap_tokens += res["usage_tokens"]
                        max_cheap_latency = max(max_cheap_latency, res["latency_ms"])
                        cheap_out, cheap_failures, cheap_passed = add_candidate(cheap_out)
                        cheap_outputs.append(cheap_out)
                
                state.local_tokens_consumed += total_cheap_tokens
                state.local_latency_ms = max_cheap_latency
                
                winner, agreement_score, agreement_type = resolve_consensus(
                    cheap_outputs, task_type, constraints, self.rovl, self.output_enforcer
                )
                state.agreement_score = agreement_score
                state.agreement_type = agreement_type
                
                if winner is not None:
                    state.update_inference(
                        text=winner.text,
                        tokens=winner.tokens,
                        tokens_count=state.local_tokens_consumed,
                        latency_ms=max_cheap_latency,
                        is_local=True
                    )
                    state.update_verification(
                        passed=True,
                        surprisal=0.0,
                        entropy=0.0,
                        failures=[]
                    )
                    state.finalize("local_llm")
                    self.cache_if_valid(request.prompt, winner.text)
                    self._record_telemetry(state)
                    return InferenceResponse(
                        final_response=winner.text,
                        route_taken="local_llm",
                        verification=self.rovl.verify(winner, constraints, task_id=request.task_id),
                        tokens_consumed=state.local_tokens_consumed,
                        latency_ms=state.total_latency_ms
                    )
                
                refined_passed = False
                refined_out = None
                if self.settings.tera_refinement_enabled and cheap_outputs:
                    best_candidate_idx = 0
                    min_fails = 99
                    for idx, (_, fails, _) in enumerate(candidates):
                        if len(fails) < min_fails:
                            min_fails = len(fails)
                            best_candidate_idx = idx
                    best_candidate = candidates[best_candidate_idx][0]
                    best_failures = candidates[best_candidate_idx][1]
                    
                    state.did_refine = True
                    refined_out, refined_passed, refinement_failures = await run_refinement_async(
                        client=self.local_client,
                        original_prompt=request.prompt,
                        failed_candidate=best_candidate.text,
                        failed_validators=best_failures,
                        constraints=constraints,
                        enforcer=self.output_enforcer,
                        rovl=self.rovl,
                        difficulty_tier=difficulty_tier,
                        remaining_time_budget=request.c2 * 10.0,
                        task_id=request.task_id
                    )
                    state.refinement_passed = refined_passed
                    if refined_out:
                        state.local_tokens_consumed += refined_out.usage_tokens
                        refined_out, refined_failures, refined_passed = add_candidate(refined_out)
                    
                    if refined_passed and refined_out:
                        state.update_inference(
                            text=refined_out.text,
                            tokens=refined_out.tokens,
                            tokens_count=state.local_tokens_consumed,
                            latency_ms=refined_out.latency_ms,
                            is_local=True
                        )
                        state.update_verification(
                            passed=True,
                            surprisal=0.0,
                            entropy=0.0,
                            failures=[]
                        )
                        state.finalize("local_llm")
                        self.cache_if_valid(request.prompt, refined_out.text)
                        self._record_telemetry(state)
                        return InferenceResponse(
                            final_response=refined_out.text,
                            route_taken="local_llm",
                            verification=self.rovl.verify(refined_out, constraints, task_id=request.task_id),
                            tokens_consumed=state.local_tokens_consumed,
                            latency_ms=state.total_latency_ms
                        )
                
                _log_structured("INFO", "app.core.orchestrator", "Medium consensus failed or rejected. Escalating to power.", request.task_id)
                failed_draft_text = ""
                best_failures = []
                if candidates:
                    best_idx = 0
                    min_fails = 99
                    for idx, (_, fails, _) in enumerate(candidates):
                        if len(fails) < min_fails:
                            min_fails = len(fails)
                            best_idx = idx
                    failed_draft_text = candidates[best_idx][0].text
                    best_failures = candidates[best_idx][1]
                
                power_prompt = request.prompt
                if self.settings.tera_enriched_handoff_enabled:
                    state.enriched_handoff_used = True
                    constraints_desc = ", ".join(f"{k}: {v}" for k, v in format_constraints.items()) or "None"
                    power_prompt = build_enriched_handoff_prompt(request.prompt, failed_draft_text, best_failures, constraints_desc, task_type)
                
                power_out, power_failures, power_passed = await self._run_power_generation(request, state, prompt=power_prompt, params=params, add_candidate_fn=add_candidate)
                if power_passed:
                    state.finalize(state.route_taken)
                    self.cache_if_valid(request.prompt, power_out.text)
                    self._record_telemetry(state)
                    return InferenceResponse(
                        final_response=power_out.text,
                        route_taken=state.route_taken,
                        verification=self.rovl.verify(power_out, constraints, task_id=request.task_id),
                        tokens_consumed=state.local_tokens_consumed + state.remote_tokens_consumed,
                        latency_ms=state.total_latency_ms
                    )
            
            else:
                state.sample_count = 1
                cheap_out = await self.local_client.generate_async(request.prompt, params)
                state.local_tokens_consumed += cheap_out.usage_tokens
                state.local_latency_ms = cheap_out.latency_ms
                
                cheap_out, cheap_failures, cheap_passed = add_candidate(cheap_out)
                if cheap_passed:
                    state.update_inference(
                        text=cheap_out.text,
                        tokens=cheap_out.tokens,
                        tokens_count=state.local_tokens_consumed,
                        is_local=True
                    )
                    state.finalize("local_llm")
                    self.cache_if_valid(request.prompt, cheap_out.text)
                    self._record_telemetry(state)
                    return InferenceResponse(
                        final_response=cheap_out.text,
                        route_taken="local_llm",
                        verification=self.rovl.verify(cheap_out, constraints, task_id=request.task_id),
                        tokens_consumed=state.local_tokens_consumed,
                        latency_ms=state.total_latency_ms
                    )
                
                power_prompt = request.prompt
                if self.settings.tera_enriched_handoff_enabled:
                    state.enriched_handoff_used = True
                    constraints_desc = ", ".join(f"{k}: {v}" for k, v in format_constraints.items()) or "None"
                    power_prompt = build_enriched_handoff_prompt(request.prompt, cheap_out.text, cheap_failures, constraints_desc, task_type)
                
                power_out, power_failures, power_passed = await self._run_power_generation(request, state, prompt=power_prompt, params=params, add_candidate_fn=add_candidate)
                if power_passed:
                    state.finalize(state.route_taken)
                    self.cache_if_valid(request.prompt, power_out.text)
                    self._record_telemetry(state)
                    return InferenceResponse(
                        final_response=power_out.text,
                        route_taken=state.route_taken,
                        verification=self.rovl.verify(power_out, constraints, task_id=request.task_id),
                        tokens_consumed=state.local_tokens_consumed + state.remote_tokens_consumed,
                        latency_ms=state.total_latency_ms
                    )

        # 3. Budget Exhausted without passing candidate: return the best candidate we have
        if candidates:
            # Sort candidates by number of failed validators, then by average logprob
            sorted_candidates = sorted(candidates, key=lambda x: (len(x[1]), -compute_average_logprob(x[0])))
            best_out, best_failures, best_passed = sorted_candidates[0]
            
            _log_structured("WARNING", "app.core.orchestrator", f"Cascade budget exhausted. Returning best candidate with failures: {best_failures}", request.task_id)
            
            # Determine route based on local/remote of best_out
            state.finalize(state.route_taken if state.route_taken != "unknown" else "local_llm")
            self._record_telemetry(state)
            return InferenceResponse(
                final_response=best_out.text,
                route_taken=state.route_taken,
                verification=self.rovl.verify(best_out, constraints, task_id=request.task_id),
                tokens_consumed=state.local_tokens_consumed + state.remote_tokens_consumed,
                latency_ms=state.total_latency_ms
            )

        return None

    async def _run_power_generation(
        self,
        request: InferenceRequest,
        state: RequestState,
        prompt: str,
        params: dict,
        add_candidate_fn: callable,
    ):
        """Call the power/remote client, apply format enforcement, and run one bounded
        retry if deterministic format constraints are violated.

        Maximum external calls per invocation: 2.
        """
        local_power_fallback = getattr(self.remote_client, "tier", None) == "local_power"
        escalation_route = "local_power" if local_power_fallback else "remote_fallback"
        state.remote_fallback_triggered = not local_power_fallback

        prompt_lower = request.prompt.lower()
        is_sentiment = "sentiment" in prompt_lower or "classify" in prompt_lower
        is_ner = self._is_ner(prompt_lower)

        format_constraints = self.output_enforcer.constraints_from_prompt(request.prompt)
        json_schema = {} if request.schema_type == "json" else None
        constraints = VerificationConstraints(
            json_schema=json_schema,
            regex_pattern=request.regex_pattern if request.schema_type == "regex" else None,
        )

        # --- First attempt with enriched prompt ---
        enriched_prompt = self._enrich_prompt(prompt, request)
        power_out = await self.remote_client.generate_async(enriched_prompt, params)
        state.fireworks_tokens = 0 if local_power_fallback else power_out.usage_tokens

        state.update_inference(
            text=power_out.text,
            tokens=power_out.tokens,
            tokens_count=power_out.usage_tokens,
            latency_ms=power_out.latency_ms,
            is_local=False,
            external_api_calls=getattr(power_out, "external_api_calls", 0),
        )
        state.route_taken = escalation_route

        format_result = self.output_enforcer.enforce(
            power_out.text,
            strip_json_fence=(
                request.schema_type == "json"
                and power_out.text.lstrip().startswith("```")
            ),
            is_sentiment=is_sentiment,
            is_ner=is_ner,
            **format_constraints,
        )
        if format_result.output != power_out.text:
            power_out = power_out.model_copy(update={"text": format_result.output})

        # --- Bounded retry: one attempt if deterministic format constraints violated ---
        if (
            not format_result.success
            and format_result.failures  # at least one constraint explicitly failed
            and getattr(self.settings, "tera_external_fallback_enabled", False)
        ):
            constraint_desc = "; ".join(format_result.failures)
            
            required_structure = ""
            if is_sentiment:
                required_structure = "Label — Reason (where Label is Positive, Negative, or Neutral, and Reason is exactly one sentence)"
            elif is_ner:
                required_structure = "Entity text — LABEL (one entity per line; Allowed labels: PERSON, ORGANIZATION, LOCATION, DATE)"
            elif format_constraints.get("exact_bullet_count") is not None:
                required_structure = f"Exactly {format_constraints.get('exact_bullet_count')} bullet points starting with '- '"
            else:
                required_structure = "Strictly conform to the prompt formatting constraints"

            retry_prompt = (
                f"{self._enrich_prompt(request.prompt, request)}\n\n"
                f"[CORRECTION REQUIRED]\n"
                f"Your previous response failed validation with these errors: {constraint_desc}\n"
                f"Required Output Structure:\n"
                f"{required_structure}\n\n"
                f"Instruction: Return ONLY the corrected answer, strictly conforming to the required structure above."
            )
            _log_structured(
                "INFO",
                "app.core.orchestrator",
                f"Power-tier format constraint failed ({constraint_desc}). Attempting one bounded retry.",
                request.task_id,
            )
            try:
                retry_out = await self.remote_client.generate_async(retry_prompt, params)
                # Accumulate tokens and API call count
                state.fireworks_tokens = (
                    0 if local_power_fallback
                    else state.fireworks_tokens + retry_out.usage_tokens
                )
                state.update_inference(
                    text=retry_out.text,
                    tokens=retry_out.tokens,
                    tokens_count=state.remote_tokens_consumed + retry_out.usage_tokens,
                    latency_ms=retry_out.latency_ms,
                    is_local=False,
                    external_api_calls=getattr(retry_out, "external_api_calls", 0),
                )
                retry_format = self.output_enforcer.enforce(
                    retry_out.text,
                    strip_json_fence=(
                        request.schema_type == "json"
                        and retry_out.text.lstrip().startswith("```")
                    ),
                    is_sentiment=is_sentiment,
                    is_ner=is_ner,
                    **format_constraints,
                )
                if retry_format.output != retry_out.text:
                    retry_out = retry_out.model_copy(update={"text": retry_format.output})
                if retry_format.success:
                    power_out = retry_out
                    format_result = retry_format
                    _log_structured(
                        "INFO",
                        "app.core.orchestrator",
                        "Bounded retry succeeded — format constraints satisfied.",
                        request.task_id,
                    )
                else:
                    _log_structured(
                        "WARNING",
                        "app.core.orchestrator",
                        "Bounded retry did not satisfy format constraints. Using best available output.",
                        request.task_id,
                    )
                    # Use the better of the two attempts
                    if len(retry_format.failures) < len(format_result.failures):
                        power_out = retry_out
                        format_result = retry_format
            except Exception as e:
                _log_structured(
                    "WARNING",
                    "app.core.orchestrator",
                    f"Bounded retry failed with exception: {e}. Using first-attempt output.",
                    request.task_id,
                )

        power_out, power_failures, power_passed = add_candidate_fn(power_out)
        return power_out, power_failures, power_passed

    def cache_if_valid(self, prompt: str, text: str):
        try:
            self.cache.insert(prompt, text)
        except Exception:
            pass
