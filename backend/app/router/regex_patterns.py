import re
from typing import Dict

"""
This module defines pre-compiled regular expression patterns for prompt keyword detection.
Each pattern is compiled with case-insensitivity and looks for common verbs or keywords 
associated with specific task domains.
"""

DEFAULT_PATTERNS: Dict[str, re.Pattern] = {
    "summarize": re.compile(
        r"\b(summarize|summary|outline|shorten|digest|abridge|condense)\b", 
        re.IGNORECASE
    ),
    "explain": re.compile(
        r"\b(explain|how|why|describe|clarify|define|explanation|what is)\b", 
        re.IGNORECASE
    ),
    "extract": re.compile(
        r"\b(extract|find|retrieve|parse|get|grab|locate|identify)\b", 
        re.IGNORECASE
    ),
    "translate": re.compile(
        r"\b(translate|translation|translate\s+to|language|french|spanish|german|chinese|japanese)\b", 
        re.IGNORECASE
    ),
    "debug": re.compile(
        r"\b(debug|fix|error|bug|issue|exception|stack\s*trace|crash|resolve)\b", 
        re.IGNORECASE
    ),
    "classify": re.compile(
        r"\b(classify|category|tag|label|group|sort|classification)\b", 
        re.IGNORECASE
    ),
    "compare": re.compile(
        r"\b(compare|difference|contrast|versus|vs|distinguish|similarities|analogy)\b", 
        re.IGNORECASE
    ),
    "calculate": re.compile(
        r"\b(calculate|solve|math|formula|equation|compute|sum|multiply|divide|subtract|add|arithmetic)\b", 
        re.IGNORECASE
    ),
    "code": re.compile(
        r"\b(code|program|script|function|class|method|snippet|syntax|develop|implement|python|javascript|typescript|c\+\+|java)\b", 
        re.IGNORECASE
    ),
    "json": re.compile(
        r"\b(json|schema|format|dictionary|payload|nested|parse\s+json)\b", 
        re.IGNORECASE
    ),
}
