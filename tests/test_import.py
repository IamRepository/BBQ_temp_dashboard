"""Import regression tests. Run from the repository root: python -m unittest discover -s tests -v

Each test class matches an issue from the audit of v1.6.4 (H1-H5, M1-M8, L2-L9), a
feature (trimming all profiles at once), or guards a format that already worked. The example files are made by tests/make_fixtures.py.
"""
import io
import sys
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA = Path(__file__).resolve().parent / 'data'
sys.path.insert(0, str(ROOT))

from profile_loader import COLORS, load_uploaded_files  # noqa: E402
from export_utils import export_sheets, export_table, profiles_to_excel  # noqa: E402
from chart_builder import MAX_POINTS, comparison, deviation, single, thin  # noqa: E402
from models import CookProfile  # noqa: E402
from roles import (ANALYZER_ROLE, ROLES, analyzer_role, default_probe, default_role, export_name,  # noqa: E402
                   probe_colours, profile_name)
from chart_builder import _line  # noqa: E402
import numpy as np  # noqa: E402
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


class M2DuplicateFiles(unittest.TestCase):
    def test_a_file_already_loaded_is_skipped(self):
        first, _ = load('ok_device_cest.csv')
        again, messages = load_uploaded_files([Upload(DATA / 'ok_device_cest.csv')], existing=first)
        self.assertEqual(again, [])
        self.assertTrue(any('already imported' in m for m in messages), messages)

    def test_the_same_file_twice_in_one_import(self):
        profiles, messages = load_uploaded_files([Upload(DATA / 'h5_fixed_setpoint.csv'), Upload(DATA / 'h5_fixed_setpoint.csv')])
        self.assertEqual(len(profiles), 2)
        self.assertTrue(any('already imported' in m for m in messages), messages)


class M3Colours(unittest.TestCase):
    def test_palette_is_the_validated_one(self):
        self.assertEqual(COLORS, ['#3987e5', '#d95926', '#199e70', '#c98500', '#d55181', '#008300', '#9085e9', '#e66767'])

    def test_a_second_import_takes_unused_colours(self):
        first, _ = load('ok_device_cest.csv')
        second, _ = load_uploaded_files([Upload(DATA / 'h5_fixed_setpoint.csv')], existing=first)
        used = {p.color for p in first}
        self.assertEqual(len(used), 3)
        self.assertTrue(all(p.color not in used for p in second), [p.color for p in second])
        self.assertEqual(len({p.color for p in first + second}), 5)


class L2NamesOnReimport(unittest.TestCase):
    def test_single_sheet_export_gives_clean_names(self):
        profiles, _ = load('l2_dashboard_export.xlsx')
        self.assertEqual([p.name for p in profiles], ['l2_dashboard_export - Connet - Probe 1', 'l2_dashboard_export - Smoque_XL - Probe 2'])
        self.assertEqual([p.channel for p in profiles], ['Connet - Probe 1', 'Smoque_XL - Probe 2'])

    def test_two_sheets_keep_the_sheet_name(self):
        profiles, _ = load('ok_two_sheets.xlsx')
        self.assertEqual([p.name for p in profiles], ['ok_two_sheets - Cook 1 - Meat', 'ok_two_sheets - Cook 2 - Meat'])


class L3ExportSheets(unittest.TestCase):
    def test_clock_and_elapsed_profiles_go_on_separate_sheets(self):
        clock, _ = load('ok_device_cest.csv')
        elapsed, _ = load('h2_elapsed_hours.csv')
        sheets = export_sheets(clock + elapsed, '1 min')
        self.assertEqual([name for name, _ in sheets], ['Cook profiles', 'Elapsed time'])
        self.assertEqual(sheets[0][1].columns[0], 'Timestamp')
        self.assertEqual(sheets[1][1].columns[0], 'Elapsed time (h)')
        book = pd.ExcelFile(io.BytesIO(profiles_to_excel(clock + elapsed, '1 min')))
        self.assertEqual(book.sheet_names, ['Cook profiles', 'Elapsed time'])

    def test_clock_only_gives_one_sheet(self):
        clock, _ = load('ok_device_cest.csv')
        self.assertEqual([name for name, _ in export_sheets(clock, '1 min')], ['Cook profiles'])


