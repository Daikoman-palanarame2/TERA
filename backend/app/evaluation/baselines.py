import random
from typing import List, Tuple, Dict

"""
This module implements baseline routing comparison strategies:
1. Always Cheap: routes every prompt directly to the cheap model lane.
2. Always Dense: routes every prompt directly to the dense model lane.
3. Random Routing: routes prompts randomly (50/50) between cheap and dense.
"""

def run_always_cheap(dataset: List[Tuple[str, int, str]], c2: float, c3: float) -> Dict[str, float]:
    """
    Purpose:
        Evaluates prompt outcomes routing exclusively to the cheap model lane.
        
    Inputs:
        dataset: List of tuples (prompt, label, domain).
        c2: Token execution cost of the cheap model.
        c3: Token execution cost of the dense model (C_max).
        
    Outputs:
        A dictionary containing "accuracy", "cost", and "normalized_cost".
        
    Time Complexity:
        O(N) where N is dataset size.
        
    Memory Complexity:
        O(1) auxiliary memory.
    """
    n = len(dataset)
    if n == 0:
        return {"accuracy": 0.0, "average_cost": 0.0, "normalized_cost": 0.0}
        
    # Cheap accuracy is the prompt's ground-truth label (1 = success, 0 = fail)
    total_acc = sum(item[1] for item in dataset)
    avg_acc = float(total_acc / n)
    avg_cost = c2
    avg_norm_cost = c2 / c3
    
    return {
        "accuracy": avg_acc,
        "average_cost": avg_cost,
        "normalized_cost": avg_norm_cost
    }


def run_always_dense(dataset: List[Tuple[str, int, str]], c3: float, alpha_dense: float) -> Dict[str, float]:
    """
    Purpose:
        Evaluates prompt outcomes routing exclusively to the dense model lane.
        
    Inputs:
        dataset: List of tuples (prompt, label, domain).
        c3: Token execution cost of the dense model.
        alpha_dense: Constant baseline accuracy parameter of the dense model.
        
    Outputs:
        A dictionary containing "accuracy", "cost", and "normalized_cost".
        
    Time Complexity:
        O(N) where N is dataset size.
        
    Memory Complexity:
        O(1) auxiliary memory.
    """
    n = len(dataset)
    if n == 0:
        return {"accuracy": 0.0, "average_cost": 0.0, "normalized_cost": 0.0}
        
    # Dense accuracy is the domain-level dense baseline constant alpha_dense
    avg_acc = alpha_dense
    avg_cost = c3
    avg_norm_cost = 1.0
    
    return {
        "accuracy": avg_acc,
        "average_cost": avg_cost,
        "normalized_cost": avg_norm_cost
    }


def run_random_routing(
    dataset: List[Tuple[str, int, str]], 
    c2: float, 
    c3: float, 
    alpha_dense: float, 
    seed: int = 42
) -> Dict[str, float]:
    """
    Purpose:
        Evaluates outcomes when selecting cheap or dense models randomly with 50/50 probability.
        
    Inputs:
        dataset: List of tuples (prompt, label, domain).
        c2: Token execution cost of the cheap model.
        c3: Token execution cost of the dense model.
        alpha_dense: Constant baseline accuracy parameter of the dense model.
        seed: Random seed for deterministic reproducibility.
        
    Outputs:
        A dictionary containing "accuracy", "cost", and "normalized_cost".
        
    Time Complexity:
        O(N) where N is dataset size.
        
    Memory Complexity:
        O(1) auxiliary memory.
    """
    n = len(dataset)
    if n == 0:
        return {"accuracy": 0.0, "average_cost": 0.0, "normalized_cost": 0.0}
        
    rng = random.Random(seed)
    total_acc = 0.0
    total_cost = 0.0
    
    for _, label, _ in dataset:
        # 50/50 chance
        if rng.choice([True, False]):
            # Cheap selected
            total_acc += label
            total_cost += c2
        else:
            # Dense selected
            total_acc += alpha_dense
            total_cost += c3
            
    return {
        "accuracy": float(total_acc / n),
        "average_cost": float(total_cost / n),
        "normalized_cost": float((total_cost / n) / c3)
    }
