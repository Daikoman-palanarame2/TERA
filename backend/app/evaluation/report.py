import json
from typing import Dict, Any

"""
This module exports reports in Markdown and JSON formats comparing TERA's 
performance against baseline strategies.
"""

def generate_json_report(tera_metrics: Dict[str, Any], baselines: Dict[str, Any]) -> str:
    """
    Purpose:
        Produces a structured JSON report mapping TERA metrics alongside baselines.
        
    Inputs:
        tera_metrics: Dict of computed TERA results.
        baselines: Dict containing cheap, dense, and random baseline stats.
        
    Outputs:
        JSON formatted string.
    """
    report_data = {
        "tera": tera_metrics,
        "baselines": baselines
    }
    return json.dumps(report_data, indent=4)


def generate_markdown_report(tera_metrics: Dict[str, Any], baselines: Dict[str, Any]) -> str:
    """
    Purpose:
        Produces a readable Markdown report containing comparisons and cost savings.
        
    Inputs:
        tera_metrics: Dict of computed TERA results.
        baselines: Dict containing cheap, dense, and random baseline stats.
        
    Outputs:
        Markdown formatted string.
    """
    cheap_base = baselines.get("always_cheap", {})
    dense_base = baselines.get("always_dense", {})
    random_base = baselines.get("random_routing", {})
    
    # Cost savings calculation: TERA vs Always Dense
    dense_cost = dense_base.get("average_cost", 1.0)
    tera_cost = tera_metrics.get("average_cost", 1.0)
    cost_savings = (1.0 - (tera_cost / dense_cost)) * 100.0 if dense_cost > 0.0 else 0.0
    
    # Cost savings calculation: TERA vs Always Cheap (represented as multiplier or increase)
    cheap_cost = cheap_base.get("average_cost", 1.0)
    
    md = []
    md.append("# TERA (Token-Efficient Routing Agent) Evaluation Report\n")
    md.append("## Overview")
    md.append(f"This report evaluates the performance of TERA against three baseline routing strategies on a benchmark dataset of size **{tera_metrics.get('dataset_size', 0)}** prompts.\n")
    
    md.append("## Strategy Performance Comparison Table")
    md.append("| Routing Strategy | Blended Accuracy | Avg Token Cost | Avg Normalized Cost |")
    md.append("| :--- | :--- | :--- | :--- |")
    md.append(f"| **TERA (Calibrated Utility)** | **{tera_metrics.get('accuracy', 0.0):.4f}** | **{tera_cost:.2f}** | **{tera_metrics.get('average_normalized_cost', 0.0):.4f}** |")
    md.append(f"| Always Cheap model lane ($M_2$) | {cheap_base.get('accuracy', 0.0):.4f} | {cheap_cost:.2f} | {cheap_base.get('normalized_cost', 0.0):.4f} |")
    md.append(f"| Always Dense model lane ($M_3$) | {dense_base.get('accuracy', 0.0):.4f} | {dense_cost:.2f} | {dense_base.get('normalized_cost', 0.0):.4f} |")
    md.append(f"| Random Routing (50/50) | {random_base.get('accuracy', 0.0):.4f} | {random_base.get('average_cost', 0.0):.2f} | {random_base.get('normalized_cost', 0.0):.4f} |\n")
    
    md.append("## Key Insights")
    md.append(f"- **Cost Savings:** TERA achieved **{cost_savings:.2f}%** token cost savings compared to the Always Dense model baseline while maintaining a calibrated utility trade-off.")
    md.append(f"- **Blended Accuracy Score:** TERA achieved an average accuracy of **{tera_metrics.get('accuracy', 0.0):.4f}**.\n")
    
    md.append("## TERA Routing Diagnostics & Confusion Statistics")
    dist = tera_metrics.get("routing_distribution_pct", {})
    md.append("### Router Decisions Distribution")
    md.append(f"- **Direct Cheap Routes ($M_2$):** {dist.get('cheap', 0.0):.2f}%")
    md.append(f"- **Direct Dense Routes ($M_3$):** {dist.get('dense', 0.0):.2f}%")
    md.append(f"- **Cascade Routes ($M_2 \\rightarrow M_3$):** {dist.get('cascade', 0.0):.2f}%\n")
    
    md.append("### ROVL Verification Metrics")
    md.append(f"- **Automatic Escalation Rate:** {tera_metrics.get('escalation_rate_pct', 0.0):.2f}%\n")
    
    confusion = tera_metrics.get("false_decisions", {})
    md.append("### Routing Confusion Metrics")
    md.append(f"- **False Cheap Decisions:** {confusion.get('false_cheap', 0)}")
    md.append(f"  *(Router selected CHEAP/CASCADE but the cheap model output failed ROVL verification)*")
    md.append(f"- **False Dense Decisions:** {confusion.get('false_dense', 0)}")
    md.append(f"  *(Router selected DENSE directly but the cheap model would have passed verification)*\n")
    
    md.append("### Efficiency & Calibration")
    md.append(f"- **Average Routing + Model Latency:** {tera_metrics.get('average_latency_ms', 0.0):.2f} ms")
    md.append(f"- **Expected Calibration Error (ECE):** {tera_metrics.get('expected_calibration_error', 0.0):.4f}")
    md.append(f"- **Brier Score:** {tera_metrics.get('brier_score', 0.0):.4f}\n")
    
    return "\n".join(md)
