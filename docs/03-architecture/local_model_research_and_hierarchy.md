# TERA Local Model Research & Hierarchy Specification

**Author:** AI Architect & Deterministic Intelligence Engineer, TERA Core Team  
**Status:** PROPOSED  
**Version:** 1.0  
**Inference Focus:** High-performance, cost-effective local model deployment

---

## 1. Executive Summary

To build a competitive, token-efficient, and reliable routing engine for TERA, we must identify the strongest open-weight models that can be hosted locally. This document provides a comprehensive research sweep of the industry's leading open-weight model families (as of mid-2026), evaluates their capability matrices across core tasks (coding, math, reasoning, structure), and details their system performance metrics (VRAM, latency, quantization, hardware support).

Finally, we propose the optimal **TERA Model Hierarchy** (Tiny, Small, Medium, Large, Judge, Router, and Verifier) designed to maximize accuracy while minimizing hosting overhead and routing latency.

---

## 2. Model Family Deep Dive

---

### 2.1 Qwen Series (Qwen 3 / Qwen 2.5 / Coder / Math)

Alibaba’s Qwen models represent the gold standard for dense open-weight performance in code, math, and logical synthesis.

*   **Accuracy:** Outstanding. Outperforms similarly sized models across MMLU, GPQA, and general knowledge benchmarks.
*   **Instruction Following:** High alignment. Excels in complex multi-turn prompts and system instructions.
*   **Math:** SOTA for open weights. Qwen2.5-Math-72B and newer Qwen3-Math variants dominate GSM8K (95%+) and MATH (80%+).
*   **Coding:** Premier coding family. Qwen2.5-Coder-32B and 72B match or beat proprietary models on HumanEval (90%+) and LiveCodeBench.
*   **Summarization:** Strong text compression, supporting dense summaries with high fact retention.
*   **Classification:** Highly accurate; fine-grained label mapping.
*   **NER:** Excellent token extraction and JSON formatting out of the box.
*   **Reasoning:** Hybrid "Thinking" modes in Qwen3 allow dynamic switching to deep reinforcement-learned reasoning chains.
*   **Latency:** Highly optimized. Dense architectures support high throughput; MoE variants (e.g. Qwen3-30B) activate few parameters, dropping latency to ~15ms first-token.
*   **VRAM:**
    *   *0.6B - 3B:* 1.5 GB to 7 GB.
    *   *7B - 14B:* 15 GB to 30 GB.
    *   *32B - 72B:* 65 GB to 145 GB (Unquantized).
    *   *GGUF/AWQ Quantized:* 32B (Q4) requires ~20 GB VRAM; 72B (Q4) requires ~45 GB VRAM.
*   **Quantization Support:** Native FP8, INT4/INT8, AWQ, GPTQ, and GGUF.
*   **ROCm Support:** Full native support in vLLM, SGLang, and PyTorch ROCm.
*   **GGUF Availability:** 100% coverage via community sharding.
*   **AWQ Availability:** Standard release on Hugging Face.
*   **Licensing:** Apache 2.0 (for models up to 32B). Larger models (72B+) use the Qwen Research and Commercial License (free up to 100M monthly active users).

---

### 2.2 DeepSeek Series (V3 / R1 / Coders / Distills)

DeepSeek’s flagship MoE models and reasoning-focused R1 series represent the pinnacle of reasoning and cost efficiency.

*   **Accuracy:** Exceptional. DeepSeek-V3 (671B MoE) and R1 match GPT-4o and Claude 3.5 Sonnet on standard intelligence tests.
*   **Instruction Following:** Excellent. High alignment, although DeepSeek-R1 reasoning models can sometimes overshoot direct instructions in favor of long `<think>` output chains.
*   **Math:** SOTA reasoning. DeepSeek-R1 scores 97.3% on GSM8K and 90.2% on MATH.
*   **Coding:** Excellent. R1 and Coder-V2 excel in multi-file logic, syntax generation, and code explanation.
*   **Summarization:** Strong, though reasoning models can output unnecessarily wordy rationales unless constrained.
*   **Classification:** Very strong.
*   **NER:** High accuracy.
*   **Reasoning:** World-class reinforcement-learned reasoning. Distilled variants (e.g., R1-Distill-Qwen-32B) inherit R1's reasoning traces and visual thought processes.
*   **Latency:** 
    *   *Full 671B MoE:* High first-token latency unless run on massive H100 clusters.
    *   *Distills (8B to 70B):* Low-to-moderate latency. Distilled models running on vLLM/Ollama output ~40-70 tokens/sec.
