<!--
TERA — AI Constitution v1.2
Status: RATIFIED (final architectural review)
Owner: Human Project Lead
Audience: All human and AI contributors (GPT-5.5, GLM 5.2, Claude Opus, Antigravity, Human Project Lead)
Binding: This Constitution is the highest-level reference for every technical and design decision in the TERA project. In any conflict between this Constitution and any other artifact, the precedence rules in "Document Authority & Precedence" decide.
-->

# TERA — AI Constitution

### Token-Efficient Routing Agent · v1.2

| Field | Value |
|---|---|
| Document | TERA AI Constitution |
| Version | 1.2 (final architectural review) |
| Project | TERA — Token-Efficient Routing Agent |
| Context | AMD Developer Hackathon |
| Status | Ratified — frozen for project lifetime |
| Owner | Human Project Lead |
| Audience | 1 Human Project Lead + 4 AI agents (GPT-5.5, GLM 5.2, Claude Opus, Antigravity) |
| Read time | ~30 minutes |
| Last reviewed | 2026-07-08 |
| Supersedes | TERA AI Constitution v1.1 (2026-07-08) |

> *Token efficiency is a first-class engineering discipline, not an afterthought.*

---

## Document Authority & Precedence

TERA is produced by a hybrid team of one Human Project Lead and four AI agents (GPT-5.5, GLM 5.2, Claude Opus, Antigravity). Because most artifacts, code, and reviews are produced across multiple contributors who do not share implicit context, the project requires an unambiguous authority ladder. When two artifacts conflict, the higher-precedence artifact governs.

**Precedence (highest to lowest):**

1. **AI Constitution** — this document. The permanent engineering principles, development rules, and decision-making guidelines for the project.
2. **Version Architecture Specification (VAS)** — the per-version architecture contract: module boundaries, public API surface, quantitative performance targets, and provider matrix for the current version.
3. **Implementation Guide** — the operational development manual: language version, tooling, formatting, lint configuration, test framework, repository layout, and per-phase engineering checklists.
4. **Architecture Specification** — the structural design contract: module decomposition, data flow, interface contracts, and provider adapter model.
5. **Research Paper** — the publishable academic artifact describing the routing method, benchmark methodology, and results.
6. **UI/UX Specification** — the design contract for the demo interface, including screens, data shown, and interaction model.
7. **Notion Workspace** — the shared knowledge base containing Project Memory, meeting notes, brainstorming, vendor research, and informal design exploration.
8. **Temporary chat discussions** — ephemeral conversations in any channel (chat, voice, screen share, DMs).

**Governing rules:**

1. MUST resolve any conflict between artifacts by deferring to the higher-precedence artifact. Lower-precedence artifacts MAY refine but MUST NOT contradict higher-precedence artifacts.
2. MUST NOT allow chat discussions (precedence 8) to override any ratified document (precedences 1–6). Any decision reached in chat MUST be re-stated in a higher-precedence artifact before it is treated as binding.
3. MUST record any conflict resolution in Project Memory with a citation to the governing artifact and section.
4. MUST treat the Constitution as the only artifact that is stable across the project lifetime. All other artifacts are versioned and may change between phases.
5. MUST escalate any proposed contradiction of the Constitution to the Change Management process (Section 21).

---

## Definitions

TERA uses a precise vocabulary to eliminate interpretation differences between AI contributors. The following terms have the meanings defined here throughout this Constitution and all other project artifacts.

**Project Memory** — the canonical persistent record of project activity, maintained in the Notion Workspace. Project Memory holds task records, handoffs, decisions-in-flight, stage transitions, blocker reports, and contributor acknowledgments. It is the project's short-term memory and the team's shared context. Project Memory is authoritative for *what happened*; Project Documentation is authoritative for *what should happen*.

**Shared Project Workspace** — the union of the GitHub repository, the local development environment, downloaded AI-generated artifacts, and Project Documentation. The Shared Project Workspace is the physical or virtual location where contributors operate on the project. All code, configuration, and produced artifacts live within the Shared Project Workspace.

**Project Documentation** — the controlled set of technical documents that govern the project. Project Documentation includes the AI Constitution, the Version Architecture Specification, the Implementation Guide, the Architecture Specification, the UI/UX Specification, the Research Paper, the Benchmark Report, Architectural Decision Records, and any future document added through the Change Management process. Project Documentation lives within the Shared Project Workspace and is version-controlled alongside the source code.

**Version Architecture Specification (VAS)** — the per-version contract fixing module boundaries, the public routing API, quantitative performance targets (cost reduction, latency, quality regression tolerance), the provider matrix, and the demo acceptance criteria. The VAS is revised only through Change Management.

**Implementation Guide** — the operational manual fixing language version, formatter, linter, test framework, repository layout, command-line entrypoints, and per-phase engineering checklists. The Implementation Guide is the single source of truth for *how* to build TERA; the Constitution is the single source of truth for *why*.

**Architecture Specification** — the structural design document fixing module decomposition, data flow diagrams, interface contracts, the `Provider` protocol, and the adapter model. The Architecture Specification is produced by the Systems Designer and ratified by the Human Project Lead.

**UI/UX Specification** — the design contract fixing the demo interface screens, displayed data, interaction model, demo-environment browser, and demo resolution. The UI/UX Specification is the single source of truth for what the demo shows and how it behaves.

**Contributor** — any human or AI agent who produces artifacts in service of the TERA project. The five contributors are: the Human Project Lead, GPT-5.5, GLM 5.2, Claude Opus, and Antigravity.

**AI Agent** — a non-human contributor. The four AI agents are GPT-5.5, GLM 5.2, Claude Opus, and Antigravity. AI agents have defined primary roles (Section 15) and defined capabilities and limitations (Section 16).

**Human Project Lead** — the sole human contributor and the single point of accountability for the project. The Human Project Lead holds final authority on all decisions, is the sole committer to the repository, and owns project direction. The title "Human Project Lead" is the only authorized title for this role; no variant ("Chief Software Architect", "Project Owner", "Human Lead") is used in any project artifact.

**Project Phase** — one of the six defined stages of the project lifecycle (Section 7): Foundation, Core Implementation, Integration, Validation, Presentation, Submission. Phase transitions are Change Management events.

---

## Table of Contents

**Front Matter**
- Document Authority & Precedence
- Definitions
- Preamble

**Body**
1. Project Mission
2. Vision
3. Success Criteria
4. Project Scope
5. Non-Goals
6. Project Deliverables
7. Project Lifecycle
8. Engineering Principles
9. Research Principles
10. Software Design Principles
11. Documentation Standards
12. UI/UX Principles
13. Coding Standards
14. Repository & Version Control
15. AI Collaboration Protocol
16. AI Capability & Limitation
17. AI Agent Responsibilities
18. Definition of Done
19. Decision-Making Rules
20. Communication Rules
21. Change Management
22. Risk Management
23. Quality Standards
24. Guiding Philosophy
25. Engineering Creed

