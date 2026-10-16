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
        self.assertTrue(any('Window: 10:00 to 10:05 on 03/10/2026, all 5 profiles' in c.value for c in at.caption), [c.value for c in at.caption])
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

    def test_full_profile_name_under_the_box(self):   # L6: since 1.6.9 the status line starts with the full name
        name = self.profiles[0].name
        self.assertTrue(any(c.value.startswith(name + '  |  ') for c in self.at.caption), [c.value for c in self.at.caption])

    def test_download_button_present(self):   # M6: the file is built on click
        self.assertEqual(self.at.get('download_button')[0].proto.label, 'Download Excel file')


class V168Layout(unittest.TestCase):
    def setUp(self):
        self.profiles, _ = load_uploaded_files([Upload(DATA / 'ok_device_cest.csv'), Upload(DATA / 'h5_fixed_setpoint.csv')])
        self.at = page(self.profiles)

    def test_charts_have_no_fixed_height_and_save_as_16_9(self):
        import json
        charts = self.at.get('plotly_chart')
        comparison_chart, single_chart = charts[0], charts[-1]
        for chart in (comparison_chart, single_chart):
            figure = json.loads(chart.proto.spec)
            self.assertNotIn('height', figure['layout'])          # the page sizes it at 16:9
            image = json.loads(chart.proto.config)['toImageButtonOptions']
            self.assertEqual((image['width'], image['height']), (1600, 900))

    def test_profile_details_come_before_the_chart(self):
        # Profile details is a full-width card between the overview cards and the comparison chart.
        source = (Path(__file__).resolve().parent.parent / 'app.py').read_text()
        self.assertLess(source.index("key='profile_details_card'"), source.index("key='chart_comparison'"))
        self.assertNotIn('main, side = st.columns', source)
        self.assertEqual(self.at.selectbox(key=f"edit_{self.at.session_state['selected_profile_id']}_role").label, 'Role')   # replaced the setpoint tick in v1.7.0


class V169CompactLayout(unittest.TestCase):
    def setUp(self):
        self.profiles, _ = load_uploaded_files([Upload(DATA / 'ok_device_cest.csv'), Upload(DATA / 'h5_fixed_setpoint.csv')])
        self.at = page(self.profiles)

    def test_summary_is_the_chart_subtitle(self):
        import json
        layout = json.loads(self.at.get('plotly_chart')[0].proto.spec)['layout']
        self.assertEqual(layout['title']['text'], 'Temperature profiles')
        self.assertEqual(layout['title']['subtitle']['text'], '5 profiles  |  2 devices  |  0.0 - 0.1 h duration range')
        self.assertFalse(any('Temperature profile comparison' in m.value for m in self.at.markdown))

    def test_one_card_controls_then_chart_then_export(self):
        source = (Path(__file__).resolve().parent.parent / 'app.py').read_text()
        order = [source.index(k) for k in ("key='profile_details_card'", "key='selected_profile_id'", "key='trim_all'",
                                           "key='chart_comparison'", "key='export_interval'", "key='download_visible_profiles'")]
        self.assertEqual(order, sorted(order))

    def test_status_line_has_file_samples_and_offset(self):
        at = self.at
        selected = at.session_state['selected_profile_id']
        at.number_input(key=f'edit_{selected}_offset_min').set_value(3.5).run()
        status = next(c.value for c in at.caption if c.value.startswith(self.profiles[0].name))
        self.assertIn('ok_device_cest.csv', status)
        self.assertIn('samples shown', status)
        self.assertIn('offset +0:03:30 (h:mm:ss)', status)


class V1610DefaultsAndTarget(unittest.TestCase):
    def setUp(self):
        self.profiles, _ = load_uploaded_files([Upload(DATA / 'ok_device_cest.csv'), Upload(DATA / 'h5_fixed_setpoint.csv')])
        self.at = page(self.profiles)

    def charts(self):
        import json
        return [(json.loads(c.proto.spec), json.loads(c.proto.config)) for c in self.at.get('plotly_chart')]

    def test_opens_dark_with_jpeg_and_line_width_3_5(self):
        figure, config = self.charts()[0]
        self.assertEqual(figure['layout']['paper_bgcolor'], '#111827')          # dark chart background
        self.assertEqual(config['toImageButtonOptions']['format'], 'jpeg')
        self.assertEqual(self.at.number_input(key='line_width_input').value, 3.5)
        self.assertEqual(figure['data'][0]['line']['width'], 3.5)

    def test_target_line_on_both_profile_charts(self):
        at = self.at
        self.assertFalse(any(f['layout'].get('shapes') for f, _ in self.charts()))   # off by default
        at.toggle(key='target_line_toggle').set_value(True).run()
        self.assertEqual(at.number_input(key='target_value').value, 200.0)
        at.number_input(key='target_value').set_value(185).run()
        self.assertEqual(problems(at), [])
        figures = [f for f, _ in self.charts()]
        for figure in (figures[0], figures[-1]):                                  # comparison and selected profile
            shape = figure['layout']['shapes'][0]
            self.assertEqual((shape['y0'], shape['y1'], shape['line']['dash']), (185, 185, 'dot'))
            self.assertIn('Target 185 °C', [a['text'] for a in figure['layout']['annotations']])


