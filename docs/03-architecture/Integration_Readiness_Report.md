# TERA V3: Integration Readiness Report

**Author:** Agent F (Chief Integration Engineer)  
**Status:** COMPLETE (Ready for Architecture Board Review)  
**Date:** July 12, 2026  
**Scope:** Integration assessment of inputs from Agents A–E (System Architecture, ML Router, Deterministic Solver, Local AI Stack, Verification Layer)

---

## Executive Summary

As the Chief Integration Engineer, this report identifies integration readiness factors by analyzing the technical specifications submitted by the respective architecture leads. 

The goal of this audit is to locate **conflicts**, **dependency issues**, **missing interfaces**, **circular dependencies**, and **integration risks** *before* code integration begins. 

In accordance with project constraints, this report does not redesign the architecture or invent new features; it highlights structural bottlenecks that must be resolved to ensure a stable, high-performance integration.

---

## 1. Identified Conflicts

### Conflict 1.1: Double-Calibration and Mathematical Divergence
*   **Source Components:** ML Router (`ML_Router_Technical_Specification.md` - Agent B) vs. ROVL V3 (`ROVL_V3_Technical_Specification.md` - Agent E).
*   **The Conflict:** 
    *   The **ML Router** performs logistic-to-isotonic probability calibration *prior* to inference to estimate the success probability of the cheap model: $\hat{P}(A_2 = 1 \mid x)$. It computes the expected utility of the cascade path assuming a static remote dense baseline accuracy $\alpha_{dense, d}$.
    *   **ROVL V3** performs a separate Platt-to-isotonic probability calibration *post* inference using generation metadata ($\bar{H}$, $I_{max}$, $S_{schema}$, $S_{ast}$, $S_{judge}$) to estimate output correctness: $\tilde{p}$.
    *   *System Mismatch:* The ML Router's cascade utility formulation assumes a perfect verification layer (0% False Positives and 0% False Negatives). However, ROVL V3 has imperfect precision/recall. If the ML Router does not model the validation error rates of ROVL V3, the routing engine will make sub-optimal routing decisions.
*   **Integration Impact:** Reduced efficiency and possible over-escalation if the prior utility models do not align with the posterior validation rates.

### Conflict 1.2: Quantized Local Inference vs. Logprob Telemetry
*   **Source Components:** Local AI Stack (Agent D) vs. ROVL V3 Tier 2 Statistical Auditing (Agent E).
*   **The Conflict:** 
    *   The **Local AI Stack** recommends highly quantized models (AWQ, GGUF, FP8, FP4) running via `vLLM` or `llama.cpp` to minimize memory and costs.
    *   **ROVL V3 Tier 2** relies on token-level log probabilities (logprobs) to compute Mean Sequence Entropy $\bar{H}$ and Token Surprisal $I(x_t)$.
    *   *System Mismatch:* Quantized runtimes (especially when compiled with certain speed-optimization flags or deployed under speculative decoding) often disable logprob generation by default, or return uncalibrated, distorted token distributions. If logprobs are absent or corrupted, ROVL V3 is forced into "degraded observability mode," disabling Tier 2 checks entirely.
*   **Integration Impact:** Bypassing Tier 2 checks reduces verification accuracy, placing the burden entirely on Tier 4 (expensive local judges) or Tier 1 (rigid schema checks).

### Conflict 1.3: Deterministic Execution Layer (DEL) Covariate Shift
*   **Source Components:** DEL Solver Registry (Agent C) vs. ML Router Classifier (Agent B).
*   **The Conflict:** 
    *   The **DEL** executes at the immediate ingress, intercepting and solving simple queries before feature extraction.
    *   The **ML Router** classifier is trained offline on historical prompt distributions to estimate task difficulty.
    *   *System Mismatch:* Intercepting and resolving the easiest tasks at the DEL layer shifts the covariate distribution of prompts that reach the ML Router. The ML Router will see a disproportionately high density of hard/unsolvable queries, causing its offline-trained logistic classifier to over-predict difficulty and over-route to the dense remote model.
*   **Integration Impact:** Leaderboard token usage inflation due to routing bias shift.

---

## 2. Dependency Issues

### Dependency 2.1: Host System ROCm Device Mapping and Failover
*   **Source Components:** Local AI Stack (Agent D) vs. Orchestrator API Client (Agent A).
*   **The Issue:** The local inference stack relies on direct hardware device mapping (`/dev/kfd`, `/dev/dri`) within the execution container. If the host system fails to expose these devices (e.g., driver version mismatch during deployment), the local models fail to load.
*   **Integration Impact:** The system will fail completely unless the model interfaces implement a transparent, non-blocking fallback to remote API endpoints when local sockets are unreachable.

