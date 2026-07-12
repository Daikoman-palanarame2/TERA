# TERA Local AI Execution Stack Specification (Agent D Edition)

**Author:** Agent D (Local Inference Systems Lead)  
**Version:** 3.0 (Frozen Architecture Implementation Blueprint)  
**Status:** Approved / Frozen  

---

## 1. Subsystem Integration & Context

This specification defines the engineering blueprint for the **Local LLM** subsystem within the frozen TERA pipeline:

```
User ──> Semantic Cache ──> Intent Parser ──> Deterministic Solver ──> [ Local LLM ] ──> ROVL Verification ──> Return
                                                                                             │
                                                                           Verification Fails│
                                                                                             ▼
                                                                                   Remote Fallback (Optional)
```

The Local LLM subsystem executes queries routed by the Deterministic Solver and feeds raw token outputs directly to the **Runtime Output Verification Layer (ROVL)**. This stack is designed to minimize local latency, maximize throughput under multi-agent concurrency, and ensure deterministic operation without altering the high-level routing flow.

---

## 2. Production Stack Selections

To guarantee maximum execution stability on AMD hardware, TERA standardizes on a dual-tier execution stack. 

### 2.1 Datacenter Server Tier (Primary)
- **Runtime & Inference Engine:** **SGLang (ROCm)**
- **Quantization:** **FP8 (E4M3/E5M2)**
- **Batching & Cache:** Continuous Batching with **RadixAttention** prefix caching and FP8 KV cache.

### 2.2 Workstation / Fallback Tier (Edge)
- **Runtime & Inference Engine:** **llama.cpp (HIPBLAS)**
- **Quantization:** **GGUF (Q4_K_M)**
- **Batching & Cache:** Static batching with virtual memory offloading (`mmap` + `mlock`).

---

## 3. Subsystem Architecture & Implementation Parameters

### 3.1 Inference Engine & Runtime Configuration

#### SGLang (ROCm) Serving Configuration
SGLang is executed in the primary container with the following CLI launch parameters for high-throughput serving:
```bash
python -m sglang.launch_server \
  --model-path /models/DeepSeek-R1-Distill-Llama-70B-FP8 \
  --host 0.0.0.0 \
  --port 30000 \
  --tp 1 \
  --mem-fraction-static 0.85 \
  --context-length 32768 \
  --enable-p2p-check \
  --kv-cache-dtype fp8_e5m2 \
  --enable-flashinfer \
  --enable-radix-cache
```

#### llama.cpp (HIPBLAS) Offload Configuration
For workstation fallback, llama.cpp executes with optimized HIP kernels:
```bash
./llama-cli \
  -m /models/qwen2.5-coder-32b-q4_k_m.gguf \
  --host 0.0.0.0 \
  --port 30000 \
  -c 32768 \
  -ngl 64 \
  --mmap \
  --mlock \
  -t 16
```

---

### 3.2 Model Loading & Memory Planning

#### Memory Pre-Allocation
To avoid runtime host-to-device synchronization page faults, SGLang must pre-allocate VRAM.
- Set `--mem-fraction-static 0.85`. This reserves 85% of VRAM for model weights and the KV cache tree, leaving 15% for Triton compile buffers and driver runtime allocations.
- Host memory loading uses `hipHostMalloc` to pin pages, guaranteeing maximum PCIe Gen 4/5 transfer speeds.

#### Memory Mapping (`mmap` & `mlock` in llama.cpp)
- **`--mmap` (Memory Map):** Enabled to allow the operating system to dynamically page parts of the model weights from disk to RAM as needed, reducing startup times.
- **`--mlock` (Memory Locking):** Enabled to lock the pages in RAM, preventing the OS virtual memory subsystem from swapping model weights out to disk during idle periods in the TERA pipeline.

---

### 3.3 GPU Planning & CPU Fallback