*   **VRAM:**
    *   *R1-Distill-Qwen-8B:* ~6-8 GB VRAM.
    *   *R1-Distill-Qwen-32B:* ~20-24 GB VRAM (Q4 GGUF).
    *   *R1-Distill-Llama-70B:* ~40-48 GB VRAM (Q4 GGUF).
    *   *Full R1 (671B):* ~320 GB+ VRAM quantized (requires 8x A100/H100 GPUs).
*   **Quantization Support:** Complete (FP8, INT4, GGUF, AWQ).
*   **ROCm Support:** Native optimization. Widely deployed on AMD MI300X clusters.
*   **GGUF Availability:** Complete.
*   **AWQ Availability:** Complete.
*   **Licensing:** MIT License (highly permissive, allowing unrestricted commercial use and modification).

---

### 2.3 Llama Series (Llama 3.3 / Llama 3.1)

Meta's Llama models are the industry standard for general-purpose utility and enterprise safety.

*   **Accuracy:** Exceptional for its size. Llama 3.3 70B is highly competitive with proprietary GPT-4 class models.
*   **Instruction Following:** Industry-leading. Extremely robust compliance with system prompts, structural constraints, and negative constraints.
*   **Math:** Strong general math, but beaten by specialized Qwen-Math or DeepSeek-R1 models.
*   **Coding:** High competence, but slightly less specialized than Qwen-Coder.
*   **Summarization:** SOTA. Produces extremely coherent, clean, and concise summaries.
*   **Classification:** Top-tier accuracy for intent routing and sentiment classification.
*   **NER:** High accuracy; reliable JSON/XML schema extraction.
*   **Reasoning:** Excellent general reasoning, logic, and multi-turn planning.
*   **Latency:** Very low. GQA (Grouped-Query Attention) architecture ensures high throughput.
*   **VRAM:**
    *   *Llama 3.1 8B:* ~16 GB (Unquantized), ~5-6 GB (Q4 GGUF).
    *   *Llama 3.3 70B:* ~140 GB (Unquantized), ~40-48 GB (Q4 GGUF).
*   **Quantization Support:** Universally supported.
*   **ROCm Support:** Native support (fully optimized by AMD and Meta).
*   **GGUF Availability:** Universal.
*   **AWQ Availability:** Universal.
*   **Licensing:** Llama 3.3 Community License (Free for research and commercial use up to 700M monthly active users).

---

### 2.4 Gemma Series (Gemma 3 / Gemma 2)

Google's Gemma models punch far above their weight due to knowledge distillation from Gemini models.

*   **Accuracy:** Very high. Gemma 3 27B performs at Gemini 1.5 Pro levels.
*   **Instruction Following:** Strong, though sometimes prone to over-refusal on edge-case safety prompts.
*   **Math:** Excellent. Outperforms Llama models of equivalent parameters.
*   **Coding:** High capability (particularly Gemma 3 27B).
*   **Summarization:** Very coherent and structured.
*   **Classification:** Excellent.
*   **NER:** High precision.
*   **Reasoning:** Excellent logical reasoning, especially in multimodal scenarios (Gemma 3 4B/12B/27B natively process images).
*   **Latency:** Moderate. Deep architectures can result in higher pre-fill times, but decoding speed is highly optimized.
*   **VRAM:**
    *   *Gemma 3 1B:* ~2 GB (CPU/GPU edge use).
    *   *Gemma 3 4B:* ~8 GB (Unquantized), ~3 GB (Q4).
    *   *Gemma 3 12B:* ~24 GB (Unquantized), ~8-9 GB (Q4).
    *   *Gemma 3 27B:* ~54 GB (Unquantized), ~18-20 GB (Q4 GGUF).
*   **Quantization Support:** Supported natively via Google QAT (Quantization-Aware Training), GGUF, and AWQ.
*   **ROCm Support:** Yes.
*   **GGUF Availability:** High.
*   **AWQ Availability:** High.
*   **Licensing:** Gemma Terms of Use (Open weights, free commercial/research use with Llama-like restrictions).

---

### 2.5 Phi Series (Phi-4 / Phi-4-mini)

Microsoft’s Phi models leverage "textbook-quality" synthetic datasets to achieve outsized reasoning.

