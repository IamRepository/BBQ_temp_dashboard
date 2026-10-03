from __future__ import annotations

import io
import re
import zipfile


def _safe_name(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("_")
    return cleaned or "profile"


def profiles_to_csv_zip(profiles, unit: str = "C") -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for profile in profiles:
            archive.writestr(f"{_safe_name(profile.name)}.csv", profile.export_frame(unit).to_csv(index=False))
    return buffer.getvalue()
