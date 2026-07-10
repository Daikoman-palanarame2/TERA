from typing import Dict

"""
This module implements the expected utility equations derived from the TERA research paper.
Calculations are executed inside a normalized, dimensionless Lagrangian optimization domain.
"""

def compute_utilities(
    calibrated_prob: float,
    c2: float,
    c3: float,
    lambda_coeff: float,
    alpha_dense: float
) -> Dict[str, float]:
    """
    Purpose:
        Computes the expected Lagrangian utility for the three candidate paths:
        1. Direct Cheap Model Path (M2)
        2. Direct Dense Model Path (M3)
        3. Cascade Path (M2 -> M3)
        
    Inputs:
        calibrated_prob: Calibrated success probability of the cheap model.
        c2: Token execution cost of the cheap model lane.
        c3: Token execution cost of the dense model lane (serves as C_max).
        lambda_coeff: Trade-off coefficient between accuracy and token frugality (in range [0, 1]).
        alpha_dense: Domain-level baseline success accuracy parameter of the dense model.
        
    Outputs:
        A dictionary containing expected utilities for:
        - "cheap": expected utility score of cheap path.
        - "dense": expected utility score of dense path.
        - "cascade": expected utility score of cascading path.
        
    Time Complexity:
        O(1) elementary floating-point arithmetic.
        
    Memory Complexity:
        O(1) memory allocation.
    """
    if c3 <= 0.0:
        raise ValueError("Dense model cost c3 must be strictly greater than 0.")
        
    # Cost normalization ratio: c2 / c3
    normalized_cheap_cost = c2 / c3
    
    # 1. Direct Cheap Model Path (M2) utility
    # U(M2) = lambda * P - (1 - lambda) * (C2 / C3)
    u_cheap = lambda_coeff * calibrated_prob - (1.0 - lambda_coeff) * normalized_cheap_cost
    
    # 2. Direct Dense Model Path (M3) utility
    # U(M3) = lambda * alpha_dense - (1 - lambda) * 1.0
    u_dense = lambda_coeff * alpha_dense - (1.0 - lambda_coeff)
    
    # 3. Cascade Path (M_cascade) utility
    # Expected accuracy: P + (1 - P) * alpha_dense
    expected_acc_cascade = calibrated_prob + (1.0 - calibrated_prob) * alpha_dense
    # Expected normalized cost: (C2 + (1 - P) * C3) / C3 = (C2 / C3) + (1 - P)
    expected_cost_cascade = normalized_cheap_cost + (1.0 - calibrated_prob)
    
    u_cascade = lambda_coeff * expected_acc_cascade - (1.0 - lambda_coeff) * expected_cost_cascade
    
    return {
        "cheap": float(u_cheap),
        "dense": float(u_dense),
        "cascade": float(u_cascade)
    }