#### Multi-GPU Tensor Parallelism (TP)
- For models up to 32B parameters: Standardize on `TP=1` on a single Radeon RX 7900 XTX (24GB VRAM) or Instinct card to avoid inter-GPU communication latency.
- For 70B+ parameters: Utilize `TP=1` on high-density Instinct nodes (192GB VRAM), or `TP=4` on multi-GPU server architectures via SGLang's internal Megatron-LM tensor parallel implementation.

#### CPU Fallback Path
When VRAM limits are breached on workstation systems, llama.cpp performs partial layer offloading:
- The parameter `-ngl` (number of GPU layers) is calculated dynamically:
  $$\text{NGL} = \min\left(\text{Total Layers}, \left\lfloor \frac{\text{VRAM}_{\text{available}} - \text{Memory}_{\text{overhead}}}{\text{Size per Layer}} \right\rfloor\right)$$
- Remaining layers are processed on the CPU using AVX-512 vector execution units.

---

### 3.4 Docker Integration Specification

```yaml
version: '3.8'

services:
  tera-local-llm:
    image: rocm/pytorch:rocm6.2-py3.10
    container_name: tera-local-llm
    ipc: host
    network_mode: host
    devices:
      - /dev/kfd:/dev/kfd
      - /dev/dri:/dev/dri
    environment:
      - HIP_VISIBLE_DEVICES=0
      - PYTORCH_HIP_ALLOC_CONF=expandable_segments:True
      - TORCH_BLAS_PREFER_HIPBLASLT=1
      - HIP_FORCE_DEV_KERNARG=1
      - NCCL_MIN_NCHANNELS=112
    volumes:
      - /opt/tera/models:/models
      - /opt/tera/cache/triton:/root/.triton
      - /opt/tera/cache/miopen:/root/.cache/miopen
    entrypoint: >
      python -m sglang.launch_server
      --model-path /models/Qwen2.5-Coder-32B-Instruct-AWQ
      --host 0.0.0.0
      --port 30000
      --mem-fraction-static 0.85
      --kv-cache-dtype fp8_e5m2
    restart: always
```

---

### 3.5 AMD ROCm/HIP Optimizations

1. **`PYTORCH_HIP_ALLOC_CONF=expandable_segments:True`:** Forces the HIP memory manager to map memory chunks in contiguous blocks. This prevents VRAM fragmentation OOMs caused by dynamic batch generation sizes.
2. **`TORCH_BLAS_PREFER_HIPBLASLT=1`:** Bypasses legacy matrix operations in favor of the optimized `hipBLASLt` library for Linear layers.
3. **QuickReduce Activation:** Embedded natively in SGLang compile paths, reducing tensor parallel sync delays across InfiniBand/Infinity Fabric backplanes.
4. **NUMA Balance Disabling:** Force host CPU kernel configurations:
   ```bash
   sysctl -w kernel.numa_balancing=0
   ```
   This prevents context-switching latency when the CPU manages GPU page tables.

---

### 3.6 Model Selection Matrix

To feed the TERA routing and cascading tiers, the following specific models are frozen for the local stack:

| TERA Role | Selected Model | Format/Quantization | Target Tier | Rationale |
| :--- | :--- | :--- | :--- | :--- |
| **Tiny Model (M2)** | Qwen 2.5 3B Instruct | AWQ 4-bit | Workstation / Edge | Lightweight, extremely fast prefill for simple routing tasks. |
| **Medium Model** | Qwen 2.5-Coder-32B-Instruct | AWQ 4-bit / FP8 | Workstation / Server | State-of-the-art 32B coding/reasoning balance. |
| **Large Model (M3)** | DeepSeek-R1-Distill-Llama-70B | FP8 | Datacenter Server | Outstanding reasoning performance on larger 70B context pools. |
| **Reasoning Model** | DeepSeek-R1 (Full MoE) | FP8 (or FP4) | Datacenter Cluster | Native reasoning chains matching o1 class logic. |
| **Coding Model** | Qwen 2.5-Coder-32B-Instruct | FP8 | Workstation / Server | Maximum LiveCodeBench performance among open-weights. |
| **Summarization Model**| Llama 3.1 70B Instruct | FP8 | Datacenter Server | Native 128k context window with low attention degradation. |
| **NER Model** | Qwen 2.5 7B Instruct | AWQ 4-bit | Workstation / Edge | High reliability in structured JSON generation. |
| **Math Model** | DeepSeek-R1-Distill-Qwen-32B | FP8 | Workstation / Server | High math scoring coupled with fast generation speeds. |
| **Verifier Model (ROVL)**| ArmoRM-Llama3-8B-v0.1 | FP16 (Non-quantized) | Workstation / Server | Precision scoring of answers during cheap model evaluation. |