### Dependency 2.2: Asynchronous Event Loop Blockage by Synchronous Solvers
*   **Source Components:** Deterministic Solvers (Agent C) vs. Execution Coordinator (Agent A).
*   **The Issue:** The Orchestration Engine is designed to run asynchronously using an event loop to execute independent DAG nodes in parallel. However, several registered DEL solvers (e.g., SymPy matrix calculations, diff generation, XML parsing) are CPU-bound, synchronous blocking functions.
*   **Integration Impact:** Running these synchronous functions directly inside the async loop will freeze the single thread, blocking concurrent requests and violating sub-second latency targets.

---

## 3. Missing Interfaces

### Interface 3.1: State Manager Variable Injection
*   **Source Components:** DEL Solver Interface (`deterministic_execution_layer_spec.md` - Agent C) vs. DAG State Manager (`tera_v3_capability_engine_architecture.md` - Agent A).
*   **The Gap:** The base solver interface defines `solve(self, prompt, context) -> str`. This returns only a raw string response. In TERA V3's DAG execution, solvers must return *structured variables* (e.g., matrices, lists, float values) to inject into the State Manager for consumption by downstream nodes.
*   **Resolution Requirement:** The solver interface must support returning a dictionary of structured variables, not just plain text.

### Interface 3.2: Logprob Format Standardization
*   **Source Components:** Model Interface (`ModelInterface` - Agent A) vs. ROVL V3 (`rovl_v3.py` - Agent E).
*   **The Gap:** The `ModelInterface` specifies a `generate(self, prompt)` method returning `InferenceResponse`. However, it does not define the standard return structure for token-level log probabilities. Different runtimes (vLLM, llama.cpp, Fireworks API) return logprobs in divergent formats (e.g., nested JSON keys, logprob arrays, or token-probability tuples).
*   **Resolution Requirement:** Standardize a unified `TokenLogprob` schema within the core `InferenceResponse` object.

### Interface 3.3: Feedback Loop for Calibration Telemetry
*   **Source Components:** Telemetry Logger (Agent A) vs. Offline Recalibration Script (Agent B).
*   **The Gap:** ROVL V3 calibration requires continuous training. There is no defined interface or API endpoint to serialize correctness indicators ($y_i$) and verification vectors ($\mathbf{s}_i$) back to the training directory (`models/`) for automated weight updates.
*   **Resolution Requirement:** Define a data export pipeline interface in the telemetry module.

---

## 4. Circular Dependencies

### Circular Dependency 4.1: Local Judge (Tier 4) vs. GPU Queue Starvation
*   **Source Components:** ROVL V3 Tier 4 Judge (Agent E) vs. Local AI Stack (Agent D).
*   **The Issue:** 
    1.  The TERA Orchestrator routes a prompt to the local Medium model ($M_2$).
    2.  $M_2$ generates an output and sends it to the ROVL V3 pipeline.
    3.  ROVL V3 invokes Tier 4, requesting the Local Judge model (which runs on the same local GPU) to verify the completion.
    4.  If the local GPU is at maximum batch capacity processing other incoming prompts, the Local Judge request is queued.
    5.  The original transaction remains open, holding the event queue slot.
*   **System Deadlock:** A circular lock occurs: the inference server cannot free up batch capacity because it is waiting for open requests to be verified, and requests cannot be verified because the judge model is blocked in the GPU queue.
*   **Resolution Requirement:** Explicit prioritization and VRAM partitioning for local judge models.

---

## 5. Potential Integration Risks

### Risk 5.1: VRAM Fragmentation and Dynamic OOMs
*   **Risk Description:** Running multiple model sizes (1.5B, 7B, 72B GGUF) concurrently on local AMD hardware can lead to sudden GPU Out-Of-Memory (OOM) failures under peak concurrent load. 
*   **Mitigation Strategy:** strict memory limits must be configured on runtimes (e.g., `gpu_memory_utilization` limits in vLLM) and model layers must be isolated.

### Risk 5.2: Backtracking Latency Accumulation
*   **Risk Description:** If a DAG node fails verification, it triggers local backtracking. If a node fails repeatedly, the sequential retry latencies will accumulate, exceeding the SLA constraint.
*   **Mitigation Strategy:** Enforce a hard ceiling on retries (e.g., max 1 local backtrack per node before escalating to the Remote API fallback).

---

## 6. Integration Checklist

Before beginning the TERA V3 integration phase, the implementation agents must verify the completion of the following tasks:

- [ ] Standardize the `InferenceResponse` JSON schema to include a unified logprob representation.
- [ ] Define structured return schemas for DEL solvers to support downstream variable injection.
- [ ] Update the ML Router's expected utility formulas to model the False Positive and False Negative rates of ROVL V3.
- [ ] Implement an asynchronous thread wrapper for synchronous DEL solvers to prevent event loop blocking.
- [ ] Establish explicit VRAM reservation boundaries for the Local Judge model to prevent GPU queue deadlocks.
- [ ] Establish automatic failover logic to Remote APIs if the local ROCm driver socket is unreachable.
