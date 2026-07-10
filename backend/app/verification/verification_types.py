from dataclasses import dataclass
from enum import Enum
from typing import List, Optional

"""
This module defines enums and immutable data containers for verification status,
reasons for output failure, and schema types.
"""

class VerificationStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"


class FailureReason(str, Enum):
    SCHEMA = "schema"
    LENGTH = "length"
    STOP_TOKEN = "stop_token"
    ENTROPY = "entropy"
    MULTIPLE = "multiple"


class SchemaType(str, Enum):
    NONE = "none"
    JSON = "json"
    REGEX = "regex"


@dataclass(frozen=True)
class VerificationResult:
    """
    Purpose:
        An immutable dataclass containing the validation outcome, failure reasons,
        token entropy, and individual validator results for telemetry and debugging.
        
    Fields:
        status: Blended status (PASS or FAIL).
        failure_reasons: List of failed checkers. If multiple fail, contains [FailureReason.MULTIPLE].
        output_entropy: Computed token entropy (None if unavailable).
        schema_passed: True if schema/regex validated successfully.
        length_passed: True if characters/tokens length bounds validated successfully.
        stop_token_passed: True if correct stop-sequence termination is confirmed.
        entropy_passed: True if output entropy is below threshold, False if above, None if unavailable.
    """
    status: VerificationStatus
    failure_reasons: List[FailureReason]
    output_entropy: Optional[float]
    schema_passed: bool
    length_passed: bool
    stop_token_passed: bool
    entropy_passed: Optional[bool]