class L4PreviewOffset(unittest.TestCase):
    def test_offset_moves_timestamps_too(self):
        profiles, _ = load('h5_fixed_setpoint.csv')
        p = profiles[0]
        p.offset_hours = 0.5
        frame = p.export_frame()
        self.assertEqual(frame.timestamp.iloc[0], ts('2026-10-03 10:30'))
        self.assertAlmostEqual(frame.elapsed_hours.iloc[0], 0.5)


class L9ClockAlignment(unittest.TestCase):
    def test_elapsed_only_profiles_are_left_out_of_the_clock_chart(self):
        clock, _ = load('ok_device_cest.csv')
        elapsed, _ = load('h2_elapsed_hours.csv')
        settings = {'alignment': 'Clock time', 'theme': 'Light', 'grid': True, 'legend': True, 'width': 2, 'smoothing_minutes': 0}
        names = [t.name for t in comparison(clock + elapsed, settings).data]
        self.assertEqual(names, [p.name for p in clock])
        settings['alignment'] = 'Original timeline'
        self.assertEqual(len(comparison(clock + elapsed, settings).data), len(clock + elapsed))


def long_cook(hours=18, name='Pit'):
    """A made-up cook logged every second, with one 20-second spike (a lid opening) at the 9-hour mark."""
    n = hours * 3600
    temperature = 110 + 3 * np.sin(np.arange(n) / 900)
    temperature[9 * 3600:9 * 3600 + 20] = 160
    data = pd.DataFrame({'timestamp': pd.date_range('2026-10-03 06:00', periods=n, freq='s'),
                         'elapsed_hours': np.arange(n) / 3600, 'temperature_c': temperature})
    return CookProfile('p-' + name, name, 'long.csv', name, COLORS[0], data)


class M6LongCooks(unittest.TestCase):
    settings = {'alignment': 'Clock time', 'theme': 'Light', 'grid': True, 'legend': True, 'width': 2, 'smoothing_minutes': 0}

    def test_thinning_keeps_the_shape_spike_and_ends(self):
        profile = long_cook()
        y = profile.data.temperature_c
        keep = thin(profile.data.timestamp, y)
        self.assertLessEqual(len(keep), MAX_POINTS + 2)
        self.assertEqual((keep[0], keep[-1]), (0, len(y) - 1))
        self.assertEqual(y.iloc[keep].max(), 160)            # the short spike is still drawn
        self.assertAlmostEqual(y.iloc[keep].min(), y.min())
        self.assertTrue(np.all(np.diff(keep) > 0))            # still in time order

    def test_short_lines_are_drawn_in_full(self):
        self.assertEqual(len(thin(range(500), np.arange(500.0))), 500)

    def test_charts_stay_small_and_statistics_use_every_reading(self):
        pit, meat = long_cook(name='Pit'), long_cook(name='Meat')
        fig = comparison([pit, meat], self.settings)
        self.assertTrue(all(len(trace.x) <= MAX_POINTS + 2 for trace in fig.data))
        self.assertLess(len(fig.to_json()), 1_000_000)
        self.assertLessEqual(len(single(pit, dict(self.settings, smoothing_minutes=5)).data[0].x), MAX_POINTS + 2)
        self.assertEqual(pit.maximum_c, 160)
        self.assertEqual(len(export_table([pit], 'As logged')), 18 * 3600)

    def test_comparison_and_single_charts_leave_the_height_to_the_page(self):   # 16:9, set by the page
        pit = long_cook()
        self.assertIsNone(comparison([pit], self.settings).layout.height)
        self.assertIsNone(single(pit, self.settings).layout.height)

    def test_target_line_follows_the_setting(self):
        pit = long_cook()
        self.assertFalse(comparison([pit], self.settings).layout.shapes)
        fig = single(pit, dict(self.settings, target=200.0, theme='Dark'))
        self.assertEqual((fig.layout.shapes[0].y0, fig.layout.shapes[0].line.color), (200.0, '#E5E7EB'))
        self.assertEqual(fig.layout.annotations[-1].text, 'Target 200 °C')

    def test_setpoint_difference_chart_is_thinned(self):
        setpoint, probe = long_cook(name='Set'), long_cook(name='Probe')
        setpoint.data['temperature_c'] = 110.0
        setpoint.is_setpoint = True
        result, problem = compare(setpoint, probe, 10)
        self.assertIsNone(problem)
        self.assertLessEqual(len(deviation(result, self.settings).data[0].x), MAX_POINTS + 2)


