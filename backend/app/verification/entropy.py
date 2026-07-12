"""
Module: backend/app/verification/entropy
Purpose:
    Calculate average token surprisal and sequence entropy from token probabilities.
"""

import math
from typing import List
from app.schemas.data_contracts import TokenLogprob


def compute_sequence_entropy(tokens: List[TokenLogprob]) -> float:
    """Calculate the average Shannon entropy across a sequence of token logprobs.

    Args:
        tokens: List of TokenLogprob instances from model metadata.

    Returns:
        The calculated mean sequence entropy score.
    """
    if not tokens:
        return 0.0

    total_entropy = 0.0
    valid_count = 0

    for t in tokens:
        if t.logprob is None or math.isnan(t.logprob) or math.isinf(t.logprob):
            continue

        lp = t.logprob
        if lp > 0.0:
            lp = 0.0  # Clamp logprob to 0.0 (prob = 1.0)

        p = math.exp(lp)
        if p <= 0.0:
            contrib = 0.0
        else:
            contrib = -p * lp

        total_entropy += contrib
        valid_count += 1

    if valid_count == 0:
        return 0.0

    return total_entropy / valid_count


def compute_average_surprisal(tokens: List[TokenLogprob]) -> float:
    """Calculate the mean surprisal score (-logprob) across generated tokens.

    Args:
        tokens: List of TokenLogprob instances.

    Returns:
        The calculated average surprisal score.
    """
    if not tokens:
        return 0.0

    total_surprisal = 0.0
    valid_count = 0

    for t in tokens:
        if t.logprob is None or math.isnan(t.logprob):
            continue

        lp = t.logprob
        if math.isinf(lp) and lp < 0:
            # Handle negative infinity (0 probability) stably
            surprisal_contrib = 100.0
        elif lp > 0.0:
            surprisal_contrib = 0.0  # Clamp positive logprob to 0.0 surprisal
        else:
            surprisal_contrib = -lp

        total_surprisal += surprisal_contrib
        valid_count += 1

    if valid_count == 0:
        return 0.0

    return total_surprisal / valid_count