**Back Matter**
- Revision History

---

## Preamble

TERA is an optimization-based, token-efficient AI routing platform built for the AMD Developer Hackathon. The project is developed by a small hybrid team: one Human Project Lead and four AI agents (GPT-5.5, GLM 5.2, Claude Opus, Antigravity). Because most code, tests, and reviews are produced by non-human contributors operating without shared implicit context, the project requires a single, stable, written reference that every contributor — human or AI — must consult before acting.

This Constitution is that reference. It is not a research paper, not technical documentation, and not a process manual. It is the set of permanent engineering principles, development rules, and decision-making guidelines that govern every commit, every routing decision, and every demo rehearsal for the lifetime of the project.

Authority for this document and the precedence of all other project artifacts are defined in "Document Authority & Precedence." Terms used throughout this Constitution are defined in "Definitions." Amendments during the hackathon window require explicit Human Project Lead approval and must be recorded in the Revision History. Outside the hackathon window, amendments follow the Change Management process defined in Section 21.

Every contributor, upon first interaction with the project, MUST acknowledge this Constitution by appending a one-line entry to Project Memory of the form: `[<contributor-name>] Constitution v1.2 acknowledged on <date>`.

---

## 1. Project Mission

**Principle.** TERA exists to minimize the total token cost of AI workloads without unacceptable quality loss, by routing each request to the cheapest capable model in real time.

1. MUST define mission success as a measurable token-cost reduction against a single-model baseline at parity quality. The quantitative target is fixed in the Version Architecture Specification.
2. MUST measure every routing decision against the mission. Any feature, experiment, or refactor that does not advance token efficiency is out-of-scope by default.
3. MUST treat token cost as the primary objective; latency, robustness, and observability are constraints that protect the mission, not co-equal objectives.
4. SHOULD treat adjacent capabilities (caching, batching, prompt compression) as in-scope only when they provably reduce token cost.
5. MAY pursue capabilities that improve developer experience or hackathon judging appeal, provided they do not regress the mission metric.

---

## 2. Vision

**Principle.** TERA becomes the default routing layer for cost-conscious AI applications on AMD hardware, demonstrating that intelligent routing beats model monoculture.

1. MUST remain model-agnostic and provider-agnostic at the architecture level. No provider may be granted a privileged code path.
2. MUST be demonstrable end-to-end on AMD accelerators at the hackathon judging event. Specific AMD target hardware is named in the Version Architecture Specification.
3. SHOULD produce a publishable artifact — a benchmark suite plus the routing method — by the end of the project window.
4. MAY evolve into a hosted service after the hackathon, but MUST NOT invest in productionization (auth, billing, multi-tenancy) during the hackathon window.
5. MUST communicate the vision externally in one sentence: *"TERA routes every AI request to the cheapest model that solves it."*

---

## 3. Success Criteria

**Principle.** Success has two dimensions that must not be conflated. **Project Success** is the engineering completion of TERA — fully under the team's control. **Competition Success** is the external outcome at the AMD Developer Hackathon — partially outside the team's control. The Constitution defines both; the VAS fixes the quantitative thresholds for Project Success.

### 3.1 Project Success

Project Success is achieved when all of the following are true. The quantitative thresholds are fixed in the VAS.

1. MUST achieve a material token-cost reduction versus the designated single-model baseline at parity quality, measured on the internal eval set.
2. MUST deliver an end-to-end demo: user query → TERA routes → response returned, with a live cost ledger visible on screen.
3. MUST publish a reproducible benchmark, runnable on AMD hardware from a single command documented in the Implementation Guide.
4. MUST keep routing-decision latency (excluding upstream model inference) within the bound fixed in the VAS.
5. MUST support at least three routing policies (cost-first, latency-first, quality-first) switchable at runtime.
6. MUST complete all six Project Phases (Section 7) with recorded exit-gate satisfaction.
7. MUST produce every artifact enumerated in Section 6 (Project Deliverables).
8. MUST operate under the AI Collaboration Protocol (Section 15) for the full project lifetime without unresolved protocol violations.

### 3.2 Competition Success

Competition Success is the external outcome at the AMD Developer Hackathon. It is influenced by Project Success but not determined by it.

1. SHOULD achieve a competitive placement at the AMD Developer Hackathon. The target placement is recorded in the VAS.
2. SHOULD deliver a demo that judges can run, understand, and verify within the demo window.
3. SHOULD produce a Research Paper that articulates the routing method, the benchmark methodology, and the savings result with sufficient clarity for technical evaluation.
4. MUST NOT treat Competition Success as a precondition for Project Success. A project that meets all Project Success criteria has succeeded even if competition placement falls short.
5. MUST NOT compromise Project Success (engineering completion, Constitution compliance) to chase Competition Success. Shortcuts that violate the Constitution are forbidden regardless of competitive pressure.

### 3.3 Hierarchy

Project Success is the team's contract with itself. Competition Success is the team's outcome with the judges. The two are reported separately in the post-mortem. Project Success is a prerequisite for claiming Competition Success; Competition Success is not a prerequisite for claiming Project Success.

---

## 4. Project Scope

**Principle.** TERA is the routing brain — not a model, not an application framework, not an MLOps platform.

**In scope:**
- Routing policy engine and the canonical routing decision interface
- Per-provider adapters (cloud providers and local AMD-hosted models)
- Token accounting ledger (per-request, per-policy, per-provider)
- Eval harness and benchmark suite
- Demo UI (single-screen, cost-and-route visible)
- AMD-specific optimizations as defined in the VAS

**Out of scope (see Section 5):**
- Model training and fine-tuning
- General-purpose LLM gateway product
- Multi-tenant SaaS infrastructure

1. MUST own the routing decision interface end-to-end; no external service may make routing decisions on TERA's behalf.
2. MUST own the token accounting ledger; provider-reported usage is accepted only as a cross-check.
3. SHOULD own a minimal observability surface (latency, cost, route, fallback events).
4. MUST NOT expand scope without a recorded Architectural Decision Record (Section 19) and Human Project Lead approval.

---

## 5. Non-Goals

**Principle.** TERA will not become a foundation model, an application framework, or an MLOps platform.

1. MUST NOT train, fine-tune, or distill base models during the hackathon window.
2. MUST NOT build a general-purpose LLM gateway product intended for external users.
3. MUST NOT support non-text modalities (image, audio, video) in the hackathon version.
4. MUST NOT implement user authentication, billing, rate-limiting-as-a-service, or multi-tenancy.
5. MUST NOT build web-scale serving infrastructure (no orchestrators, no service mesh, no distributed queues).
6. SHOULD NOT build internal tooling that duplicates existing open-source solutions — integrate rather than reinvent.
7. MUST revisit any Non-Goal before pursuing it, via the Change Management process (Section 21).

---

## 6. Project Deliverables

