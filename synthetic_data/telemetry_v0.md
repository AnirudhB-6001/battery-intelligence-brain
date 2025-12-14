# Synthetic Telemetry Dataset v0

## 1. Dataset Purpose

This synthetic telemetry dataset exists to **exercise the Battery Intelligence Brain**, not to simulate real battery physics.

Its purpose is to:
- validate reasoning, evidence generation, and confidence handling
- test adapter contracts and data expectations
- allow controlled discovery of trends, anomalies, and gaps

This dataset will be **replaced by real telemetry** when available.  
Accuracy is less important than **clarity, consistency, and intentional behavior**.

---

## 2. Asset Hierarchy (v0 World)

### Site
- `site_alpha`

### Assets (Racks)
- `rack_01`
- `rack_02`

Each rack has the following metadata:

| Field | Description |
|-----|------------|
| `asset_id` | Stable unique identifier |
| `asset_type` | `rack` |
| `parent_asset_id` | `site_alpha` |
| `chemistry` | e.g. `LFP` |
| `install_date` | ISO date |
| `nominal_capacity_kwh` | Float |

#### Example Metadata
- `rack_01`:  
  - chemistry: LFP  
  - install_date: 2024-01-01  
  - nominal_capacity_kwh: 100  

- `rack_02`:  
  - chemistry: LFP  
  - install_date: 2024-01-01  
  - nominal_capacity_kwh: 100  

---

## 3. Telemetry Signals (v0)

All telemetry is time-series data with a fixed cadence.

### Cadence
- **15-minute intervals**

### Signals

| Signal | Unit | Description |
|-----|-----|------------|
| `timestamp` | ISO 8601 | Time of observation |
| `asset_id` | string | Target asset |
| `soc` | % | State of Charge |
| `soh` | % | State of Health |
| `temperature` | °C | Average rack temperature |
| `power` | kW | Net charge (+) / discharge (–) |
| `status` | enum | `idle`, `charging`, `discharging` |
| `data_quality_flag` | enum | `ok`, `missing`, `suspect` |

---

## 4. Behavioral Patterns (Intentional)

This dataset encodes **deliberate, discoverable behavior**.

### rack_01 (Baseline / Control)
- Stable temperature profile
- Normal operational cycling
- Slow, near-linear SoH decline
- No anomalies
- No data gaps

### rack_02 (Degradation Case)
- Slightly higher operating temperature
- Similar cycling profile initially
- After **Day 7**:
  - accelerated SoH decline
- One **temperature spike event** (short duration)
- One **short telemetry gap** (≤ 2 hours)

These behaviors are designed so the Brain can:
- compare assets
- detect worsening trends
- flag anomalies
- lower confidence where data is missing

---

## 5. Known Truths (Ground Truth – Internal)

These truths are **not available to the Brain**, but used for validation.

- `rack_02` is degrading faster than `rack_01`
- The degradation rate change begins after Day 7
- The temperature spike precedes accelerated degradation
- The telemetry gap affects confidence but not trend direction

If the Brain cannot:
- identify `rack_02` as higher risk
- cite evidence correctly
- express uncertainty due to the data gap  

then the Brain is behaving incorrectly.

---

## 6. Explicit Non-Goals

- No electrochemical realism
- No real degradation physics
- No seasonal or market coupling
- No attempt at prediction accuracy

This dataset exists only to **teach the Brain how to think**.
