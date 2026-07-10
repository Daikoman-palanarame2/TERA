import json
import re
from typing import List, Optional
from app.verification.verification_types import SchemaType

"""
This module implements deterministic, CPU-bound validation checkers for prompt completions.
"""

def validate_schema(text: str, schema_type: SchemaType, regex_pattern: Optional[str] = None) -> bool:
    """
    Purpose:
        Validates completion string structure against JSON parse or regular expressions.
        
    Inputs:
        text: Prompt completion string to validate.
        schema_type: SchemaType enum selection (NONE, JSON, or REGEX).
        regex_pattern: Optional regex pattern string to evaluate.
        
    Outputs:
        True if text conforms to selected schema constraints, False otherwise.
        
    Time Complexity:
        - SchemaType.JSON: O(L) where L is text character length.
        - SchemaType.REGEX: O(L * P) where P is regex pattern complexity.
        - SchemaType.NONE: O(1).
        
    Memory Complexity:
        O(L) to load the JSON AST structure.
    """
    if schema_type == SchemaType.NONE:
        return True
        
    if schema_type == SchemaType.JSON:
        try:
            json.loads(text)
            return True
        except (json.JSONDecodeError, TypeError):
            return False
            
    if schema_type == SchemaType.REGEX:
        if not regex_pattern:
            return True
        try:
            match = re.search(regex_pattern, text)
            return match is not None
        except re.error:
            return False
            
    return False


def validate_length(
    text: str, 
    min_chars: Optional[int] = None, 
    max_chars: Optional[int] = None, 
    max_token_ceiling_hit: bool = False
) -> bool:
    """
    Purpose:
        Validates completion absolute character bounds and checks token ceiling flags.
        
    Inputs:
        text: Prompt completion string to validate.
        min_chars: Minimum required character count (optional).
        max_chars: Maximum allowed character count (optional).
        max_token_ceiling_hit: Boolean flag from model client indicating execution truncated
                              due to token budget limit hits.
                              
    Outputs:
        True if all bounds are respected and token ceiling was not hit, False otherwise.
        
    Time Complexity:
        O(1) (evaluates len(text) and boolean flag).
        
    Memory Complexity:
        O(1) auxiliary memory.
    """
    if max_token_ceiling_hit:
        return False
        
    length = len(text)
    if min_chars is not None and length < min_chars:
        return False
        
    if max_chars is not None and length > max_chars:
        return False
        
    return True


def validate_stop_tokens(text: str, stop_sequences: Optional[List[str]] = None) -> bool:
    """
    Purpose:
        Validates that the generated output terminates cleanly with a valid stop token,
        preventing acceptance of abruptly truncated sentences.
        
    Inputs:
        text: Prompt completion string to validate.
        stop_sequences: List of string stop tokens (e.g. ['\n', '}', '<|im_end|>']).
        
    Outputs:
        True if text terminates with at least one stop sequence (or if none are configured).
        False if text terminates without matching stop sequences.
        
    Time Complexity:
        O(S * W) where S is number of stop sequences and W is average stop sequence length.
        
    Memory Complexity:
        O(1) auxiliary memory.
    """
    if not stop_sequences:
        return True
        
    for seq in stop_sequences:
        if text.endswith(seq):
            return True
            
    return False
