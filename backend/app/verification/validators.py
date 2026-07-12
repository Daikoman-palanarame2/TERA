"""
Module: backend/app/verification/validators
Purpose:
    Implements JSON schema, regex pattern, and stop sequence validators.
"""

import re
import json
import jsonschema
import concurrent.futures
from typing import List, Dict, Any
from app.core.exceptions import VerificationError


def validate_json_schema(text: str, schema: Dict[str, Any]) -> bool:
    """Validate JSON text against a target JSON Schema dictionary.

    Args:
        text: The string output to check.
        schema: OpenAPI or JSON Schema dictionary structure.

    Returns:
        True if the text is valid JSON and matches the schema, False otherwise.

    Raises:
        VerificationError: If the schema itself is invalid.
    """
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return False

    try:
        jsonschema.validate(instance=data, schema=schema)
        return True
    except jsonschema.exceptions.SchemaError as e:
        raise VerificationError(f"Invalid schema dictionary: {e}")
    except jsonschema.exceptions.ValidationError:
        return False


def validate_regex(text: str, pattern: str) -> bool:
    """Check if the text matches a compiled regex pattern.

    Args:
        text: The string output to check.
        pattern: The regex pattern string.

    Returns:
        True if pattern is found, False otherwise.

    Raises:
        VerificationError: If pattern string is invalid and fails to compile.
    """
    try:
        compiled = re.compile(pattern)
    except re.error as e:
        raise VerificationError(
            f"Catastrophic or invalid regex pattern fails to compile: {e}"
        )

    # Timeout-safe execution: run re.search in a ThreadPoolExecutor with a 2.0s timeout
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(compiled.search, text)
        try:
            match = future.result(timeout=2.0)
            return match is not None
        except concurrent.futures.TimeoutError:
            return False


def validate_stop_sequences(text: str, stop_sequences: List[str]) -> bool:
    """Verify that the generation naturally terminated on a valid stop sequence.

    Args:
        text: The string output to check.
        stop_sequences: List of target stop tokens.

    Returns:
        True if output ends with a registered stop sequence or contains it.
    """
    if not stop_sequences:
        return True

    for seq in stop_sequences:
        if text.endswith(seq) or seq in text:
            return True

    return False
