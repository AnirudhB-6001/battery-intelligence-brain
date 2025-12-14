import csv
import json
import math
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

OUT_DIR = Path("synthetic_data/generated/v0")
OUT_DIR.mkdir(parents=True, exist_ok=True)

ASSETS_PATH = OUT_DIR / "assets.json"
TELEMETRY_PATH = OUT_DIR / "telemetry.csv"
EVENTS_PATH = OUT_DIR / "events.csv"

RANDOM_SEED = 42
random.seed(RANDOM_SEED)

START_TS = datetime(2025, 12, 1, 0, 0, tzinfo=timezone.utc)
DAYS = 14
CADENCE_MIN = 15
POINTS_PER_DAY = int((24 * 60) / CADENCE_MIN)
TOTAL_POINTS = DAYS * POINTS_PER_DAY

SITE_ID = "site_alpha"
RACKS = [
    {
        "asset_id": "rack_01",
        "asset_type": "rack",
        "parent_asset_id": SITE_ID,
        "chemistry": "LFP",
        "install_date": "2024-01-01",
        "nominal_capacity_kwh": 100.0,
    },
    {
        "asset_id": "rack_02",
        "asset_type": "rack",
        "parent_asset_id": SITE_ID,
        "chemistry": "LFP",
        "install_date": "2024-01-01",
        "nominal_capacity_kwh": 100.0,
    },
]

# Intentional behaviors (from telemetry_v0.md)
DAY7_INDEX = 7 * POINTS_PER_DAY  # after Day 7, rack_02 degradation accelerates

# One short telemetry gap (≤2h): choose 8 points = 2h
GAP_START = START_TS + timedelta(days=10, hours=10)  # arbitrary but consistent
GAP_END = GAP_START + timedelta(minutes=CADENCE_MIN * 8)

# One minor anomaly: temp spike event (short duration)
SPIKE_START = START_TS + timedelta(days=8, hours=14)
SPIKE_END = SPIKE_START + timedelta(minutes=CADENCE_MIN * 4)  # 1 hour spike


def clamp(x, lo, hi):
    return max(lo, min(hi, x))


def soc_profile(t_index: int) -> float:
    # Smooth daily cycle between ~25% and ~90%
    # 0..(points/day-1) maps to 0..2π
    phase = (t_index % POINTS_PER_DAY) / POINTS_PER_DAY * 2 * math.pi
    base = 57.5 + 32.5 * math.sin(phase)  # 25..90
    noise = random.uniform(-1.2, 1.2)
    return clamp(base + noise, 0.0, 100.0)


def power_from_soc_change(prev_soc: float, curr_soc: float) -> float:
    # Rough mapping: if SOC rises -> charging (+kW), falls -> discharging (-kW)
    delta = curr_soc - prev_soc
    # Scale delta into kW; purely synthetic
    return clamp(delta * 4.0, -50.0, 50.0)


def status_from_power(p: float) -> str:
    if p > 2.0:
        return "charging"
    if p < -2.0:
        return "discharging"
    return "idle"


def temp_baseline(rack_id: str, t_index: int) -> float:
    # rack_02 runs a bit hotter
    offset = 0.0 if rack_id == "rack_01" else 2.0
    # gentle daily wave
    phase = (t_index % POINTS_PER_DAY) / POINTS_PER_DAY * 2 * math.pi
    base = 28.0 + 1.8 * math.sin(phase)
    noise = random.uniform(-0.4, 0.4)
    return base + offset + noise


def soh_value(rack_id: str, t_index: int) -> float:
    # Slow linear decline for rack_01
    # For rack_02: same decline until Day 7, then accelerates
    # Units: percent; start around ~100%
    start = 100.0
    per_point_decline_base = 0.002 / POINTS_PER_DAY  # ~0.002% per day
    if rack_id == "rack_01":
        decline = per_point_decline_base * t_index
    else:
        # rack_02: base decline + extra after Day 7
        extra = 0.0
        if t_index >= DAY7_INDEX:
            extra = (0.006 / POINTS_PER_DAY) * (t_index - DAY7_INDEX)  # extra ~0.006% per day after day 7
        decline = per_point_decline_base * t_index + extra
    noise = random.uniform(-0.01, 0.01)
    return clamp(start - decline + noise, 80.0, 100.0)