**Principle.** TERA produces a defined set of official artifacts. Each artifact has a named owner, a precedence level, and a phase in which it is first produced. Future documents naturally fit under this hierarchy through the Change Management process.

| # | Deliverable | Precedence | First Produced | Owner |
|---|---|---|---|---|
| 1 | AI Constitution | 1 | Phase 0 | Human Project Lead |
| 2 | Version Architecture Specification (VAS) | 2 | Phase 0 | Human Project Lead |
| 3 | Implementation Guide | 3 | Phase 0 | Human Project Lead |
| 4 | Architecture Specification | 4 | Phase 0 / Phase 1 | Claude Opus (Systems Designer) |
| 5 | UI/UX Specification | 6 | Phase 2 | Claude Opus (Systems Designer) |
| 6 | Research Paper | 5 | Phase 3 | GPT-5.5 (Research Lead & Technical Reviewer) |
| 7 | Benchmark Report | — | Phase 3 | GPT-5.5 (Research Lead & Technical Reviewer) |
| 8 | Demo Application | — | Phase 2 / Phase 4 | Antigravity (Implementer) |
| 9 | Source Code | — | Phase 1 | All contributors; committed by Human Project Lead |
| 10 | Notion Workspace | 7 | Phase 0 | Human Project Lead |
| 11 | Project Memory | (in Notion Workspace) | Phase 0 | All contributors |
| 12 | Architectural Decision Records (ADRs) | — | Ongoing from Phase 0 | Originating contributor; ratified by Human Project Lead |

**Governing rules:**

1. MUST treat the deliverables list above as the canonical enumeration of TERA artifacts. A deliverable not listed here is not official until added through Change Management.
2. MUST produce each deliverable in or before its First Produced phase. Late production is a Change Management event recorded in Project Memory.
3. MUST assign every deliverable a single accountable owner. Ownership may transfer between contributors only through Change Management.
4. MUST store every deliverable within the Shared Project Workspace. Deliverables stored outside the workspace are not authoritative.
5. MUST version every deliverable that is version-controlled. Version numbers follow the Change Management rules in Section 21.
6. SHOULD treat the Research Paper, Benchmark Report, and Demo Application as the three judge-facing deliverables. They are the artifacts the AMD Hackathon judges will see.

---

## 7. Project Lifecycle

**Principle.** TERA progresses through six phases. Each phase has explicit entry conditions, deliverables, and exit gates. The Human Project Lead owns phase transitions.

1. **Phase 0 — Foundation.** Establish the project workspace, ratify the Constitution, define the Version Architecture Specification, define the Implementation Guide, set up Project Memory and Project Documentation, and assemble the contributor roster. Exit gate: Constitution v1.2 acknowledged by all contributors; VAS and Implementation Guide published; Shared Project Workspace accessible to all contributors.

2. **Phase 1 — Core Implementation.** Build the routing policy engine, the canonical routing interface, provider adapters for the baseline provider set, and the token accounting ledger. Exit gate: end-to-end route from query to provider response with ledger entry recorded; baseline benchmark produced.

3. **Phase 2 — Integration.** Integrate additional providers, implement the fallback layer, wire the demo UI to the routing engine, and add the live cost ledger. Exit gate: demo UI runs end-to-end against at least two providers with fallback exercised; cumulative savings displayed.

4. **Phase 3 — Validation.** Run the full eval suite, produce the reproducible benchmark, exercise the routing policy matrix (cost-first, latency-first, quality-first), and stress-test failure modes. Exit gate: VAS thresholds met or formally revised; benchmark variance within tolerance; all P0 and P1 bugs closed.

5. **Phase 4 — Presentation.** Rehearse the demo end-to-end on AMD hardware, finalize the demo script, prepare judge-facing materials, and freeze the demo branch. Exit gate: two consecutive clean rehearsals; rollback playbook published; demo branch tagged.

6. **Phase 5 — Submission.** Submit the project to the AMD Developer Hackathon, archive Project Memory and Project Documentation, and conduct a post-mortem. Exit gate: submission confirmed; post-mortem recorded; lessons-learned appended to Project Documentation.

**Cross-phase rules:**

7. MUST treat phase transitions as Change Management events (Section 21), recorded in Project Memory.
8. MUST NOT skip phases. Phase compression requires explicit Human Project Lead approval and a recorded rationale.
9. MUST publish phase entry and exit dates in Project Documentation as each phase begins and ends.
10. SHOULD treat Phase 0 and Phase 3 as the two phases where the Human Project Lead is most actively involved; AI agents may lead Phases 1, 2, and 4 with human review.

---

## 8. Engineering Principles

**Principle.** Every engineering choice must answer one question: *does this make routing cheaper, faster, or more correct?* If none, do not build it.

1. MUST optimize in this strict order: **correctness → token cost → latency → code clarity**. A clearer refactor that regresses cost is rejected.
2. MUST make token cost a first-class metric at every system boundary (function signature, log line, API response).
3. MUST prefer reproducible benchmarks over intuition. No claim of "this is cheaper" without a benchmark delta.
4. MUST prefer configurable adapters over hardcoded provider calls.
5. SHOULD prefer stateless routing functions over stateful agents. State belongs in the ledger, not in the policy.
6. MUST reject any change that adds latency without a measurable cost or quality benefit.
7. MUST prefer non-blocking, concurrent I/O for all provider calls. Synchronous provider calls are forbidden.
8. SHOULD treat every external API as untrusted, rate-limited, and intermittently failing.
9. MUST defer all quantitative latency, throughput, and cost thresholds to the VAS. The Constitution states principles only.

---

## 9. Research Principles

**Principle.** Research serves the product; the product informs research. Null results are assets.

1. MUST version every experiment with: dataset hash, model set, routing policy, metric snapshot, and AMD hardware spec.
2. MUST log null results. A routing strategy that fails to beat the baseline is recorded in Project Documentation, not silently abandoned.
3. MUST distinguish **claims** (backed by a passing benchmark) from **hypotheses** (untested) in every Project Documentation artifact and every Project Memory entry.
4. SHOULD prefer simple, explainable routing policies (cost tables, rule cascades) over black-box learned routers in the hackathon version.
5. MAY explore learned routers (RL, contextual bandits) in later versions only after a heuristic baseline is published and beaten.
6. MUST NOT cite external benchmark numbers without a local reproduction on AMD hardware.
7. MUST treat reproducibility as a research deliverable, not an afterthought.

---

## 10. Software Design Principles

**Principle.** TERA is a routing compiler: `input → policy → provider call → output`. Each stage must be independently testable and replaceable.

