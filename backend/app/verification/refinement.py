import logging
import time
from typing import List, Dict, Any, Optional, Tuple
from app.schemas.data_contracts import RawModelOutput, VerificationConstraints
from app.verification.rovl import ROVL
from app.verification.output_enforcer import OutputEnforcer
from app.core.exceptions import InferenceTimeoutError

logger = logging.getLogger("app.verification.refinement")

def format_refinement_prompt(
    original_prompt: str,
    failed_candidate: str,
    verification_failures: List[str],
    constraints_desc: str
) -> str:
    failures_str = ", ".join(verification_failures)
    return (
        f"Review the original request and the failed answer below. "
        f"Your task is to correct the answer to satisfy all constraints.\n\n"
        f"Original Request:\n{original_prompt}\n\n"
        f"Failed Answer:\n{failed_candidate}\n\n"
        f"Reasons for Failure:\n{failures_str}\n\n"
        f"Required Output Constraints:\n{constraints_desc}\n\n"
        f"Independently correct the answer. Return ONLY the final corrected output."
    )

def should_refine(
    difficulty_tier: str,
    failed_candidate: str,
    failed_validators: List[str],
    remaining_time_budget: float,
    time_limit: float = 2.0
) -> bool:
    """
    Conditions for Refinement:
    - Must not be direct_power (only medium tasks).
    - Remaining budget must be sufficient (e.g., > 2.0s).
    - Output must not be extremely long/open-ended.
    - Must not fail fundamental semantic checks (e.g., if it's empty).
    """
    if difficulty_tier == "direct_power":
        return False
    if remaining_time_budget < time_limit:
        return False
    if not failed_candidate.strip():
        return False
    if len(failed_candidate) > 800:
        return False
    # If the client failed with severe errors, don't refine
    if "timeout" in failed_validators or "empty" in failed_validators:
        return False
    return True

async def run_refinement_async(
    client: Any,
    original_prompt: str,
    failed_candidate: str,
    failed_validators: List[str],
    constraints: VerificationConstraints,
    enforcer: OutputEnforcer,
    rovl: ROVL,
    difficulty_tier: str,
    remaining_time_budget: float,
    task_id: str
) -> Tuple[Optional[RawModelOutput], bool, List[str]]:
    """
    Performs exactly one refinement call.
    Returns: Tuple of (refined_output, passed, failed_validators_list)
    """
    if not should_refine(difficulty_tier, failed_candidate, failed_validators, remaining_time_budget):
        return None, False, ["refinement_precheck_failed"]

    # Gather description of constraints
    constraints_list = []
    if constraints.json_schema:
        constraints_list.append("Return valid JSON schema format.")
    if constraints.regex_pattern:
        constraints_list.append(f"Match regular expression pattern: {constraints.regex_pattern}")
    format_constraints = enforcer.constraints_from_prompt(original_prompt)
    for k, v in format_constraints.items():
        constraints_list.append(f"{k}: {v}")
    
    constraints_desc = "\n".join(constraints_list) if constraints_list else "None specified."

    refinement_prompt = format_refinement_prompt(
        original_prompt, failed_candidate, failed_validators, constraints_desc
    )

    t0 = time.perf_counter()
    try:
        # Call model with a smaller max_tokens or timeout if needed, but keeping standard call structure
        refined_output = await client.generate_async(refinement_prompt, {"task_id": f"{task_id}_refinement"})
        latency = (time.perf_counter() - t0) * 1000.0
        
        # Verify refined output
        ver_res = rovl.verify(refined_output, constraints)
        format_result = enforcer.enforce(
            refined_output.text,
            strip_json_fence=(
                constraints.json_schema is not None
                and refined_output.text.lstrip().startswith("```")
            ),
            **format_constraints,
        )

        final_failures = list(ver_res.failed_validators) + list(format_result.failures)
        passed = ver_res.passed and format_result.success

        if passed:
            if format_result.output != refined_output.text:
                refined_output = refined_output.model_copy(update={"text": format_result.output})
            return refined_output, True, []
        else:
            return refined_output, False, final_failures

    except Exception as e:
        logger.warning(f"Refinement execution failed for task {task_id}: {e}")
        return None, False, [f"refinement_error: {str(e)}"]
