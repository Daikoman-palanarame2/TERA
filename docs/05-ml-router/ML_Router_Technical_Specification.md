# TERA ML Router Technical Specification

**Version:** 1.0 (Hackathon Edition)

---

## 1. Purpose

This document specifies the engineering implementation of TERA's intelligent routing engine.

Unlike the accompanying research paper, which presents the theoretical formulation of the routing algorithm, this specification focuses on the practical implementation of the routing pipeline, component interactions, configuration, and execution flow.

The ML Router is responsible for minimizing inference cost while maintaining a target accuracy threshold through dynamic model selection.

---

## 2. Objectives

The router is designed to achieve the following objectives:
- Minimize total token consumption.
- Preserve response quality through calibrated confidence estimation.
- Operate with negligible computational overhead.
- Avoid GPU-dependent preprocessing.
- Automatically recover from low-quality model outputs.

---

## 3. Router Pipeline

```
Incoming Prompt
      │
      ▼
Feature Extraction
      │
      ▼
Difficulty Prediction
(Logistic Regression)
      │
      ▼
Probability Calibration
(Isotonic Regression)
      │
      ▼
Expected Utility Computation
      │
      ▼
Route Selection
      │
 ┌────┼────┐
 │    │    │
 ▼     ▼    ▼
M₂   M₃  Cascade
      │
      ▼
Runtime Output Verification
      │
      ▼
Final Response
```

---

## 4. Components

### 4.1 Feature Extraction Module

#### Purpose
Extract lightweight lexical features from an incoming prompt.

- **Inputs:** Prompt String
- **Outputs:** Feature Vector \(\phi(x)\)

#### Features
| Feature | Description |
| :--- | :--- |
| **Prompt Length** | Character count |
| **Symbol Density** | Ratio of symbols to characters |
| **Regex Density** | Keyword/domain detection |
| **BM25 Score** | Similarity to historical prompts |

### 4.2 Difficulty Estimator

#### Model
Offline-trained Logistic Regression.

- **Input:** \(\phi(x)\)
- **Output:** Difficulty Score \(s\)

#### Properties
- CPU-only inference
- \(O(d)\)
- < 1 KB serialized model

### 4.3 Probability Calibration
Raw logistic scores are calibrated using Isotonic Regression.

- **Input:** Difficulty Score
- **Output:** \(P(\text{success} \mid \text{prompt})\)

#### Purpose
Convert classifier confidence into calibrated probabilities suitable for optimization.

### 4.4 Utility Engine

#### Canonical Source
The mathematical formulations in this section are reproduced directly from the research paper *Token-Efficient LLM Routing via Calibrated Utility Optimization for Resource-Constrained Inference*. If discrepancies arise between this document, implementation code, or future documentation revisions, the research paper is the authoritative source.

The utility engine evaluates every available execution path:
- **Direct Cheap Model Path ($M_2$)**
- **Direct Dense Model Path ($M_3$)**
- **Cascade Path ($M_2 \rightarrow M_3$)**

Each path receives an expected utility score. The highest-scoring path is selected.

#### Cost Normalization
To prevent objective mismatch when optimizing integer token costs against dimensionless probabilities, token costs are normalized against the maximum potential system expenditure:
$$\tilde{C}_M(x) = \frac{C_M(x)}{C_{\text{max}}}$$
where $C_{\text{max}} = C_3$ (the total cost of routing directly through $M_3$). This bounds the cost metric within $[0, 1]$.

#### Lagrangian Utility Optimization
The system utility payload $U(M)$ is defined using the Lagrangian multiplier $\lambda \in [0, 1]$:
$$U(M) = \lambda \cdot \mathbb{E}[A_M(x)] - (1 - \lambda) \cdot \mathbb{E}[\tilde{C}_M(x)]$$
The agent selects the path $M^*$ that maximizes this value:
$$M^* = \arg\max_{M \in \{M_2, M_3, M_{\text{cascade}}\}} U(M)$$

#### Path Utility Equations
1. **Direct Cheap Model Path ($M_2$)**:
   $$\mathbb{E}[A_{M_2}(x)] = \hat{P}(A_2 = 1 \mid x)$$
   $$\mathbb{E}[\tilde{C}_{M_2}(x)] = \frac{C_2}{C_3}$$
   $$U(M_2) = \lambda \cdot \hat{P}(A_2 = 1 \mid x) - (1 - \lambda) \cdot \frac{C_2}{C_3}$$

2. **Direct Dense Model Path ($M_3$)**:
   $$\mathbb{E}[A_{M_3}(x)] = \alpha_{\text{dense}, d}$$
   $$\mathbb{E}[\tilde{C}_{M_3}(x)] = 1.0$$
   $$U(M_3) = \lambda \cdot \alpha_{\text{dense}, d} - (1 - \lambda)$$
   where $\alpha_{\text{dense}, d}$ represents the baseline dense accuracy in the broad task domain $d \in \{\text{math}, \text{logic}, \text{code}, \text{gen}\}$.