class TrimAllProfiles(unittest.TestCase):
    def test_clock_window_trims_every_profile_that_has_readings_inside(self):
        clock, _ = load('ok_device_cest.csv')        # 15:34:00 to 15:34:12
        setpoint, _ = load('h5_fixed_setpoint.csv')   # 10:00 to 10:09
        start, end = pd.Timestamp('2026-10-03 15:34:03'), pd.Timestamp('2026-10-03 15:34:08')
        for p in clock:
            self.assertTrue(p.trim_to(start, end, True))
            self.assertTrue(p.plotted_data.timestamp.between(start, end).all())
        self.assertEqual(clock[0].plotted_data.timestamp.iloc[0], start)
        self.assertFalse(setpoint[0].trim_to(start, end, True))     # nothing inside: left as it was
        self.assertEqual(len(setpoint[0].plotted_data), 10)

    def test_the_time_offset_is_respected(self):
        profile = load('h5_fixed_setpoint.csv')[0][0]
        profile.offset_hours = 1                       # drawn at 11:00 to 11:09
        profile.trim_to(pd.Timestamp('2026-10-03 11:05'), pd.Timestamp('2026-10-03 12:00'), True)
        self.assertEqual(profile.export_frame().timestamp.iloc[0], pd.Timestamp('2026-10-03 11:05'))
        self.assertEqual(len(profile.plotted_data), 5)

    def test_hours_window_for_profiles_without_clock_times(self):
        profiles, _ = load('h2_elapsed_hours.csv')    # 0 to 3 h every 0.25 h
        for p in profiles:
            self.assertTrue(p.trim_to(0.5, 2.0, False))
            self.assertEqual(p.plotted_data.elapsed_hours.tolist(), [0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0])
        self.assertEqual(profiles[0].window(False), (0.5, 2.0))


class M7PinnedVersions(unittest.TestCase):
    def test_streamlit_and_plotly_are_pinned(self):
        lines = (ROOT / 'requirements.txt').read_text().splitlines()
        for package in ('streamlit', 'plotly', 'pandas', 'openpyxl', 'xlrd'):
            self.assertTrue(any(line.startswith(package + '==') for line in lines), package)


class L7NoUnusedFiles(unittest.TestCase):
    def test_example_data_removed(self):
        self.assertFalse((ROOT / 'example_data.py').exists())


