import logging
from typing import List

logger = logging.getLogger("app.verification.handoff")

def is_formatting_only_failure(failed_validators: List[str], task_type: str) -> bool:
    """
    Check if the failures are strictly formatting-related.
    """
    if task_type in ["numeric", "prose"]:
        return False
    semantic_validators = {"entropy", "average_surprisal", "probability_floor", "local_judge"}
    for f in failed_validators:
        if f in semantic_validators:
            return False
    return True

def build_enriched_handoff_prompt(
    original_prompt: str,
    failed_candidate: str,
    failed_validators: List[str],
    constraints_desc: str,
    task_type: str
) -> str:
    """
    Builds a compact enriched prompt instructing independent solving.
    Only includes the prior draft if the failure is narrowly formatting-related.
    """
    failures_str = ", ".join(failed_validators)
    prompt_str = (
        "Solve the original request independently and return only the requested output.\n\n"
        f"Original Request:\n{original_prompt}\n\n"
        f"The earlier attempt was rejected for: {failures_str}\n"
        f"Required output constraints: {constraints_desc}\n"
    )
    if is_formatting_only_failure(failed_validators, task_type):
        prompt_str += f"\nPrior draft for formatting reference:\n{failed_candidate}\n"
    return prompt_str
