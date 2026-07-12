"""
Module: backend/app/solvers/plugins/text_counter_solver
Purpose:
    Deterministic solver for counting words, characters, lines, or
    occurrences in a target text block.
"""

import re
from app.solvers.base_solver import BaseSolver
from app.core.exceptions import VerificationError


class TextCounterSolver(BaseSolver):
    """Solver for counting elements within text string datasets."""

    @property
    def name(self) -> str:
        """Return the unique code name string of the solver."""
        return "text_counter_solver"

    @property
    def pattern(self) -> str:
        """Return the pre-compiled regex trigger string."""
        # Only claim prompts with an explicit payload boundary.  Requiring a
        # quoted payload or ``:`` prevents factual/narrative questions such as
        # "number of words in the English language" from being miscounted.
        standard = (
            r"(?:words|characters|chars|lines)\s+(?:in|of)\s*"
            r"(?:['\"].*['\"]|:.*)"
        )
        occurrences = (
            r"occurrences\s+(?:of\s+)?['\"].*?['\"]\s+(?:in|of)\s*"
            r"(?:['\"].*['\"]|:.*)"
        )
        implicit_occurrences = (
            r"['\"].*?['\"]\s+(?:in|of)\s*"
            r"(?:['\"].*['\"]|:.*)"
        )
        # The lookahead validates the complete shape while the final capture
        # preserves the historical group contract consumed by ``solve``.
        return (
            rf"(?is)^\s*(?=(?:count|number\s+of)\s+"
            rf"(?:{standard}|{occurrences}|{implicit_occurrences})\s*$)"
            r"(?:count|number\s+of)\s+"
            r"(words|characters|chars|lines|occurrences|['\"].*?['\"])"
        )

    def solve(self, prompt: str) -> str:
        """Execute the deterministic counting algorithm.

        Args:
            prompt: The raw user prompt containing the text block and counting constraints.

        Returns:
            The counted total representation formatted as a string.

        Raises:
            VerificationError: If parsing the prompt structure fails or
                               unsupported configurations are requested.
        """
        match = re.search(self.pattern, prompt)
        if not match:
            raise VerificationError(
                "Prompt does not match text counter pattern.", task_id=None
            )

        matched_category = match.group(1).lower()

        # Determine category and target substring
        target_sub = None
        if matched_category in ("words", "characters", "chars", "lines", "occurrences"):
            category = matched_category
        else:
            # It matched a quoted string directly, which represents an implicit occurrences category
            category = "occurrences"
            target_sub = self._clean_quotes(matched_category)

        text_content = ""

        # Extract target_sub and text_content based on category
        if category == "occurrences":
            if target_sub is not None:
                # If target_sub was already extracted from the pattern match, we just extract text_content
                # Pattern: count 'sub' in 'text'
                text_match = re.search(
                    rf"(?i)count\s+['\"]{re.escape(target_sub)}['\"]\s+(?:in|of)\s+['\"](.*?)['\"]",
                    prompt,
                    re.DOTALL,
                )
                if not text_match:
                    text_match = re.search(
                        rf"(?i)count\s+['\"]{re.escape(target_sub)}['\"]\s+(?:in|of)\s*:\s*(.*)",
                        prompt,
                        re.DOTALL,
                    )
                if text_match:
                    text_content = text_match.group(1)
                else:
                    # Fallback lookup for "in/of"
                    fallback_match = re.search(
                        r"(?i)\b(?:in|of)\s+(.*)", prompt, re.DOTALL
                    )
                    if fallback_match:
                        text_content = fallback_match.group(1)
                    else:
                        raise VerificationError(
                            "Failed to parse occurrences text content.", task_id=None
                        )
            else:
                # Standard explicit category: count occurrences of 'sub' in 'text'
                occ_match = re.search(
                    r"(?i)(?:count|number\s+of)\s+occurrences\s+(?:of\s+)?['\"](.*?)['\"]\s+(?:in|of)\s+['\"](.*?)['\"]",
                    prompt,
                    re.DOTALL,
                )
                if not occ_match:
                    occ_match = re.search(
                        r"(?i)(?:count|number\s+of)\s+occurrences\s+(?:of\s+)?['\"](.*?)['\"]\s+(?:in|of)\s*:\s*(.*)",
                        prompt,
                        re.DOTALL,
                    )
                if occ_match:
                    target_sub = occ_match.group(1)
                    text_content = occ_match.group(2)
                else:
                    raise VerificationError(
                        "Failed to parse occurrences target and text.", task_id=None
                    )
        else:
            # Words, characters, lines
            text_match = re.search(
                r"(?i)(?:count|number\s+of)\s+(?:words|characters|chars|lines)\s+(?:in|of)\s+['\"](.*?)['\"]",
                prompt,
                re.DOTALL,
            )
            if not text_match:
                text_match = re.search(
                    r"(?i)(?:count|number\s+of)\s+(?:words|characters|chars|lines)\s+(?:in|of)\s*:\s*(.*)",
                    prompt,
                    re.DOTALL,
                )
            if text_match:
                text_content = text_match.group(1)
            else:
                fallback_match = re.search(r"(?i)\b(?:in|of)\s+(.*)", prompt, re.DOTALL)
                if fallback_match:
                    text_content = fallback_match.group(1)
                else:
                    raise VerificationError(
                        "Failed to parse target text.", task_id=None
                    )

        # Uniformly clean quotes and strip whitespace from text_content and target_sub
        text_content = self._clean_quotes(text_content)
        if target_sub is not None:
            target_sub = self._clean_quotes(target_sub)

        # Counting Algorithms
        if category == "words":
            count = len(text_content.split()) if text_content else 0
        elif category in ("characters", "chars"):
            count = len(text_content)
        elif category == "lines":
            count = len(text_content.splitlines()) if text_content else 0
        elif category == "occurrences":
            if target_sub is None:
                raise VerificationError("No occurrence target specified.", task_id=None)
            count = text_content.count(target_sub)
        else:
            raise VerificationError(
                f"Unsupported counter category: {category}", task_id=None
            )

        return str(count)

    def _clean_quotes(self, text: str) -> str:
        """Helper to clean leading/trailing whitespace and matching quote wrappers.

        Args:
            text: The input string.

        Returns:
            The cleaned string.
        """
        text = text.strip()
        if len(text) >= 2 and text.startswith(("'", '"')) and text.endswith(text[0]):
            return text[1:-1]
        return text
