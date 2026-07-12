"""Conservative post-generation enforcement for exact output constraints.

The enforcer only performs syntax-preserving normalization.  It never pads,
truncates, merges, or generates semantic content to make an answer pass.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import re
from typing import Sequence


@dataclass(frozen=True)
class EnforcementResult:
    """Immutable outcome of deterministic output enforcement."""

    success: bool
    output: str
    failures: tuple[str, ...] = ()
    transformations: tuple[str, ...] = ()


class OutputEnforcer:
    """Validate Track 1 formatting constraints without changing meaning."""

    _FENCE = re.compile(
        r"\A\s*```(?P<language>[A-Za-z0-9_-]*)[ \t]*\r?\n"
        r"(?P<body>.*?)\r?\n```\s*\Z",
        re.DOTALL,
    )
    _BULLET = re.compile(r"^\s*(?:[-+*]|\d+[.)])\s+(?P<body>\S.*)$")
    _WORD = re.compile(r"[^\W_]+(?:['’-][^\W_]+)*", re.UNICODE)
    _SENTENCE = re.compile(r"\S(?:.*?\S)?(?:[.!?]+(?=\s|$)|$)", re.DOTALL)

    @staticmethod
    def constraints_from_prompt(prompt: str) -> dict[str, int]:
        """Extract only explicit, unambiguous count constraints from a prompt."""
        constraints: dict[str, int] = {}
        number_words = {
            "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
            "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
        }
        number = r"(?P<count>\d+|one|two|three|four|five|six|seven|eight|nine|ten)"
        sentence_match = re.search(
            rf"\b(?:exactly\s+)?{number}\s+sentences?\b", prompt, re.IGNORECASE
        )
        bullet_match = re.search(
            rf"\b(?:exactly\s+)?{number}\s+bullet(?:\s+points?)?\b",
            prompt,
            re.IGNORECASE,
        )
        word_match = re.search(
            r"\b(?:no\s+(?:longer|more)\s+than|at\s+most|maximum(?:\s+of)?)\s+"
            r"(?P<count>\d+)\s+words?(?:\s+per\s+bullet|\s+each)?\b",
            prompt,
            re.IGNORECASE,
        )
        if sentence_match:
            raw = sentence_match.group("count").casefold()
            constraints["exact_sentence_count"] = int(raw) if raw.isdigit() else number_words[raw]
        if bullet_match:
            raw = bullet_match.group("count").casefold()
            constraints["exact_bullet_count"] = int(raw) if raw.isdigit() else number_words[raw]
        if word_match:
            constraints["max_words_per_bullet"] = int(word_match.group("count"))
        return constraints

    def enforce(
        self,
        text: str,
        *,
        exact_sentence_count: int | None = None,
        exact_bullet_count: int | None = None,
        max_words_per_bullet: int | None = None,
        classification_labels: Sequence[str] | None = None,
        strip_json_fence: bool = False,
    ) -> EnforcementResult:
        """Normalize safe wrappers and validate requested format constraints.

        Failed constraints leave semantic content intact and are reported using
        stable machine-readable failure codes.
        """
        self._validate_nonnegative("exact_sentence_count", exact_sentence_count)
        self._validate_nonnegative("exact_bullet_count", exact_bullet_count)
        self._validate_nonnegative("max_words_per_bullet", max_words_per_bullet)
        if not isinstance(text, str):
            raise TypeError("text must be a string")

        output = text.strip()
        failures: list[str] = []
        transformations: list[str] = []

        if strip_json_fence:
            output, json_failure, changed = self._strip_json_fence(output)
            if json_failure:
                failures.append(json_failure)
            if changed:
                transformations.append("json_fence_stripped")

        if classification_labels is not None:
            output, label_failure, changed = self._normalize_label(
                output, classification_labels
            )
            if label_failure:
                failures.append(label_failure)
            if changed:
                transformations.append("classification_label_normalized")

        if exact_sentence_count is not None:
            if self.count_sentences(output) != exact_sentence_count:
                failures.append("exact_sentence_count")

        bullets = self._bullet_bodies(output)
        if exact_bullet_count is not None and len(bullets) != exact_bullet_count:
            failures.append("exact_bullet_count")

        if max_words_per_bullet is not None:
            if not bullets or any(
                self.count_words(body) > max_words_per_bullet for body in bullets
            ):
                failures.append("max_words_per_bullet")

        return EnforcementResult(
            success=not failures,
            output=output,
            failures=tuple(failures),
            transformations=tuple(transformations),
        )

    @classmethod
    def count_words(cls, text: str) -> int:
        """Count Unicode words, retaining internal apostrophes and hyphens."""
        return len(cls._WORD.findall(text))

    @classmethod
    def count_sentences(cls, text: str) -> int:
        """Count non-empty punctuation-delimited sentences conservatively."""
        return len(cls._SENTENCE.findall(text.strip())) if text.strip() else 0

    @classmethod
    def _bullet_bodies(cls, text: str) -> list[str]:
        return [
            match.group("body")
            for line in text.splitlines()
            if (match := cls._BULLET.fullmatch(line)) is not None
        ]

    @classmethod
    def _strip_json_fence(cls, text: str) -> tuple[str, str | None, bool]:
        match = cls._FENCE.fullmatch(text)
        candidate = text
        changed = False
        if match:
            language = match.group("language").casefold()
            if language not in {"", "json"}:
                return text, "unsafe_json_fence", False
            candidate = match.group("body").strip()
            changed = True
        try:
            json.loads(candidate)
        except (json.JSONDecodeError, TypeError):
            return text, "invalid_json", False
        return candidate, None, changed

    @staticmethod
    def _normalize_label(
        text: str, labels: Sequence[str]
    ) -> tuple[str, str | None, bool]:
        canonical: dict[str, str] = {}
        for label in labels:
            if not isinstance(label, str) or not label.strip():
                raise ValueError("classification labels must be non-empty strings")
            key = " ".join(label.split()).casefold()
            if key in canonical and canonical[key] != label:
                raise ValueError("classification labels are ambiguous after normalization")
            canonical[key] = label
        if not canonical:
            raise ValueError("classification_labels must not be empty")

        candidate = text.strip()
        key = " ".join(candidate.split()).casefold()
        if key not in canonical:
            return text, "classification_label", False
        normalized = canonical[key]
        return normalized, None, normalized != text

    @staticmethod
    def _validate_nonnegative(name: str, value: int | None) -> None:
        if value is not None and (
            isinstance(value, bool) or not isinstance(value, int) or value < 0
        ):
            raise ValueError(f"{name} must be a non-negative integer")
