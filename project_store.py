"""Probe-2-Plot projects (v1.9.0): a cook saved with everything needed to show it again.

One project is one file ("<name>.p2p", a zip) that holds:
  project.json         name, date, notes, every profile's settings and the chart settings
  readings/<n>.csv     each profile's readings exactly as imported (time, temperature)
  files/<sha1>/<name>  the original uploaded files, untouched (kept for reference; opening does not re-parse them)

The same file is used in two ways:
  - "Save project file" / "Open project file" works everywhere (Streamlit Cloud, a laptop, the NAS).
  - In library mode (P2P_MODE=library, set on the NAS) the app also keeps the files in P2P_DATA/projects/,
    one file per project, and lists them in the app. Deleted projects go to P2P_DATA/projects/deleted/.

Nothing here depends on Streamlit, so the library can later move to a database or be read by the Brisket
Tenderness Analyzer without touching the app.
"""
import io
import json
import os
import re
import tempfile
import uuid
import zipfile
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd

from models import CookProfile

FORMAT = 'probe-2-plot-project'
FORMAT_VERSION = 1
EXTENSION = '.p2p'

# Limits for files opened from outside (a project file is untrusted input).
MAX_ENTRIES = 400
MAX_UNPACKED = 400 * 1024 * 1024        # all members together, unpacked
MAX_JSON = 5 * 1024 * 1024
MAX_PROFILES = 100

_ID = re.compile(r'^[0-9a-f]{12}$')
_FINGERPRINT = re.compile(r'^[0-9a-f]{40}$')


class ProjectError(ValueError):
    """A project file that cannot be opened; the message is shown to the user as it is."""


# ---------------------------------------------------------------- configuration (environment, for the NAS)

def library_enabled():
    """True when the app keeps a project library on disk (the NAS: P2P_MODE=library)."""
    return os.environ.get('P2P_MODE', '').strip().lower() == 'library'


def data_dir():
    """Where the library lives: P2P_DATA (the Docker volume /data on the NAS), else ./data."""
    return Path(os.environ.get('P2P_DATA', 'data'))


def new_project_id():
    return uuid.uuid4().hex[:12]


def file_name(name, saved=None):
    """A safe download name: "Brisket 14-Nov-26.p2p"."""
    clean = re.sub(r'[^\w\- .()]+', '', str(name)).strip(' .') or 'Probe-2-Plot project'
    return clean[:80] + EXTENSION


# ---------------------------------------------------------------- write

def _json_safe(value):
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(v) for v in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, (date, datetime, pd.Timestamp)):
        return value.isoformat()
    if hasattr(value, 'item'):                     # numpy scalars
        return value.item()
    return str(value)


def _readings_csv(frame):
    out = pd.DataFrame({'elapsed_hours': frame['elapsed_hours'].astype(float),
                        'temperature_c': frame['temperature_c'].astype(float)})
    if 'timestamp' in frame:
        out['timestamp'] = pd.to_datetime(frame['timestamp']).dt.strftime('%Y-%m-%dT%H:%M:%S.%f')
    return out.to_csv(index=False).encode('utf-8')        # shortest exact form of every number (round-trips)


def project_bytes(project, profiles, settings, sources, app_version=''):
    """The project file as bytes.

    project:  {'id', 'name', 'date' (datetime.date), 'notes'}
    profiles: the CookProfile list, in dashboard order
    settings: chart and page settings, a plain dict (saved as JSON)
    sources:  {sha1 fingerprint: (file name, bytes)} of the original files, as many as are available
    """
    buffer = io.BytesIO()
    entries, used = [], set()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for n, p in enumerate(profiles):
            path = f'readings/{n}.csv'
            archive.writestr(path, _readings_csv(p.data))
            entries.append({
                'id': p.profile_id, 'name': p.name, 'source_file': p.source_file, 'channel': p.channel,
                'color': p.color, 'visible': bool(p.visible), 'offset_hours': float(p.offset_hours),
                'trim_start': int(p.trim_start), 'trim_end': None if p.trim_end is None else int(p.trim_end),
                'is_setpoint': bool(p.is_setpoint), 'role': p.role, 'probe': p.probe, 'line_style': p.line_style,
                'metadata': _json_safe(p.metadata), 'readings': path, 'rows': int(len(p.data))})
            used.add(p.metadata.get('fingerprint'))
        files = []
        for fingerprint, (name, raw) in sources.items():
            if fingerprint not in used or not _FINGERPRINT.match(str(fingerprint)):
                continue                           # only files that profiles of this project came from
            safe = re.sub(r'[^\w\- .()]+', '_', Path(str(name)).name)[:120] or 'file'
            path = f'files/{fingerprint}/{safe}'
            archive.writestr(path, raw)
            files.append({'fingerprint': fingerprint, 'name': str(name), 'path': path, 'bytes': len(raw)})
        manifest = {
            'format': FORMAT, 'format_version': FORMAT_VERSION, 'app_version': app_version,
            'saved_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
            'project': {'id': project['id'], 'name': str(project['name']).strip() or 'Untitled cook',
                        'date': _json_safe(project.get('date')), 'notes': str(project.get('notes') or '')},
            'profiles': entries, 'files': files, 'settings': _json_safe(settings)}
        archive.writestr('project.json', json.dumps(manifest, indent=1, ensure_ascii=False))
    return buffer.getvalue()


