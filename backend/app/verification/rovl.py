from typing import List, Optional

from app.verification.verification_types import (
    VerificationStatus, 
    FailureReason, 
    SchemaType, 
    VerificationResult
)
from app.verification.validators import (
    validate_schema, 
    validate_length, 
    validate_stop_tokens
)
from app.verification.entropy import compute_entropy

class ROVL:
    """
    Purpose:
        The Runtime Output Verification Layer (ROVL) orchestrates validation checks
        on generations produced by the cheap model lane. If completions fail schema,
        length, stop-token, or entropy checks, it flags validation failure to trigger
        automatic escalation to the dense model lane.
        
    Time Complexity:
        O(L + T + S * W) dominated by schema checks (JSON/regex), entropy loop, 
        and stop sequence matching.
        
    Memory Complexity:
        O(L) to load completion strings and token statistics in memory.
    """

    def __init__(self, entropy_threshold: float = 3.0, stop_sequences: Optional[List[str]] = None) -> None:
        """
        Purpose:
            Initializes the verification layer with specific threshold parameters.
            
        Inputs:
            entropy_threshold: The maximum acceptable sequence entropy threshold (default: 3.0).
            stop_sequences: List of string stop tokens (e.g. ['\n', '}', '<|im_end|>']).
            
        Outputs:
            None
        """
        self.entropy_threshold = entropy_threshold
        self.stop_sequences = stop_sequences or []

    def verify(
        self,
        text: str,
        token_probs: Optional[List[float]] = None,
        schema_type: SchemaType = SchemaType.NONE,
        regex_pattern: Optional[str] = None,
        min_chars: Optional[int] = None,
        max_chars: Optional[int] = None,
        max_token_ceiling_hit: bool = False
    ) -> VerificationResult:
        """
        Purpose:
            Runs all validators and aggregates outcomes, implementing degraded observability fallback.
            
        Inputs:
            text: Prompt completion string to check.
            token_probs: List of generated token probabilities (None if unavailable).
            schema_type: SchemaType enum.
            regex_pattern: Optional regex pattern.
            min_chars: Minimum character count.
            max_chars: Maximum character count.
            max_token_ceiling_hit: True if model truncated execution at token ceiling.
            
        Outputs:
            A frozen VerificationResult containing individual outcome metrics.
            
        Time/Memory Complexity:
            Same as class definitions, completing in microsecond scales.
        """
        # 1. Schema Validation
        schema_passed = validate_schema(text, schema_type, regex_pattern)
        
        # 2. Length Validation
        length_passed = validate_length(text, min_chars, max_chars, max_token_ceiling_hit)
        
        # 3. Stop token Validation
        stop_token_passed = validate_stop_tokens(text, self.stop_sequences)
        
        # 4. Entropy Validation (with Degraded Observability Fallback)
        output_entropy = compute_entropy(token_probs)
        if output_entropy is None:
            # Degraded observability mode: suspend checking, skip failure marking
            entropy_passed = None
        else:
            entropy_passed = output_entropy <= self.entropy_threshold
            
        # 5. Aggregate failures
        reasons: List[FailureReason] = []
        
        if not schema_passed:
            reasons.append(FailureReason.SCHEMA)
        if not length_passed:
            reasons.append(FailureReason.LENGTH)
        if not stop_token_passed:
            reasons.append(FailureReason.STOP_TOKEN)
        if entropy_passed is False:
            reasons.append(FailureReason.ENTROPY)
            
        if len(reasons) > 0:
            status = VerificationStatus.FAIL
            # If multiple checkers fail, return FailureReason.MULTIPLE
            if len(reasons) > 1:
                failure_reasons = [FailureReason.MULTIPLE]
            else:
                failure_reasons = reasons
        else:
            status = VerificationStatus.PASS
            failure_reasons = []
            
        return VerificationResult(
            status=status,
            failure_reasons=failure_reasons,
            output_entropy=output_entropy,
            schema_passed=schema_passed,
            length_passed=length_passed,
            stop_token_passed=stop_token_passed,
            entropy_passed=entropy_passed
        )
