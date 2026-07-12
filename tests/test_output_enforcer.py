"""Tests for conservative Track 1 output-format enforcement."""

import pytest

from app.verification.output_enforcer import OutputEnforcer


def test_exact_sentence_count_passes_without_rewriting() -> None:
    text = "AMD accelerates local AI. TERA reduces external tokens!"
    result = OutputEnforcer().enforce(text, exact_sentence_count=2)
    assert result.success
    assert result.output == text
    assert not result.transformations


def test_sentence_mismatch_fails_without_inventing_content() -> None:
    text = "One sentence only."
    result = OutputEnforcer().enforce(text, exact_sentence_count=2)
    assert not result.success
    assert result.output == text
    assert result.failures == ("exact_sentence_count",)


def test_exact_bullets_and_word_limit_support_markdown_and_numbering() -> None:
    text = "- Fast local route\n2. Zero external tokens\n* Verified output"
    result = OutputEnforcer().enforce(
        text, exact_bullet_count=3, max_words_per_bullet=3
    )
    assert result.success
    assert result.output == text


def test_bullet_constraints_report_each_failure_without_truncation() -> None:
    text = "- this bullet contains far too many words\nnot a bullet"
    result = OutputEnforcer().enforce(
        text, exact_bullet_count=2, max_words_per_bullet=3
    )
    assert not result.success
    assert result.output == text
    assert result.failures == ("exact_bullet_count", "max_words_per_bullet")


def test_classification_label_normalizes_only_exact_casefolded_label() -> None:
    result = OutputEnforcer().enforce(
        "  poSITive  ", classification_labels=("Positive", "Negative")
    )
    assert result.success
    assert result.output == "Positive"
    assert result.transformations == ("classification_label_normalized",)


def test_unknown_classification_label_is_not_fuzzily_replaced() -> None:
    result = OutputEnforcer().enforce(
        "mostly positive", classification_labels=("Positive", "Negative")
    )
    assert not result.success
    assert result.output == "mostly positive"
    assert result.failures == ("classification_label",)


def test_valid_json_fence_is_safely_stripped() -> None:
    result = OutputEnforcer().enforce(
        '```json\n{"route": "local"}\n```', strip_json_fence=True
    )
    assert result.success
    assert result.output == '{"route": "local"}'
    assert result.transformations == ("json_fence_stripped",)


@pytest.mark.parametrize(
    "text,failure",
    [
        ('prefix\n```json\n{"ok": true}\n```', "invalid_json"),
        ("```json\n{not valid}\n```", "invalid_json"),
        ('```python\n{"ok": true}\n```', "unsafe_json_fence"),
    ],
)
def test_json_stripping_rejects_unsafe_or_invalid_wrappers(
    text: str, failure: str
) -> None:
    result = OutputEnforcer().enforce(text, strip_json_fence=True)
    assert not result.success
    assert result.output == text
    assert result.failures == (failure,)


def test_plain_valid_json_is_accepted_without_transformation() -> None:
    text = '{"ok": true}'
    result = OutputEnforcer().enforce(text, strip_json_fence=True)
    assert result.success
    assert result.output == text
    assert not result.transformations


def test_invalid_constraint_values_are_rejected() -> None:
    with pytest.raises(ValueError):
        OutputEnforcer().enforce("text", exact_bullet_count=-1)
    with pytest.raises(ValueError):
        OutputEnforcer().enforce("text", exact_sentence_count=True)


def test_explicit_prompt_constraints_are_extracted() -> None:
    constraints = OutputEnforcer.constraints_from_prompt(
        "Summarize in exactly three bullet points, each no longer than 15 words."
    )
    assert constraints == {
        "exact_bullet_count": 3,
        "max_words_per_bullet": 15,
    }


def test_sentence_prompt_constraint_and_ambiguous_prompt_handling() -> None:
    assert OutputEnforcer.constraints_from_prompt(
        "Respond in exactly two sentences."
    ) == {"exact_sentence_count": 2}
    assert OutputEnforcer.constraints_from_prompt(
        "Give a concise and readable summary."
    ) == {}
