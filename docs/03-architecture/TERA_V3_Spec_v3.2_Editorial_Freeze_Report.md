# TERA V3 Interface & Module Contract Specification v3.2
## Final Editorial Freeze — Validation Report

**Status:** Frozen  
**Version:** 3.2 (Final Editorial Pass)  
**Date:** July 12, 2026  

---

## Editorial Changes Applied

The following **six editorial corrections** were applied. No interfaces, contracts, dependency rules, repository layout, or implementation behaviour were changed.

### 1. Removed Local Windows File Path (Section 4.10 — `TokenLogprob`)

**Before:**
```
defined in [data_contracts.py](<machine-local-path>/backend/app/schemas/data_contracts.py)
```

**After:**
```
defined in [data_contracts.py](backend/app/schemas/data_contracts.py)
```

*Rationale:* Replaced machine-specific OS path with a portable, repository-relative reference.

---

### 2. Corrected Estimator Responsibility Wording (Section 3.4 — `estimators`)

**Before:**
```
Computes entropy, length, and feature metrics to output numerical thresholds.
```

**After:**
```
Computes character length, symbol ratio, regex density, and BM25 similarity features to output difficulty estimates (defined in Section 4.7).
```

*Rationale:* The frozen `feature_extractor.py` implementation extracts a 4-dimensional `FeatureVector` (`length`, `symbol_ratio`, `regex_density`, `bm25_score`). The estimators module does not compute entropy. Wording now matches the implementation. Cross-reference to `DifficultyEstimate` (Section 4.7) added for reader navigation.

---

### 3. Verified and Standardised Log Module Convention (Section 9 — Logging Contract)

**Finding:** Section 9 uses Python import path notation (`app.inference.fast_model_client`). No filesystem path notation appears in Section 9. Convention is already consistent throughout.

**Change:** No text change required. Convention confirmed as Python import paths. The example in Section 9.2 already uses `app.inference.fast_model_client`, which is consistent with Python `logging.getLogger(__name__)` usage.

---

### 4. Added `TokenLogprob` to Thread Safety Immutable Objects (Section 8)

**Before:**
```
Core contracts (`RoutingDecision`, `Task`, `RawModelOutput`) must be implemented as read-only dataclasses
```

**After:**
```
Core contracts (`RoutingDecision`, `Task`, `RawModelOutput`, `TokenLogprob`) must be implemented as read-only dataclasses
```

*Rationale:* `TokenLogprob` is a transport model embedded inside `RawModelOutput.tokens`. It is a transport schema and must follow the same `@dataclass(frozen=True)` constraint as all other transport contracts.

---

### 5. Documented `RawModelOutput.tokens` Field Constraints (Section 4.11)

**Before:**
```
`tokens`: `List[TokenLogprob]` (Array of token details and log probability metrics)
```

**After:**
```
`tokens`: `List[TokenLogprob]` (Array of token details and log probability metrics, defined in Section 4.10; always present but may be empty if logprobs are unavailable)
```

*Rationale:* The ROVL implementation in `backend/app/verification/entropy.py` explicitly handles the case of an empty token list as a documented edge condition. Field documentation now reflects this.

---

### 6. Added Section Cross-References for `RawModelOutput` and `VerificationConstraints` (Sections 3.6 and 3.7)

**Section 3.6 (`inference`) — Before:**
```
- **Expected Outputs**: `RawModelOutput`.
```
**After:**
```
- **Expected Outputs**: `RawModelOutput` (defined in Section 4.11).
```

**Section 3.7 (`verification`) — Before:**
```
- **Expected Inputs**: `RawModelOutput` and `VerificationConstraints`.
```
**After:**
```
- **Expected Inputs**: `RawModelOutput` (defined in Section 4.11) and `VerificationConstraints` (defined in Section 4.5).
```

*Rationale:* Improves document navigability for implementers referencing module responsibilities.

---

## No Architectural Changes Confirmation

I explicitly confirm the following:

| Category | Status |
| :--- | :---: |
| **Interfaces changed** | ❌ None |
| **Contracts changed** | ❌ None |
| **Dependency rules changed** | ❌ None |
| **Repository layout changed** | ❌ None |
| **Implementation behaviour changed** | ❌ None |
| **New APIs added or removed** | ❌ None |
| **Routing behaviour altered** | ❌ None |
| **Module responsibilities redesigned** | ❌ None |

All changes are purely documentary: wording clarification, path normalisation, cross-reference links, and thread-safety enumeration completeness.

---

## Automated Validation Results

All 16 automated checks passed against the published document:

| Check | Result |
| :--- | :---: |
| No absolute Windows path | ✅ PASS |
| No `file:///` path | ✅ PASS |
| No legacy entropy in estimators description | ✅ PASS |
| `TokenLogprob` in immutable objects list | ✅ PASS |
| `RawModelOutput` references Section 4.11 | ✅ PASS |
| `VerificationConstraints` references Section 4.5 | ✅ PASS |
| `RawModelOutput.tokens` field has empty-list clarification | ✅ PASS |
| No `TelemetryRecord` in main body | ✅ PASS |
| No `src/app` in main body | ✅ PASS |
| No `schema_type` in main body | ✅ PASS |
| No `min_chars` in main body | ✅ PASS |
| No `max_chars` in main body | ✅ PASS |
| No `failure_reason` in main body | ✅ PASS |
| No stray legacy `entropy` in main body | ✅ PASS |
| Log module example uses Python import path | ✅ PASS |
| Log module example is not a filesystem path | ✅ PASS |

---

## Final Publication Checklist

- ✅ **Section numbering verified** — All section headings 1 through 17 are numbered sequentially and correctly ordered.
- ✅ **Cross-references verified** — `RawModelOutput` and `TokenLogprob` include explicit section anchors. `VerificationConstraints` references Section 4.5. All interface sections refer to correct contract sections.
- ✅ **Repository paths verified** — All paths use `backend/app/*` convention. No `src/app`, `validators/`, `deterministic/`, or `config/` legacy paths remain in the main body.
- ✅ **Naming consistency verified** — Zero occurrences of `CHEAP`, `DENSE`, `CASCADE`, `c2`, `c3`, `local model`, `remote model`, `utility routing`, `ValidationError`, or `ModelUnavailableError` in the main body.
- ✅ **Mermaid diagrams verified** — Both diagrams (Section 13.1 and 13.2) use canonical names only: `SEMANTIC_CACHE`, `FAST_MODEL`, `POWER_MODEL`, `DETERMINISTIC_SOLVER`, `ROVL`, `TelemetryLog`.
- ✅ **Data contracts verified** — `VerificationConstraints`, `VerificationResult`, `TelemetryLog`, `RawModelOutput`, and `TokenLogprob` all match the frozen codebase schemas.
- ✅ **Public interfaces verified** — All eight interface definitions use correct V3 parameter types and canonical names.
- ✅ **Editorial cleanup complete** — No legacy terminology, no OS-specific paths, no mixed conventions remain anywhere in either document.

---

## Final Verdict

**READY FOR IMPLEMENTATION**

`tera_v3_interface_module_contract_specification.md` is published as the authoritative, editorially frozen **Version 3.2** of the TERA V3 Interface & Module Contract Specification and is suitable for permanent inclusion in the TERA V3 documentation set.

---

## Final Approval Statement

✅ Architecture approved  
✅ Editorial review complete  
✅ Validation complete  
✅ Repository portable  
✅ Ready for commit  
✅ Ready for implementation  