*   **Accuracy:** High. Phi-4 14B outperforms many 30B/70B models in cognitive tests.
*   **Instruction Following:** High compliance.
*   **Math:** SOTA for under 15B parameters. Phi-4-reasoning is a mathematics powerhouse.
*   **Coding:** Excellent code generation and syntax correctness.
*   **Summarization:** Good, but limited by smaller context windows compared to Qwen/Llama.
*   **Classification:** Excellent and cheap.
*   **NER:** High accuracy.
*   **Reasoning:** Strong. The reasoning variants use reinforcement learning to output detailed thought chains.
*   **Latency:** Extremely fast. Phi-4-mini (3.8B) outputs up to 300 tokens/second on consumer hardware.
*   **VRAM:**
    *   *Phi-4-mini (3.8B):* ~8 GB (Unquantized), ~2.5 GB (Q4).
    *   *Phi-4 (14B):* ~28 GB (Unquantized), ~9-10 GB (Q4).
*   **Quantization Support:** Full support.
*   **ROCm Support:** Native via llama.cpp and vLLM.
*   **GGUF Availability:** Universal.
*   **AWQ Availability:** Universal.
*   **Licensing:** MIT License (completely permissive, commercial-friendly).

---

### 2.6 GLM & Yi Series

*   **GLM (Zhipu AI):** SOTA tool use and function calling. Released under the **MIT license** for open-weight versions (e.g. GLM-4-9B, GLM-4-32B). Excellent for agent routing and structural code validation.
*   **Yi (01.AI):** Yi-1.5 (6B, 9B, 34B) is released under the **Apache 2.0 license**. Excellent multilingual capabilities, especially Chinese/English. Great general language comprehension.

---

### 2.7 SmolLM & OpenCoder

*   **SmolLM2 (Hugging Face):** Super-compact models (135M, 360M, 1.7B) under **Apache 2.0 license**. Ideal for edge computing and basic parsing fallbacks.
*   **OpenCoder:** Purely transparent code models (1.5B, 8B) under **Apache 2.0 license**. Excellent for high-speed, local syntax verification.

---

## 3. Comparative Summary Table

| Model Family / Size | Context | Primary Strengths | Quantized VRAM (Q4) | Licensing | Primary Local Role |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **SmolLM2 (1.7B)** | 8K | High-speed parsing, counting | ~1.5 GB | Apache 2.0 | Tiny / Parser |
| **Gemma 3 (1B / 4B)** | 32K/128K | Edge multimodal, languages | ~2.5 GB / ~3.0 GB | Gemma Terms | Edge / Multimodal |
| **Phi-4-mini (3.8B)** | 32K | Fast coding, MMLU, reasoning | ~2.5 GB | MIT | Small / Speed |
| **Phi-4 (14B)** | 32K | Reasoning, Math, STEM | ~9.5 GB | MIT | Medium / Reasoning |
| **GLM-4 (9B / 32B)** | 128K | Tool use, function calling | ~6.0 GB / ~22.0 GB | MIT | Verifier / Tool Use |
| **Qwen2.5-Coder (32B)** | 128K | Coding, syntax matching | ~20.0 GB | Apache 2.0 | Medium / Coder |
| **DeepSeek-R1-Distill-Qwen (32B)** | 128K | Reinforcement reasoning, math | ~20.0 GB | MIT | Medium / Reasoning |
| **Llama 3.3 (70B)** | 128K | Instruction compliance, safety | ~42.0 GB | Llama License | Judge / Large |
| **DeepSeek-R1-Distill-Llama (70B)** | 128K | Complex reasoning, math | ~44.0 GB | MIT | Large / Complex |

---

## 4. TERA Model Hierarchy Design

We propose a multi-tiered hierarchy to balance latency, VRAM, and capability. The DEL (Deterministic Execution Layer) sits at the top to bypass all LLM operations where possible.

```
                         Incoming Request
                                │
                                ▼
         ┌──────────────────────────────────────────────┐
         │   Deterministic Execution Layer (DEL)        │
         │   (Regex, Ast, Dictionaries, IP, Math)       │
         └──────────────────────┬───────────────────────┘
                                │ Bypass Miss
                                ▼
         ┌──────────────────────────────────────────────┐
         │         TERA Router (Phi-4-mini)             │
         └──────────────────────┬───────────────────────┘
                                │
          ┌─────────────────────┼─────────────────────┐
          ▼                     ▼                     ▼
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│   Tiny Lane      │  │   Medium Lane    │  │   Large Lane     │
│ (SmolLM2-1.7B)   │  │ (Qwen2.5-Cod-32B)│  │ (Llama 3.3 70B)  │
└─────────┬────────┘  └─────────┬────────┘  └─────────┬────────┘
          │                     │                     │
          ▼                     ▼                     ▼
┌──────────────────────────────────────────────────────────────┐
│           Output Verifier (GLM-4-9B / Phi-4-mini)            │
└───────────────────────────────┬──────────────────────────────┘
                                │ Validation Fail
                                ▼
┌──────────────────────────────────────────────────────────────┐
│                  Judge / Escalation Lane                     │
│           (DeepSeek-R1-Distill-Llama-70B / o1)               │
└───────────────────────────────┬──────────────────────────────┘
                                │
                                ▼
                         Final Response
```

