"""v1.9.0: projects. A cook saved with its files and every setting, opened again exactly as it was.

Saving and opening are tested through the app in library mode (P2P_MODE=library, a temporary P2P_DATA), which runs
the same code as "Save project file" / "Open project file"; the file format itself is tested directly.
"""
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
import zipfile
from datetime import date
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import project_store as ps                                         # noqa: E402
from profile_loader import file_fingerprint, load_uploaded_files  # noqa: E402
from test_app import DATA, Upload, page, problems                  # noqa: E402

FILES = ['c2d_typhur_probe_1.csv', 'ok_device_cest.csv']


def cook():
    profiles, _ = load_uploaded_files([Upload(DATA / f) for f in FILES])
    for p in profiles:
        p.role = 'Ambient' if 'Ambient' in p.channel else 'Pit' if 'cavity' in p.channel else 'Meat'
        p.probe = Path(p.source_file).stem
    sources = {file_fingerprint((DATA / f).read_bytes()): (f, (DATA / f).read_bytes()) for f in FILES}
    return profiles, sources


def same_profiles(test, before, after):
    test.assertEqual(len(before), len(after))
    for a, b in zip(before, after):
        pd.testing.assert_frame_equal(a.data.reset_index(drop=True), b.data.reset_index(drop=True), check_dtype=False, check_exact=True)
        for field in ('profile_id', 'name', 'source_file', 'channel', 'color', 'offset_hours', 'trim_start', 'trim_end',
                      'is_setpoint', 'role', 'probe', 'line_style'):
            test.assertEqual(getattr(a, field), getattr(b, field), field)


class FileFormat(unittest.TestCase):
    def test_round_trip_is_exact(self):
        profiles, sources = cook()
        profiles[0].offset_hours, profiles[0].trim_start, profiles[0].trim_end = 0.25, 3, 10
        profiles[1].line_style, profiles[2].is_setpoint = 'dash', True
        raw = ps.project_bytes({'id': ps.new_project_id(), 'name': 'Brisket', 'date': date(2026, 10, 25), 'notes': 'wrapped 16:40'},
                               profiles, {'alignment_selector': 'Clock', 'hidden_roles': {'Meat'}}, sources, '1.9.0')
        back = ps.read_project(raw)
        same_profiles(self, profiles, back['profiles'])
        self.assertEqual(back['project']['name'], 'Brisket')
        self.assertEqual(back['project']['date'], date(2026, 10, 25))
        self.assertEqual(back['settings'], {'alignment_selector': 'Clock', 'hidden_roles': ['Meat']})
        self.assertEqual({name for name, _ in back['sources'].values()}, set(FILES))
        self.assertEqual(back['sources'][file_fingerprint((DATA / FILES[0]).read_bytes())][1], (DATA / FILES[0]).read_bytes())
        self.assertEqual(back['app_version'], '1.9.0')

    def test_only_files_the_profiles_came_from_are_saved(self):
        profiles, sources = cook()
        sources['f' * 40] = ('other.csv', b'time,temp\n')
        raw = ps.project_bytes({'id': ps.new_project_id(), 'name': 'x'}, profiles[:2], {}, sources)
        self.assertEqual({n for n, _ in ps.read_project(raw)['sources'].values()}, {'c2d_typhur_probe_1.csv'})

    def rejected(self, raw, words):
        with self.assertRaises(ps.ProjectError) as caught:
            ps.read_project(raw)
        self.assertIn(words, str(caught.exception))

    def zipped(self, members):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w') as archive:
            for name, content in members.items():
                archive.writestr(name, content)
        return buffer.getvalue()

    def test_bad_files_are_refused_with_a_message(self):
        self.rejected(b'not a zip', 'not a Probe-2-Plot project file')
        self.rejected(self.zipped({'other.txt': 'x'}), 'no project.json')
        self.rejected(self.zipped({'project.json': '{bad'}), 'damaged')
        self.rejected(self.zipped({'project.json': json.dumps({'format': 'something else'})}), 'not a Probe-2-Plot')
        newer = {'format': ps.FORMAT, 'format_version': ps.FORMAT_VERSION + 1, 'profiles': []}
        self.rejected(self.zipped({'project.json': json.dumps(newer)}), 'newer Probe-2-Plot')
        empty = {'format': ps.FORMAT, 'format_version': 1, 'profiles': []}
        self.rejected(self.zipped({'project.json': json.dumps(empty)}), 'no profiles')
        escape = {'format': ps.FORMAT, 'format_version': 1, 'profiles': [{'id': 'a', 'readings': '../../etc/passwd'}]}
        self.rejected(self.zipped({'project.json': json.dumps(escape)}), 'damaged')

    def test_huge_unpacked_size_is_refused(self):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as archive:
            archive.writestr('project.json', '{}')
            archive.writestr('readings/0.csv', b'0' * (ps.MAX_UNPACKED + 1))   # compresses to almost nothing
        self.rejected(buffer.getvalue(), 'too large')

    def test_download_name_is_safe(self):
        self.assertEqual(ps.file_name('Brisket 14-Nov-26'), 'Brisket 14-Nov-26.p2p')
        self.assertEqual(ps.file_name('../../x<y>:z'), 'xyz.p2p')
        self.assertEqual(ps.file_name('   '), 'Probe-2-Plot project.p2p')