class V170Roles(unittest.TestCase):
    """Roles for multi-device cooks, agreed 16 Oct 2026: column picker, roles, colour by probe and
    line style by role, Analyzer-compatible export names, typed start times flagged."""

    def test_default_roles_from_column_names(self):
        expected = {'Ambient temperature': 'Ambient', 'Grate probe': 'Grate', 'Meat temperature': 'Meat', 'Internal': 'Meat', 'cavity temperature': 'Pit',
                    'Probe 1': 'Meat', 'Setpoint': 'Setpoint', 'Set point': 'Setpoint', 'Target': 'Setpoint', 'Pit temp': 'Pit',
                    'Point': 'Point', 'Flat probe': 'Flat', 'Hold probe': 'Hold', 'Humidity sensor': 'Other'}
        self.assertEqual({c: default_role(c) for c in expected}, expected)

    def test_ambient_and_grate_are_separate_roles(self):   # v1.7.5
        self.assertEqual(default_role('Ambient temperature'), 'Ambient')       # Typhur sensor in the probe handle, at the meat
        self.assertEqual(default_role('Grate'), 'Grate')                       # fixed at grate level
        self.assertEqual(ROLES.index('Ambient') + 1, ROLES.index('Grate'))
        for name in ('Typhur probe 1 - Ambient', 'Weber grill - Grate'):
            self.assertEqual(analyzer_role(export_name(name, name.split(' - ')[1])), 'Cook Grate')   # the Analyzer has no ambient role

    def test_probe_labels(self):
        self.assertEqual(default_probe('Smoque_XL.csv', 'Probe 1'), 'Smoque_XL Probe 1')
        self.assertEqual(default_probe('Smoque_XL.csv', 'cavity temperature'), 'Smoque_XL')
        self.assertEqual(default_probe('Typhur probe 2.csv', 'Meat temperature'), 'Typhur probe 2')
        self.assertEqual(default_probe('cook.xlsx', 'Meat', 'Day 2'), 'cook Day 2')

    def test_every_export_name_gets_the_intended_analyzer_role(self):
        probes = ['Smoque_XL', 'Smoque_XL Probe 1', 'Typhur probe 2', 'Typhur 1', 'Grill point', 'Flat top', 'Holding cabinet',
                  'Ambient sensor', 'Weber controller', 'PID', 'Probe']
        for probe in probes:
            for role in ROLES:
                with self.subTest(probe=probe, role=role):
                    name = export_name(profile_name(probe, role), role)
                    wanted = ANALYZER_ROLE[role]
                    if wanted is None:
                        self.assertNotIn(analyzer_role(name), ('Point', 'Flat'), name)   # never taken for a brisket probe
                    else:
                        self.assertEqual(analyzer_role(name), wanted, name)
                    self.assertTrue(name.strip(' -'), name)

    def test_export_names_change_only_when_needed(self):
        self.assertEqual(export_name('Typhur 2 - Point', 'Point'), 'Typhur 2 - Point')
        self.assertEqual(export_name('Smoque_XL Probe 1 - Meat', 'Meat'), 'XL Probe 1 - Meat')
        self.assertEqual(export_name('Typhur 3 - Pit', 'Pit'), 'Typhur 3 - Pit (PID)')
        self.assertEqual(export_name('Weber - Setpoint', 'Setpoint'), 'Weber - Set temperature')

    def test_colour_by_probe(self):
        probes = [f'Typhur {n}' for n in (1, 2, 3, 4) for _ in (0, 1)] + ['Smoque_XL', 'Smoque_XL Probe 1', 'Smoque_XL Probe 2']
        colours = probe_colours(probes, [], COLORS)
        self.assertEqual(len(set(colours.values())), 7)          # 7 probes, 11 lines, within the 8 colours
        again = probe_colours(['Typhur 1', 'New probe'], [('Typhur 1', colours['Typhur 1'])], COLORS)
        self.assertEqual(again['Typhur 1'], colours['Typhur 1'])
        self.assertNotEqual(again['New probe'], colours['Typhur 1'])

    def test_lines_are_solid_unless_chosen(self):   # v1.7.1: no automatic dashes; style chosen per profile
        settings = {'width': 3.5}
        profile = load('c2d_typhur_probe_1.csv')[0][0]
        for role in ('Meat', 'Point', 'Ambient', 'Grate', 'Pit', 'Hold', 'Other'):
            profile.role, profile.is_setpoint = role, False
            self.assertIsNone(_line(profile, settings).get('dash'), role)
        profile.role, profile.is_setpoint = 'Setpoint', True
        self.assertEqual(_line(profile, settings)['dash'], 'dash')                 # a setpoint starts dashed
        profile.line_style = 'solid'
        self.assertIsNone(_line(profile, settings).get('dash'))                     # ... and can be made solid
        profile.role, profile.is_setpoint, profile.line_style = 'Pit', False, 'dot'
        self.assertEqual(_line(profile, settings)['dash'], 'dot')

    def test_chart_to_data_files_and_start_time_source(self):
        profiles, messages = load('c2d_typhur_probe_1.csv', 'c2d_typhur_probe_2.csv')
        self.assertEqual([p.channel for p in profiles], ['Ambient temperature', 'Meat temperature'] * 2)
        self.assertEqual([p.metadata['start_source'] for p in profiles], ['read and confirmed'] * 2 + ['typed'] * 2)
        text = ' '.join(messages)
        self.assertIn('Start time typed', text)
        self.assertNotIn('Start time source', text)                               # not listed as a skipped column
        self.assertEqual(profiles[2].data.timestamp.iloc[0], ts('2026-10-16 10:30'))   # probe 2 started 30 min later

    def test_merged_export_reimports_with_the_same_roles(self):
        profiles, _ = load('c2d_typhur_probe_1.csv', 'c2d_typhur_probe_2.csv', 'ok_device_cest.csv')
        roles = {'Ambient temperature': 'Ambient', 'Meat temperature': 'Point', 'cavity temperature': 'Pit', 'Probe 1': 'Flat', 'Probe 2': 'Meat'}
        for p in profiles:
            p.role, p.probe = roles[p.channel], default_probe(p.source_file, p.channel)
            p.name = profile_name(p.probe, p.role)
        sheet = export_sheets(profiles, 'As logged')[0][1]
        columns = [c for c in sheet.columns if c != 'Timestamp']
        self.assertEqual(len(columns), len(profiles))
        self.assertEqual([default_role(c) for c in columns], [p.role for p in profiles])
        self.assertEqual([analyzer_role(c) for c in columns], [ANALYZER_ROLE[p.role] for p in profiles])


