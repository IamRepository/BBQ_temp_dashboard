"""Roles for multi-device cooks (v1.7.0).

Each profile has a role (what it measures) and a probe label (which probe or device it comes from).
Colour follows the probe and line style follows the role, so four Typhur probes with an ambient and a
meat line each, plus a Weber controller, stay within the 8 validated colours.

The Excel export names are made to be read correctly by the Brisket Tenderness Analyzer, which picks a
role for each column from words in its name (pit_engine.classify_columns, Analyzer v2.8.3).
"""
import re
from pathlib import Path

ROLES = ['Meat', 'Point', 'Flat', 'Grate', 'Pit', 'Hold', 'Setpoint', 'Other']

ROLE_HELP = {
    'Meat': 'A meat probe, place not given (choose Point or Flat for brisket).',
    'Point': 'Meat probe in the brisket point.',
    'Flat': 'Meat probe in the brisket flat.',
    'Grate': 'Air temperature at grate level, for example a Typhur Ambient reading.',
    'Pit': "The cooker's own controller or cavity reading, for example the Weber Smoque XL.",
    'Hold': 'Air temperature in the holding oven or cabinet.',
    'Setpoint': 'The temperature the cooker was set to hold. Drawn dashed, never smoothed, and used in Setpoint vs measured.',
    'Other': 'Anything else.',
}

# Line style per role (Plotly dash names). Setpoints stay dashed as before; the target line is dotted.
ROLE_DASH = {'Meat': 'solid', 'Point': 'solid', 'Flat': 'solid', 'Grate': 'dashdot', 'Pit': 'longdash',
             'Hold': 'longdashdot', 'Setpoint': 'dash', 'Other': 'solid', '': 'solid'}

# Default role from the column name, checked in this order.
_DEFAULTS = [
    ('Setpoint', r'set\s*point|\bset\s*temp|target|\bset\b'),   # before Point: "Setpoint" contains "point"
    ('Point', r'point'),
    ('Flat', r'flat'),
    ('Hold', r'\bhold|holding|environment'),
    ('Grate', r'grate|ambient'),
    ('Pit', r'cavity|controller|\bpit\b|\bpid\b|smoker|chamber'),
    ('Meat', r'meat|internal|probe|food|brisket|core|kern'),
]


def default_role(column_name):
    """Suggested role for a column, from words in its name. The user can change it."""
    name = str(column_name).lower()
    for role, pattern in _DEFAULTS:
        if re.search(pattern, name):
            return role
    return 'Other'


_PROBE_NUMBER = re.compile(r'\bprobe\s*(\d+)\b', re.I)


def default_probe(source_file, column_name, sheet=''):
    """Suggested probe label: the file name, plus the probe number when the column names one
    ("Smoque_XL Probe 1"), so each physical probe gets its own colour."""
    label = Path(source_file).stem
    if sheet:
        label = f'{label} {sheet}'
    number = _PROBE_NUMBER.search(str(column_name))
    if number and not _PROBE_NUMBER.search(label):
        label = f'{label} Probe {number.group(1)}'
    return label


def profile_name(probe, role):
    return f'{probe} - {role}'


def unique_names(names, taken=()):
    """The names, made unique against each other and against `taken` by adding 2, 3, ..."""
    used = set(taken)
    out = []
    for name in names:
        candidate, n = name, 2
        while candidate in used:
            candidate = f'{name} {n}'
            n += 1
        used.add(candidate)
        out.append(candidate)
    return out


# --- The Brisket Tenderness Analyzer's column rules (pit_engine.classify_columns, v2.8.3), checked in order ---
A_POINT, A_FLAT, A_PID, A_GRATE, A_HOLD = 'Point', 'Flat', 'Cook PID', 'Cook Grate', 'Hold Env'
_ANALYZER_RULES = [
    (A_POINT, ('point',)),
    (A_FLAT, ('flat',)),
    (A_HOLD, ('hold environment', 'hold probe', 'holding probe', 'holding oven', 'oven probe', 'hold oven', 'cvap',
              'holding cabinet', 'environment')),
    (A_GRATE, ('grate', 'ambient', 'pit probe', 'chamber probe')),
    (A_PID, ('cavity temperature', 'controller', 'smoker', 'smoque', 'built-in pit', 'pid')),
    (A_FLAT, ('meat', 'internal', 'food', 'brisket', 'probe')),   # generic meat names: the Analyzer guesses Flat
]

