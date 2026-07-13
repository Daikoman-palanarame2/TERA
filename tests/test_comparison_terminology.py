from app.core.orchestrator import TERAOrchestrator


def test_ml_dl_comparison_adds_missing_manual_feature_distinction():
    prompt = "What is the difference between machine learning and deep learning?"
    answer = (
        "Deep learning is a subset of machine learning that uses a multi-layer "
        "neural network to automatically extract features."
    )

    completed = TERAOrchestrator._ensure_comparison_terminology(prompt, answer)

    assert "feature engineering" in completed
    assert "automatically extract" in completed


def test_comparison_terminology_does_not_duplicate_complete_answer():
    prompt = "Compare machine learning and deep learning."
    answer = (
        "Machine learning can use manual feature engineering, while deep learning "
        "neural networks automatically extract features."
    )

    assert TERAOrchestrator._ensure_comparison_terminology(prompt, answer) == answer


def test_comparison_terminology_ignores_unrelated_comparison():
    answer = "RAM is volatile while ROM is non-volatile."
    assert TERAOrchestrator._ensure_comparison_terminology(
        "Explain the difference between RAM and ROM.", answer
    ) == answer
