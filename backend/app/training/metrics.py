import numpy as np

"""
This module implements validation and calibration quality metrics:
Expected Calibration Error (ECE) and Brier Score.
"""

def compute_brier_score(y_true: np.ndarray, y_prob: np.ndarray) -> float:
    """
    Purpose:
        Computes the Brier score, which measures the mean squared difference 
        between predicted probabilities and actual binary outcomes.
        
    Inputs:
        y_true: Array of binary ground-truth labels (0 or 1).
        y_prob: Array of predicted probabilities in range [0, 1].
        
    Outputs:
        A float representing the Brier score. Lower scores indicate better calibration.
        
    Time Complexity:
        O(N) where N is the number of samples.
        
    Memory Complexity:
        O(1) auxiliary memory.
    """
    if len(y_true) != len(y_prob):
        raise ValueError("Inputs y_true and y_prob must have identical dimensions.")
    return float(np.mean((y_true - y_prob) ** 2))


def compute_ece(y_true: np.ndarray, y_prob: np.ndarray, n_bins: int = 10) -> float:
    """
    Purpose:
        Computes the Expected Calibration Error (ECE) which bins predictions 
        and weights the absolute difference between average confidence and accuracy.
        
    Inputs:
        y_true: Array of binary ground-truth labels (0 or 1).
        y_prob: Array of predicted probabilities in range [0, 1].
        n_bins: Number of equal-width bins to divide [0, 1] (default 10).
        
    Outputs:
        A float representing the ECE score (value between 0.0 and 1.0).
        
    Time Complexity:
        O(N + B) where N is number of samples and B is number of bins.
        
    Memory Complexity:
        O(B) memory to store bin statistics.
    """
    if len(y_true) != len(y_prob):
        raise ValueError("Inputs y_true and y_prob must have identical dimensions.")
        
    ece = 0.0
    n_samples = len(y_true)
    if n_samples == 0:
        return 0.0
        
    # Bin boundaries
    bin_boundaries = np.linspace(0.0, 1.0, n_bins + 1)
    
    for i in range(n_bins):
        bin_lower = bin_boundaries[i]
        bin_upper = bin_boundaries[i + 1]
        
        # Find indices falling inside the bin
        if i == n_bins - 1:
            # Include 1.0 in the last bin
            in_bin = (y_prob >= bin_lower) & (y_prob <= bin_upper)
        else:
            in_bin = (y_prob >= bin_lower) & (y_prob < bin_upper)
            
        bin_size = int(np.sum(in_bin))
        if bin_size > 0:
            # Accuracy is average label count
            bin_acc = float(np.mean(y_true[in_bin]))
            # Confidence is average predicted probability
            bin_conf = float(np.mean(y_prob[in_bin]))
            # Weighted bin error contribution
            ece += (bin_size / n_samples) * abs(bin_acc - bin_conf)
            
    return ece
