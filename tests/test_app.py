"""App regression tests with Streamlit's test runner. Run from the repository root:
python -m unittest discover -s tests -v

Every example file in tests/data is loaded into the page, which must build without an
error, and the main interactions (trim, reset, rename, remove, setpoint comparison) are
exercised on a small made-up cook.
"""
import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = Path(__file__).resolve().parent / 'data'
sys.path.insert(0, str(ROOT))

from streamlit.testing.v1 import AppTest  # noqa: E402
from profile_loader import load_uploaded_files  # noqa: E402

APP = str(ROOT / 'app.py')



def captions(at):
    """Caption texts as shown on the page (app.md backslash-escapes Markdown characters in names since v1.8.1)."""
    return [re.sub(r'\\(.)', r'\1', c.value) for c in at.caption]


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
        return next(w for w in widgets if w.key and w.key.startswith('edit_') and w.key.endswith(suffix))

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
        self.assertTrue(any('+0:03:30' in c for c in captions(self.at)), [c for c in captions(self.at)])

    def test_rename_warning_clears_on_another_profile(self):   # L1
        names = [p.name for p in self.profiles]
        next(t for t in self.at.text_input if t.key and t.key.startswith('edit_') and t.key.endswith('_name')).set_value(names[1]).run()
        self.assertIn('Profile names must be unique.', [w.value for w in self.at.warning])
        self.at.selectbox(key='selected_profile_id').set_value(self.profiles[2].profile_id).run()
        self.assertNotIn('Profile names must be unique.', [w.value for w in self.at.warning])

    def test_devices_card(self):   # L5; D7 (v1.8.2): the card counts probes, and says how many files
        labels = {m.label: m.value for m in self.at.metric}
        self.assertNotIn('CHANNELS', labels)
        self.assertEqual(labels.get('PROBES'), '5')                      # cavity + 2 probes, setpoint + 1 probe
        self.assertEqual(next(m for m in self.at.metric if m.label == 'PROBES').proto.delta, 'From 2 files')

    def test_clock_alignment_names_profiles_without_clock_times(self):   # L9
        elapsed, _ = load_uploaded_files([Upload(DATA / 'h2_elapsed_hours.csv')])
        at = AppTest.from_file(APP, default_timeout=120)
        at.session_state['profiles'] = self.profiles + elapsed
        at.session_state['alignment_selector'] = 'Clock'
        at.run()
        self.assertEqual(problems(at), [])
        notes = ' '.join(c for c in captions(at))
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
        self.assertTrue(any('left as they were' in c for c in captions(at)))   # the 15:34 file has nothing inside
        self.assertTrue(any('Window: 10:00 to 10:05 on 03/10/2026, all 5 profiles' in c for c in captions(at)), [c for c in captions(at)])
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
        self.assertTrue(any(c.startswith(name + '  |  ') for c in captions(self.at)), [c for c in captions(self.at)])

    def test_download_button_present(self):   # M6: the file is built on click
        self.assertEqual(self.at.get('download_button')[1].proto.label, 'Download Excel file')   # [0] = Save project file (v1.9.0)


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
        self.assertEqual(layout['title']['subtitle']['text'], '5 profiles  |  5 probes  |  0.0 - 0.1 h duration range')
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
        status = next(c for c in captions(at) if c.startswith(self.profiles[0].name))
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
        self.assertFalse(any(f['layout'].get('shapes') for f, _ in self.charts()))   # none by default
        at.number_input(key='target_count').set_value(1).run()
        self.assertEqual(at.number_input(key='target_value_0').value, 200.0)
        at.number_input(key='target_value_0').set_value(185).run()
        self.assertEqual(problems(at), [])
        figures = [f for f, _ in self.charts()]
        for figure in (figures[0], figures[-1]):                                  # comparison and selected profile
            shape = figure['layout']['shapes'][0]
            self.assertEqual((shape['y0'], shape['y1'], shape['line']['dash']), (185, 185, 'dot'))
            self.assertIn('Target 185 °C', [a['text'] for a in figure['layout']['annotations']])


