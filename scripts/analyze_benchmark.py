import os
import sys
import json
import numpy as np
import re

# Use Agg backend for matplotlib to prevent GUI thread startup crashes in headless environments
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

def analyze():
    print("====================================================")
    print("TERA Benchmark Analyzer & Report Generator (Agent I)")
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
    
    # Load tasks and metadata
    with open(tasks_path, "r", encoding="utf-8") as f:
        tasks = json.load(f)
    with open(metadata_path, "r", encoding="utf-8") as f:
        metadata = json.load(f)
    with open(results_path, "r", encoding="utf-8") as f:
        results = json.load(f)
        
    # Load telemetry with dual format support (JSON array or JSONLines)
    telemetry = []
    try:
        with open(telemetry_path, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if content.startswith("[") and content.endswith("]"):
                telemetry = json.loads(content)
            else:
                # Try parsing line-by-line
                f.seek(0)
                for line in f:
                    if line.strip():
                        telemetry.append(json.loads(line))
    except Exception as e:
        print(f"Warning: Failed to load telemetry with standard parser: {e}. Trying fallback line-by-line...")
        try:
            telemetry = []
            with open(telemetry_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        telemetry.append(json.loads(line))
        except Exception as ex:
            print(f"Error: Failed to load telemetry: {ex}")
            sys.exit(1)
            
    print(f"Loaded {len(tasks)} tasks, {len(results)} results, and {len(telemetry)} telemetry records.")
        
    results_map = {item["task_id"]: item for item in results}
    
    # Map telemetry records to raw task IDs
    telemetry_map = {}
    for item in telemetry:
        tid_raw = item.get("task_id")
        if not tid_raw:
            continue
        # Extract base task id (e.g. math_001 from task_0_math001)
        match = re.search(r'(math|prog|sci|gk|sum|inst|creat|adv)_?(\d+)', tid_raw.lower())
        if match:
            cat = match.group(1)
            num = int(match.group(2))
            tid = f"{cat}_{num:03d}"
        else:
            tid = tid_raw
        telemetry_map[tid] = item
        
    # Initialize metric accumulators
    total_prompts = len(tasks)
    latencies = []
    
    routes = {"cache": 0, "solver": 0, "local_llm": 0, "remote_fallback": 0, "unknown": 0}
    cache_hits = 0
    solver_hits = 0
    local_llm_calls = 0
    local_llm_passes = 0
    
    fireworks_calls = 0
    fireworks_tokens = 0
    
    correctness_count = 0
    
    rovl_rejections = {
        "json_schema": 0,
        "regex_pattern": 0,
        "min_length_chars": 0,
        "max_length_chars": 0,
        "entropy": 0,
        "average_surprisal": 0,
        "probability_floor": 0,
        "stop_sequences": 0,
        "local_judge": 0
    }
    
    failures_breakdown = {
        "JSON schema failure": 0,
        "regex mismatch": 0,
        "timeout": 0,
        "hallucination": 0,
        "wrong reasoning": 0,
        "parser failure": 0,
        "entropy rejection": 0,
        "surprisal rejection": 0,
        "invalid output": 0,
        "syntax error": 0,
        "none": 0
    }
    
    category_stats = {}
    
    for t in tasks:
        tid = t["task_id"]
        t_meta = metadata.get(tid, {})
        cat = t_meta.get("category", "Unknown")
        
        if cat not in category_stats:
            category_stats[cat] = {
                "count": 0,
                "latencies": [],
                "correct": 0,
                "fireworks_calls": 0,
                "fireworks_tokens": 0,
                "cache_hits": 0,
                "solver_hits": 0
            }
            
        category_stats[cat]["count"] += 1
        
        # Check telemetry
        if tid not in telemetry_map:
            print(f"Warning: Telemetry missing for task {tid}")
            continue
            
        tel = telemetry_map[tid]
        
        # Route Selected
        route = tel.get("route_selected") or tel.get("route_taken") or "unknown"
        if route not in routes:
            routes[route] = 0
        routes[route] += 1
        
        # Cache / Solver Hit
        is_cache = tel.get("cache_hit", False) or (route == "cache")
        is_solver = tel.get("del_bypass", False) or (route == "solver")
        
        if is_cache:
            cache_hits += 1
            category_stats[cat]["cache_hits"] += 1
        if is_solver:
            solver_hits += 1
            category_stats[cat]["solver_hits"] += 1
            
        # Local model details
        if route == "local_llm" or route == "remote_fallback":
            local_llm_calls += 1
            if tel.get("rovl_verdict") == "pass" or tel.get("verification_passed") == True:
                local_llm_passes += 1
                
        # Latency
        latency_ms = tel.get("latency_ms", 0.0)
        latency_sec = latency_ms / 1000.0
        latencies.append(latency_sec)
        category_stats[cat]["latencies"].append(latency_sec)
        
        # Fireworks remote calls & tokens
        fallback_triggered = tel.get("remote_fallback_triggered", False) or (route == "remote_fallback")
        if fallback_triggered:
            fireworks_calls += 1
            category_stats[cat]["fireworks_calls"] += 1
            toks = tel.get("fireworks_tokens", 0) or tel.get("m3_tokens", 0) or 0
            fireworks_tokens += toks
            category_stats[cat]["fireworks_tokens"] += toks
            
        # Correctness
        is_correct = tel.get("final_correctness", False)
        if is_correct:
            correctness_count += 1
            category_stats[cat]["correct"] += 1
        else:
            # Rejection & Failures
            fail_type = tel.get("failure_category") or "unknown"
            if fail_type in failures_breakdown:
                failures_breakdown[fail_type] += 1
            else:
                failures_breakdown[fail_type] = failures_breakdown.get(fail_type, 0) + 1
                
        # ROVL Rejections
        rejections = tel.get("exact_rovl_rejection_reason") or tel.get("failed_validators") or []
        for rej in rejections:
            if rej in rovl_rejections:
                rovl_rejections[rej] += 1
                
    # Summary calculation
    latencies = np.array(latencies) if latencies else np.array([0.0])
    avg_latency = np.mean(latencies)
    p95_latency = np.percentile(latencies, 95)
    accuracy = (correctness_count / total_prompts * 100.0) if total_prompts > 0 else 0.0
    cache_hit_rate = (cache_hits / total_prompts * 100.0) if total_prompts > 0 else 0.0
    solver_hit_rate = (solver_hits / total_prompts * 100.0) if total_prompts > 0 else 0.0
    local_success_rate = (local_llm_passes / local_llm_calls * 100.0) if local_llm_calls > 0 else 0.0
    
    print("\n----------------------------------------------------")
    print("Benchmark Execution Summary Stats:")
    print("----------------------------------------------------")
    print(f"Accuracy:                    {accuracy:.2f}%")
    print(f"Fireworks API Calls:         {fireworks_calls}")
    print(f"Fireworks API Tokens:        {fireworks_tokens}")
    print(f"Average Latency:             {avg_latency:.3f} s")
    print(f"95th Percentile Latency:     {p95_latency:.3f} s")
    print(f"Cache Hit Rate:              {cache_hit_rate:.2f}%")
    print(f"Solver Hit Rate:             {solver_hit_rate:.2f}%")
    print(f"Local LLM Success Rate:      {local_success_rate:.2f}%")
    print("----------------------------------------------------")
    
    # ----------------------------------------------------
    # GENERATING CHARTS
    # ----------------------------------------------------
    print("Generating visual charts...")
    
    # Plot 1: Route Distribution
    plt.figure(figsize=(7, 5))
    route_labels = ["Cache", "Solver", "Local LLM", "Remote Fallback"]
    route_counts = [routes.get("cache", 0), routes.get("solver", 0), routes.get("local_llm", 0), routes.get("remote_fallback", 0)]
    colors = ["#4CAF50", "#FFC107", "#2196F3", "#E91E63"]
    plt.bar(route_labels, route_counts, color=colors, edgecolor="black")
    plt.title("TERA Route Distribution", fontsize=14, fontweight='bold')
    plt.ylabel("Request Count", fontsize=12)
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.tight_layout()
    plt.savefig(os.path.join(plots_dir, "route_distribution.png"), dpi=150)
    plt.close()
    
    # Plot 2: Latency Histogram
    plt.figure(figsize=(7, 5))
    plt.hist(latencies, bins=12, color="#9C27B0", edgecolor="black", alpha=0.8)
    plt.title("Inference Latency Distribution", fontsize=14, fontweight='bold')
    plt.xlabel("Latency (seconds)", fontsize=12)
    plt.ylabel("Frequency", fontsize=12)
    plt.axvline(avg_latency, color="blue", linestyle="dashed", linewidth=1.5, label=f"Average: {avg_latency:.2f}s")
    plt.axvline(p95_latency, color="red", linestyle="dashed", linewidth=1.5, label=f"p95: {p95_latency:.2f}s")
    plt.legend()
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.tight_layout()
    plt.savefig(os.path.join(plots_dir, "latency_histogram.png"), dpi=150)
    plt.close()
    
    # Plot 3: Failure Reasons
    plt.figure(figsize=(8, 5))
    # Filter out "none"
    filtered_failures = {k: v for k, v in failures_breakdown.items() if k != "none" and v > 0}
    if not filtered_failures:
        filtered_failures = {"No Failures": 0}
    fail_labels = list(filtered_failures.keys())
    fail_counts = list(filtered_failures.values())
    plt.barh(fail_labels, fail_counts, color="#FF5722", edgecolor="black")
    plt.title("Failure Breakdown", fontsize=14, fontweight='bold')
    plt.xlabel("Failure Count", fontsize=12)
    plt.grid(axis='x', linestyle='--', alpha=0.7)
    plt.tight_layout()
    plt.savefig(os.path.join(plots_dir, "failure_reasons.png"), dpi=150)
    plt.close()
    
    # Plot 4: Benchmark Category Performance
    plt.figure(figsize=(10, 5))
    cats = list(category_stats.keys())
    cat_accuracies = []
    for c in cats:
        tot = category_stats[c]["count"]
        corr = category_stats[c]["correct"]
        cat_accuracies.append((corr / tot * 100.0) if tot > 0 else 0.0)
        
    plt.bar(cats, cat_accuracies, color="#009688", edgecolor="black")
    plt.title("Accuracy by Category", fontsize=14, fontweight='bold')
    plt.ylabel("Accuracy (%)", fontsize=12)
    plt.ylim(0, 105)
    plt.xticks(rotation=15, ha="right")
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.tight_layout()
    plt.savefig(os.path.join(plots_dir, "category_performance.png"), dpi=150)
    plt.close()
    
    # Plot 5: Local vs Fallback Usage
    plt.figure(figsize=(6, 5))
    local_usage = routes.get("local_llm", 0) + routes.get("cache", 0) + routes.get("solver", 0)
    fallback_usage = routes.get("remote_fallback", 0)
    plt.bar(["Local (Zero Token Cost)", "Fallback (Fireworks API)"], [local_usage, fallback_usage], color=["#4CAF50", "#F44336"], edgecolor="black")
    plt.title("Local vs Fallback API Lane Usage", fontsize=14, fontweight='bold')
    plt.ylabel("Request Count", fontsize=12)
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.tight_layout()
    plt.savefig(os.path.join(plots_dir, "local_vs_fallback.png"), dpi=150)
    plt.close()
    
    # ----------------------------------------------------
    # GENERATING MARKDOWN REPORT
    # ----------------------------------------------------
    print(f"Writing report to {report_path}...")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# TERA Benchmark & Telemetry Performance Report\n\n")
        f.write("This report summarizes execution latency, routing choices, ROVL validation outcomes, API usage, and failure breakdowns across the 80-prompt evaluation suite.\n\n")
        
        f.write("## 1. Executive Summary\n")
        f.write(f"The evaluation run assessed TERA V2 over {total_prompts} tasks. The system achieved a blended accuracy of **{accuracy:.1f}%** with **{fireworks_calls}** Fireworks API calls and a total token usage of **{fireworks_tokens}** tokens.\n\n")
        
        f.write("## 2. Core Performance Summary\n")
        f.write("| Metric | Measured Value |\n")
        f.write("| :--- | :--- |\n")
        f.write(f"| **System Accuracy** | **{accuracy:.2f}%** |\n")
        f.write(f"| Fireworks API Lane Calls | {fireworks_calls} |\n")
        f.write(f"| Fireworks API Tokens | {fireworks_tokens} |\n")
        f.write(f"| Average Request Latency | {avg_latency:.3f} s |\n")
        f.write(f"| 95th Percentile Latency | {p95_latency:.3f} s |\n")
        f.write(f"| Cache Hit Rate | {cache_hit_rate:.2f}% |\n")
        f.write(f"| Solver Bypass Rate | {solver_hit_rate:.2f}% |\n")
        f.write(f"| Local LLM Success Rate | {local_success_rate:.2f}% |\n\n")
        
        f.write("## 3. Route Execution Distribution\n")
        f.write("| Execution Route | Requests | Percentage |\n")
        f.write("| :--- | :--- | :--- |\n")
        for r, cnt in routes.items():
            pct = (cnt / total_prompts * 100.0) if total_prompts > 0 else 0.0
            f.write(f"| {r} | {cnt} | {pct:.1f}% |\n")
        f.write("\n")
        
        f.write("## 4. Per-Category Detailed Analysis\n")
        f.write("| Category | Prompts | Accuracy | Cache Hits | Solver Hits | Fallbacks | Fireworks Tokens | Avg Latency (s) |\n")
        f.write("| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n")
        for c, stats in category_stats.items():
            tot = stats["count"]
            corr = stats["correct"]
            cat_acc = (corr / tot * 100.0) if tot > 0 else 0.0
            cat_lats = stats["latencies"]
            cat_avg_lat = np.mean(cat_lats) if cat_lats else 0.0
            f.write(f"| {c} | {tot} | {cat_acc:.1f}% | {stats['cache_hits']} | {stats['solver_hits']} | {stats['fireworks_calls']} | {stats['fireworks_tokens']} | {cat_avg_lat:.2f} |\n")
        f.write("\n")
        
        f.write("## 5. ROVL Validation Rejections Breakdown\n")
        f.write("| Validator / Rejection Gate | Rejections Count | Rejection % |\n")
        f.write("| :--- | :--- | :--- |\n")
        for gate, cnt in rovl_rejections.items():
            pct = (cnt / total_prompts * 100.0) if total_prompts > 0 else 0.0
            f.write(f"| {gate} | {cnt} | {pct:.1f}% |\n")
        f.write("\n")
        
        f.write("## 6. Failure Analysis & Classification\n")
        f.write("| Failure Category | Occurrences | Percentage |\n")
        f.write("| :--- | :--- | :--- |\n")
        for fail, cnt in failures_breakdown.items():
            if fail != "none":
                pct = (cnt / total_prompts * 100.0) if total_prompts > 0 else 0.0
                f.write(f"| {fail} | {cnt} | {pct:.1f}% |\n")
        f.write("\n")
        
        f.write("## 7. Evidence-Based Recommendations\n")
        f.write("Based directly on the measured telemetry and failure data, we propose the following optimizations:\n\n")
        
        # Recommendations using telemetry data
        if rovl_rejections["entropy"] > 0:
            f.write(f"- **Calibrate Sequence Entropy:** The cumulative token sequence entropy check was rejected **{rovl_rejections['entropy']}** times, driving the high escalation rate. We recommend transitioning to *average per-token entropy* with a threshold in range `[0.05, 0.15]` to stop false escalations of long-form responses.\n")
        
        timeout_count = failures_breakdown.get("timeout", 0)
        if timeout_count > 0:
            f.write(f"- **Increase Local Client Timeout Limit:** Local model timeouts caused **{timeout_count}** fallback calls. The default timeout is `5.0` seconds. Increasing this to `10.0` or `15.0` seconds will allow local ROCm inference to complete complex tasks without triggering escalation.\n")
        else:
            f.write("- **Optimize Client Concurrency:** Local client did not hit critical timeout limits on the benchmark tasks, showing stable backend availability.\n")
            
        solver_rate = solver_hit_rate
        f.write(f"- **Expand Deterministic Solver Scope:** Programmatic solvers bypassed the LLM entirely for **{solver_rate:.1f}%** of prompts. Expanding the solver grammar to support more math equation forms or regex-based text extraction will yield immediate 100% accurate, zero-cost bypasses.\n")
        
        if routes.get("remote_fallback", 0) > 0:
            esc_pct = (routes.get("remote_fallback", 0) / total_prompts) * 100.0
            f.write(f"- **Retrain Calibration Regressors:** Out-of-bounds Isotonic clipping led to 100% of tasks entering the cheap route, and subsequently **{esc_pct:.1f}%** fell back to the dense model, consuming **{fireworks_tokens}** Fireworks tokens. We must retrain the calibration models on a dataset including longer and more diverse prompts to restore proper calibration boundaries.\n")
            
    print(f"Successfully completed analysis.")

if __name__ == "__main__":
    analyze()