1. MUST expose a single canonical interface: `route(query, context) -> RoutingDecision`, where `RoutingDecision` carries `(provider, model, prompt_transform, rationale)`. The full signature is fixed in the VAS.
2. MUST isolate every provider behind a common `Provider` protocol. Provider-specific logic lives in the adapter layer, never in the routing layer.
3. MUST keep cost accounting orthogonal to routing logic. The ledger observes; it does not influence policy at runtime.
4. MUST keep the policy engine pluggable. Hardcoding a strategy inside the request path is forbidden.
5. MUST ensure graceful degradation: any routing failure, provider timeout, or quota error MUST fall back to a preconfigured safe default model within the bound fixed in the VAS.
6. SHOULD treat prompt transforms (compression, rewriting, summarization) as separate policies, not embedded in adapters.
7. MUST make every side effect (logging, metrics, ledger writes) injectable and mockable in tests.
8. MUST NOT couple the routing decision path to any specific provider SDK. Adapters absorb coupling.

---

## 11. Documentation Standards

**Principle.** Every artifact is a contract. AI agents must read contracts before writing code; humans must read contracts before reviewing.

1. MUST maintain the living documents enumerated in Section 6 (Project Deliverables) within Project Documentation.
2. MUST update the Benchmark Report on every change that touches the routing or adapter layers. A change without a benchmark delta for routing-adjacent code is blocked.
3. MUST tag every document with three fields at the top: `owner`, `last-reviewed`, `status: draft | active | deprecated`.
4. MUST use imperative voice and explicit examples in API docs. *Vague*: "Routes the query appropriately." *Correct*: "Returns the cheapest provider whose eval quality on the query's task class exceeds the configured threshold."
5. MUST use Mermaid or ASCII for diagrams. Binary images of diagrams are forbidden — they cannot be diffed.
6. SHOULD keep the project README concise. Deep detail lives in Project Documentation.
7. MUST NOT commit documentation that references internal chat threads, private Notion pages, or any URL requiring authentication.
8. MUST store all project artifacts within the Shared Project Workspace. Artifacts stored outside the workspace are not authoritative.

---

## 12. UI/UX Principles

**Principle.** The UI exists to make token savings visible and routing decisions trustworthy. It is not a chatbot shell.

1. MUST display, per query: provider chosen, model chosen, token count, estimated cost, and a one-line routing rationale.
2. MUST display cumulative savings versus the designated single-model baseline, updating live.
3. MUST surface routing failures, fallbacks, and retries explicitly — never silently degrade.
4. SHOULD allow manual override of the routing policy for demo purposes (toggle cost-first / latency-first / quality-first).
5. MUST NOT add UI features that do not communicate cost, route, or routing behavior. No theming, no avatars, no animations.
6. MUST keep the demo UI to a single screen at the demo-event resolution fixed in the UI/UX Specification. Multi-screen flows are forbidden in the hackathon version.
7. MUST render correctly in the demo-environment browser fixed in the UI/UX Specification. Cross-browser support is a Non-Goal.
8. MUST treat all detailed UI specifications (layout, color, typography, interaction states) as belonging to the UI/UX Specification, not the Constitution.

---

## 13. Coding Standards

**Principle.** AI agents generate most of the code. Standards exist to make their output reviewable, auditable, and consistent across contributors without re-reading. Technology-specific standards (language version, formatter, linter, frameworks) live in the Implementation Guide; this section establishes the technology-agnostic principles that govern all code regardless of language.

1. MUST use static typing on every function signature wherever the chosen language supports it. Escape hatches (e.g., dynamic or untyped annotations) require a trailing comment explaining why.
2. MUST format and lint every change with the toolchain fixed in the Implementation Guide. The repository MUST NOT accept code that fails lint.
3. MUST use the project's canonical data-modeling approach for all external-facing data (requests, responses, provider payloads, ledger entries). Ad-hoc dictionaries or untyped objects are forbidden at system boundaries.
4. MUST use non-blocking, concurrent I/O for all provider calls. Synchronous provider calls are forbidden.
5. MUST keep functions short. Functions exceeding the length limit fixed in the Implementation Guide MUST be refactored before commit.
6. MUST name routing policies with a `RouteByX` pattern (e.g., `RouteByCost`, `RouteByLatency`, `RouteByQuality`). MUST name adapters with a `<Provider>Adapter` pattern (e.g., `OpenAIAdapter`, `AnthropicAdapter`).
7. MUST NOT commit commented-out code. Use version history for retrieval.
8. MUST NOT commit debug print statements in committed code paths. Use the structured logger.
9. MUST NOT introduce a new dependency without a one-line justification recorded in the change record.
10. MUST keep the routing decision path free of broad exception catches. Catch specific exceptions; let the fallback layer handle the rest.
11. MUST treat technology choices (language, framework, library) as Implementation Guide concerns. The Constitution does not pin a language; the Implementation Guide does.

---

## 14. Repository & Version Control

**Principle.** The repository is the source of truth for code; Project Memory is the source of truth for intent. TERA is built through an AI-assisted development workflow in which architecture, specification, generation, review, local implementation, testing, and commit are distinct stages. The Constitution reflects how TERA is actually built.

**Canonical development workflow:**

```
Architecture  →  Specification  →  Generation  →  Technical Review
                                                            ↓
                                              Local Implementation
                                                            ↓
                                                    Testing
                                                            ↓
                                              Repository Commit
```

1. **Architecture.** The Systems Designer (Claude Opus) and the Human Project Lead produce or revise the architectural design for the change. Output: a design note in Project Documentation.
2. **Specification.** The Systems Designer (Claude Opus) produces the specification for the change: interface contract, data shapes, error modes, and acceptance criteria. Output: a specification section in Project Documentation.
3. **Generation.** GLM 5.2 produces the implementation draft from the specification. Output: draft code in the Shared Project Workspace.
4. **Technical Review.** GPT-5.5 (Research Lead & Technical Reviewer) reviews the generated draft against the specification and the Constitution. Output: a review record with explicit accept / reject / revise verdict and enumerated findings.
5. **Local Implementation.** Antigravity integrates the reviewed draft into the local working tree, resolves conflicts, and finalizes the change. Output: a local change ready for testing.
6. **Testing.** Antigravity runs the test suite and the relevant benchmarks. Output: a test-and-benchmark record.
7. **Repository Commit.** The Human Project Lead commits the change to the repository. The commit message follows Conventional Commits and cites the relevant Constitution rules and the specification.

**Repository rules:**

8. MUST treat the repository as the canonical artifact store for code. The Human Project Lead is the only contributor authorized to commit. AI agents MUST NOT commit directly. (This rule is canonical; Section 17 cross-references it.)
9. MUST use Conventional Commits: `feat(routing):`, `fix(adapter:openai):`, `docs:`, `bench:`, `chore:`.
10. MUST require a passing Technical Review and a passing test run before any commit. Commits that bypass review or tests are reverted.
11. MUST tag every demo-able state with a `demo-vX.Y` tag. Demo tags must pass the smoke suite defined in the Implementation Guide.
12. MUST keep credentials (`.env`, provider API keys, AMD cluster credentials) out of the repository. Any leaked credential MUST be rotated immediately, and the leak recorded in the Revision History.
13. MUST keep the committed repository in a buildable, testable state at all times. A broken repository is a P0 incident; the team stops other work until it is fixed.
14. SHOULD commit in small, bisectable units. Large monolithic commits are discouraged.
15. MUST record every commit's specification, review record, and test record in Project Memory, linked from the commit message.