3. **Cascade Path ($M_{\text{cascade}}$)**:
   $$\mathbb{E}[A_{\text{cascade}}(x)] = \hat{P}(A_2 = 1 \mid x) + \left(1 - \hat{P}(A_2 = 1 \mid x)\right)\alpha_{\text{dense}, d}$$
   $$\mathbb{E}[\tilde{C}_{\text{cascade}}(x)] = \frac{C_2 + \left(1 - \hat{P}(A_2 = 1 \mid x)\right)C_3}{C_3}$$
   $$U(M_{\text{cascade}}) = \lambda \cdot \left[ \hat{P}(A_2 = 1 \mid x) + \left(1 - \hat{P}(A_2 = 1 \mid x)\right)\alpha_{\text{dense}, d} \right] - (1 - \lambda) \cdot \left[ \frac{C_2}{C_3} + \left(1 - \hat{P}(A_2 = 1 \mid x)\right) \right]$$

#### Mathematical Notation Reference Table
| Symbol | Meaning |
| :--- | :--- |
| $C_2$ | Token cost of the cheap model |
| $C_3$ | Token cost of the dense model |
| $C_{\text{max}}$ | Maximum routing cost, equal to $C_3$ |
| $\tilde{C}_M(x)$ | Normalized routing cost |
| $\hat{P}(A_2=1\mid x)$ | Calibrated probability that the cheap model succeeds |
| $\alpha_{\text{dense},d}$ | Offline-profiled dense model baseline accuracy for task domain $d$ |
| $\lambda$ | Accuracy-versus-cost trade-off coefficient |
| $\mathbb{E}[A_M(x)]$ | Expected routing accuracy |
| $\mathbb{E}[\tilde{C}_M(x)]$ | Expected normalized routing cost |
| $U(M)$ | Expected utility of routing path $M$ |

### 4.5 Route Selector

#### Responsibilities
- Compare utility values
- Choose optimal model
- Produce routing metadata

#### Example
```json
{
  "selected_model": "M2",
  "confidence": 0.91,
  "route": "cheap"
}
```

### 4.6 Runtime Output Verification Layer (ROVL)

#### Purpose
Detect failed generations before returning results.

#### Checks
- Schema validation
- Length validation
- Stop-token validation
- Entropy validation (when supported)

Failure results in automatic escalation to the dense model.

---

## 5. Data Flow

```
User Prompt -> Feature Extraction -> Difficulty Prediction -> Calibration -> Utility Evaluation -> Route Selection -> Model Inference -> Verification -> Response
```

---

## 6. Training Pipeline

The router is trained offline.

```
Dataset -> Feature Extraction -> Training Split -> Logistic Regression -> Calibration Split -> Isotonic Regression -> Serialized Models -> Deployment
```

*Note: No online learning occurs during inference.*

---

## 7. Model Artifacts

The router depends on the following serialized assets.

```
models/
├── logistic_regression.pkl
├── isotonic_regression.pkl
├── bm25_index.pkl
└── feature_config.json
```

These assets are loaded during application startup.

---

## 8. Configuration

### Example Configuration
```yaml
cheap_model: llama3-8b
dense_model: gpt-4.1
lambda: 0.65
min_confidence: 0.80
entropy_threshold: 2.7
max_tokens: 512
```

All routing behavior is configurable without modifying source code.

---

## 9. Error Handling

The router should gracefully recover from common failures.

| Failure | Action |
| :--- | :--- |
| **Missing feature** | Return default value |
| **Calibration unavailable** | Use raw logistic score |
| **Cheap model timeout** | Escalate to dense model |
| **Verification failure** | Retry using dense model |
| **Dense model failure** | Return system error |

---

## 10. Performance Targets

| Metric | Target |
| :--- | :--- |
| **Routing latency** | < 0.1 ms |
| **Memory usage** | < 5 MB |
| **Feature extraction** | CPU only |
| **GPU dependency** | None |
| **Router availability** | 99.9% |

---

## 11. Directory Structure

```
models/
├── logistic_regression.pkl
├── isotonic_regression.pkl
├── bm25_index.pkl
└── feature_config.json
```

---

## 12. Future Enhancements

Potential future improvements include:
- Multi-model routing beyond two model tiers.
- Adaptive utility weighting.
- Online probability recalibration.
- User-specific routing policies.
- Reinforcement learning for route optimization.
- Distributed routing across multiple inference servers.

---

## 13. Relationship to Other Documents

| Document | Purpose |
| :--- | :--- |
| **PRD** | Defines product goals and requirements. |
| **UI/UX Specification** | Defines the user interface and experience. |
| **Constitution** | Establishes engineering principles and development rules. |
| **System Architecture** | Describes how all major system components interact. |
| **ML Router Technical Specification** | Details the implementation of the routing engine. |
| **Research Paper** | Presents the theoretical foundations and mathematical formulation of the routing algorithm. |
| **Deployment Guide** | Explains how to build, configure, and run the system. |

---

### Status of Documentation

```
docs/
├── 01-product/
│   └── PRD.md
├── 02-design/
│   └── UI_UX_Specification.md
├── 03-architecture/
│   ├── Constitution.md
│   └── System_Architecture.md
└── 05-ml-router/
    └── ML_Router_Technical_Specification.md
```