class V173TargetLines(unittest.TestCase):
    def setUp(self):
        self.profiles, _ = load_uploaded_files([Upload(DATA / 'ok_device_cest.csv'), Upload(DATA / 'h5_fixed_setpoint.csv')])
        self.at = page(self.profiles)

    def layout(self, index=0):
        import json
        return json.loads(self.at.get('plotly_chart')[index].proto.spec)['layout']

    def test_several_named_target_lines(self):
        at = self.at
        at.number_input(key='target_count').set_value(3).run()
        at.text_input(key='target_name_0').set_value('Pit')
        at.number_input(key='target_value_0').set_value(120)
        at.text_input(key='target_name_1').set_value('Meat <done>')
        at.number_input(key='target_value_1').set_value(95)
        at.text_input(key='target_name_2').set_value('')                         # empty name: numbered
        at.run()
        self.assertEqual(problems(at), [])
        for index in (0, -1):
            layout = self.layout(index)
            self.assertEqual(sorted(s['y0'] for s in layout['shapes']), [95, 120, 120])   # third keeps its default 120
            labels = [a['text'] for a in layout['annotations']]
            for label in ('Pit 120 °C', 'Meat &lt;done&gt; 95 °C', 'Target 3 120 °C'):
                self.assertIn(label, labels)

    def test_fewer_lines_after_lowering_the_count(self):
        at = self.at
        at.number_input(key='target_count').set_value(4).run()
        self.assertEqual(len(self.layout()['shapes']), 4)
        at.number_input(key='target_count').set_value(2).run()
        self.assertEqual(len(self.layout()['shapes']), 2)
        at.number_input(key='target_count').set_value(0).run()
        self.assertFalse(self.layout().get('shapes'))

    def test_at_most_five(self):
        self.assertEqual(self.at.number_input(key='target_count').max, 5)


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
        self.assertEqual(at.selectbox(key='imp_test_0_role').value, 'Ambient')
        self.assertEqual(at.text_input(key='imp_test_5_probe').value, 'ok_device_cest Probe 1')
        preview = next(c for c in captions(at) if c.startswith('Will be added as'))
        for name in ('c2d_typhur_probe_1 - Ambient', 'c2d_typhur_probe_1 - Meat', 'c2d_typhur_probe_2 - Ambient', 'ok_device_cest - Pit',
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
        self.assertEqual(by_name['c2d_typhur_probe_1 - Ambient'].color, by_name['c2d_typhur_probe_1 - Meat'].color)   # one probe, one colour
        self.assertEqual(len({p.color for p in profiles}), 5)                                                     # 5 probes
        self.assertTrue(by_name['ok_device_cest - Pit'].role == 'Pit' and not by_name['ok_device_cest - Pit'].is_setpoint)
        traces = {t['name']: t.get('line', {}).get('dash') for t in json.loads(at.get('plotly_chart')[0].proto.spec)['data']}
        self.assertIsNone(traces['c2d_typhur_probe_1 - Ambient'])     # v1.7.1: solid unless a style is chosen
        self.assertIsNone(traces['ok_device_cest - Pit'])
        self.assertIsNone(traces['c2d_typhur_probe_1 - Meat'])

    def test_choices_are_applied(self):
        at = self.at
        at.checkbox(key='imp_test_0_use').uncheck()                    # leave out probe 1 ambient
        at.selectbox(key='imp_test_1_role').set_value('Point')
        at.text_input(key='imp_test_1_probe').set_value('Typhur 1').run()
        self.assertIn('Typhur 1 - Point', next(c for c in captions(at) if c.startswith('Will be added as')))
        at.button(key='apply_import').click().run()
        names = [p.name for p in at.session_state['profiles']]
        self.assertEqual(len(names), 6)
        self.assertIn('Typhur 1 - Point', names)
        self.assertNotIn('c2d_typhur_probe_1 - Ambient', names)
        self.assertTrue(any('1 column(s) left out' in m for m in at.session_state['import_messages']))

    def test_cancel_adds_nothing(self):
        at = self.at
        at.button(key='cancel_import').click().run()
        self.assertEqual(at.session_state['profiles'], [])
        self.assertNotIn('pending_import', at.session_state)
        self.assertTrue(any('Start: add your cook files' in m.value for m in at.markdown))

    def test_typed_start_flagged_in_the_status_line(self):
        at = self.at
        at.button(key='apply_import').click().run()
        typed = next(p for p in at.session_state['profiles'] if p.metadata.get('start_source') == 'typed')
        at.selectbox(key='selected_profile_id').set_value(typed.profile_id).run()
        self.assertTrue(any('start time typed in Chart-2-Data, check it' in c for c in captions(at)))

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


class V171LineStyle(unittest.TestCase):
    def setUp(self):
        self.profiles, _ = load_uploaded_files([Upload(DATA / 'ok_device_cest.csv'), Upload(DATA / 'h5_fixed_setpoint.csv')])
        self.at = page(self.profiles)

    def dashes(self):
        import json
        return {t['name']: t.get('line', {}).get('dash') for t in json.loads(self.at.get('plotly_chart')[0].proto.spec)['data']}

    def test_line_style_per_profile(self):
        at = self.at
        selected = at.session_state['selected_profile_id']
        name = next(p.name for p in self.profiles if p.profile_id == selected)
        box = at.selectbox(key=f'edit_{selected}_style')
        self.assertEqual((box.label, box.value), ('Line style', 'Solid'))
        self.assertIsNone(self.dashes()[name])
        box.set_value('Dotted').run()
        self.assertEqual(problems(at), [])
        self.assertEqual(self.dashes()[name], 'dot')
        others = [p.name for p in self.profiles if p.profile_id != selected]
        self.assertTrue(all(self.dashes()[n] is None for n in others))            # only this profile changed

    def test_setpoint_role_starts_dashed_and_can_be_solid(self):
        at = self.at
        setpoint = next(p for p in self.profiles if p.channel == 'Setpoint')
        at.selectbox(key='selected_profile_id').set_value(setpoint.profile_id).run()
        at.selectbox(key=f'edit_{setpoint.profile_id}_role').set_value('Setpoint').run()
        name = next(p.name for p in at.session_state['profiles'] if p.profile_id == setpoint.profile_id)
        self.assertEqual(at.selectbox(key=f'edit_{setpoint.profile_id}_style').value, 'Dashed')
        self.assertEqual(self.dashes()[name + ' (setpoint)'], 'dash')
        at.selectbox(key=f'edit_{setpoint.profile_id}_style').set_value('Solid').run()
        self.assertIsNone(self.dashes()[name + ' (setpoint)'])


class V172Logo(unittest.TestCase):
    def test_monitoring_logo_in_title(self):
        at = page([])
        logos = [m.value for m in list(at.markdown) + list(at.sidebar.markdown) if 'cp-logo' in m.value]
        self.assertTrue(any('page-title' in m and '>monitoring</span>Probe-2-Plot' in m for m in logos), logos)
        source = (Path(__file__).resolve().parent.parent / 'app.py').read_text()
        self.assertIn("LOGO = 'monitoring'", source)
        self.assertIn("page_icon=f':material/{LOGO}:'", source)


class V174TextSizeAndTargetLabels(unittest.TestCase):
    def setUp(self):
        self.profiles, _ = load_uploaded_files([Upload(DATA / 'ok_device_cest.csv'), Upload(DATA / 'h5_fixed_setpoint.csv')])
        self.at = page(self.profiles)

    def layouts(self):
        import json
        return [json.loads(c.proto.spec)['layout'] for c in self.at.get('plotly_chart')]

    def test_all_target_labels_on_the_left(self):
        at = self.at
        at.number_input(key='target_count').set_value(3).run()
        for layout in (self.layouts()[0], self.layouts()[-1]):
            targets = [a for a in layout['annotations'] if a['text'].endswith('°C')]
            self.assertEqual(len(targets), 3)
            self.assertTrue(all(a['x'] == 0 and a['xanchor'] == 'left' for a in targets), targets)

    def test_close_targets_label_above_and_below(self):
        at = self.at
        at.number_input(key='target_count').set_value(3).run()
        for i, value in enumerate((230, 80, 72)):
            at.number_input(key=f'target_value_{i}').set_value(value)
        at.run()
        labels = {a['text']: a['yanchor'] for a in self.layouts()[0]['annotations'] if a['text'].endswith('°C')}
        self.assertEqual(labels['Target 230 °C'], 'bottom')      # above its line
        self.assertEqual(labels['Target 2 80 °C'], 'bottom')
        self.assertEqual(labels['Target 3 72 °C'], 'top')        # 8 °C under another target: below its line

    def test_chart_text_size(self):
        at = self.at
        base = self.layouts()[0]
        self.assertEqual((base['title']['font']['size'], base['xaxis']['tickfont']['size'], base['yaxis']['title']['font']['size']), (18, 12, 14))
        at.button_group(key='chart_text_size').set_value('150%').run()
        self.assertEqual(problems(at), [])
        for layout in self.layouts():                                            # every chart, including Setpoint vs measured
            self.assertEqual(layout['xaxis']['tickfont']['size'], 18)
            self.assertEqual(layout['yaxis']['title']['font']['size'], 21)
            self.assertEqual(layout['legend']['font']['size'], 16)
        big = self.layouts()[0]
        self.assertEqual(big['title']['font']['size'], 27)
        self.assertGreater(big['margin']['t'], base['margin']['t'])


class V176RolesShown(unittest.TestCase):
    def setUp(self):
        self.profiles, _ = load_uploaded_files([Upload(DATA / 'c2d_typhur_probe_1.csv'), Upload(DATA / 'ok_device_cest.csv')])
        roles = {'Ambient temperature': 'Ambient', 'Meat temperature': 'Meat', 'cavity temperature': 'Pit', 'Probe 1': 'Meat', 'Probe 2': 'Meat'}
        for p in self.profiles:
            p.role = roles[p.channel]
        self.at = page(self.profiles)

    def chart(self):
        import json
        return json.loads(self.at.get('plotly_chart')[0].proto.spec)

    def pills(self):
        return next(g for g in self.at.get('button_group') if str(g.key).startswith('roles_shown_'))

    def test_legend_grouped_by_role_and_beside_the_plot(self):
        figure = self.chart()
        titles = [t['legendgrouptitle']['text'] for t in figure['data']]
        self.assertEqual(titles, sorted(titles, key=['Meat', 'Point', 'Flat', 'Ambient', 'Grate', 'Pit', 'Hold', 'Setpoint', 'Other'].index))
        self.assertEqual(figure['layout']['legend']['orientation'], 'v')
        self.assertEqual(self.pills().options, ['Meat', 'Ambient', 'Pit'])

    def test_switching_a_role_off_and_keeping_it_off(self):
        at = self.at
        self.pills().set_value(['Ambient', 'Pit']).run()
        self.assertEqual(problems(at), [])
        figure = self.chart()
        self.assertEqual({t['legendgrouptitle']['text'] for t in figure['data']}, {'Ambient', 'Pit'})
        self.assertIn('hidden: Meat', figure['layout']['title']['subtitle']['text'])
        self.assertTrue(figure['layout']['title']['subtitle']['text'].startswith('2 of 5 profiles'))
        at.toggle(key='grid_lines_toggle').set_value(False).run()                 # any other change keeps the choice
        self.assertEqual({t['legendgrouptitle']['text'] for t in self.chart()['data']}, {'Ambient', 'Pit'})
        self.assertEqual(set(self.pills().value), {'Ambient', 'Pit'})
        self.pills().set_value(['Meat', 'Ambient', 'Pit']).run()
        self.assertEqual(len(self.chart()['data']), 5)
        self.assertNotIn('hidden', self.chart()['layout']['title']['subtitle']['text'])


class V177Name(unittest.TestCase):
    def test_new_name_in_tab_and_title(self):
        source = APP.read_text(encoding='utf-8') if hasattr(APP, 'read_text') else open(APP, encoding='utf-8').read()
        self.assertIn("page_title='Probe-2-Plot'", source)
        self.assertEqual(source.count('</span>Probe-2-Plot</div>'), 1)
        self.assertNotIn('Cook Profile Dashboard', source)
        self.assertNotIn('Chart to Data', source)


class V178UploadHint(unittest.TestCase):
    def test_upload_hint_uses_the_muted_text_colour(self):
        # Streamlit draws "200MB per file" in its light-theme grey (1.2:1 on the dark upload box) unless overridden.
        source = open(APP, encoding='utf-8').read()
        self.assertIn('[data-testid="stFileUploaderDropzoneInstructions"] * {{color:var(--muted)!important;}}', source)


class V180Toolbar(unittest.TestCase):
    """v1.8.0: no sidebar; a start card before the first import, then a toolbar with Add files and Chart options pop-overs."""

    def test_empty_page_has_start_card_and_no_sidebar(self):
        at = page([])
        self.assertEqual(problems(at), [])
        self.assertEqual(len(at.sidebar.children), 0)
        self.assertTrue(any('Start: add your cook files' in m.value for m in at.markdown))
        self.assertEqual(len(at.get('file_uploader')), 2)          # cook files + Open a project file (v1.9.0)
        self.assertEqual([p.proto.popover.label for p in at.get('popover')], ['Project', 'Chart options', 'Clear all'])     # no Add files before the first import
        self.assertTrue(at.button(key='clear_profiles_button').disabled)

    def test_toolbar_after_import(self):
        profiles, _ = load_uploaded_files([Upload(DATA / 'ok_device_cest.csv')])
        at = page(profiles)
        self.assertEqual(problems(at), [])
        self.assertFalse(any('Start: add your cook files' in m.value for m in at.markdown))
        self.assertEqual([p.proto.popover.label for p in at.get('popover')], ['Project', 'Add files', 'Chart options', 'Clear all'])
        self.assertEqual(len(at.get('file_uploader')), 2)                                   # Add files + Open a project file
        for key in ('alignment_selector', 'smoothing_selector', 'theme_selector', 'chart_text_size', 'image_format_selector'):
            self.assertTrue(any(w.key == key for w in at.get('button_group')), key)
        at.toggle(key='grid_lines_toggle').set_value(False).run()                             # Chart options still work
        at.number_input(key='target_count').set_value(2).run()
        self.assertEqual(problems(at), [])
        self.assertEqual(len([w for w in at.text_input if str(w.key).startswith('target_name_')]), 2)

    def test_import_notes_folded_with_count(self):
        at = page([])
        at.session_state['import_messages'] = ['a.csv: note one.', 'Imported 1 profile(s).']
        at.run()
        self.assertTrue(any(e.label == 'Import notes (2)' for e in at.expander))



class V181ClearAllAndNames(unittest.TestCase):
    """v1.8.1: Clear all asks first and starts the next cook clean; names are shown exactly as written."""

    def setUp(self):
        self.profiles, _ = load_uploaded_files([Upload(DATA / 'c2d_typhur_probe_1.csv'), Upload(DATA / 'ok_device_cest.csv')])
        for p in self.profiles:
            p.role = 'Ambient' if 'Ambient' in p.channel else 'Pit' if 'cavity' in p.channel else 'Meat'

    def pills(self, at):
        return next(g for g in at.get('button_group') if str(g.key).startswith('roles_shown_'))

    def test_clear_all_confirms_and_resets_state(self):
        at = page(self.profiles)
        self.assertEqual(at.button(key='clear_profiles_button').label, f'Remove all {len(self.profiles)} profiles')
        self.pills(at).set_value(['Ambient', 'Pit']).run()                      # Meat hidden
        at.session_state['import_messages'] = ['old note']
        at.run()
        at.button(key='clear_profiles_button').click().run()
        self.assertEqual(problems(at), [])
        self.assertEqual(at.session_state['profiles'], [])
        for key in ('hidden_roles', 'import_messages', 'group_trim_note'):
            self.assertNotIn(key, at.session_state)
        self.assertFalse(any(e.label.startswith('Import notes') for e in at.expander))
        at.session_state['profiles'] = list(self.profiles)                        # the next cook shows every role
        at.session_state['visible_profile_ids'] = [p.profile_id for p in self.profiles]
        at.run()
        self.assertEqual(sorted(self.pills(at).value), ['Ambient', 'Meat', 'Pit'])

    def test_all_roles_hidden_says_so(self):
        at = page(self.profiles)
        self.pills(at).set_value([]).run()
        self.assertEqual(problems(at), [])
        spec = json.loads(at.get('plotly_chart')[0].proto.spec)
        self.assertTrue(spec['layout']['title']['subtitle']['text'].startswith('All roles hidden'))

    def test_names_shown_as_written_in_captions(self):
        self.profiles[0].name = 'Typhur_1 [x](y) $5$'
        at = page(self.profiles)
        at.selectbox(key='selected_profile_id').set_value(self.profiles[0].profile_id).run()
        raw = next(c.value for c in at.caption if 'samples shown' in c.value)
        self.assertTrue(raw.startswith(r'Typhur\_1 \[x\]\(y\) \$5\$'), raw)
        self.assertTrue(captions(at) and any(c.startswith('Typhur_1 [x](y) $5$') for c in captions(at)))

    def test_role_help_explains_every_role(self):
        at = page(self.profiles)
        role_select = next(s for s in at.selectbox if str(s.key).endswith('_role'))
        for role in ('Ambient', 'Grate', 'Pit', 'Setpoint'):
            self.assertIn(f'**{role}**', role_select.help)


class V182ProbeField(unittest.TestCase):
    """D8: the probe label can be changed in Profile details; colour and the default name follow it."""

    def setUp(self):
        self.profiles, _ = load_uploaded_files([Upload(DATA / 'c2d_typhur_probe_1.csv'), Upload(DATA / 'c2d_typhur_probe_2.csv')])
        for p in self.profiles:                                             # as Check the import names them
            p.role = 'Ambient' if 'Ambient' in p.channel else 'Meat'
            p.probe = Path(p.source_file).stem
            p.name = f'{p.probe} - {p.role}'
        from profile_loader import COLORS
        from roles import probe_colours
        colours = probe_colours([p.probe for p in self.profiles], [], COLORS)
        for p in self.profiles:
            p.color = colours[p.probe]
        self.at = page(self.profiles)
        self.by_name = {p.name: p for p in self.at.session_state['profiles']}

    def select(self, name):
        self.at.selectbox(key='selected_profile_id').set_value(self.by_name[name].profile_id).run()
        return self.by_name[name]

    def test_new_probe_gets_its_own_colour_and_name(self):
        p = self.select('c2d_typhur_probe_1 - Meat')
        partner = self.by_name['c2d_typhur_probe_1 - Ambient']
        self.assertEqual(p.color, partner.color)
        self.at.text_input(key=f'edit_{p.profile_id}_probe').set_value('Typhur 1 point').run()
        self.assertEqual(problems(self.at), [])
        p = next(q for q in self.at.session_state['profiles'] if q.profile_id == p.profile_id)
        self.assertEqual((p.probe, p.name), ('Typhur 1 point', 'Typhur 1 point - Meat'))
        self.assertNotEqual(p.color, partner.color)
        self.assertNotIn(p.color, {q.color for q in self.at.session_state['profiles'] if q is not p})
        self.assertEqual(self.at.color_picker(key=f'edit_{p.profile_id}_color').value.lower(), p.color.lower())

    def test_joining_a_probe_takes_its_colour(self):
        p = self.select('c2d_typhur_probe_2 - Meat')
        target = self.by_name['c2d_typhur_probe_1 - Ambient']
        self.at.text_input(key=f'edit_{p.profile_id}_probe').set_value('c2d_typhur_probe_1').run()
        p = next(q for q in self.at.session_state['profiles'] if q.profile_id == p.profile_id)
        self.assertEqual(p.color, target.color)
        self.assertEqual(p.name, 'c2d_typhur_probe_1 - Meat 2')            # c2d_typhur_probe_1 - Meat is taken

    def test_blank_probe_is_ignored(self):
        p = self.select('c2d_typhur_probe_1 - Meat')
        self.at.text_input(key=f'edit_{p.profile_id}_probe').set_value('  ').run()
        self.assertEqual(self.at.text_input(key=f'edit_{p.profile_id}_probe').value, 'c2d_typhur_probe_1')



class V183ImportHeaderTooltips(unittest.TestCase):
    """v1.8.1 put the role explanations, with blank lines, into the Role header's tooltip: the blank line ended the HTML
    block, so the explanations were printed across the Check the import card and the header became '">Role'."""

    def test_headers_are_one_line_of_html(self):
        profiles, _ = load_uploaded_files([Upload(DATA / 'c2d_typhur_probe_1.csv')])
        at = page([])
        at.session_state['pending_import'] = {'profiles': profiles, 'messages': [], 'keep': True, 'batch': 'test'}
        at.run()
        heads = [m.value for m in at.markdown if 'class="import-head"' in m.value]
        self.assertEqual(len(heads), 4)
        for head in heads:
            self.assertNotIn('\n', head)
            self.assertRegex(head, r'^<div class="import-head" title="[^"<>]*">[^<>"]+</div>$')
        role = next(h for h in heads if h.endswith('>Role</div>'))
        self.assertIn('Ambient: Air right next to the meat', role)
        self.assertIn('&#10;', role)


class V184CardsUnderTheChart(unittest.TestCase):
    """Owner's request (6 Nov 2026): the overview cards sit under the comparison chart, so the toolbar is right above
    the Profile details and chart card."""

    def order(self, at):
        out = []

        def walk(node):
            for child in getattr(node, 'children', {}).values():
                kind = getattr(child, 'type', '')
                if kind == 'metric':
                    out.append(('metric', child.label))
                elif kind == 'plotly_chart':
                    out.append(('chart', None))
                elif getattr(child, 'key', None) in ('alignment_selector',):
                    out.append(('toolbar', None))
                walk(child)
        walk(at._tree)
        return out

    def test_toolbar_then_chart_then_cards(self):
        profiles, _ = load_uploaded_files([Upload(DATA / 'ok_device_cest.csv')])
        at = page(profiles)
        order = self.order(at)
        first = lambda item: order.index(item)  # noqa: E731
        self.assertLess(first(('toolbar', None)), first(('chart', None)))
        self.assertLess(first(('chart', None)), first(('metric', 'PROFILES')))
        self.assertEqual([label for kind, label in order if kind == 'metric'][:4],
                         ['PROFILES', 'PROBES', 'DURATION RANGE', 'TEMPERATURE RANGE'])

    def test_profiles_shown_box_is_themed_on_streamlit_166(self):
        # Streamlit 1.66 wraps the multiselect tags in a new box drawn in its light-theme grey (white on the dark page).
        source = open(APP, encoding='utf-8').read()
        self.assertIn('[data-testid="stMultiSelect"] div:has(> [data-testid="stMultiSelectTagsContainer"])', source)
