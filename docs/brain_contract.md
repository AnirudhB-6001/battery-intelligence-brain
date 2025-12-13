# Battery Intelligence Brain – Contract v0.1

> **Status:** Draft / Foundational
>
> **Purpose:** This document defines the stable, long‑term contract for the *Battery Intelligence Brain*. Everything else (data sources, ML models, LLMs, UIs) must adapt to this contract. The contract is designed to survive changing inputs, incomplete data, and future expansion.

---

## 0. Non‑Negotiable Principles

1. **The Brain does not own data.** It consumes data through adapters.
2. **The Brain does not implement physics or ML.** It calls models through contracts.
3. **Every answer must have evidence.** No evidence → no answer.
4. **Uncertainty is a first‑class output.** Confidence and escalation are mandatory.
5. **Extensibility beats optimization.** New capabilities must plug into existing interfaces.

---

## 1. High‑Level Responsibility of the Brain

The Brain is responsible for:

* Understanding *what kind of question* is being asked
* Determining *what information is required*
* Orchestrating calls to data, models, and knowledge
* Validating completeness and quality
* Producing structured answers with evidence and confidence
* Refusing or escalating when requirements are not met

The Brain is **not** responsible for:

* Data ingestion mechanics
* Sensor accuracy
* Model training
* UI rendering

---

## 2. Core Interface Categories

The Brain interacts with the world only through the following interface categories:

1. Input Adapters
2. Model Adapters
3. Knowledge Base
4. Reasoning & Orchestration
5. Evidence Engine
6. Confidence & Escalation Engine
7. Output Packagers

Each category is mandatory.

---

## 3. Input Adapters

### 3.1 Telemetry Adapter

**Purpose:** Provide operational battery and system telemetry in a normalized form.

**Required Capabilities:**

* Time‑series retrieval
* Asset hierarchy awareness
* Event / alarm retrieval
* Asset metadata access

**Conceptual Contract:**

* `get_timeseries(asset_id, signals, time_window)`
* `get_events(asset_id, time_window)`
* `get_asset_context(asset_id)`

**Notes:**

* Source can be synthetic, CSV, API, or proprietary cloud
* The Brain assumes *nothing* about signal quality

---

### 3.2 Market Adapter

**Purpose:** Provide external economic or environmental context affecting decisions.

**Examples:**

* Energy prices
* Forecasts
* Outages
* Policy signals (future)

**Conceptual Contract:**

* `get_price_curve(market, time_window)`
* `get_forecast(market, time_window)`
* `get_market_context(market)`

---

## 4. Model Adapter Layer

**Purpose:** Allow proprietary or third‑party intelligence to plug into the Brain.

**Key Rule:** The Brain never implements models.

**Supported Model Types (Non‑Exhaustive):**

* Health estimation
* Degradation forecasting
* Anomaly detection
* Scenario simulation
* Dispatch / action recommendation

**Conceptual Contract:**

* `run_model(model_name, inputs) → outputs + model_confidence`

**Notes:**

* Models may be deterministic, ML‑based, physics‑based, or hybrid
* Model outputs must be explainable enough to be cited in evidence

---

## 5. Knowledge Base

**Purpose:** Enforce domain logic, language, policy, and operational constraints.

**Knowledge Types:**

* Definitions & glossary
* Operating playbooks
* Thresholds & norms
* Assumption registry
* Escalation policies
* Output language rules

**Conceptual Contract:**

* `get_definition(term)`
* `get_playbook(topic, role)`
* `get_threshold(asset_type, metric)`
* `get_template(output_type)`

**Notes:**

* The Knowledge Base constrains what the Brain is *allowed* to say
* Absence of KB coverage lowers confidence automatically

---

## 6. Reasoning & Orchestration Layer

**Purpose:** Coordinate all actions required to answer a question.

**Responsibilities:**

* Classify question intent
* Identify required inputs
* Sequence adapter and model calls
* Validate completeness
* Track assumptions

**Key Behaviors:**

* Ask for clarification if inputs are missing
* Abort if critical data is unavailable
* Never fabricate missing values

---

## 7. Evidence Engine

**Purpose:** Produce an auditable explanation for every answer.

**Evidence Bundle Must Include:**

* Data sources used
* Time windows
* Calculations performed
* Models referenced
* Knowledge Base rules applied
* Known gaps and assumptions

**Conceptual Contract:**

* `build_evidence(answer_context) → evidence_bundle`

---

## 8. Confidence & Escalation Engine

**Purpose:** Quantify trustworthiness and manage risk.

**Inputs to Confidence:**

* Data completeness
* Data freshness
* Model validity
* Knowledge Base coverage
* Time horizon

**Outputs:**

* Confidence score or band
* Explanation of confidence
* Escalation decision

**Escalation Actions:**

* Ask follow‑up questions
* Warn user explicitly
* Flag for human review

---

## 9. Output Packagers

**Purpose:** Adapt the same answer for different audiences.

**Supported Output Types:**

* Asset manager summaries
* Operations alerts
* Finance / CFO memos
* Board‑level narratives
* API‑ready structured outputs

**Conceptual Contract:**

* `format_output(answer, evidence, confidence, role)`

---

## 10. Extensibility Rules

Any future feature must:

* Plug into an existing interface category
* Not bypass evidence or confidence layers
* Not embed logic directly into adapters

If a feature cannot fit this contract, the contract must be revised *explicitly*.

---

## 11. Explicit Non‑Goals (v0.x)

* Perfect predictions
* Real‑time guarantees
* End‑user UI polish
* Market optimization accuracy

The focus is architectural correctness and cognitive integrity.

---

## 12. Versioning

* This document is **Brain Contract v0.1**
* Changes require a version bump and rationale
* Backward compatibility is preferred

---

**End of Brain Contract v0.1**