if __name__ == '__main__':
    unittest.main()


class MemoryUpload:
    """An uploaded file made in the test (no file on disk)."""
    def __init__(self, name, data):
        self.name, self._bytes = name, data.encode('utf-8') if isinstance(data, str) else data

    def getvalue(self):
        return self._bytes


class V181WideFileWithDropouts(unittest.TestCase):
    """D1: short rows were placed by trying every combination of columns (minutes for a 26-column file)."""

    def test_wide_file_with_short_rows_imports_fast(self):
        import time
        header = 'Time,' + ','.join(f'Probe {i} temp' for i in range(1, 26))
        rows = [header] + [f'10:{m:02d}:00,' + ','.join(str(60 + 4 * j + m % 2) for j in range(25)) for m in range(6)]
        rows += [f'10:{m:02d}:00,' + ','.join(str(60 + 4 * j) for j in range(0, 25, 2)) for m in range(6, 12)]   # 13 of 25 values
        start = time.perf_counter()
        profiles, messages = load_uploaded_files([MemoryUpload('wide.csv', '\n'.join(rows))])
        self.assertLess(time.perf_counter() - start, 5)
        self.assertEqual(len(profiles), 25)
        self.assertIn('6 row(s) had fewer values than the header', ' '.join(messages))
        probe_3 = next(p for p in profiles if p.channel == 'Probe 3 temp')            # every second probe still reads its own column
        self.assertAlmostEqual(probe_3.data.temperature_c.iloc[-1], 68.0)

    def test_same_placement_as_trying_every_combination(self):
        import itertools
        import random
        from profile_loader import _best_placement
        rng = random.Random(7)
        for _ in range(1500):
            n = rng.randint(2, 8); k = rng.randint(1, n)
            last = [rng.choice([None, float(rng.randint(20, 200))]) for _ in range(n)]
            values = [rng.choice([float('nan'), float(rng.randint(20, 200))]) for _ in range(k)]
            cost = lambda cols: sum(abs(v - last[c]) for v, c in zip(values, cols) if last[c] is not None and v == v)  # noqa: E731
            self.assertEqual(_best_placement(values, last), min(itertools.combinations(range(n), k), key=cost))


class V181TimeZones(unittest.TestCase):
    """D2: US Central (CST) and other common zone names; zone names not recognised are reported."""

    def test_us_central_clock_change_runs_forward(self):
        from profile_loader import parse_clock
        times, note = parse_clock(pd.Series(['2026-11-01 01:50:00 CDT', '2026-11-01 01:55:00 CDT',
                                             '2026-11-01 01:00:00 CST', '2026-11-01 01:05:00 CST']), 'Time')
        self.assertEqual(list(times.dt.strftime('%H:%M')), ['01:50', '01:55', '02:00', '02:05'])
        self.assertIn('CDT to CST', note)

    def test_australian_summer_time(self):
        from profile_loader import parse_clock
        times, _ = parse_clock(pd.Series(['2026-04-05 02:50:00 AEDT', '2026-04-05 02:00:00 AEST']), 'Time')
        self.assertEqual(list(times.dt.strftime('%H:%M')), ['02:50', '03:00'])

    def test_unknown_zone_name_is_reported(self):
        from profile_loader import parse_clock
        times, note = parse_clock(pd.Series(['2026-11-01 01:50:00 IST', '2026-11-01 01:55:00 IST']), 'Time')
        self.assertEqual(list(times.dt.strftime('%H:%M')), ['01:50', '01:55'])
        self.assertIn('time zone IST not recognised', note)


class V181ExportHeadersAsText(unittest.TestCase):
    """A profile or file name starting with '=' became a formula cell in the Excel header."""

    def test_formula_like_name_stays_text(self):
        import openpyxl
        profiles, _ = load_uploaded_files([MemoryUpload('=SUM(1,2).csv', (DATA / 'ok_device_cest.csv').read_bytes())])
        sheet = openpyxl.load_workbook(io.BytesIO(profiles_to_excel(profiles))).active
        headers = [c for c in sheet[1] if isinstance(c.value, str) and c.value.startswith('=')]
        self.assertTrue(headers)
        self.assertTrue(all(c.data_type == 's' for c in headers), [(c.value, c.data_type) for c in headers])
        self.assertIn('=SUM(1,2)', str(pd.read_excel(io.BytesIO(profiles_to_excel(profiles))).columns[1]))


