from __future__ import annotations


def max_duration(profiles) -> float:
    return max((p.duration_hours + p.offset_hours for p in profiles), default=0.0)


def max_temperature(profiles, unit: str = "C") -> float:
    return max((p.temperature_max(unit) for p in profiles), default=0.0)


def total_readings(profiles) -> int:
    return sum(len(p.data) for p in profiles)
