"""Import regression tests. Run from the repository root: python -m unittest discover -s tests -v

Each test class matches an issue from the audit of v1.6.4 (H1-H5, M1, M8) or guards a
format that already worked. The example files are made by tests/make_fixtures.py.
"""
import sys
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA = Path(__file__).resolve().parent / 'data'
sys.path.insert(0, str(ROOT))

from profile_loader import load_uploaded_files  # noqa: E402
from export_utils import export_table, profiles_to_excel  # noqa: E402
from analysis import compare  # noqa: E402


class Upload:
    """Stands in for a Streamlit uploaded file."""
    def __init__(self, path):
        self.name = Path(path).name
        self._bytes = Path(path).read_bytes()

    def getvalue(self):
        return self._bytes


def load(*names):
    return load_uploaded_files([Upload(DATA / n) for n in names])


def ts(text):
    return pd.Timestamp(text)


class H1YearFirstDates(unittest.TestCase):
    def test_dates_and_duration_across_midnight(self):
        profiles, _ = load('h1_iso_midnight.csv')
        self.assertEqual(len(profiles), 1)
        data = profiles[0].data
        self.assertEqual(data.timestamp.iloc[0], ts('2026-10-03 23:58'))
        self.assertEqual(data.timestamp.iloc[-1], ts('2026-10-04 00:02'))
        self.assertAlmostEqual(profiles[0].duration_hours, 4 / 60, places=6)


class H2ElapsedTime(unittest.TestCase):
    def test_minutes(self):
        profiles, _ = load('h2_elapsed_minutes.csv')
        self.assertEqual(len(profiles), 1)
        self.assertNotIn('timestamp', profiles[0].data)
        self.assertAlmostEqual(profiles[0].duration_hours, 2.0, places=6)

    def test_hours(self):
        profiles, _ = load('h2_elapsed_hours.csv')
        self.assertEqual([p.channel for p in profiles], ['Pit', 'Meat'])
        for p in profiles:
            self.assertNotIn('timestamp', p.data)
            self.assertAlmostEqual(p.duration_hours, 3.0, places=6)

    def test_excel_date_serials_are_clock_times(self):
        profiles, _ = load('ok_excel_serial_dates.xlsx')
        self.assertEqual(len(profiles), 1)
        self.assertEqual(profiles[0].data.timestamp.iloc[0], ts('2026-10-03 10:00'))
        self.assertAlmostEqual(profiles[0].duration_hours, 4 / 60, places=4)


class H3UtcOffsets(unittest.TestCase):
    def test_offset_kept_as_local_clock_time(self):
        profiles, _ = load('h3_utc_offset.csv')
        data = profiles[0].data
        self.assertIsNone(data.timestamp.dt.tz)
        self.assertEqual(data.timestamp.iloc[0], ts('2026-10-03 15:00'))

    def test_z_suffix(self):
        profiles, _ = load('h3_utc_z.csv')
        data = profiles[0].data
        self.assertIsNone(data.timestamp.dt.tz)
        self.assertEqual(data.timestamp.iloc[0], ts('2026-10-03 13:00'))

    def test_export_and_comparison_next_to_a_plain_file(self):
        offset, _ = load('h3_utc_offset.csv')
        plain, _ = load('h5_fixed_setpoint.csv')
        profiles = offset + plain
        export_table(profiles, '1 min')
        self.assertGreater(len(profiles_to_excel(profiles, 'As logged')), 0)
        setpoint = next(p for p in plain if p.channel == 'Setpoint')
        setpoint.is_setpoint = True
        result, problem = compare(setpoint, offset[0], 10)
        self.assertTrue(result is not None or problem)  # no exception; no overlap is a valid answer


class H4ClockChange(unittest.TestCase):
    expected_times = ['2026-10-25 02:30', '2026-10-25 02:50', '2026-10-25 03:10', '2026-10-25 03:30', '2026-10-25 04:10']

    def check(self, name):
        profiles, messages = load(name)
        data = profiles[0].data
        self.assertEqual(data.temperature_c.tolist(), [80, 81, 82, 83, 84])
        self.assertEqual(data.timestamp.tolist(), [ts(t) for t in self.expected_times])
        self.assertAlmostEqual(profiles[0].duration_hours, 100 / 60, places=6)
        self.assertTrue(any('clock' in m.lower() for m in messages), messages)

    def test_zone_names(self):
        self.check('h4_dst_zone_names.csv')

    def test_without_zone_names(self):
        self.check('h4_dst_no_zone.csv')


class H5FixedSetpoint(unittest.TestCase):
    def test_constant_setpoint_is_kept(self):
        profiles, _ = load('h5_fixed_setpoint.csv')
        self.assertEqual([p.channel for p in profiles], ['Setpoint', 'Probe 1'])
        self.assertEqual(set(profiles[0].data.temperature_c), {120})


class M1AllTemperatureColumns(unittest.TestCase):
    def test_target_imported_and_non_temperatures_skipped_with_a_note(self):
        profiles, messages = load('m1_extra_columns.csv')
        self.assertEqual([p.channel for p in profiles], ['Pit temp', 'Meat', 'Target'])
        text = ' '.join(messages)
        self.assertIn('Fan %', text)
        self.assertIn('Battery', text)


class M8Fahrenheit(unittest.TestCase):
    def test_converted_to_celsius_with_a_note(self):
        profiles, messages = load('m8_fahrenheit.csv')
        self.assertEqual([p.channel for p in profiles], ['Meat', 'Pit'])
        self.assertAlmostEqual(profiles[0].data.temperature_c.iloc[0], (150 - 32) * 5 / 9, places=6)
        self.assertAlmostEqual(profiles[1].data.temperature_c.iloc[0], (250 - 32) * 5 / 9, places=6)
        self.assertTrue(any('°F' in m or 'Fahrenheit' in m for m in messages), messages)


class FormatsThatAlreadyWork(unittest.TestCase):
    def test_thermometer_export_with_cest_and_probe_dropouts(self):
        profiles, messages = load('ok_device_cest.csv')
        self.assertEqual([p.channel for p in profiles], ['cavity temperature', 'Probe 1', 'Probe 2'])
        self.assertEqual(profiles[0].data.timestamp.iloc[0], ts('2026-10-03 15:34:00'))
        self.assertTrue(any('fewer values than the header' in m for m in messages), messages)

    def test_semicolons_and_decimal_commas(self):
        profiles, _ = load('ok_semicolon_comma.csv')
        self.assertEqual(profiles[0].data.temperature_c.tolist(), [23.5, 24.0, 24.5])
        self.assertEqual(profiles[0].data.timestamp.iloc[0], ts('2026-10-03 10:00'))

    def test_workbook_with_two_sheets(self):
        profiles, _ = load('ok_two_sheets.xlsx')
        self.assertEqual(len(profiles), 2)
        self.assertEqual(profiles[1].data.timestamp.iloc[0], ts('2026-10-04 10:00'))


if __name__ == '__main__':
    unittest.main()
