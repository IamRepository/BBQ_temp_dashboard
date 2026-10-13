"""App regression tests with Streamlit's test runner. Run from the repository root:
python -m unittest discover -s tests -v

Every example file in tests/data is loaded into the page, which must build without an
error, and the main interactions (trim, reset, rename, remove, setpoint comparison) are
exercised on a small made-up cook.
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = Path(__file__).resolve().parent / 'data'
sys.path.insert(0, str(ROOT))

from streamlit.testing.v1 import AppTest  # noqa: E402
from profile_loader import load_uploaded_files  # noqa: E402

APP = str(ROOT / 'app.py')


class Upload:
    def __init__(self, path):
        self.name = Path(path).name
        self._bytes = Path(path).read_bytes()

    def getvalue(self):
        return self._bytes


def page(profiles):
    at = AppTest.from_file(APP, default_timeout=120)
    at.session_state['profiles'] = list(profiles)
    at.run()
    return at


def problems(at):
    return [str(e.value)[:200] for e in at.exception]


class EveryExampleFileOnThePage(unittest.TestCase):
    def test_each_file_alone(self):
        for path in sorted(DATA.iterdir()):
            with self.subTest(file=path.name):
                profiles, _ = load_uploaded_files([Upload(path)])
                self.assertTrue(profiles, f'{path.name}: no profiles imported')
                self.assertEqual(problems(page(profiles)), [])

    def test_all_files_together(self):
        profiles, _ = load_uploaded_files([Upload(p) for p in sorted(DATA.iterdir())])
        self.assertEqual(problems(page(profiles)), [])


class MainInteractions(unittest.TestCase):
    def setUp(self):
        self.profiles, _ = load_uploaded_files([Upload(DATA / 'ok_device_cest.csv'), Upload(DATA / 'h5_fixed_setpoint.csv')])
        self.at = page(self.profiles)

    def key(self, widgets, suffix):
        return next(w for w in widgets if w.key and w.key.endswith(suffix))

    def test_version_and_overview(self):
        from version import VERSION
        self.assertTrue(any(f'Version {VERSION}' in m.value for m in self.at.markdown))
        self.assertEqual(len(self.at.multiselect[0].value), len(self.profiles))

    def test_trim_and_reset(self):
        selected = self.at.session_state['selected_profile_id']
        self.key(self.at.slider, '_trim').set_value((2, 8)).run()
        self.assertEqual(problems(self.at), [])
        next(b for b in self.at.button if b.key == f'edit_{selected}_reset_trim').click().run()
        self.assertEqual(problems(self.at), [])
        self.assertEqual(self.key(self.at.slider, '_trim').value[0], 0)

    def test_rename_and_duplicate_name_warning(self):
        self.key(self.at.text_input, '_name').set_value('My cook').run()
        self.assertEqual(self.at.session_state['profiles'][0].name, 'My cook')
        other = self.at.session_state['profiles'][1].name
        self.key(self.at.text_input, '_name').set_value(other).run()
        self.assertIn('Profile names must be unique.', [w.value for w in self.at.warning])

    def test_remove_profile(self):
        next(b for b in self.at.button if b.key and b.key.startswith('remove_')).click().run()
        self.assertEqual(problems(self.at), [])
        self.assertEqual(len(self.at.session_state['profiles']), len(self.profiles) - 1)

    def test_setpoint_comparison(self):
        setpoint = next(p for p in self.profiles if p.channel == 'Setpoint')
        probe = next(p for p in self.profiles if p.source_file == setpoint.source_file and p is not setpoint)
        setpoint.is_setpoint = True
        at = AppTest.from_file(APP, default_timeout=120)
        at.session_state['profiles'] = list(self.profiles)
        at.session_state['compare_setpoint_id'] = setpoint.profile_id
        at.session_state['compare_probe_id'] = probe.profile_id
        at.run()
        self.assertEqual(problems(at), [])
        labels = [m.label for m in at.metric]
        self.assertIn('TIME WITHIN BAND', labels)


class V166Interactions(unittest.TestCase):
    def setUp(self):
        self.profiles, _ = load_uploaded_files([Upload(DATA / 'ok_device_cest.csv'), Upload(DATA / 'h5_fixed_setpoint.csv')])
        self.at = page(self.profiles)

    def test_charts_use_the_dashboard_colours_not_streamlits_chart_theme(self):   # M4
        charts = self.at.get('plotly_chart')
        self.assertTrue(charts)
        self.assertTrue(all(c.proto.theme == '' for c in charts), [c.proto.theme for c in charts])

    def test_time_offset_in_minutes(self):   # M5
        selected = self.at.session_state['selected_profile_id']
        box = next(n for n in self.at.number_input if n.key == f'edit_{selected}_offset_min')
        box.set_value(3.5).run()
        self.assertEqual(problems(self.at), [])
        profile = next(p for p in self.at.session_state['profiles'] if p.profile_id == selected)
        self.assertAlmostEqual(profile.offset_hours, 3.5 / 60)
        self.assertTrue(any('+0:03:30' in c.value for c in self.at.caption), [c.value for c in self.at.caption])

    def test_rename_warning_clears_on_another_profile(self):   # L1
        names = [p.name for p in self.profiles]
        next(t for t in self.at.text_input if t.key and t.key.endswith('_name')).set_value(names[1]).run()
        self.assertIn('Profile names must be unique.', [w.value for w in self.at.warning])
        self.at.selectbox(key='selected_profile_id').set_value(self.profiles[2].profile_id).run()
        self.assertNotIn('Profile names must be unique.', [w.value for w in self.at.warning])

    def test_devices_card(self):   # L5
        labels = {m.label: m.value for m in self.at.metric}
        self.assertNotIn('CHANNELS', labels)
        self.assertEqual(labels.get('DEVICES'), '2')

    def test_clock_alignment_names_profiles_without_clock_times(self):   # L9
        elapsed, _ = load_uploaded_files([Upload(DATA / 'h2_elapsed_hours.csv')])
        at = AppTest.from_file(APP, default_timeout=120)
        at.session_state['profiles'] = self.profiles + elapsed
        at.session_state['alignment_selector'] = 'Clock'
        at.run()
        self.assertEqual(problems(at), [])
        notes = ' '.join(c.value for c in at.caption)
        self.assertIn('not shown in Clock alignment', notes)
        self.assertIn(elapsed[0].name, notes)


if __name__ == '__main__':
    unittest.main()


class V167Interactions(unittest.TestCase):
    def setUp(self):
        self.profiles, _ = load_uploaded_files([Upload(DATA / 'ok_device_cest.csv'), Upload(DATA / 'h5_fixed_setpoint.csv')])
        self.at = page(self.profiles)

    def test_trim_all_profiles_together(self):
        at = self.at
        self.assertEqual(at.checkbox(key='trim_all').label, 'Trim all profiles together')
        at.checkbox(key='trim_all').check().run()
        slider = at.slider(key='trim_all_clock')
        self.assertEqual(slider.label, 'Trim all profiles')
        low = slider.value[0]
        self.assertEqual(low.strftime('%H:%M'), '10:00')
        slider.set_value((low, low.replace(minute=5))).run()          # 10:00 to 10:05
        self.assertEqual(problems(at), [])
        shown = {p.channel: len(p.plotted_data) for p in at.session_state['profiles']}
        self.assertEqual(shown['Setpoint'], 6)
        self.assertEqual(shown['Probe 1'], 6)
        self.assertTrue(any('left as they were' in c.value for c in at.caption))   # the 15:34 file has nothing inside
        self.assertTrue(any(c.value.startswith('Window: 10:00 to 10:05 on 03/10/2026') for c in at.caption), [c.value for c in at.caption])
        at.button(key='reset_all_trims').click().run()
        self.assertTrue(all(len(p.plotted_data) == len(p.data) for p in at.session_state['profiles']))

    def test_single_profile_slider_follows_a_group_trim(self):
        at = self.at
        at.checkbox(key='trim_all').check().run()
        low = at.slider(key='trim_all_clock').value[0]
        at.slider(key='trim_all_clock').set_value((low, low.replace(minute=5))).run()
        at.checkbox(key='trim_all').uncheck().run()
        selected = at.session_state['selected_profile_id']
        profile = next(p for p in at.session_state['profiles'] if p.profile_id == selected)
        self.assertEqual(at.slider(key=f'edit_{selected}_trim').value, profile.trim_bounds())

    def test_full_profile_name_under_the_box(self):   # L6
        name = self.profiles[0].name
        self.assertTrue(any('profile-fullname' in m.value and name in m.value for m in self.at.markdown))

    def test_download_button_present(self):   # M6: the file is built on click
        self.assertEqual(self.at.get('download_button')[0].proto.label, 'Download Excel file')