class V181SmallFixes(unittest.TestCase):
    def test_csv_error_says_why(self):   # D5
        _, messages = load_uploaded_files([MemoryUpload('broken.csv', 'time,temp\n"10:00,1\n10:01,2\n')])
        self.assertIn('could not be parsed as CSV (', ' '.join(messages))

    def test_grill_is_a_pit_word(self):   # D9
        self.assertEqual([default_role(c) for c in ('Grill temp', 'Grill_temp', 'Grill grate', 'Grilled chicken probe')],
                         ['Pit', 'Pit', 'Grate', 'Meat'])

    def test_upload_limit_is_25_mb(self):
        config = (ROOT / '.streamlit' / 'config.toml').read_text(encoding='utf-8')
        self.assertRegex(config, r'(?m)^\[server\][\s\S]*^maxUploadSize = 25$')

    def test_names_escaped_in_charts(self):
        profiles, _ = load_uploaded_files([MemoryUpload('x<br>y.csv', (DATA / 'ok_device_cest.csv').read_bytes())])
        settings = {'alignment': 'Original timeline', 'smoothing_minutes': 0, 'theme': 'Dark', 'grid': True, 'legend': True,
                    'width': 3.5}
        fig = comparison(profiles, settings)
        self.assertTrue(all(t.name.startswith('x&lt;br&gt;y') for t in fig.data), [t.name for t in fig.data])
        self.assertTrue(single(profiles[0], settings).layout.title.text.startswith('x&lt;br&gt;y'))


class V182ExportKeepsAProbeName(unittest.TestCase):
    """D4: removing the Analyzer's role words could leave only the role ("Hold oven - Meat" -> "Meat")."""

    def test_neutral_probe_label_when_only_the_role_is_left(self):
        cases = {('Hold oven - Meat', 'Meat', 'Hold oven'): 'Device - Meat',
                 ('Environment - Ambient', 'Ambient', 'Environment log'): 'log - Ambient',
                 ('Point probe - Other', 'Other', 'Point probe'): 'Device - Other',
                 ('Meat - Setpoint', 'Setpoint', 'meat'): 'Device - Set temperature',
                 ('Typhur 3 - Pit', 'Pit', 'Typhur 3'): 'Typhur 3 - Pit (PID)',             # unchanged cases
                 ('Smoque_XL Probe 1 - Meat', 'Meat', 'Smoque_XL'): 'XL Probe 1 - Meat'}
        for (name, role, fallback), expected in cases.items():
            got = export_name(name, role, fallback)
            self.assertEqual(got, expected, name)
            self.assertEqual(analyzer_role(got), ANALYZER_ROLE[role], got)

    def test_two_such_columns_stay_apart_in_the_export(self):
        a, b = long_cook(1, 'Hold oven - Meat'), long_cook(1, 'Environment - Meat')
        a.role = b.role = 'Meat'
        a.source_file, b.source_file = 'Hold oven.csv', 'Kitchen.csv'
        columns = list(export_table([a, b]).columns)[1:]
        self.assertEqual(columns, ['Device - Meat (°C)', 'Kitchen - Meat (°C)'])



class V182LegendUnderSmallCharts(unittest.TestCase):
    """The selected profile's legend sits under the chart, where Plotly makes room for it at any width
    (the old estimate above the plot left an empty band on wide screens)."""

    def test_single_chart_legend_at_the_bottom(self):
        profiles, _ = load('ok_device_cest.csv')
        settings = {'alignment': 'Original timeline', 'smoothing_minutes': 5, 'theme': 'Dark', 'grid': True, 'legend': True,
                    'width': 3.5, 'text_size': '175%'}
        layout = single(profiles[0], settings).layout
        self.assertEqual((layout.legend.orientation, layout.legend.yref, layout.legend.y, layout.legend.yanchor), ('h', 'container', 0, 'bottom'))
        self.assertEqual(layout.margin.t, round(86 * 1.75))                 # no estimated extra rows

    def test_grouped_comparison_legend_stays_beside(self):
        profiles, _ = load('ok_device_cest.csv')
        for p in profiles:
            p.role = 'Meat'
        settings = {'alignment': 'Original timeline', 'smoothing_minutes': 0, 'theme': 'Dark', 'grid': True, 'legend': True, 'width': 3.5}
        self.assertEqual((comparison(profiles, settings).layout.legend.orientation), 'v')