# ---------------------------------------------------------------- read

def _open_zip(raw):
    try:
        archive = zipfile.ZipFile(io.BytesIO(raw))
    except (zipfile.BadZipFile, OSError, ValueError):
        raise ProjectError('This is not a Probe-2-Plot project file (.p2p).') from None
    infos = archive.infolist()
    if len(infos) > MAX_ENTRIES or sum(i.file_size for i in infos) > MAX_UNPACKED:
        raise ProjectError('This project file is too large to open.')
    return archive


def _manifest(archive):
    try:
        info = archive.getinfo('project.json')
    except KeyError:
        raise ProjectError('This is not a Probe-2-Plot project file (no project.json inside).') from None
    if info.file_size > MAX_JSON:
        raise ProjectError('This project file is too large to open.')
    try:
        manifest = json.loads(archive.read(info).decode('utf-8'))
    except (ValueError, UnicodeDecodeError):
        raise ProjectError('The project file is damaged (project.json cannot be read).') from None
    if not isinstance(manifest, dict) or manifest.get('format') != FORMAT:
        raise ProjectError('This is not a Probe-2-Plot project file.')
    version = manifest.get('format_version')
    if not isinstance(version, int) or version < 1:
        raise ProjectError('The project file is damaged (unknown format version).')
    if version > FORMAT_VERSION:
        raise ProjectError(f'This project was saved by a newer Probe-2-Plot (format {version}); update the app to open it.')
    return manifest


def _text(value, limit=500):
    return str(value if value is not None else '')[:limit]


def _readings(archive, path):
    if not isinstance(path, str) or not re.fullmatch(r'readings/\d{1,4}\.csv', path):
        raise ProjectError('The project file is damaged (a readings entry is missing).')
    try:
        frame = pd.read_csv(io.BytesIO(archive.read(path)), float_precision='round_trip')   # exact, not the fast approximation
    except KeyError:
        raise ProjectError('The project file is damaged (a readings entry is missing).') from None
    except Exception:
        raise ProjectError('The project file is damaged (readings cannot be read).') from None
    if not {'elapsed_hours', 'temperature_c'} <= set(frame.columns):
        raise ProjectError('The project file is damaged (readings without time or temperature).')
    out = pd.DataFrame({'elapsed_hours': pd.to_numeric(frame['elapsed_hours'], errors='coerce'),
                        'temperature_c': pd.to_numeric(frame['temperature_c'], errors='coerce')})
    if 'timestamp' in frame:
        out['timestamp'] = pd.to_datetime(frame['timestamp'], errors='coerce', format='ISO8601')
    out = out.dropna(subset=['elapsed_hours', 'temperature_c']).reset_index(drop=True)
    if len(out) < 2:
        raise ProjectError('The project file is damaged (a profile has fewer than 2 readings).')
    return out


