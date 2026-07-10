import csv
import random
from typing import List, Tuple

"""
This module handles loading labeled datasets from CSV files and performing
reproducible, deterministic train/calibration/validation splitting.
"""

def load_csv_dataset(filepath: str) -> List[Tuple[str, int, str]]:
    """
    Purpose:
        Loads a labeled dataset from a CSV file. Expected columns: prompt, label, [domain].
    
    Inputs:
        filepath: Path to the CSV file to load.
    
    Outputs:
        A list of tuples: (prompt, label, domain).
        
    Time Complexity:
        O(N) where N is the number of rows in the CSV file.
        
    Memory Complexity:
        O(N) to store the dataset in memory.
    """
    dataset = []
    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        # Read header to find column indices
        header = next(reader, None)
        if not header:
            return []
            
        # Match indices
        header_lower = [col.lower().strip() for col in header]
        try:
            prompt_idx = header_lower.index("prompt")
            label_idx = header_lower.index("label")
        except ValueError as e:
            raise ValueError("CSV must contain 'prompt' and 'label' columns.") from e
            
        domain_idx = header_lower.index("domain") if "domain" in header_lower else None
        
        for row in reader:
            if not row:
                continue
            prompt = row[prompt_idx]
            label = int(row[label_idx].strip())
            domain = row[domain_idx].strip() if (domain_idx is not None and domain_idx < len(row)) else "gen"
            dataset.append((prompt, label, domain))
            
    return dataset


def split_dataset(
    dataset: list, 
    train_pct: float = 0.6, 
    cal_pct: float = 0.2, 
    val_pct: float = 0.2, 
    seed: int = 42
) -> Tuple[list, list, list]:
    """
    Purpose:
        Splits a list dataset into Train, Calibration, and Validation subsets.
        Uses a local Random instance to ensure no global mutable state is affected.
        
    Inputs:
        dataset: The list of data points to split.
        train_pct: Target percentage of dataset for training (default 0.6).
        cal_pct: Target percentage of dataset for calibration (default 0.2).
        val_pct: Target percentage of dataset for validation (default 0.2).
        seed: Random seed for reproducibility.
        
    Outputs:
        A tuple of lists: (train_subset, calibration_subset, validation_subset).
        
    Time Complexity:
        O(N) to shuffle and slice lists.
        
    Memory Complexity:
        O(N) to create the split lists.
    """
    if not (0.99 <= train_pct + cal_pct + val_pct <= 1.01):
        raise ValueError("Split percentages must sum to 1.0")
        
    rng = random.Random(seed)
    shuffled = list(dataset)
    rng.shuffle(shuffled)
    
    n = len(shuffled)
    n_train = int(n * train_pct)
    n_cal = int(n * cal_pct)
    
    train_subset = shuffled[:n_train]
    cal_subset = shuffled[n_train:n_train + n_cal]
    val_subset = shuffled[n_train + n_cal:]
    
    return train_subset, cal_subset, val_subset