---

### 4.1 Tier 1: Tiny (SmolLM2-1.7B-Instruct)
*   **Primary Tasks:** Simple classification, sentence counting, basic token transformations, NER fallbacks, structured string parsing.
*   **Why:** 
    *   *Latency:* First-token response in $<10\text{ ms}$; outputs $>120\text{ tokens/sec}$ on simple CPU threads.
    *   *Memory footprint:* Requires $<1.5\text{ GB}$ VRAM when quantized to 4-bit, making it loadable on standard edge services without impacting production model VRAM.
    *   *Licensing:* Apache 2.0 permits unrestricted integration.

### 4.2 Tier 2: Small (Phi-4-mini-Instruct)
*   **Primary Tasks:** General conversational logic, simple schema generation, basic coding tasks, text formatting, and API intent routing.
*   **Why:** 
    *   *Performance-to-Size Ratio:* At only 3.8B parameters, it outperforms older 7B/13B models in math and logic.
    *   *Licensing:* The MIT license is highly developer-friendly.
    *   *VRAM:* Requires only ~2.5 GB VRAM in 4-bit quantization, allowing it to co-exist on the same GPU as larger models.

### 4.3 Tier 3: Medium (Qwen2.5-Coder-32B-Instruct / DeepSeek-R1-Distill-Qwen-32B)
*   **Primary Tasks:** Complex coding, mathematical logic, intermediate structured JSON schema parsing, and multi-file analysis.
*   **Why:** 
    *   *SOTA Coding:* Qwen2.5-Coder-32B is widely recognized as the strongest open-weight 32B model for software engineering.
    *   *Reasoning:* DeepSeek-R1-Distill-Qwen-32B brings reinforcement-learned thought processes to a consumer-grade VRAM footprint (~20 GB in Q4).
    *   *VRAM:* Fits fully on a single RTX 3090/4090 (24GB VRAM) while running at $>40\text{ tokens/sec}$.

### 4.4 Tier 4: Large (DeepSeek-R1-Distill-Llama-70B / Llama 3.3 70B Instruct)
*   **Primary Tasks:** Multi-step reasoning, complex algorithm synthesis, code translation across paradigms, and agent execution.
*   **Why:** 
    *   *Frontier Capability:* The 70B distilled R1 model performs comparably to closed-source reasoning engines on coding and mathematical tests.
    *   *VRAM:* Requires ~44 GB VRAM (Q4 GGUF), fitting comfortably on dual 24GB consumer GPUs (RTX 3090/4090) or high-end unified memory Mac workstations.

### 4.5 Tier 5: Judge (Llama 3.3 70B Instruct)
*   **Primary Tasks:** Evaluating output quality, ranking candidate completions, auditing cheap model generations, and comparing semantic alignment.
*   **Why:** 
    *   *Alignment:* Llama 3.3 70B is highly aligned with human preferences and instruction-following, making it the most robust open-weight choice for "LLM-as-a-judge" workflows.
    *   *Context:* Supports a 128K context window, permitting evaluation of long conversational histories and source files.

### 4.6 Tier 6: Router (Phi-4-mini-Instruct)
*   **Primary Tasks:** Prompt difficulty classification, intent detection, domain classification (e.g. math vs. code vs. dialogue), and cost-utility routing.
*   **Why:** 
    *   *Speed:* Must run in $<15\text{ ms}$ to prevent adding latency overhead to the request.
    *   *Instruction Compliance:* Phi-4-mini has excellent instruction following, allowing it to output structured JSON parameters representing prompt complexity.

### 4.7 Tier 7: Verifier (GLM-4-9B-Instruct)
*   **Primary Tasks:** Syntax verification (JSON/XML/HTML validity check), tool invocation matching, argument validation, and stop-token monitoring.
*   **Why:** 
    *   *Agent & Tool Optimization:* GLM-4-9B is trained specifically for SOTA function-calling and tool verification workflows.
    *   *Licensing:* Permissive MIT license allows customization for strict schema verification routines.

---

> [!TIP]
> By choosing **MIT** and **Apache 2.0** models for the execution pipeline (Phi-4-mini, SmolLM2, Qwen2.5-Coder, GLM-4, DeepSeek-R1-Distill), the platform maintains absolute licensing compliance for commercial distributions without intellectual property liability.
