from __future__ import annotations

from dataclasses import dataclass, field
import pandas as pd


@dataclass
class CookProfile:
    profile_id: str
    name: str
    source_file: str
    channel: str
    color: str
    data: pd.DataFrame
    visible: bool = True
    offset_hours: float = 0.0
    metadata: dict = field(default_factory=dict)

    @property
    def duration_hours(self) -> float:
        if self.data.empty:
            return 0.0
        return float(self.data["elapsed_hours"].max() - self.data["elapsed_hours"].min())

    def temperature_min(self, unit: str = "C") -> float:
        values = self._temperature_series(unit)
        return float(values.min()) if not values.empty else 0.0

    def temperature_max(self, unit: str = "C") -> float:
        values = self._temperature_series(unit)
        return float(values.max()) if not values.empty else 0.0

    def _temperature_series(self, unit: str):
        c = self.data["temperature_c"]
        return c * 9 / 5 + 32 if unit == "F" else c

    def export_frame(self, unit: str = "C") -> pd.DataFrame:
        out = self.data.copy()
        out["elapsed_hours"] = out["elapsed_hours"] + self.offset_hours
        out[f"temperature_{unit.lower()}"] = self._temperature_series(unit)
        columns = ["elapsed_hours", f"temperature_{unit.lower()}"]
        if "timestamp" in out.columns:
            columns.insert(0, "timestamp")
        return out[columns]
