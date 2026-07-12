"""
Module: backend/app/verification/rovl
Purpose:
    Core verification engine implementing the ROVL V2 pipeline: evaluates structural
    schema matching, average per-token surprisal, stop-token termination, and orchestrates
    the Local Judge model check.
"""

import math
import json
import logging
from datetime import datetime
from typing import List, Optional, Callable

from app.schemas.data_contracts import (
    VerificationResult,
    VerificationConstraints,
    RawModelOutput,
)
from app.core.exceptions import VerificationError, ConfigurationError
from app.core.config import (
    ENTROPY_THRESHOLD,
    SURPRISAL_THRESHOLD,
    MIN_PROBABILITY_FLOOR,
)
from app.verification.validators import (
    validate_json_schema,
    validate_regex,
    validate_stop_sequences,
)
from app.verification.entropy import compute_sequence_entropy, compute_average_surprisal

# Configure logger name as required by structured logging contract
logger = logging.getLogger("tera_core")


def log_structured(level: str, message: str, task_id: Optional[str] = None) -> None:
    """Helper to output single-line JSON logs to stdout according to logging contract."""
    log_entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "log_level": level,
        "module": "app.verification.rovl",
        "message": message,
        "task_id": task_id,
    }
    json_str = json.dumps(log_entry)
    # Output using python logging which directs to stdout
    if level == "INFO":
        logger.info(json_str)
    elif level == "WARNING":
        logger.warning(json_str)
    elif level == "ERROR":
        logger.error(json_str)
    else:
        logger.debug(json_str)


class ROVL:
    """Runtime Output Verification Layer orchestrating checks across syntax and logprobs."""

    def __init__(
        self,
        entropy_threshold: float = ENTROPY_THRESHOLD,
        min_prob_floor: float = MIN_PROBABILITY_FLOOR,
        local_judge: Optional[Callable[[str], bool]] = None,
    ) -> None:
        """Initialize audit limits from Settings configuration."""
        # Ensure configuration parameters are valid
        if entropy_threshold is None or entropy_threshold < 0:
            raise ConfigurationError("Entropy threshold must be a non-negative float.")
        if min_prob_floor is None or min_prob_floor < 0.0 or min_prob_floor > 1.0:
            raise ConfigurationError(
                "Min probability floor must be between 0.0 and 1.0."
            )

        self.entropy_threshold = entropy_threshold
        self.min_prob_floor = min_prob_floor
        self.surprisal_threshold = SURPRISAL_THRESHOLD
        self.local_judge = local_judge

    def verify(
        self,
        output: RawModelOutput,
        constraints: VerificationConstraints,
        task_id: Optional[str] = None,
    ) -> VerificationResult:
        """Orchestrate verification pipeline check across syntax and statistical entropy.

        Raises:
            VerificationError: If critical validation engines fail structurally.
        """
        # Validate inputs type conformity
        if output is None or constraints is None:
            raise VerificationError(
                "RawModelOutput and VerificationConstraints must not be None."
            )

        failed_validators: List[str] = []

        # ─── TIER 1: SCHEMA VALIDATION ───
        if constraints.json_schema is not None:
            try:
                schema_passed = validate_json_schema(
                    output.text, constraints.json_schema
                )
                if not schema_passed:
                    failed_validators.append("json_schema")
            except VerificationError as e:
                log_structured(
                    "ERROR",
                    f"JSON Schema compilation or validation failed: {e}",
                    task_id,
                )
                raise
            except Exception as e:
                log_structured(
                    "ERROR",
                    f"JSON Schema verification structural failure: {e}",
                    task_id,
                )
                raise VerificationError(
                    f"JSON Schema verification structural failure: {e}"
                )

        if constraints.regex_pattern is not None:
            try:
                regex_passed = validate_regex(output.text, constraints.regex_pattern)
                if not regex_passed:
                    failed_validators.append("regex_pattern")
            except VerificationError as e:
                log_structured(
                    "ERROR", f"Regex compilation or execution failed: {e}", task_id
                )
                raise
            except Exception as e:
                log_structured(
                    "ERROR", f"Regex verification structural failure: {e}", task_id
                )
                raise VerificationError(f"Regex verification structural failure: {e}")

        # Character length constraints
        if constraints.min_length_chars is not None:
            if len(output.text) < constraints.min_length_chars:
                failed_validators.append("min_length_chars")

        if constraints.max_length_chars is not None:
            if len(output.text) > constraints.max_length_chars:
                failed_validators.append("max_length_chars")

        # ─── TIER 2: ENTROPY & SURPRISAL ───
        entropy_val = compute_sequence_entropy(output.tokens)
        surprisal_val = compute_average_surprisal(output.tokens)

        # 1. Entropy validation
        if entropy_val > self.entropy_threshold:
            failed_validators.append("entropy")
            log_structured(
                "WARNING",
                f"Sequence entropy exceeded threshold. Value: {entropy_val:.2f}, Limit: {self.entropy_threshold:.2f}",
                task_id,
            )

        # 2. Average surprisal validation
        if surprisal_val > self.surprisal_threshold:
            failed_validators.append("average_surprisal")
            log_structured(
                "WARNING",
                f"Average surprisal exceeded threshold. Value: {surprisal_val:.2f}, Limit: {self.surprisal_threshold:.2f}",
                task_id,
            )

        # 3. Minimum probability floor check on logprobs
        prob_floor_failed = False
        for token in output.tokens:
            if token.logprob is not None:
                try:
                    p = math.exp(token.logprob)
                except (ValueError, OverflowError):
                    p = 0.0
                if p < self.min_prob_floor:
                    prob_floor_failed = True
                    break
        if prob_floor_failed:
            failed_validators.append("probability_floor")
            log_structured(
                "WARNING",
                f"Token probability fell below min probability floor {self.min_prob_floor}",
                task_id,
            )

        # ─── TIER 3: STOP SEQUENCE VALIDATION ───
        if constraints.stop_sequences:
            try:
                stop_passed = validate_stop_sequences(
                    output.text, constraints.stop_sequences
                )
                if not stop_passed:
                    failed_validators.append("stop_sequences")
            except Exception as e:
                log_structured("ERROR", f"Stop sequence matching failed: {e}", task_id)
                raise VerificationError(f"Stop sequence matching failed: {e}")

        # ─── TIER 4: LOCAL JUDGE ───
        # Runs if all core syntactic and statistical checks have passed
        if len(failed_validators) == 0 and self.local_judge is not None:
            try:
                judge_passed = self.local_judge(output.text)
                if not judge_passed:
                    failed_validators.append("local_judge")
            except Exception as e:
                log_structured("ERROR", f"Local Judge execution failed: {e}", task_id)
                raise VerificationError(f"Local Judge execution failed: {e}")

        passed = len(failed_validators) == 0

        return VerificationResult(
            passed=passed,
            average_surprisal=surprisal_val,
            sequence_entropy=entropy_val,
            failed_validators=failed_validators,
        )