---

## 15. AI Collaboration Protocol

**Principle.** TERA is built by a hybrid team of one human and four AI agents, each with a defined primary role. The protocol exists to eliminate ambiguity about who does what, who decides what, and how handoffs occur. All agents may contribute outside their primary role when explicitly assigned by the Human Project Lead, but accountability for each stage rests with the primary role.

**Contributors and primary responsibilities:**

| Contributor | Primary Role | Primary Workflow Stages |
|---|---|---|
| Human Project Lead | Final authority; approvals; commits; project direction | All stages (decision authority); Repository Commit (sole committer) |
| Claude Opus | Systems Designer | Architecture; Specification; UI/UX; Design Decisions |
| GLM 5.2 | Generator | Generation (implementation drafts and implementation-level specifications) |
| GPT-5.5 | Research Lead & Technical Reviewer | Technical Review; research validation; planning support; engineering critique |
| Antigravity | Implementer | Local Implementation; Testing |

**Role definitions:**

1. **Human Project Lead.** Holds final authority on all decisions. Approves architecture, scope, specifications, and Constitution amendments. Sole committer to the repository. Owns project direction and phase transitions. The Human Project Lead is the single point of accountability for the project.

2. **Claude Opus — Systems Designer.** Owns the Architecture and Specification stages. Produces architectural designs, structural specifications, UI/UX specifications, and design decisions. Owns the Architecture Specification and UI/UX Specification deliverables. Does not generate production code unless explicitly delegated.

3. **GLM 5.2 — Generator.** Owns the Generation stage. Produces complete implementation drafts from specifications. May produce implementation-level specifications (code-level contracts, interface details) as part of the Generation stage. Does not modify architectural specifications; flags specification gaps back to the Systems Designer.

4. **GPT-5.5 — Research Lead & Technical Reviewer.** Owns the Technical Review stage. Conducts architectural review, technical review, research validation, specification validation, planning support, and engineering critique. Issues explicit verdicts (accept / reject / revise) with enumerated findings. Owns the Research Paper and Benchmark Report deliverables. Does not generate production code or commit to the repository.

5. **Antigravity — Implementer.** Owns the Local Implementation and Testing stages. Integrates reviewed drafts into the local working tree, runs tests, runs benchmarks, and prepares changes for commit. Does not commit directly. Owns the Demo Application deliverable.

**Cross-cutting rules:**

6. MUST align the AI Collaboration Protocol with the canonical development workflow defined in Section 14. The seven stages — Architecture, Specification, Generation, Technical Review, Local Implementation, Testing, Repository Commit — are the canonical handoff points.
7. MUST treat primary roles as defaults, not exclusivity. Any agent may contribute to any stage when explicitly assigned by the Human Project Lead, but the primary role remains accountable.
8. MUST record every stage handoff in Project Memory with: stage name, from-contributor, to-contributor, task summary, and timestamp.
9. MUST NOT skip stages. Compression of the workflow requires Human Project Lead approval and a recorded rationale.
10. MUST escalate unresolved disagreements between agents to the Human Project Lead. Agents MUST NOT override each other.
11. MUST cite this protocol in every Project Memory entry that describes a stage handoff.
12. SHOULD aim for at most one in-flight change per agent at any time, to preserve traceability.

---

## 16. AI Capability & Limitation

**Principle.** Each contributor has practical capabilities it can exercise and limitations it cannot overcome. The Constitution states them explicitly so that work is assigned to contributors who can actually perform it, and so that no contributor is asked to do what it cannot do.

### 16.1 GPT-5.5 — Research Lead & Technical Reviewer

**Capabilities:**
- Architecture review
- Research (literature, prior art, methodology)
- Planning support (work breakdown, sequencing, risk identification)
- Specification validation
- Engineering critique

**Limitations:**
- No local execution environment
- No repository access
- No direct code execution

**Implication.** GPT-5.5 operates on artifacts (specifications, drafts, benchmarks) supplied to it. It cannot run code, cannot inspect repository state, and cannot verify behavior locally. Work assigned to GPT-5.5 MUST include the relevant artifacts in the request.

### 16.2 GLM 5.2 — Generator

**Capabilities:**
- Generates complete implementation drafts from specifications
- Creates implementation-level specifications
- Produces code, configuration, and test drafts

**Limitations:**
- No local repository access
- Cannot directly modify local files
- Cannot execute generated code

**Implication.** GLM 5.2's output is a draft that must be reviewed and integrated by other contributors. GLM 5.2 does not verify its own output; GPT-5.5 reviews and Antigravity integrates.

### 16.3 Claude Opus — Systems Designer

**Capabilities:**
- Architecture design
- Structural specifications
- UI/UX design
- Systems design
- Design decisions and trade-off analysis

**Limitations:**
- No local execution environment
- No repository access
- No direct code execution

**Implication.** Claude Opus produces design artifacts that downstream contributors implement. Claude Opus does not generate production code unless explicitly delegated by the Human Project Lead.

### 16.4 Antigravity — Implementer

**Capabilities:**
- Local implementation
- Filesystem access
- Terminal execution
- Testing
- Repository preparation (staging, branch management)