---

### 3.7 Context Management & Batching

#### Continuous Batching (SGLang Scheduling)
The server operates SGLang’s dynamic batch scheduler. Incoming requests from the router are queued and grouped mid-inference cycle, bypassing static padding. 
- Prefill requests are dynamically chunked (`--chunked-prefill-size 512`) to prevent decoding steps from stalling.

#### RadixAttention Prefix Caching
Because TERA uses structural templates and system instructions during intent parsing and verification loops, SGLang maintains a Radix Tree of the KV cache.
- Exact match prefix queries (e.g., prompt templates, system headers) achieve $0\text{ ms}$ prefill time, instantly executing the decode phase.
- LRU (Least Recently Used) caching policy evicts oldest leaves when VRAM reaches memory fraction limits.

---

### 3.8 Performance Estimates & Sizing Metrics

The following metrics represent expected performance bounds under the frozen architecture configuration:

#### Tier 1 Datacenter: DeepSeek-R1-Distill-Llama-70B (FP8) on AMD Instinct MI300X
- **VRAM Allocation:** 73.5 GB (Weights) + 110 GB (KV Cache) + 8.5 GB (Overheads)
- **Time to First Token (TTFT - 1k prompt):** **120 ms**
- **Inter-Token Latency (ITL):** **11.7 ms**
- **Generation Speed:** **85 tokens/sec** (Single stream)
- **Aggregate Concurrency Throughput:** **3,100 tokens/sec** (C=64)

#### Tier 2 Workstation: Qwen 2.5-Coder-32B (AWQ) on Radeon RX 7900 XTX
- **VRAM Allocation:** 17.9 GB (Weights) + 3.6 GB (KV Cache) + 2.5 GB (Overheads)
- **Time to First Token (TTFT - 1k prompt):** **180 ms**
- **Inter-Token Latency (ITL):** **22.2 ms**
- **Generation Speed:** **45 tokens/sec** (Single stream)
- **Aggregate Concurrency Throughput:** **180 tokens/sec** (C=4)

---

### 3.9 Startup & Failure Recovery Optimization

#### Cold-Start Minimization (Pre-heating)
To prevent the first user request from triggering a timeout during Triton kernel compilation, the server executes a pre-heating script:
1. Warmup queries spanning various prompt lengths (e.g., 256, 1024, 4096 tokens) are fired sequentially against the loopback adapter (`127.0.0.1:30000`).
2. MIOpen compiler caches are pre-compiled and written to `/root/.cache/miopen`.
3. The server only opens its external Docker socket once warmup queries return a successful status code.

#### Failure Recovery Strategy
If the Local LLM engine encounters a failure (e.g., driver reset or VRAM OOM):
1. **Internal Fallback Check:** SGLang automatically drops max batch size and retries the request with a cleared KV cache.
2. **ROVL Escalation:** If the Local LLM engine does not respond within $1,500\text{ ms}$, the ROVL verification layer intercepts the error and routes the prompt directly to the **Remote Fallback** system.
3. **Container Health Watchdog:** Docker Compose enforces an active health check endpoint:
   ```yaml
   healthcheck:
     test: ["CMD", "curl", "-f", "http://localhost:30000/health"]
     interval: 10s
     timeout: 5s
     retries: 3
   ```
   If healthchecks fail 3 consecutive times, Docker automatically restarts the container.
