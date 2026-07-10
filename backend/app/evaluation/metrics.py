import numpy as np
from typing import List, Dict, Any
from app.training.metrics import compute_brier_score, compute_ece

"""
This module computes statistical evaluation metrics for routing runs,
including ECE, Brier score, latencies, cost, and routing confusion states.
"""

def compute_evaluation_metrics(
    results: List[dict],
    labels: np.ndarray,
    c2: float,
    c3: float,
    alpha_dense: float
) -> Dict[str, Any]:
    """
    Purpose:
        Computes TERA system-level evaluation metrics and routing confusion metrics.
        
    Inputs:
        results: List of raw query outcome dictionaries from Labeled EvaluationRunner.
        labels: Numpy array of ground-truth binary accuracy labels.
        c2: Token cost of cheap model.
        c3: Token cost of dense model.
        alpha_dense: Domain baseline accuracy of dense model.
        
    Outputs:
        A dictionary containing cost, accuracy, calibration, and confusion stats.
        
    Time Complexity:
        O(N) where N is the number of query results.
        
    Memory Complexity:
        O(N) to store metric arrays.
    """
    n = len(results)
    if n == 0:
        return {}
        
    # Lists for calculation
    selected_routes = [r["selected_route"] for r in results]
    escalated_flags = [r["escalated"] for r in results]
    probs = np.array([r["calibrated_probability"] for r in results])
    latencies = np.array([r["latency_ms"] for r in results])
    
    # 1. Routing distribution
    cheap_count = selected_routes.count("cheap")
    dense_count = selected_routes.count("dense")
    cascade_count = selected_routes.count("cascade")
    
    cheap_pct = float(cheap_count / n) * 100.0
    dense_pct = float(dense_count / n) * 100.0
    cascade_pct = float(cascade_count / n) * 100.0
    
    # 2. Escalation Rate
    # Escalated only happens if selected route was cheap or cascade
    non_direct_dense = cheap_count + cascade_count
    escalations = escalated_flags.count(True)
    escalation_rate = float(escalations / non_direct_dense) * 100.0 if non_direct_dense > 0 else 0.0
    
    # 3. Cost & Latency
    costs = []
    accuracies = []
    
    # False decisions counters
    false_cheap_count = 0
    false_dense_count = 0
    
    for i, res in enumerate(results):
        route = res["selected_route"]
        escalated = res["escalated"]
        label = labels[i]
        
        # Cost assignment
        if route == "dense":
            costs.append(c3)
            # Direct dense accuracy is baseline alpha_dense
            accuracies.append(alpha_dense)
            
            # False Dense: Router chose dense, but cheap would have succeeded (label == 1)
            if label == 1:
                false_dense_count += 1
                
        else:
            # cheap or cascade
            if escalated:
                costs.append(c2 + c3)
                accuracies.append(alpha_dense)
            else:
                costs.append(c2)
                # Successful cheap run: accuracy is label (should be 1)
                accuracies.append(label)
                
            # False Cheap: Router chose cheap/cascade, but cheap failed (label == 0)
            if label == 0:
                false_cheap_count += 1
                
    avg_cost = float(np.mean(costs))
    avg_norm_cost = float(avg_cost / c3)
    avg_latency = float(np.mean(latencies))
    avg_acc = float(np.mean(accuracies))
    
    # 4. Calibration Stats
    ece = compute_ece(labels, probs)
    brier = compute_brier_score(labels, probs)
    
    return {
        "dataset_size": n,
        "routing_distribution_pct": {
            "cheap": cheap_pct,
            "dense": dense_pct,
            "cascade": cascade_pct
        },
        "escalation_rate_pct": escalation_rate,
        "false_decisions": {
            "false_cheap": false_cheap_count,
            "false_dense": false_dense_count
        },
        "accuracy": avg_acc,
        "average_cost": avg_cost,
        "average_normalized_cost": avg_norm_cost,
        "average_latency_ms": avg_latency,
        "expected_calibration_error": ece,
        "brier_score": brier
    }