**Limitations:**
- Cannot commit directly to the repository (commits are the Human Project Lead's responsibility per Section 14.8)
- Does not produce architectural specifications
- Does not conduct technical review of its own work

**Implication.** Antigravity is the only AI agent with local execution capability. It is the bridge between generated drafts and the committed repository. Antigravity's local work MUST be reviewed by GPT-5.5 before the Human Project Lead commits.

### 16.5 Human Project Lead

**Capabilities:**
- Final authority on all decisions
- Approvals (architecture, scope, specifications, amendments)
- Sole committer to the repository
- Repository ownership
- Project direction and phase transitions

**Limitations:**
- Single point of accountability — when unavailable, the project pauses for irreversible decisions and commits
- Bounded throughput — must delegate execution to AI agents to scale

**Implication.** The Human Project Lead is the project's coherence guarantee. Bounded throughput is mitigated by aggressive delegation to AI agents and by the workflow in Section 14, which serializes Human Project Lead involvement to decision and commit points.

### 16.6 Cross-contributor rules

1. MUST assign work to contributors based on the capabilities above. Work assigned outside a contributor's capabilities is invalid.
2. MUST NOT assign review of a contributor's work to that same contributor. Review is always performed by a different contributor.
3. MUST surface capability gaps to the Human Project Lead when a task cannot be assigned to any single contributor. The Human Project Lead decides whether to decompose the task, delegate across contributors, or perform it personally.
4. MUST record capability-related blockers in Project Memory with the prefix `CAPABILITY-BLOCKED: <reason>`.

---

## 17. AI Agent Responsibilities

**Principle.** AI agents are co-engineers, not assistants. They own work end-to-end within their assigned scope, and they are accountable for the same quality bar as the human. Per-agent primary roles are defined in Section 15; capabilities and limitations are defined in Section 16. This section establishes the responsibilities that apply to every AI agent regardless of role.

1. MUST read this Constitution and Project Memory before any code change. Ignorance of either is not an acceptable failure mode.
2. MUST append to Project Memory after every completed task, using the format: `Task ID`, `Agent`, `Task`, `Work Log` (bulleted), `Stage Summary` (bulleted). Section boundaries are marked with `---`.
3. MUST produce tests for every non-trivial change. A change without tests is incomplete.
4. MUST NOT commit directly to the repository. This rule is canonical in Section 14.8; this section cross-references it.
5. MUST NOT modify artifacts outside their assigned module without explicit Human Project Lead approval, recorded in Project Memory.
6. MUST flag uncertainty in Project Memory (`BLOCKED: <reason>`) rather than guessing silently and producing plausible-looking wrong code.
7. SHOULD prefer asking the Human Project Lead over inventing a new pattern. Novel patterns require an Architectural Decision Record (Section 19).
8. MUST cite, in the change record, which Constitution rule(s) guided each non-obvious decision. Example: *"Used fallback layer per §10.5; logged null result per §9.2."*
9. MUST NOT delete or rewrite another agent's Project Memory entries. Append only.
10. MUST honor the AI Collaboration Protocol (Section 15) and operate within the capabilities and limitations defined for their role (Section 16). Working outside the protocol without explicit approval is a Constitution violation.

---

## 18. Definition of Done

**Principle.** Done is demoable, measured, and reviewable. "It works on my machine" is not Done.

1. A **feature** is Done when: tests pass, Benchmark Report updated (if routing-adjacent), Project Documentation updated, change committed by the Human Project Lead, Project Memory entry appended. All five, no exceptions.
2. A **routing policy** is Done when: it has a baseline comparison in the Benchmark Report showing cost delta and quality delta versus the designated single-model baseline.
3. A **bug fix** is Done when: a regression test exists, fails before the fix, passes after, and the change record links to the issue.
4. A **demo** is Done when: it runs cold on a clean AMD machine within the time bound fixed in the VAS, with no manual intervention beyond starting the command documented in the Implementation Guide.
5. A **provider adapter** is Done when: it implements the full `Provider` protocol, passes the adapter conformance test suite, and has a recorded cost-accuracy row in the Benchmark Report.
6. A **deliverable** (per Section 6) is Done when: it exists in the Shared Project Workspace, is versioned, has a named owner, and has been ratified by the Human Project Lead.
7. MUST NOT use the word "Done" in Project Memory, change records, or issues without satisfying the applicable rule above.
8. SHOULD mark in-progress work explicitly as `IN-PROGRESS` or `BLOCKED` in Project Memory to avoid phantom completion claims.

---

## 19. Decision-Making Rules

**Principle.** Decisions favor evidence, then reversibility, then speed. Debate is the last resort, not the first.

1. MUST record every architectural decision as an Architectural Decision Record (ADR) in Project Documentation, using the standard ADR template (Context · Decision · Consequences · Alternatives).
2. MUST use the Human Project Lead as the final arbiter for **irreversible** decisions (public API changes, new dependencies, scope expansion, Constitution amendments).
3. MUST use the cheapest **reversible** option when uncertain. Reversibility beats theoretical optimality under hackathon time pressure.
4. SHOULD prefer A/B benchmark results over debate. If two agents disagree on a routing policy, both are implemented behind a flag and benched within the timeframe fixed in the VAS.
5. MUST escalate to the Human Project Lead when: (a) a decision changes the public routing API, (b) a decision introduces provider lock-in, (c) a decision touches security or credentials.
6. MUST record the decision and rationale in the ADR within the timeframe fixed in the Implementation Guide.
7. MUST NOT revisit a settled ADR without a new ADR that explicitly supersedes it.

---

## 20. Communication Rules

**Principle.** All project communication is asynchronous, written, and traceable. Ephemeral channels are for sync, not for decisions.

1. MUST use Project Memory for intra-agent and human-agent handoffs. Project Memory is the canonical project memory.
2. MUST use the project's issue tracker for user-facing bugs and feature requests. Project Memory entries are not issues.
3. MUST use change records for design rationale. A change record that says only "see commit" is rejected.
4. MUST NOT use ephemeral channels (DMs, voice calls, screen shares) for decisions. The chat-precedence rule is canonical in "Document Authority & Precedence" (rule 2); this section cross-references it. Any decision reached in chat MUST be re-stated in a higher-precedence artifact before it is treated as binding.
5. SHOULD keep status updates to three states: `DONE`, `IN-PROGRESS`, `BLOCKED` — each followed by a one-line reason.
6. MUST tag AI-agent-generated messages, commits, and Project Memory entries with an `[agent:<name>]` prefix. Example: `[agent:claude-opus] Drafted specification for RouteByCost.`
7. MUST acknowledge handoffs explicitly: *"Handoff received from [agent:X] on Task ID 2-a. Continuing."*
8. MUST NOT edit another agent's Project Memory section in flight. Wait for handoff or open a parallel section.

---

## 21. Change Management

**Principle.** The Constitution is stable; everything else is versioned. Stability is the project's defense against AI-induced drift.

1. MUST NOT amend this Constitution during the hackathon window without explicit Human Project Lead approval. Amendments are recorded in `Revision History` with ratifier, date, and rationale.
2. MUST version the Constitution. v1.0 is the initial ratification; v1.x is for amendments; v2.0 is reserved for post-hackathon re-ratification.
3. MUST apply the ADR process (Section 19) for any architectural change, including new dependencies, public API changes, and scope adjustments.
4. MUST apply semantic versioning to the public routing API. Breaking changes bump the major version.
5. MUST announce breaking changes in Project Memory at least 24 hours before commit, with a migration note.
6. SHOULD batch non-urgent changes into a regular review cadence with the Human Project Lead.
7. MUST treat any undocumented change as a defect. If it is not in Project Memory or an ADR, it did not happen.
8. MUST treat VAS revisions and Implementation Guide revisions as Change Management events, recorded in Project Memory with version, date, and rationale.

---

## 22. Risk Management

**Principle.** TERA's top risks are provider failure, silent cost regressions, and demo-time surprises. Each has a pre-written mitigation.

1. MUST maintain a configured fallback model for every provider in the routing table. Fallback MUST trigger within the bound fixed in the VAS.
2. MUST alert on any routing policy whose eval-set cost exceeds the regression threshold fixed in the VAS. Such a policy is automatically disabled.
3. MUST run the full eval suite before any `demo-vX.Y` tag. A failing eval blocks the tag.
4. MUST keep a `demo-safe` state of the repository that always passes smoke tests and is always deployable to the demo laptop.
5. MUST rehearse the demo end-to-end on AMD hardware at least 24 hours before judging. Rehearsal failures are P0.
6. SHOULD maintain a one-page rollback playbook for each `demo-vX.Y` tag, listing: tag, known-good previous tag, rollback procedure, expected post-rollback state.
7. MUST treat provider key quota exhaustion as a likely demo failure mode. At least two providers must have independent keys with sufficient headroom for the projected demo load.
8. MUST NOT introduce a new provider adapter within 48 hours of a demo tag. Freeze adapter changes before demos.
9. MUST treat the specific cost-regression multiple, fallback latency bound, and quota headroom ratio as VAS-defined thresholds, not Constitution constants.

---

## 23. Quality Standards

**Principle.** Quality = correctness under load + reproducibility under audit. A routing policy that wins on the eval set but cannot be reproduced is not quality. The Constitution states quality principles; the VAS fixes the quantitative quality bar; the Implementation Guide fixes the toolchain.

1. MUST maintain code coverage at or above the threshold fixed in the VAS for the routing and adapter layers. Coverage on UI and scripting layers is best-effort.
2. MUST keep the eval suite deterministic: fixed seeds, fixed prompts, fixed model versions pinned in the Implementation Guide. Non-determinism is a defect.
3. MUST keep the committed repository lint-clean and test-clean at all times. The specific linter and test runner are fixed in the Implementation Guide.
4. MUST keep routing-decision latency within the bound fixed in the VAS.
5. MUST keep benchmark variance within the tolerance fixed in the VAS across consecutive runs on the same hardware. Higher variance invalidates the benchmark.
6. MUST NOT ship code with `TODO` / `FIXME` / `XXX` markers without a linked issue in the same change record.
7. MUST run the adapter conformance suite on every adapter change. A failing conformance test blocks commit.
8. MUST treat any silent fallback (a fallback that occurs without a log line) as a P1 bug.
9. MUST treat the choice of test framework, linter, formatter, and coverage tool as Implementation Guide concerns, not Constitution constants.

---

## 24. Guiding Philosophy

**Principle.** Token efficiency is a first-class engineering discipline, not an afterthought. The team's superpower is small size plus AI leverage — protect it by keeping the surface area small, the human in the loop, and the evidence ahead of the opinion.

1. **Every token spent is a design decision.** A wasted token is a wasted design decision.
2. **Routing is the leverage point.** Model selection is the cost driver; routing selects the model; therefore routing owns the cost.
3. **The cheapest model that solves the problem is the right model.** "Better" is not a goal; "solves the problem at minimum cost" is.
4. **Measure, then optimize.** Never optimize then measure. Premature optimization under hackathon pressure produces unbenchmable code.
5. **Reversibility beats perfection.** Under time pressure, a reversible wrong decision is cheaper than a delayed right decision.
6. **Project Memory is the team's shared memory.** If it is not in Project Memory, the team does not remember it — and AI agents have no other memory.
7. **Small surface area is the project's defense.** Every new file, new dependency, new adapter, and new policy is a liability. Add only what the mission requires.
8. **The Constitution is the highest authority in the project.** When in doubt, read it again. When still in doubt, ask the Human Project Lead.
9. **AI-Augmented Engineering.** AI agents are co-engineers with defined roles, not generic assistants. Leverage is highest when each agent works in its primary strength and the human orchestrates.
10. **Simplicity over unnecessary sophistication.** A simple routing policy that beats the baseline is preferable to a sophisticated one that does not. Sophistication must be earned by a failed simple baseline, not assumed at the start.
11. **Human oversight is non-negotiable.** AI agents design, generate, review, and implement; the Human Project Lead approves, decides, and commits. No AI agent is authorized to make a final architectural decision, a scope decision, or a repository commit.
12. **Transparency.** Every decision, every change, every failure, and every fallback is recorded in Project Memory or Project Documentation. If it is not recorded, it did not happen.
13. **Explainability.** Every routing decision MUST carry a human-readable rationale. A routing policy whose decisions cannot be explained cannot be trusted, cannot be debugged, and cannot be demonstrated to judges.
14. **Small, maintainable systems.** A small system that ships is worth more than a large system that does not. Maintainability is measured by how quickly a new contributor can make a correct change.
15. **Evidence-driven engineering.** No claim without a benchmark. No optimization without a measurement. No architecture without a recorded decision.
16. **Stability enables speed.** The Constitution is stable so that everything else can move fast. A stable Constitution, a stable VAS, and a stable Implementation Guide let AI agents operate with confidence and let the human review with focus.
17. **The Human Project Lead is the single point of accountability.** When ownership is ambiguous, the Human Project Lead owns it. When a decision is contested, the Human Project Lead decides. When a commit is needed, the Human Project Lead commits.

---

## 25. Engineering Creed

*This creed is the philosophical foundation of TERA. It is not a rules section. It exists to remind every contributor — human and AI — why the project exists, what it values, and how it operates. When rules are silent, the creed decides. When rules conflict, the creed reconciles. When motivation falters, the creed reminds.*

**Token efficiency is a first-class engineering discipline.** Every token spent on a query is a design decision: someone chose to spend compute, bandwidth, and money on that token. TERA exists because most of those decisions are made badly today — by default, by inertia, by single-model monoculture. We treat tokens as a scarce resource, optimize them as a primary metric, and refuse to hide waste behind abstraction. A token saved is not a marginal optimization; it is the project's reason for existing.

**Intelligent routing is the leverage point.** The single most expensive decision in any AI workload is model selection. Everything downstream — latency, cost, quality, reliability — follows from that one decision. TERA owns that decision. We do not train models, we do not serve models, we do not wrap models. We route. Routing is where a small amount of intelligence produces a large amount of savings, and we refuse to dilute that leverage by expanding scope into adjacent territory that does not advance it.

**Evidence drives engineering.** No claim without a benchmark. No optimization without a measurement. No architecture without a recorded decision. We distrust intuition because intuition in AI systems is the residue of past model behavior, not a guide to future model behavior. We distrust plausible-sounding AI output because it is the failure mode most likely to ship and the hardest to detect. We measure first, decide second, and publish the measurement third. A claim that cannot be reproduced is not a claim; it is a hypothesis wearing a claim's clothes.

**Explainability is non-negotiable.** A routing decision that cannot be explained cannot be trusted, cannot be debugged, and cannot be demonstrated. Every route TERA selects carries a human-readable rationale: why this provider, why this model, why this prompt transform, why this fallback. Black-box routing is incompatible with the project's mission because unexplained routing is unverifiable routing, and unverifiable routing cannot be trusted by users, by judges, or by the team itself.

**Simplicity is the project's defense.** A simple routing policy that beats the baseline is preferable to a sophisticated one that does not. Sophistication is earned by a failed simple baseline, not assumed at the start. Every new file, dependency, adapter, and policy is a liability the project must carry for its lifetime. We add only what the mission requires and resist what the mission does not. When tempted to add complexity, we ask: what simple baseline has failed to make this necessary? If the answer is "none," the complexity is premature.

**AI-human collaboration is the team's superpower.** TERA is built by one human and four AI agents, each working in its primary strength — design, generation, review, implementation — with the human orchestrating. Hybrid teams beat both pure-human and pure-AI teams when the division of labor is explicit, the handoffs are recorded, and the human remains the single point of accountability. We protect this superpower by keeping roles clear, the surface area small, and the workflow honest. We do not blur roles to save time; we honor roles to preserve quality.

**Maintainability is measured, not assumed.** A system is maintainable when a new contributor — human or AI, with no prior context — can make a correct change in bounded time. We optimize for that metric, not for theoretical elegance, not for cleverness, not for line count. The Constitution, the VAS, and the Implementation Guide exist to make this metric achievable. When maintainability and novelty conflict, maintainability wins. When maintainability and speed conflict, we slow down long enough to write the record that lets the next contributor move fast.

**Measurable optimization is the project's contract with itself.** TERA does not claim to be efficient; TERA proves it. Every routing policy ships with a benchmark delta. Every fallback ships with a measured trigger. Every claim of savings is a number with a methodology, a baseline, and a reproduction command. We do not optimize in the dark, and we do not ship optimizations we cannot reproduce. The benchmark is not a deliverable; it is the deliverable that legitimizes every other deliverable.

**This creed is the project's foundation.** Rules may evolve, versions may change, providers may come and go, but the creed holds. When in doubt, return to the creed. When the rules are silent, the creed decides. When the rules conflict, the creed reconciles. When the project ends, the creed is what we keep — and what we carry into the next problem that deserves this kind of attention.

---

## Revision History

| Version | Date | Author | Change | Rationale |
|---|---|---|---|---|
| v1.0 | 2026-07-08 | Human Project Lead | Initial ratification. All 20 sections established. | Establish stable baseline for TERA project prior to first commit; bind all human and AI contributors (GPT-5.5, GLM 5.2, Claude Opus, Antigravity) to a single written reference for the AMD Developer Hackathon window. |
| v1.1 | 2026-07-08 | Human Project Lead | Architectural review revision. Added Document Authority & Precedence, Project Lifecycle, AI Collaboration Protocol. Removed technology-specific rules (relocated conceptually to Implementation Guide). Removed hard numerical thresholds (deferred to VAS). Generalized filesystem paths. Expanded Guiding Philosophy. | Align the Constitution with the actual TERA development workflow (AI-assisted, single-committer, role-specialized), remove technology-specific and threshold-specific content that belongs in the VAS or Implementation Guide, generalize filesystem paths to portable concepts, and formalize document authority, AI collaboration, and project lifecycle. |
| v1.2 | 2026-07-08 | Human Project Lead | Final architectural review. Added Definitions, Project Deliverables, AI Capability & Limitation, Engineering Creed. Standardized terminology to "Human Project Lead." Renamed Claude Opus role to Systems Designer; renamed GPT-5.5 role to Research Lead & Technical Reviewer. Split Success Criteria into Project Success and Competition Success. Removed duplicated rules (cross-referenced canonical locations). Added Architecture Specification to precedence ladder. | Final ratification pass. Eliminate interpretation differences between AI contributors via formal Definitions. Eliminate ambiguity in contributor roles via explicit Capability & Limitation section. Eliminate conflation of engineering completion with competition outcome. Establish a philosophical foundation via the Engineering Creed. Reduce repetition without weakening authority. Produce the publication-ready Constitution frozen for the remainder of the project. |
| v2.0 | — | — | — | *(reserved for post-hackathon re-ratification)* |

**v1.2 change summary:**

- **NEW — Definitions.** Formal definitions of Project Memory, Shared Project Workspace, Project Documentation, VAS, Implementation Guide, Architecture Specification, UI/UX Specification, Contributor, AI Agent, Human Project Lead, and Project Phase. Eliminates interpretation differences between contributors.
- **REVISED — Document Authority & Precedence.** Architecture Specification added as precedence level 4 (between Implementation Guide and Research Paper). Notion Workspace clarified as the container of Project Memory.
- **REVISED — Terminology.** "Chief Software Architect" removed entirely. "Human Project Lead" is the only authorized title for the human contributor role, used consistently throughout the document and Revision History.
- **REVISED — §3 Success Criteria.** Split into §3.1 Project Success (engineering completion, under team control), §3.2 Competition Success (external outcome at AMD Developer Hackathon), and §3.3 Hierarchy (Project Success is a prerequisite for claiming Competition Success; Competition Success is not a prerequisite for claiming Project Success).
- **NEW — §6 Project Deliverables.** Canonical enumeration of 12 official project artifacts with precedence, first-produced phase, and owner. Future documents fit under this hierarchy through Change Management.
- **REVISED — §14 Repository & Version Control.** Workflow stages updated to reflect renamed roles (Claude Opus as Systems Designer, GPT-5.5 as Research Lead & Technical Reviewer).
- **REVISED — §15 AI Collaboration Protocol.** Claude Opus primary role renamed to Systems Designer (Architecture, Specifications, UI/UX, Design Decisions). GPT-5.5 primary role renamed to Research Lead & Technical Reviewer (architectural review, technical review, research validation, specification validation, planning support, engineering critique). Role definitions expanded.
- **NEW — §16 AI Capability & Limitation.** Per-contributor capabilities and limitations for GPT-5.5, GLM 5.2, Claude Opus, Antigravity, and Human Project Lead. Cross-contributor rules for assignment, review independence, and capability-gap escalation.
- **REVISED — §17 AI Agent Responsibilities.** Removed duplicated no-commit rule (now cross-references §14.8). Removed duplicated capability statement (now cross-references §16).
- **REVISED — §20 Communication Rules.** Removed duplicated chat-precedence rule (now cross-references Document Authority & Precedence, rule 2).
- **NEW — §25 Engineering Creed.** Approximately one-page philosophical foundation covering token efficiency, intelligent routing, evidence-driven engineering, explainability, simplicity, AI-human collaboration, maintainability, and measurable optimization. Distinct from Guiding Philosophy: creed is narrative and inspirational; philosophy is concise and auditable.
- **PRESERVED — All other sections.** §1, §2, §4, §5, §7, §8, §9, §10, §11, §12, §13, §18, §19, §21, §22, §23, §24 preserved without substantive change. Section numbers shifted to accommodate new sections.

**Amendment process.** Any contributor may propose an amendment by raising a change request with the Human Project Lead titled `Constitution amendment: <summary>`. The Human Project Lead reviews, accepts, rejects, or defers. Accepted amendments are recorded as a new row above with version, date, ratifier, and rationale. The Constitution version is bumped according to the Change Management rules in Section 21.

**End of Constitution v1.2.**
