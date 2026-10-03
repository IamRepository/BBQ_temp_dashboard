from __future__ import annotations

import io
import re
import uuid
from pathlib import Path
from typing import Iterable

import pandas as pd

from models import CookProfile

COLORS = ["#f97316", "#38bdf8", "#a78bfa", "#22c55e", "#f43f5e", "#eab308", "#14b8a6", "#fb7185"]
TIME_WORDS = ("time", "date", "timestamp", "datetime", "elapsed", "hour", "minute")
TEMP_WORDS = ("temp", "temperature", "probe", "meat", "point", "flat", "pit", "ambient", "cavity", "grate")


def _read_csv(data: bytes) -> pd.DataFrame:
    last_error = None
    for encoding in ("utf-8-sig", "utf-8", "latin-1"):
        for sep in (None, ",", ";", "\t"):
            try:
                return pd.read_csv(io.BytesIO(data), encoding=encoding, sep=sep, engine="python")
            except Exception as exc:
                last_error = exc
    raise ValueError(f"Could not read CSV: {last_error}")


def _read_workbook(data: bytes, suffix: str) -> dict[str, pd.DataFrame]:
    engine = "xlrd" if suffix == ".xls" else "openpyxl"
    return pd.read_excel(io.BytesIO(data), sheet_name=None, engine=engine)


def _clean_numeric(series: pd.Series) -> pd.Series:
    if pd.api.types.is_numeric_dtype(series):
        return pd.to_numeric(series, errors="coerce")
    cleaned = series.astype(str).str.strip().str.replace(" ", "", regex=False)
    comma_decimal = cleaned.str.contains(",", regex=False).mean() > cleaned.str.contains("\.", regex=False).mean()
    if comma_decimal:
        cleaned = cleaned.str.replace(".", "", regex=False).str.replace(",", ".", regex=False)
    return pd.to_numeric(cleaned, errors="coerce")


def _detect_time(df: pd.DataFrame) -> tuple[pd.Series, pd.Series | None, str]:
    normalized = {c: str(c).strip().lower() for c in df.columns}
    candidates = [c for c, name in normalized.items() if any(word in name for word in TIME_WORDS)]
    candidates += [c for c in df.columns if c not in candidates]
    for column in candidates:
        parsed = pd.to_datetime(df[column], errors="coerce", dayfirst=True)
        if parsed.notna().mean() >= 0.75 and parsed.nunique() > 1:
            elapsed = (parsed - parsed.dropna().iloc[0]).dt.total_seconds() / 3600
            return elapsed, parsed, str(column)
    for column in candidates:
        numeric = _clean_numeric(df[column])
        if numeric.notna().mean() >= 0.75 and numeric.nunique() > 1:
            label = normalized[column]
            if "minute" in label or re.search(r"\bmin\b", label):
                numeric = numeric / 60
            elif "second" in label or re.search(r"\bsec\b", label):
                numeric = numeric / 3600
            return numeric - numeric.dropna().iloc[0], None, str(column)
    return pd.Series(range(len(df)), index=df.index, dtype=float), None, "row number"


def _temperature_columns(df: pd.DataFrame, time_column: str) -> list[str]:
    scored = []
    for column in df.columns:
        if str(column) == time_column:
            continue
        numeric = _clean_numeric(df[column])
        ratio = numeric.notna().mean()
        if ratio < 0.60 or numeric.nunique() < 2:
            continue
        name = str(column).lower()
        keyword_score = 2 if any(word in name for word in TEMP_WORDS) else 0
        plausible = numeric.dropna().between(-50, 400).mean()
        if plausible >= 0.90:
            scored.append((keyword_score, ratio, str(column)))
    scored.sort(reverse=True)
    preferred = [item[2] for item in scored if item[0] > 0]
    return preferred or [item[2] for item in scored]


def dataframe_to_profiles(df: pd.DataFrame, source_file: str, sheet: str | None, color_start: int = 0):
    messages = []
    if df.empty:
        return [], [f"Skipped empty table in {source_file}."]
    df = df.dropna(how="all").dropna(axis=1, how="all")
    elapsed, timestamp, time_column = _detect_time(df)
    temp_columns = _temperature_columns(df, time_column)
    if not temp_columns:
        return [], [f"No temperature-like numeric columns found in {source_file}{' / ' + sheet if sheet else ''}."]
    profiles = []
    for i, column in enumerate(temp_columns):
        temp = _clean_numeric(df[column])
        out = pd.DataFrame({"elapsed_hours": elapsed, "temperature_c": temp})
        if timestamp is not None:
            out["timestamp"] = timestamp
        out = out.replace([float("inf"), float("-inf")], pd.NA).dropna(subset=["elapsed_hours", "temperature_c"])
        out = out.sort_values("elapsed_hours").drop_duplicates("elapsed_hours", keep="last").reset_index(drop=True)
        if len(out) < 2:
            continue
        base = Path(source_file).stem
        name = f"{base} - {sheet} - {column}" if sheet else f"{base} - {column}"
        profiles.append(CookProfile(
            profile_id=uuid.uuid4().hex,
            name=name,
            source_file=source_file,
            channel=str(column),
            color=COLORS[(color_start + i) % len(COLORS)],
            data=out,
            metadata={"sheet": sheet or "", "time_column": time_column, "temperature_column": str(column)},
        ))
    messages.append(f"{source_file}: detected time from '{time_column}' and created {len(profiles)} profile(s).")
    return profiles, messages


def load_uploaded_files(uploaded_files: Iterable):
    profiles = []
    messages = []
    for uploaded in uploaded_files:
        suffix = Path(uploaded.name).suffix.lower()
        raw = uploaded.getvalue()
        if suffix == ".csv":
            tables = {None: _read_csv(raw)}
        elif suffix in (".xlsx", ".xls"):
            tables = _read_workbook(raw, suffix)
        else:
            messages.append(f"Skipped unsupported file: {uploaded.name}")
            continue
        for sheet, df in tables.items():
            loaded, notes = dataframe_to_profiles(df, uploaded.name, sheet, len(profiles))
            profiles.extend(loaded)
            messages.extend(notes)
    names = {}
    for profile in profiles:
        count = names.get(profile.name, 0) + 1
        names[profile.name] = count
        if count > 1:
            profile.name = f"{profile.name} ({count})"
    return profiles, messages
