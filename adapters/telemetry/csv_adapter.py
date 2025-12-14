from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def _parse_iso(ts: str) -> datetime:
    # Accepts ISO strings with timezone; falls back to UTC if missing.
    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _in_window(ts: datetime, window: Optional[Tuple[datetime, datetime]]) -> bool:
    if window is None:
        return True
    start, end = window
    return start <= ts < end


@dataclass
class TimeWindow:
    start: datetime
    end: datetime

    @staticmethod
    def from_iso(start_iso: str, end_iso: str) -> "TimeWindow":
        return TimeWindow(start=_parse_iso(start_iso), end=_parse_iso(end_iso))

    def as_tuple(self) -> Tuple[datetime, datetime]:
        return (self.start, self.end)


class CsvTelemetryAdapter:
    """
    CSV-backed Telemetry Adapter v0.

    Backed by:
      - synthetic_data/generated/v0/assets.json
      - synthetic_data/generated/v0/telemetry.csv
      - synthetic_data/generated/v0/events.csv

    This adapter is intentionally simple:
      - loads files on init
      - performs in-memory filtering
      - returns normalized dict structures
    """

    def __init__(self, base_dir: str | Path = "synthetic_data/generated/v0") -> None:
        self.base_dir = Path(base_dir)
        self.assets_path = self.base_dir / "assets.json"
        self.telemetry_path = self.base_dir / "telemetry.csv"
        self.events_path = self.base_dir / "events.csv"

        self._assets_doc = self._load_assets()
        self._asset_index = self._index_assets(self._assets_doc)
        self._telemetry_rows = self._load_telemetry()
        self._events_rows = self._load_events()

    # -------------------------
    # Public Contract Methods
    # -------------------------

    def get_asset_context(self, asset_id: str) -> Dict[str, Any]:
        """
        Returns metadata/context for a given asset_id.
        Raises KeyError if not found.
        """
        if asset_id == self._assets_doc.get("site", {}).get("asset_id"):
            return self._assets_doc["site"]

        asset = self._asset_index.get(asset_id)
        if not asset:
            raise KeyError(f"Unknown asset_id: {asset_id}")

        # Keep it stable and predictable
        return {
            "asset_id": asset["asset_id"],
            "asset_type": asset.get("asset_type", "unknown"),
            "parent_asset_id": asset.get("parent_asset_id"),
            "metadata": {
                "chemistry": asset.get("chemistry"),
                "install_date": asset.get("install_date"),
                "nominal_capacity_kwh": asset.get("nominal_capacity_kwh"),
            },
        }

    def get_events(self, asset_id: str, time_window: Optional[TimeWindow] = None) -> List[Dict[str, Any]]:
        """
        Returns events for an asset in a time window.
        """
        window = time_window.as_tuple() if time_window else None
        out: List[Dict[str, Any]] = []

        for e in self._events_rows:
            if e.get("asset_id") != asset_id:
                continue

            start_ts = _parse_iso(e["start_ts"])
            end_ts = _parse_iso(e["end_ts"])

            # Event overlaps window if any part intersects
            if window is not None:
                w_start, w_end = window
                overlaps = not (end_ts <= w_start or start_ts >= w_end)
                if not overlaps:
                    continue

            out.append(
                {
                    "event_id": e.get("event_id"),
                    "asset_id": e.get("asset_id"),
                    "event_type": e.get("event_type"),
                    "start_ts": start_ts.isoformat(),
                    "end_ts": end_ts.isoformat(),
                    "severity": e.get("severity"),
                    "notes": e.get("notes", ""),
                }
            )

        # sort by start time
        out.sort(key=lambda x: x["start_ts"])
        return out

    def get_timeseries(
        self,
        asset_id: str,
        signals: List[str],
        time_window: Optional[TimeWindow] = None,
        *,
        include_missing: bool = True,
    ) -> Dict[str, Any]:
        """
        Returns normalized time-series rows for given asset_id and signals.

        Output shape:
        {
          "asset_id": ...,
          "signals": [...],
          "time_window": {"start": ..., "end": ...} | None,
          "rows": [
             {"timestamp": "...", "<signal>": value_or_None, ..., "data_quality_flag": "..."}
          ],
          "row_count": N
        }

        Notes:
        - Always includes `timestamp` and `data_quality_flag`
        - Missing rows are returned as None values if include_missing=True
        """
        allowed = {"soc", "soh", "temperature", "power", "status"}
        bad = [s for s in signals if s not in allowed]
        if bad:
            raise ValueError(f"Unsupported signals: {bad}. Allowed: {sorted(allowed)}")

        window = time_window.as_tuple() if time_window else None
        rows: List[Dict[str, Any]] = []

        for r in self._telemetry_rows:
            if r.get("asset_id") != asset_id:
                continue

            ts = _parse_iso(r["timestamp"])
            if not _in_window(ts, window):
                continue

            dq = (r.get("data_quality_flag") or "ok").strip()

            # If row is marked missing, either skip or include placeholders
            if dq == "missing" and not include_missing:
                continue

            row: Dict[str, Any] = {
                "timestamp": ts.isoformat(),
                "data_quality_flag": dq,
            }

            for s in signals:
                row[s] = self._coerce_value(s, r.get(s), dq)

            rows.append(row)

        return {
            "asset_id": asset_id,
            "signals": signals,
            "time_window": (
                {"start": time_window.start.isoformat(), "end": time_window.end.isoformat()}
                if time_window
                else None
            ),
            "rows": rows,
            "row_count": len(rows),
        }

    # -------------------------
    # Internal Loaders
    # -------------------------

    def _load_assets(self) -> Dict[str, Any]:
        if not self.assets_path.exists():
            raise FileNotFoundError(f"assets.json not found at: {self.assets_path}")
        return json.loads(self.assets_path.read_text(encoding="utf-8"))

    def _index_assets(self, assets_doc: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        idx: Dict[str, Dict[str, Any]] = {}
        for a in assets_doc.get("assets", []):
            if "asset_id" in a:
                idx[a["asset_id"]] = a
        return idx

    def _load_telemetry(self) -> List[Dict[str, str]]:
        if not self.telemetry_path.exists():
            raise FileNotFoundError(f"telemetry.csv not found at: {self.telemetry_path}")
        with self.telemetry_path.open("r", encoding="utf-8") as f:
            return list(csv.DictReader(f))

    def _load_events(self) -> List[Dict[str, str]]:
        if not self.events_path.exists():
            raise FileNotFoundError(f"events.csv not found at: {self.events_path}")
        with self.events_path.open("r", encoding="utf-8") as f:
            return list(csv.DictReader(f))

    def _coerce_value(self, signal: str, raw: Optional[str], dq: str) -> Any:
        # Missing row or missing field returns None
        if dq == "missing" or raw is None or raw == "":
            return None

        if signal in {"soc", "soh", "temperature", "power"}:
            try:
                return float(raw)
            except ValueError:
                return None

        # status is string enum
        if signal == "status":
            return str(raw).strip() if raw is not None else None

        return raw