# What the Analyzer should make of each dashboard role (None: no Analyzer role, left to the user there).
ANALYZER_ROLE = {'Point': A_POINT, 'Flat': A_FLAT, 'Meat': A_FLAT, 'Grate': A_GRATE, 'Pit': A_PID, 'Hold': A_HOLD,
                 'Setpoint': None, 'Other': None, '': None}
# Word added to an export name when it is needed for the Analyzer to see the role.
_ROLE_WORD = {'Point': 'Point', 'Flat': 'Flat', 'Meat': 'Meat', 'Grate': 'Grate', 'Pit': 'Pit (PID)', 'Hold': 'Hold probe'}
_MEAT_ROLES = (A_POINT, A_FLAT)


def analyzer_role(name):
    """The role the Analyzer gives a column with this name by its name alone (None: it decides by shape)."""
    lowered = str(name).lower()
    if lowered == 'poin':
        return A_POINT
    for role, hints in _ANALYZER_RULES:
        if any(h in lowered for h in hints):
            return role
    return None


def export_name(name, role):
    """The profile name as written in the Excel export: unchanged when the Analyzer already reads the
    intended role from it, otherwise with misleading words removed and the role word added.
    Examples: "Smoque_XL Probe 1 - Meat" contains "smoque" (a controller word for the Analyzer), so it
    becomes "XL Probe 1 - Meat"; "Typhur 3 - Pit" becomes "Typhur 3 - Pit (PID)"; a setpoint never
    contains "point", which the Analyzer would take for the brisket point."""
    wanted = ANALYZER_ROLE.get(role)
    if wanted is None:
        # No Analyzer role (Setpoint, Other): only make sure it is not taken for a brisket probe.
        cleaned = re.sub(r'set\s*-?\s*point', 'Set temperature', name, flags=re.I)
        if analyzer_role(cleaned) in _MEAT_ROLES:
            for analyzer, hints in _ANALYZER_RULES:   # every word the Analyzer reads as meat, "probe" included
                if analyzer in _MEAT_ROLES:
                    for hint in hints:
                        cleaned = re.sub(re.escape(hint), '', cleaned, flags=re.I)
            cleaned = re.sub(r'[\s_\-]{2,}', lambda m: ' - ' if '-' in m.group(0) else ' ', cleaned).strip(' _-') or role
        return cleaned
    if analyzer_role(name) == wanted:
        return name
    cleaned = name
    for analyzer, hints in _ANALYZER_RULES:
        if analyzer == wanted:
            continue
        for hint in hints:
            cleaned = re.sub(re.escape(hint), '', cleaned, flags=re.I)
    cleaned = re.sub(r'[\s_\-]{2,}', lambda m: ' - ' if '-' in m.group(0) else ' ', cleaned).strip(' _-')
    if analyzer_role(cleaned) != wanted:
        ending = re.compile(rf'(\s-\s){re.escape(role)}$', re.I)
        if ending.search(cleaned):
            cleaned = ending.sub(lambda m: m.group(1) + _ROLE_WORD[role], cleaned)   # "... - Hold" -> "... - Hold probe"
        else:
            cleaned = f'{cleaned} - {_ROLE_WORD[role]}' if cleaned else _ROLE_WORD[role]
    if analyzer_role(cleaned) != wanted:   # cannot happen with the rules above; kept as a safe fallback
        cleaned = _ROLE_WORD[role]
    return cleaned


def probe_colours(probes, existing, palette):
    """One colour per probe label. Labels already on the dashboard keep their colour; new labels take the
    first unused colour, and past 8 the least-used one."""
    colours = {}
    counts = {c: 0 for c in palette}
    for probe, colour in existing:
        colours.setdefault(probe, colour)
        if colour in counts:
            counts[colour] += 1
    for probe in probes:
        if probe in colours:
            continue
        colour = min(palette, key=lambda c: (counts[c], palette.index(c)))
        colours[probe] = colour
        counts[colour] += 1
    return colours
