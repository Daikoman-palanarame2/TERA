import os
import sys
import json
import numpy as np

# Use Agg backend for matplotlib to prevent GUI thread startup crashes in headless environments
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

def analyze():
    print("====================================================")
    print("TERA Benchmark Analyzer & Report Generator")
    print("====================================================")
    
    tasks_path = "evaluation/benchmark_tasks.json"
    metadata_path = "evaluation/benchmark_metadata.json"
    results_path = "evaluation/results.json"
    telemetry_path = "evaluation/telemetry.json"
    plots_dir = "evaluation/plots"
    report_path = "evaluation/benchmark_report.md"
    
    if not (os.path.exists(tasks_path) and os.path.exists(metadata_path) and os.path.exists(results_path) and os.path.exists(telemetry_path)):
        print("Error: Missing required benchmark input or output files. Run run_benchmark.py first.")
        sys.exit(1)
        
    os.makedirs(plots_dir, exist_ok=True)
    
    # Load data
    with open(tasks_path, "r", encoding="utf-8") as f:
        tasks = json.load(f)
    with open(metadata_path, "r", encoding="utf-8") as f:
        metadata = json.load(f)
    with open(results_path, "r", encoding="utf-8") as f:
        results = json.load(f)
    with open(telemetry_path, "r", encoding="utf-8") as f:
        telemetry = json.load(f)
        
    results_map = {item["task_id"]: item for item in results}
    telemetry_map = {item["task_id"]: item for item in telemetry}
    
    # Overall statistics
    total_prompts = len(tasks)
    latencies = []
    cheap_count = 0
    dense_count = 0
    escalation_count = 0
    
    total_prompt_tokens = 0
    total_completion_tokens = 0
    
    # Cost rates (per 1M tokens)
    # Cheap: deepseek-v4-pro ($0.15/1M input, $0.60/1M output)
    # Dense: gpt-oss-120b ($1.50/1M input, $5.00/1M output)
    total_cost = 0.0
    router_probs = []
    
    escalation_reasons = {}
    category_stats = {}
    
    # Failure metrics
    failures = {
        "empty_answers": [],
        "missing_task_ids": [],
        "missing_telemetry": [],
        "duplicate_answers": {},
        "schema_violations": [],
        "malformed_outputs": []
    }
    
    answer_occurrences = {}
    
    for t in tasks:
        tid = t["task_id"]
        t_meta = metadata.get(tid, {})
        cat = t_meta.get("category", "Unknown")
        
        if cat not in category_stats:
            category_stats[cat] = {
                "count": 0,
                "latencies": [],
                "escalations": 0,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "cost": 0.0
            }
            
        category_stats[cat]["count"] += 1
        
        # Check result
        if tid not in results_map:
            failures["missing_task_ids"].append(tid)
            continue
            
        res = results_map[tid]
        ans = res.get("answer", "")
        
        # 1. Empty Answer Check
        if not ans or not ans.strip():
            failures["empty_answers"].append(tid)
            
        # 2. Duplicate Answer Check
        if ans:
            if ans not in answer_occurrences:
                answer_occurrences[ans] = []
            answer_occurrences[ans].append(tid)
            
        # Check telemetry
        if tid not in telemetry_map:
            failures["missing_telemetry"].append(tid)
            continue
            
        tel = telemetry_map[tid]
        route = tel.get("selected_route")
        escalated = tel.get("escalated", False)
        
        if route == "cheap":
            cheap_count += 1
        elif route == "dense":
            dense_count += 1
            
        if escalated:
            escalation_count += 1
            category_stats[cat]["escalations"] += 1
            
        meta = tel.get("metadata", {})
        latency = meta.get("inference_time_ms", 0.0) / 1000.0
        latencies.append(latency)
        category_stats[cat]["latencies"].append(latency)
        
        prob = meta.get("router_probability")
        if prob is not None:
            router_probs.append(prob)
            
        esc_reason = meta.get("escalation_reason")
        if escalated and esc_reason:
            escalation_reasons[esc_reason] = escalation_reasons.get(esc_reason, 0) + 1
            
        model_meta = meta.get("model_metadata", {})
        usage = model_meta.get("usage", {})
        
        p_tok = usage.get("prompt_tokens", 0)
        c_tok = usage.get("completion_tokens", 0)
        
        total_prompt_tokens += p_tok
        total_completion_tokens += c_tok
        
        category_stats[cat]["prompt_tokens"] += p_tok
        category_stats[cat]["completion_tokens"] += c_tok
        
        # Schema violations or error detection
        if "error" in tel or "error" in meta or "error" in model_meta or route == "error":
            failures["schema_violations"].append(tid)
            
        model_name = model_meta.get("model", "")
        # Calculate cost based on actual model queried
        task_cost = 0.0
        if "gpt-oss-120b" in model_name or "gpt" in model_name or "dense" in model_name:
            task_cost = (p_tok * 1.50 / 1e6) + (c_tok * 5.00 / 1e6)
        else:
            task_cost = (p_tok * 0.15 / 1e6) + (c_tok * 0.60 / 1e6)
            
        total_cost += task_cost
        category_stats[cat]["cost"] += task_cost

    # Process duplicate occurrences
    for ans, tids in answer_occurrences.items():
        if len(tids) > 1:
            failures["duplicate_answers"][ans] = tids

    # Latency calculations
    latencies = np.array(latencies) if latencies else np.array([0.0])
    avg_latency = np.mean(latencies)
    med_latency = np.median(latencies)
    min_latency = np.min(latencies)
    max_latency = np.max(latencies)
    p95_latency = np.percentile(latencies, 95)
    
    # General metrics
    cheap_pct = (cheap_count / total_prompts * 100.0) if total_prompts > 0 else 0.0
    dense_pct = (dense_count / total_prompts * 100.0) if total_prompts > 0 else 0.0
    esc_rate = (escalation_count / total_prompts * 100.0) if total_prompts > 0 else 0.0
    
    total_tokens = total_prompt_tokens + total_completion_tokens
    avg_prompt_tokens = total_prompt_tokens / total_prompts if total_prompts > 0 else 0
    avg_completion_tokens = total_completion_tokens / total_prompts if total_prompts > 0 else 0
    avg_tokens = total_tokens / total_prompts if total_prompts > 0 else 0
    avg_cost = total_cost / total_prompts if total_prompts > 0 else 0.0
    avg_router_prob = np.mean(router_probs) if router_probs else 0.0

    print("Generating Visualization Plots...")
    
    # Plot 1: Route Distribution
    plt.figure(figsize=(6, 5))
    plt.bar(["Cheap Route", "Dense Route"], [cheap_count, dense_count], color=["#4CAF50", "#2196F3"])
    plt.title("TERA Routing Distribution")
    plt.ylabel("Prompts count")
    plt.tight_layout()
    plt.savefig(os.path.join(plots_dir, "route_distribution.png"))
    plt.close()
    
    # Plot 2: Escalation Distribution
    plt.figure(figsize=(6, 5))
    plt.bar(["Accepted Cheap", "Escalated to Dense"], [total_prompts - escalation_count, escalation_count], color=["#009688", "#FF5722"])
    plt.title("TERA Completion Escalations")
    plt.ylabel("Prompts count")
    plt.tight_layout()
    plt.savefig(os.path.join(plots_dir, "escalation_distribution.png"))
    plt.close()
    
    # Plot 3: Latency Histogram
    plt.figure(figsize=(7, 5))
    plt.hist(latencies, bins=10, color="#E91E63", edgecolor="black")
    plt.title("TERA Inference Latency Distribution")
    plt.xlabel("Latency (seconds)")
    plt.ylabel("Frequency")
    plt.axvline(avg_latency, color="blue", linestyle="dashed", linewidth=1.5, label=f"Average: {avg_latency:.2f}s")
    plt.axvline(med_latency, color="green", linestyle="dashed", linewidth=1.5, label=f"Median: {med_latency:.2f}s")
    plt.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(plots_dir, "latency_histogram.png"))
    plt.close()
    
    # Plot 4: Tokens per Category
    plt.figure(figsize=(10, 6))
    categories = list(category_stats.keys())
    tokens = [category_stats[c]["prompt_tokens"] + category_stats[c]["completion_tokens"] for c in categories]
    plt.barh(categories, tokens, color="#9C27B0")
    plt.title("Total Token Consumption per Category")
    plt.xlabel("Tokens count")
    plt.tight_layout()
    plt.savefig(os.path.join(plots_dir, "tokens_per_category.png"))
    plt.close()
    
    # Plot 5: Cost per Category
    plt.figure(figsize=(10, 6))
    costs = [category_stats[c]["cost"] for c in categories]
    plt.barh(categories, costs, color="#FF9800")
    plt.title("Estimated Fireworks Cost per Category")
    plt.xlabel("Cost (USD)")
    plt.tight_layout()
    plt.savefig(os.path.join(plots_dir, "cost_per_category.png"))
    plt.close()

    # Generate Recommendations dynamically
    recommendations = []
    if esc_rate > 35.0:
        recommendations.append(f"High escalation rate detected ({esc_rate:.1f}%). Programming or instruction-following constraints are likely triggering frequent verification failures. Consider checking ROVL thresholds.")
    else:
        recommendations.append(f"Excellent cheap routing utilization! Only {esc_rate:.1f}% of cheap route selections required dense model escalation.")
        
    if dense_pct > 60.0:
        recommendations.append("Dense model lane is heavily utilized. The router predicts high complexity or low accuracy probabilities across most categories. Consider adjusting the lambda frugality coefficient if lower costs are desired.")
    else:
        recommendations.append("The router is efficiently utilizing the cheap model lane across diverse tasks, maximizing token efficiency.")
        
    if avg_latency > 3.0:
        recommendations.append(f"Average latency is relatively high ({avg_latency:.2f}s). Latency spikes may be caused by concurrent network requests or long-context summarizations.")
        
    if len(failures["empty_answers"]) > 0:
        recommendations.append(f"Warning: {len(failures['empty_answers'])} tasks yielded empty responses. Check if the backend client is receiving correct JSON completions.")
    else:
        recommendations.append("Zero empty responses detected. API adapters are returning complete completions.")

    # Write Markdown Report
    print("Writing Benchmark Markdown Report...")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# TERA Offline Benchmark Performance Report\n\n")
        f.write("This report provides a detailed performance summary of TERA on the 80-prompt evaluation dataset.\n\n")
        
        f.write("## 1. Executive Summary\n")
        f.write("TERA was benchmarked over 80 realistic prompts spanning 8 distinct categories. The evaluation assesses latency bounds, routing decisions, calibration, token economies, and cost savings on the Fireworks API.\n\n")
        
        f.write("## 2. Overall Statistics\n")
        f.write("| Metric | Value |\n")
        f.write("| :--- | :--- |\n")
        f.write(f"| Total Prompts | {total_prompts} |\n")
        f.write(f"| Average Latency | {avg_latency:.3f} s |\n")
        f.write(f"| Median Latency | {med_latency:.3f} s |\n")
        f.write(f"| Minimum Latency | {min_latency:.3f} s |\n")
        f.write(f"| Maximum Latency | {max_latency:.3f} s |\n")
        f.write(f"| 95th Percentile Latency | {p95_latency:.3f} s |\n")
        f.write(f"| Average Router Probability | {avg_router_prob:.4f} |\n")
        f.write(f"| Estimated Total Cost | ${total_cost:.5f} |\n")
        f.write(f"| Average Cost per Prompt | ${avg_cost:.5f} |\n\n")
        
        f.write("## 3. Routing Analysis\n")
        f.write("| Route Selection | Count | Percentage |\n")
        f.write("| :--- | :--- | :--- |\n")
        f.write(f"| Cheap Route | {cheap_count} | {cheap_pct:.1f}% |\n")
        f.write(f"| Dense Route | {dense_count} | {dense_pct:.1f}% |\n")
        f.write(f"| Escalated to Dense | {escalation_count} | {esc_rate:.1f}% |\n\n")
        
        if escalation_reasons:
            f.write("### Escalation Reasons Breakdown\n")
            f.write("| Reason | Count |\n")
            f.write("| :--- | :--- |\n")
            for r, cnt in escalation_reasons.items():
                f.write(f"| {r} | {cnt} |\n")
            f.write("\n")
            
        f.write("## 4. Token Consumption Statistics\n")
        f.write("| Token Metric | Count |\n")
        f.write("| :--- | :--- |\n")
        f.write(f"| Total Prompt Tokens | {total_prompt_tokens} |\n")
        f.write(f"| Total Completion Tokens | {total_completion_tokens} |\n")
        f.write(f"| Total Tokens | {total_tokens} |\n")
        f.write(f"| Average Prompt Tokens | {avg_prompt_tokens:.1f} |\n")
        f.write(f"| Average Completion Tokens | {avg_completion_tokens:.1f} |\n")
        f.write(f"| Average Tokens per Prompt | {avg_tokens:.1f} |\n\n")
        
        f.write("## 5. Per-Category Results\n")
        f.write("| Category | Prompts | Avg Latency (s) | Escalation Rate | Avg Tokens | Total Cost |\n")
        f.write("| :--- | :--- | :--- | :--- | :--- | :--- |\n")
        for cat, stat in category_stats.items():
            cat_lats = stat["latencies"]
            cat_avg_lat = np.mean(cat_lats) if cat_lats else 0.0
            cat_esc_rate = (stat["escalations"] / stat["count"] * 100.0) if stat["count"] > 0 else 0.0
            cat_avg_tok = (stat["prompt_tokens"] + stat["completion_tokens"]) / stat["count"] if stat["count"] > 0 else 0
            f.write(f"| {cat} | {stat['count']} | {cat_avg_lat:.3f} | {cat_esc_rate:.1f}% | {cat_avg_tok:.1f} | ${stat['cost']:.5f} |\n")
        f.write("\n")
        
        f.write("## 6. Failure Analysis\n")
        f.write(f"- **Empty Responses:** {len(failures['empty_answers'])}\n")
        if failures["empty_answers"]:
            f.write(f"  - Task IDs: {', '.join(failures['empty_answers'])}\n")
            
        f.write(f"- **Missing Task IDs:** {len(failures['missing_task_ids'])}\n")
        if failures["missing_task_ids"]:
            f.write(f"  - Task IDs: {', '.join(failures['missing_task_ids'])}\n")
            
        f.write(f"- **Missing Telemetry logs:** {len(failures['missing_telemetry'])}\n")
        if failures["missing_telemetry"]:
            f.write(f"  - Task IDs: {', '.join(failures['missing_telemetry'])}\n")
            
        f.write(f"- **Schema/Validation Failures:** {len(failures['schema_violations'])}\n")
        if failures["schema_violations"]:
            f.write(f"  - Task IDs: {', '.join(failures['schema_violations'])}\n")
            
        dup_count = sum(len(v) for v in failures["duplicate_answers"].values())
        f.write(f"- **Duplicate Answers:** {dup_count} (indicates repetitive outputs or model loops)\n\n")
        
        f.write("## 7. Recommendations\n")
        for rec in recommendations:
            f.write(f"- {rec}\n")
        f.write("\n")
        
    print(f"Successfully generated report at {report_path} and plots in {plots_dir}.")

if __name__ == "__main__":
    analyze()
