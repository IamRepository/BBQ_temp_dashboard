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


if __name__ == '__main__':
    unittest.main()