def is_in_window(ts: datetime, start: datetime, end: datetime) -> bool:
    return start <= ts < end


def main():
    # Write assets.json
    assets_doc = {
        "site": {"asset_id": SITE_ID, "asset_type": "site"},
        "assets": RACKS,
        "notes": {
            "cadence_minutes": CADENCE_MIN,
            "start_ts": START_TS.isoformat(),
            "days": DAYS,
            "seed": RANDOM_SEED,
        },
    }
    ASSETS_PATH.write_text(json.dumps(assets_doc, indent=2))

    # Write events.csv
    with EVENTS_PATH.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "event_id",
                "asset_id",
                "event_type",
                "start_ts",
                "end_ts",
                "severity",
                "notes",
            ],
        )
        w.writeheader()
        w.writerow(
            {
                "event_id": "ev_temp_spike_rack_02",
                "asset_id": "rack_02",
                "event_type": "temp_spike",
                "start_ts": SPIKE_START.isoformat(),
                "end_ts": SPIKE_END.isoformat(),
                "severity": "minor",
                "notes": "Short temperature spike; should be detectable and referenced in evidence.",
            }
        )
        w.writerow(
            {
                "event_id": "ev_gap_rack_02",
                "asset_id": "rack_02",
                "event_type": "telemetry_gap",
                "start_ts": GAP_START.isoformat(),
                "end_ts": GAP_END.isoformat(),
                "severity": "minor",
                "notes": "Short telemetry gap (<= 2h). Should reduce confidence.",
            }
        )

    # Write telemetry.csv
    with TELEMETRY_PATH.open("w", newline="", encoding="utf-8") as f:
        fieldnames = [
            "timestamp",
            "asset_id",
            "soc",
            "soh",
            "temperature",
            "power",
            "status",
            "data_quality_flag",
        ]
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()

        prev_soc = {r["asset_id"]: None for r in RACKS}

        for i in range(TOTAL_POINTS):
            ts = START_TS + timedelta(minutes=CADENCE_MIN * i)

            for rack in RACKS:
                rack_id = rack["asset_id"]

                # Telemetry gap: we mark points as missing and skip writing core signals
                if rack_id == "rack_02" and is_in_window(ts, GAP_START, GAP_END):
                    w.writerow(
                        {
                            "timestamp": ts.isoformat(),
                            "asset_id": rack_id,
                            "soc": "",
                            "soh": "",
                            "temperature": "",
                            "power": "",
                            "status": "",
                            "data_quality_flag": "missing",
                        }
                    )
                    continue

                soc = soc_profile(i)
                soh = soh_value(rack_id, i)
                temp = temp_baseline(rack_id, i)

                # Inject spike in rack_02 temperature
                if rack_id == "rack_02" and is_in_window(ts, SPIKE_START, SPIKE_END):
                    temp += 8.0  # short spike

                # power/status derived from SOC movement (simple synthetic behavior)
                pwr = 0.0
                if prev_soc[rack_id] is not None:
                    pwr = power_from_soc_change(prev_soc[rack_id], soc)
                prev_soc[rack_id] = soc

                status = status_from_power(pwr)

                # data quality: mostly ok
                dq = "ok"

                w.writerow(
                    {
                        "timestamp": ts.isoformat(),
                        "asset_id": rack_id,
                        "soc": f"{soc:.2f}",
                        "soh": f"{soh:.4f}",
                        "temperature": f"{temp:.2f}",
                        "power": f"{pwr:.2f}",
                        "status": status,
                        "data_quality_flag": dq,
                    }
                )

    print("Generated:")
    print(f"- {ASSETS_PATH}")
    print(f"- {TELEMETRY_PATH}")
    print(f"- {EVENTS_PATH}")


if __name__ == "__main__":
    main()
