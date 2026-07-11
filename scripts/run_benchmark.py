import os
import sys
import json
import time
import subprocess

def run():
    print("====================================================")
    print("TERA Offline Benchmark Runner")
    print("====================================================")
    
    input_path = "evaluation/benchmark_tasks.json"
    output_path = "evaluation/results.json"
    telemetry_path = "evaluation/telemetry.json"
    
    if not os.path.exists(input_path):
        print(f"Error: Benchmark tasks not found at {input_path}")
        sys.exit(1)
        
    script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../backend/app/run_batch.py"))
    
    cmd = [
        sys.executable,
        script_path,
        "--input", input_path,
        "--output", output_path
    ]
    
    # We check if a live FIREWORKS_API_KEY is available; if not, we fallback to mock mode for dry-runs
    if not os.environ.get("FIREWORKS_API_KEY") and not os.path.exists(".env"):
        print("Notice: No FIREWORKS_API_KEY found in environment or .env. Running in --mock mode.")
        cmd.append("--mock")
        
    t0 = time.perf_counter()
    result = subprocess.run(cmd, capture_output=False)
    elapsed = time.perf_counter() - t0
    
    if result.returncode != 0:
        print(f"Error: Benchmark run failed with exit code {result.returncode}", file=sys.stderr)
        sys.exit(result.returncode)
        
    print("\n----------------------------------------------------")
    print("Run Completed Successfully. Extracting statistics...")
    print("----------------------------------------------------")
    
    if not os.path.exists(telemetry_path):
        print(f"Warning: Telemetry file {telemetry_path} not found. Basic stats only.")
        print(f"Total prompts: {len(json.load(open(input_path)))}")
        print(f"Elapsed time: {elapsed:.2f} seconds")
        return
        
    with open(telemetry_path, "r", encoding="utf-8") as f:
        telemetry_data = json.load(f)
        
    total_prompts = len(telemetry_data)
    cheap_count = 0
    dense_count = 0
    escalation_count = 0
    
    total_prompt_tokens = 0
    total_completion_tokens = 0
    total_latency_ms = 0.0
    
    # Pricing rates (per 1M tokens)
    # Cheap: deepseek-v4-pro ($0.15/1M input, $0.60/1M output)
    # Dense: gpt-oss-120b ($1.50/1M input, $5.00/1M output)
    estimated_cost = 0.0
    
    for item in telemetry_data:
        route = item.get("selected_route")
        escalated = item.get("escalated", False)
        
        if route == "cheap":
            cheap_count += 1
        elif route == "dense":
            dense_count += 1
            
        if escalated:
            escalation_count += 1
            
        meta = item.get("metadata", {})
        total_latency_ms += meta.get("inference_time_ms", 0.0)
        
        model_meta = meta.get("model_metadata", {})
        usage = model_meta.get("usage", {})
        
        p_tok = usage.get("prompt_tokens", 0)
        c_tok = usage.get("completion_tokens", 0)
        
        total_prompt_tokens += p_tok
        total_completion_tokens += c_tok
        
        model_name = model_meta.get("model", "")
        # Calculate cost based on actual model queried
        if "gpt-oss-120b" in model_name or "gpt" in model_name or "dense" in model_name:
            estimated_cost += (p_tok * 1.50 / 1e6) + (c_tok * 5.00 / 1e6)
        else:
            estimated_cost += (p_tok * 0.15 / 1e6) + (c_tok * 0.60 / 1e6)
            
    avg_latency = (total_latency_ms / 1000.0) / total_prompts if total_prompts > 0 else 0.0
    avg_prompt_tokens = total_prompt_tokens / total_prompts if total_prompts > 0 else 0
    avg_completion_tokens = total_completion_tokens / total_prompts if total_prompts > 0 else 0
    
    print(f"Total prompts:            {total_prompts}")
    print(f"Elapsed time:             {elapsed:.2f} seconds")
    print(f"Average latency:          {avg_latency:.2f} seconds")
    print(f"Cheap routes selected:    {cheap_count}")
    print(f"Dense routes selected:    {dense_count}")
    print(f"Escalation count:         {escalation_count}")
    print(f"Average prompt tokens:    {avg_prompt_tokens:.1f}")
    print(f"Average completion tokens:{avg_completion_tokens:.1f}")
    print(f"Estimated Fireworks cost: ${estimated_cost:.5f}")
    print("====================================================")

if __name__ == "__main__":
    run()
