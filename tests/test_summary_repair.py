from app.core.orchestrator import TERAOrchestrator
from app.verification.output_enforcer import OutputEnforcer


def test_two_sentence_contrast_summary_repair_preserves_both_sides():
    prompt = (
        "Summarize in exactly two sentences: Machine learning supports healthcare "
        "diagnosis, planning and monitoring, but raises interpretability, privacy, "
        "liability, bias and regulatory concerns."
    )

    repaired = TERAOrchestrator._repair_two_sentence_contrast_summary(prompt)

    assert repaired is not None
    assert OutputEnforcer.count_sentences(repaired) == 2
    assert "healthcare diagnosis" in repaired
    assert "privacy" in repaired
    assert "regulatory" in repaired


def test_two_sentence_repair_declines_ambiguous_source():
    assert TERAOrchestrator._repair_two_sentence_contrast_summary(
        "Summarize this paragraph concisely."
    ) is None