class V170ImportReview(unittest.TestCase):
    """The column picker: nothing is added until the user confirms columns, roles and probes."""

    def setUp(self):
        self.new, self.messages = load_uploaded_files([Upload(DATA / 'c2d_typhur_probe_1.csv'), Upload(DATA / 'c2d_typhur_probe_2.csv'),
                                                       Upload(DATA / 'ok_device_cest.csv')])
        self.at = AppTest.from_file(APP, default_timeout=120)
        self.at.session_state['profiles'] = []
        self.at.session_state['pending_import'] = {'profiles': self.new, 'messages': self.messages, 'keep': True, 'batch': 'test'}
        self.at.run()

    def test_review_card_lists_every_column_with_defaults(self):
        at = self.at
        self.assertEqual(problems(at), [])
        self.assertTrue(any('Check the import' in m.value for m in at.markdown))
        self.assertEqual(at.session_state['profiles'], [])                       # nothing added yet
        self.assertEqual(len([c for c in at.checkbox if c.key and c.key.startswith('imp_test_')]), 7)
        self.assertEqual(at.selectbox(key='imp_test_0_role').value, 'Grate')
        self.assertEqual(at.text_input(key='imp_test_5_probe').value, 'ok_device_cest Probe 1')
        preview = next(c.value for c in at.caption if c.value.startswith('Will be added as'))
        for name in ('c2d_typhur_probe_1 - Grate', 'c2d_typhur_probe_1 - Meat', 'c2d_typhur_probe_2 - Grate', 'ok_device_cest - Pit',
                     'ok_device_cest Probe 1 - Meat', 'ok_device_cest Probe 2 - Meat'):
            self.assertIn(name, preview)

    def test_add_gives_roles_names_colours_and_line_styles(self):
        import json
        at = self.at
        at.button(key='apply_import').click().run()
        self.assertEqual(problems(at), [])
        profiles = at.session_state['profiles']
        self.assertNotIn('pending_import', at.session_state)
        self.assertEqual(len(profiles), 7)
        by_name = {p.name: p for p in profiles}
        self.assertEqual(by_name['c2d_typhur_probe_1 - Grate'].color, by_name['c2d_typhur_probe_1 - Meat'].color)   # one probe, one colour
        self.assertEqual(len({p.color for p in profiles}), 5)                                                     # 5 probes
        self.assertTrue(by_name['ok_device_cest - Pit'].role == 'Pit' and not by_name['ok_device_cest - Pit'].is_setpoint)
        traces = {t['name']: t.get('line', {}).get('dash') for t in json.loads(at.get('plotly_chart')[0].proto.spec)['data']}
        self.assertEqual(traces['c2d_typhur_probe_1 - Grate'], 'dashdot')
        self.assertEqual(traces['ok_device_cest - Pit'], 'longdash')
        self.assertIsNone(traces['c2d_typhur_probe_1 - Meat'])

    def test_choices_are_applied(self):
        at = self.at
        at.checkbox(key='imp_test_0_use').uncheck()                    # leave out probe 1 ambient
        at.selectbox(key='imp_test_1_role').set_value('Point')
        at.text_input(key='imp_test_1_probe').set_value('Typhur 1').run()
        self.assertIn('Typhur 1 - Point', next(c.value for c in at.caption if c.value.startswith('Will be added as')))
        at.button(key='apply_import').click().run()
        names = [p.name for p in at.session_state['profiles']]
        self.assertEqual(len(names), 6)
        self.assertIn('Typhur 1 - Point', names)
        self.assertNotIn('c2d_typhur_probe_1 - Grate', names)
        self.assertTrue(any('1 column(s) left out' in m for m in at.session_state['import_messages']))

    def test_cancel_adds_nothing(self):
        at = self.at
        at.button(key='cancel_import').click().run()
        self.assertEqual(at.session_state['profiles'], [])
        self.assertNotIn('pending_import', at.session_state)
        self.assertTrue(any('to begin' in i.value for i in at.info))

    def test_typed_start_flagged_in_the_status_line(self):
        at = self.at
        at.button(key='apply_import').click().run()
        typed = next(p for p in at.session_state['profiles'] if p.metadata.get('start_source') == 'typed')
        at.selectbox(key='selected_profile_id').set_value(typed.profile_id).run()
        self.assertTrue(any('start time typed in Chart to Data, check it' in c.value for c in at.caption))

    def test_role_change_renames_and_sets_the_setpoint(self):
        at = self.at
        at.button(key='apply_import').click().run()
        pit = next(p for p in at.session_state['profiles'] if p.role == 'Pit')
        at.selectbox(key='selected_profile_id').set_value(pit.profile_id).run()
        at.selectbox(key=f'edit_{pit.profile_id}_role').set_value('Setpoint').run()
        self.assertEqual(problems(at), [])
        pit = next(p for p in at.session_state['profiles'] if p.profile_id == pit.profile_id)
        self.assertEqual((pit.name, pit.is_setpoint), ('ok_device_cest - Setpoint', True))
        self.assertFalse(any('Set the Role of a profile to "Setpoint"' in i.value for i in at.info))   # comparison now available
