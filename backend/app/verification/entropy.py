import math
from typing import List, Optional

"""
This module implements validation entropy calculations using the generated token probabilities.
"""

def compute_entropy(probs: Optional[List[float]]) -> Optional[float]:
    """
    Purpose:
        Computes the natural log sequence entropy across a list of token probabilities:
        H = -sum(p_t * ln(p_t))
        
    Inputs:
        probs: List of floating-point probabilities in range [0, 1].
        
    Outputs:
        A float representing the sequence entropy. Returns None if probabilities 
        are empty, None, or invalid.
        
    Time Complexity:
        O(T) where T is the number of tokens (length of probs).
        
    Memory Complexity:
        O(1) auxiliary memory.
    """
    if probs is None or len(probs) == 0:
        return None
        
    entropy = 0.0
    for p in probs:
        # Ignore non-positive probabilities and clamp upper bound to 1.0
        if p <= 0.0:
            continue
        elif p > 1.0:
            p = 1.0
            
        entropy -= p * math.log(p)
        
    return float(entropy)