class LibraryOnDisk(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.library = ps.Library(self.root)
        profiles, sources = cook()
        self.raw = ps.project_bytes({'id': 'a1b2c3d4e5f6', 'name': 'Brisket', 'date': date(2026, 10, 25)}, profiles, {}, sources)

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def test_save_list_update_delete(self):
        self.library.save('a1b2c3d4e5f6', self.raw)
        self.assertEqual([(p['id'], p['name'], p['profiles']) for p in self.library.projects()], [('a1b2c3d4e5f6', 'Brisket', 5)])
        self.library.save('a1b2c3d4e5f6', self.raw)                       # saving again updates the same entry
        self.assertEqual(len(self.library.projects()), 1)
        self.assertEqual(list(self.library.folder.glob('.saving-*')), [])  # no temporary files left behind
        self.library.delete('a1b2c3d4e5f6')
        self.assertEqual(self.library.projects(), [])
        self.assertEqual(len(list((self.library.folder / 'deleted').glob('*.p2p'))), 1)   # kept, not destroyed

    def test_never_stores_a_file_it_cannot_open(self):
        with self.assertRaises(ps.ProjectError):
            self.library.save('a1b2c3d4e5f6', b'junk')
        self.assertEqual(self.library.projects(), [])

    def test_ids_cannot_reach_outside_the_folder(self):
        for bad in ('../escape', 'a/b', '', 'A1B2C3D4E5F6'):
            with self.assertRaises(ps.ProjectError):
                self.library.load(bad)

    def test_a_damaged_file_does_not_break_the_list(self):
        self.library.save('a1b2c3d4e5f6', self.raw)
        (self.library.folder / '0000000000aa.p2p').write_bytes(b'junk')
        names = [p['name'] for p in self.library.projects()]
        self.assertIn('Brisket', names)
        self.assertTrue(any('damaged' in n for n in names))


class InTheApp(unittest.TestCase):
    """The Project pop-over: save to the library, Clear all, open it again: the page is the same as before."""

    def setUp(self):
        self.root = tempfile.mkdtemp()
        os.environ['P2P_MODE'], os.environ['P2P_DATA'] = 'library', self.root

    def tearDown(self):
        os.environ.pop('P2P_MODE', None)
        os.environ.pop('P2P_DATA', None)
        shutil.rmtree(self.root, ignore_errors=True)

    def test_save_clear_open_restores_the_page(self):
        profiles, sources = cook()
        at = page(profiles)
        at.session_state['source_files'] = sources
        first = profiles[0].profile_id
        # Change things a user would change.
        at.number_input(key=f'edit_{first}_offset_min').set_value(12.0).run()
        at.selectbox(key=f'edit_{first}_style').set_value('Dotted').run()
        at.button_group(key='alignment_selector').set_value('Clock').run()
        at.number_input(key='target_count').set_value(2).run()
        at.text_input(key='target_name_0').set_value('Pit target').run()
        at.number_input(key='target_value_0').set_value(120.0).run()
        at.text_input(key='project_name').set_value('Brisket 25 Oct').run()
        at.date_input(key='project_date').set_value(date(2026, 10, 25)).run()
        at.text_area(key='project_notes').set_value('Wrapped at 16:40.').run()
        at.button(key='save_project_library').click().run()
        self.assertEqual(problems(at), [])
        before = [p for p in at.session_state['profiles']]
        saved = ps.Library(self.root).projects()
        self.assertEqual([(s['name'], s['date'], s['profiles']) for s in saved], [('Brisket 25 Oct', date(2026, 10, 25), 5)])

        at.button(key='clear_profiles_button').click().run()
        self.assertEqual(at.session_state['profiles'], [])
        at.button(key='open_library_project').click().run()
        self.assertEqual(problems(at), [])
        same_profiles(self, before, at.session_state['profiles'])
        self.assertAlmostEqual(at.session_state['profiles'][0].offset_hours, 0.2)
        self.assertEqual(at.session_state['profiles'][0].line_style, 'dot')
        self.assertEqual(at.button_group(key='alignment_selector').value, 'Clock')
        self.assertEqual(at.number_input(key='target_count').value, 2)
        self.assertEqual((at.text_input(key='target_name_0').value, at.number_input(key='target_value_0').value), ('Pit target', 120.0))
        self.assertEqual(at.text_input(key='project_name').value, 'Brisket 25 Oct')
        self.assertEqual(at.text_area(key='project_notes').value, 'Wrapped at 16:40.')
        self.assertEqual(at.session_state['source_files'].keys(), sources.keys())
        self.assertTrue(any('Opened project "Brisket 25 Oct" from the library' in m for m in at.session_state['import_messages']))
        self.assertEqual(at.number_input(key=f'edit_{first}_offset_min').value, 12.0)   # the profile fields show the project
        self.assertEqual([w.value for w in at.warning], [])                               # no "set via Session State" warnings

    def test_delete_needs_the_tick(self):
        profiles, sources = cook()
        at = page(profiles)
        at.button(key='save_project_library').click().run()
        at.button(key='delete_library_project').click().run()
        self.assertEqual(len(ps.Library(self.root).projects()), 1)
        self.assertIn('Tick "Yes, delete it" first.', [e.value for e in at.error])
        at.checkbox(key='library_confirm_delete').check().run()
        at.button(key='delete_library_project').click().run()
        self.assertEqual(ps.Library(self.root).projects(), [])

    def test_empty_page_can_open_a_project(self):
        profiles, sources = cook()
        ps.Library(self.root).save('a1b2c3d4e5f6', ps.project_bytes({'id': 'a1b2c3d4e5f6', 'name': 'Old cook'}, profiles, {}, sources))
        at = page([])
        self.assertEqual(problems(at), [])
        at.button(key='open_library_project').click().run()
        self.assertEqual(problems(at), [])
        self.assertEqual(len(at.session_state['profiles']), 5)
        self.assertTrue(at.get('plotly_chart'))


class WithoutLibrary(unittest.TestCase):
    """Streamlit Cloud and laptops: project files only; nothing is written to the server."""

    def test_no_library_controls(self):
        os.environ.pop('P2P_MODE', None)
        profiles, _ = cook()
        at = page(profiles)
        self.assertEqual(problems(at), [])
        keys = {w.key for w in list(at.button) + list(at.selectbox)}
        self.assertNotIn('save_project_library', keys)
        self.assertNotIn('library_choice', keys)
        self.assertIn('open_project_file', keys)
        self.assertEqual([b.proto.label for b in at.get('download_button')][0], 'Save project file')
        first_day = min(p.data.timestamp.min() for p in profiles if 'timestamp' in p.data).date()
        self.assertEqual(at.text_input(key='project_name').value, f'Cook {first_day:%d-%b-%y}')   # the day of the first reading


if __name__ == '__main__':
    unittest.main()


class Deployment(unittest.TestCase):
    """NAS files (Docker / Synology Container Manager), as for the Bresaola Tracker."""
    ROOT = Path(__file__).resolve().parents[1]

    def test_image_tag_is_the_app_version(self):
        # A fixed image name made Container Manager reuse the old image (Bresaola, 27 Oct 2026).
        from version import VERSION
        tag = __import__('re').search(r'^\s*image:\s*probe-2-plot:(\S+)', (self.ROOT / 'compose.yaml').read_text(), __import__('re').M)
        self.assertTrue(tag)
        self.assertEqual(tag.group(1), VERSION)

    def test_library_mode_port_and_volume(self):
        compose = (self.ROOT / 'compose.yaml').read_text()
        for line in ('P2P_MODE: library', 'P2P_DATA: /data', '- ./data:/data', 'network_mode: host', '--server.port=8522'):
            self.assertIn(line, compose)
        self.assertIn('P2P_MODE=library', (self.ROOT / 'Dockerfile').read_text())

    def test_data_stays_out_of_git_and_image(self):
        for name in ('.gitignore', '.dockerignore'):
            lines = (self.ROOT / name).read_text().split()
            self.assertIn('data/', lines, name)
            self.assertIn('*.p2p', lines, name)


class AutoUpdateScript(unittest.TestCase):
    """scripts/nas-update.sh, run against a local git repository and a stand-in `docker` (no network, no Docker)."""
    ROOT = Path(__file__).resolve().parents[1]

    def setUp(self):
        import shutil
        import subprocess
        import tempfile
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.git = lambda *a, cwd=None: subprocess.run(['git', '-c', 'user.name=t', '-c', 'user.email=t@t', *a], cwd=cwd,
                                                       check=True, capture_output=True, text=True).stdout.strip()
        self.origin = self.tmp / 'origin'
        self.origin.mkdir()
        self.git('init', '-q', '-b', 'stable', cwd=self.origin)
        self.release('1.0.0')
        # the NAS folder as it comes from a ZIP: the same files, no .git, plus the library
        self.app = self.tmp / 'nas' / 'probe-2-plot'
        shutil.copytree(self.origin, self.app, ignore=shutil.ignore_patterns('.git'))
        (self.app / 'scripts').mkdir(exist_ok=True)
        shutil.copy(self.ROOT / 'scripts' / 'nas-update.sh', self.app / 'scripts' / 'nas-update.sh')
        (self.app / 'data' / 'projects').mkdir(parents=True)
        (self.app / 'data' / 'projects' / 'aaaaaaaaaaaa.p2p').write_bytes(b'precious')
        # stand-ins: docker reports the version of the checked-out files (or a wrong one for 9.9.9), curl succeeds
        self.bin = self.tmp / 'bin'
        self.bin.mkdir()
        (self.bin / 'docker').write_text(
            '#!/bin/sh\ncase "$1" in\n  exec) v=$(sed -n "s/^VERSION *= *\'\\([^\']*\\)\'.*/\\1/p" "$APP_DIR/version.py"); '
            '[ "$v" = 9.9.9 ] && v=0.0.0; echo "$v";;\n  images) ;;\n  *) exit 0;;\nesac\n')
        (self.bin / 'curl').write_text('#!/bin/sh\nexit 0\n')
        for f in ('docker', 'curl'):
            (self.bin / f).chmod(0o755)

    def release(self, version):
        (self.origin / 'version.py').write_text(f"VERSION = '{version}'\n")
        (self.origin / 'compose.yaml').write_text(f'services:\n  probe-2-plot:\n    image: probe-2-plot:{version}\n')
        self.git('add', '-A', cwd=self.origin)
        self.git('commit', '-q', '-m', f'v{version}', cwd=self.origin)

    def run_script(self):
        import os
        import subprocess
        env = dict(os.environ, PATH=f'{self.bin}:{os.environ["PATH"]}', REPO=str(self.origin), WAIT='1',
                   APP_DIR=str(self.app))
        r = subprocess.run(['sh', str(self.app / 'scripts' / 'nas-update.sh')], env=env, capture_output=True, text=True)
        return r.returncode, r.stdout + r.stderr

    def test_first_run_update_then_up_to_date_then_bad_version_rolls_back(self):
        code, out = self.run_script()
        self.assertEqual(code, 0, out)
        self.assertIn('OK: 1.0.0 is running', out)
        # the library is untouched and a copy was made first
        self.assertEqual((self.app / 'data' / 'projects' / 'aaaaaaaaaaaa.p2p').read_bytes(), b'precious')
        copies = list((self.app / 'data' / 'pre-update').glob('projects-*/aaaaaaaaaaaa.p2p'))
        self.assertEqual(len(copies), 1)

        code, out = self.run_script()
        self.assertEqual((code, 'up to date' in out), (0, True), out)

        self.release('1.0.1')
        code, out = self.run_script()
        self.assertEqual(code, 0, out)
        self.assertIn('OK: 1.0.1 is running', out)

        # a version whose container does not report itself correctly: back to 1.0.1, and not retried
        self.release('9.9.9')
        code, out = self.run_script()
        self.assertEqual(code, 1, out)
        self.assertIn('back on', out)
        self.assertIn('1.0.1', (self.app / 'version.py').read_text())
        self.assertTrue((self.app / 'update.failed').exists())
        code, out = self.run_script()
        self.assertEqual(code, 1)
        self.assertIn('not trying again', out)
        self.assertEqual((self.app / 'data' / 'projects' / 'aaaaaaaaaaaa.p2p').read_bytes(), b'precious')

        # the next release replaces the failed one
        self.release('1.0.2')
        code, out = self.run_script()
        self.assertEqual(code, 0, out)
        self.assertFalse((self.app / 'update.failed').exists())

    def test_runtime_files_stay_out_of_git_and_image(self):
        for name in ('.gitignore', '.dockerignore'):
            lines = (self.ROOT / name).read_text().split()
            self.assertIn('update.log', lines, name)
            self.assertIn('update.failed', lines, name)