def _date(value):
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def read_project(raw):
    """Everything in a project file: {'project', 'profiles' (CookProfile list), 'settings', 'sources', 'saved_at',
    'app_version'}. Raises ProjectError with a message for the user when the file cannot be opened."""
    archive = _open_zip(raw)
    manifest = _manifest(archive)
    meta = manifest.get('project') or {}
    entries = manifest.get('profiles')
    if not isinstance(entries, list) or not entries:
        raise ProjectError('The project file holds no profiles.')
    if len(entries) > MAX_PROFILES:
        raise ProjectError('This project file is too large to open.')
    profiles, seen = [], set()
    for entry in entries:
        if not isinstance(entry, dict):
            raise ProjectError('The project file is damaged (a profile entry is not readable).')
        pid = _text(entry.get('id'), 64)
        if not re.fullmatch(r'[0-9a-zA-Z]{1,64}', pid) or pid in seen:
            pid = uuid.uuid4().hex                 # missing or duplicate id: a new one
        seen.add(pid)
        trim_end = entry.get('trim_end')
        metadata = entry.get('metadata') if isinstance(entry.get('metadata'), dict) else {}
        try:
            profiles.append(CookProfile(
                profile_id=pid, name=_text(entry.get('name'), 200) or 'Profile', source_file=_text(entry.get('source_file'), 200),
                channel=_text(entry.get('channel'), 200), color=_text(entry.get('color'), 20) or '#3987e5',
                data=_readings(archive, entry.get('readings')), visible=bool(entry.get('visible', True)),
                offset_hours=float(entry.get('offset_hours') or 0.0), metadata=metadata,
                trim_start=max(0, int(entry.get('trim_start') or 0)), trim_end=None if trim_end is None else max(0, int(trim_end)),
                is_setpoint=bool(entry.get('is_setpoint')), role=_text(entry.get('role'), 20), probe=_text(entry.get('probe'), 200),
                line_style=_text(entry.get('line_style'), 20)))
        except (TypeError, ValueError):
            raise ProjectError('The project file is damaged (a profile setting is not readable).') from None
    sources = {}
    for item in manifest.get('files') or []:
        if not isinstance(item, dict):
            continue
        fingerprint, path = str(item.get('fingerprint', '')), item.get('path')
        if _FINGERPRINT.match(fingerprint) and isinstance(path, str) and path.startswith(f'files/{fingerprint}/'):
            try:
                sources[fingerprint] = (_text(item.get('name'), 200), archive.read(path))
            except KeyError:
                pass                               # an original is missing: the readings are what count
    project = {'id': meta.get('id') if _ID.match(str(meta.get('id', ''))) else new_project_id(),
               'name': _text(meta.get('name'), 120) or 'Untitled cook', 'date': _date(meta.get('date')),
               'notes': _text(meta.get('notes'), 5000)}
    settings = manifest.get('settings') if isinstance(manifest.get('settings'), dict) else {}
    return {'project': project, 'profiles': profiles, 'settings': settings, 'sources': sources,
            'saved_at': _text(manifest.get('saved_at'), 40), 'app_version': _text(manifest.get('app_version'), 20)}


def summary(raw):
    """The library list entry of a project file, reading project.json only."""
    manifest = _manifest(_open_zip(raw))
    meta = manifest.get('project') or {}
    return {'id': str(meta.get('id', '')), 'name': _text(meta.get('name'), 120) or 'Untitled cook',
            'date': _date(meta.get('date')), 'notes': _text(meta.get('notes'), 5000),
            'profiles': len(manifest.get('profiles') or []), 'saved_at': _text(manifest.get('saved_at'), 40)}


# ---------------------------------------------------------------- library (the NAS)

class Library:
    """Project files in <root>/projects/<id>.p2p. Writes are atomic (a temporary file, then a rename), so a
    crash or a full disk never leaves half a project; deleted projects are moved to projects/deleted/."""

    def __init__(self, root=None):
        self.root = Path(root) if root is not None else data_dir()
        self.folder = self.root / 'projects'

    def _path(self, project_id):
        if not _ID.match(str(project_id)):
            raise ProjectError('Unknown project.')
        return self.folder / f'{project_id}{EXTENSION}'

    def save(self, project_id, raw):
        read_project(raw)                          # never store a file the app could not open again
        self.folder.mkdir(parents=True, exist_ok=True)
        target = self._path(project_id)
        handle, temporary = tempfile.mkstemp(dir=self.folder, prefix='.saving-', suffix=EXTENSION)
        try:
            with os.fdopen(handle, 'wb') as out:
                out.write(raw)
                out.flush()
                os.fsync(out.fileno())
            os.replace(temporary, target)
        except BaseException:
            Path(temporary).unlink(missing_ok=True)
            raise
        return target

    def load(self, project_id):
        path = self._path(project_id)
        if not path.is_file():
            raise ProjectError('This project is no longer in the library.')
        return path.read_bytes()

    def delete(self, project_id):
        path = self._path(project_id)
        if path.is_file():
            bin_folder = self.folder / 'deleted'
            bin_folder.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')
            os.replace(path, bin_folder / f'{project_id}-{stamp}{EXTENSION}')

    def projects(self):
        """Saved projects, newest cook first; unreadable files are listed as damaged instead of breaking the list."""
        if not self.folder.is_dir():
            return []
        out = []
        for path in self.folder.glob(f'*{EXTENSION}'):
            if not _ID.match(path.stem):
                continue
            try:
                item = summary(path.read_bytes())
                item['id'] = path.stem                 # the file name is the id the library uses
            except ProjectError as exc:
                item = {'id': path.stem, 'name': f'{path.name} (damaged: {exc})', 'date': None, 'notes': '',
                        'profiles': 0, 'saved_at': '', 'damaged': True}
            out.append(item)
        return sorted(out, key=lambda i: (i['date'] or date.min, i['saved_at']), reverse=True)
