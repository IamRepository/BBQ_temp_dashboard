import streamlit as st
from profile_loader import load_uploaded_files
from chart_builder import comparison, single, deviation
from analysis import compare
from export_utils import profiles_to_zip
from version import VERSION

st.set_page_config(page_title='Cook Profile Dashboard', page_icon='CP', layout='wide', initial_sidebar_state='expanded')

if 'profiles' not in st.session_state:
    st.session_state.profiles = []
P = st.session_state.profiles


def reset_trim(profile, widget_key):
    # Runs as a button callback, i.e. before the slider is created in the next run.
    last = max(len(profile.data) - 1, 0)
    profile.trim_start, profile.trim_end = 0, last
    st.session_state[widget_key] = (0, last)


def remove_profile(profile_id):
    remaining = [p for p in st.session_state.profiles if p.profile_id != profile_id]
    st.session_state.profiles = remaining
    st.session_state.visible_profile_ids = [i for i in st.session_state.get('visible_profile_ids', []) if i != profile_id]
    st.session_state.selected_profile_id = remaining[0].profile_id if remaining else None


def clear_profiles():
    st.session_state.profiles = []
    st.session_state.visible_profile_ids = []
    st.session_state.selected_profile_id = None


def rename_profile(profile_id, widget_key):
    # Runs before the rerun, so the new name shows everywhere immediately.
    new_name = st.session_state[widget_key].strip()
    profile = next((p for p in st.session_state.profiles if p.profile_id == profile_id), None)
    if profile is None or not new_name or new_name == profile.name:
        st.session_state.rename_error = None
    elif any(p.name == new_name and p.profile_id != profile_id for p in st.session_state.profiles):
        st.session_state.rename_error = 'Profile names must be unique.'
    else:
        profile.name = new_name
        st.session_state.rename_error = None

with st.sidebar:
    st.markdown('<div class="side-brand">Cook Profile</div><div class="side-sub">Temperature dashboard</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-label">DATA</div>', unsafe_allow_html=True)
    files = st.file_uploader('Upload CSV or Excel files', type=['csv', 'xlsx', 'xls'], accept_multiple_files=True, key='uploaded_profile_files')
    keep = st.checkbox('Keep existing profiles', True, key='keep_existing_profiles')
    if st.button('Import uploaded files', type='primary', width='stretch', disabled=not files, key='import_profiles_button'):
        try:
            new, messages = load_uploaded_files(files)
            st.session_state.profiles = (P + new) if keep else new
            previously_shown = st.session_state.get('visible_profile_ids', []) if keep else []
            st.session_state.visible_profile_ids = previously_shown + [p.profile_id for p in new]
            st.session_state.import_messages = messages + [f'Imported {len(new)} profile(s).']
            st.rerun()
        except Exception as exc:
            st.error(f'Import failed: {exc}')
    st.button('Clear all profiles', width='stretch', key='clear_profiles_button', on_click=clear_profiles)
    if st.session_state.get('import_messages'):
        with st.expander('Import notes', expanded=True):
            for message in st.session_state.import_messages:
                st.caption(message)

    st.markdown('<div class="section-label">APPEARANCE</div>', unsafe_allow_html=True)
    theme = st.segmented_control('Theme', ['Light', 'Dark'], default='Light', key='theme_selector') or 'Light'
    alignment_modes = {'Start': 'Original timeline', 'Peak': 'Align peak', 'End': 'Align end', 'Clock': 'Clock time'}
    alignment_notes = {
        'Start': 'Every profile starts at zero.',
        'Peak': 'Every profile is centred on its own highest point.',
        'End': 'Every profile ends at zero.',
        'Clock': 'Real time of day, so profiles from different devices line up.',
    }
    alignment_choice = st.segmented_control('Timeline alignment', list(alignment_modes), default='Start', key='alignment_selector') or 'Start'
    alignment = alignment_modes[alignment_choice]
    st.caption(alignment_notes[alignment_choice])
    smoothing_options = {'Off': 0, '1 min': 1, '5 min': 5, '10 min': 10}
    smoothing_choice = st.segmented_control('Smoothing', list(smoothing_options), default='Off', key='smoothing_selector') or 'Off'
    smoothing_minutes = smoothing_options[smoothing_choice]
    st.caption('Rolling average on measured lines. Setpoints and exported data stay untouched.' if smoothing_minutes else 'Show readings exactly as logged.')
    with st.expander('Chart options'):
        grid = st.checkbox('Grid lines', True, key='grid_lines_toggle')
        legend = st.checkbox('Legend', True, key='legend_toggle')
        width = st.slider('Line width', 1.0, 5.0, 2.5, .5, key='line_width_slider')

is_dark = theme == 'Dark'
colors = {
    'page': '#0F172A' if is_dark else '#F8FAFC',
    'sidebar': '#111827' if is_dark else '#FFFFFF',
    'card': '#111827' if is_dark else '#FFFFFF',
    'card_alt': '#1F2937' if is_dark else '#F8FAFC',
    'text': '#F3F4F6' if is_dark else '#172033',
    'muted': '#9CA3AF' if is_dark else '#64748B',
    'border': '#263244' if is_dark else '#E2E8F0',
    'accent': '#2563EB',
    'accent_hover': '#1D4ED8',
    'danger': '#DC2626',
    'tag_bg': '#1F2937' if is_dark else '#E8EEF7',
    'tag_border': '#374151' if is_dark else '#D7E0EC',
    'tag_text': '#E5E7EB' if is_dark else '#334155',
    'shadow': '0 8px 24px rgba(0,0,0,.16)' if is_dark else '0 4px 16px rgba(15,23,42,.055)',
}

st.markdown(f'''<style>
:root {{--page:{colors['page']};--sidebar:{colors['sidebar']};--card:{colors['card']};--card-alt:{colors['card_alt']};--text:{colors['text']};--muted:{colors['muted']};--border:{colors['border']};--accent:{colors['accent']};}}
.stApp {{background:var(--page); color:var(--text);}}
[data-testid="stHeader"] {{background:color-mix(in srgb, var(--page) 88%, transparent);}}
[data-testid="stSidebar"] {{background:var(--sidebar); border-right:1px solid var(--border);}}
[data-testid="stSidebar"] > div:first-child {{padding-top:1.2rem;}}
.block-container {{max-width:1600px; padding-top:4.4rem; padding-bottom:3rem;}}
h1,h2,h3,p,label,[data-testid="stMarkdownContainer"] {{color:var(--text);}}
.side-brand {{font-size:1.15rem;font-weight:750;color:var(--text);letter-spacing:-.02em}}
.side-sub {{font-size:.78rem;color:var(--muted);margin-bottom:1.8rem}}
.section-label {{font-size:.68rem;font-weight:750;letter-spacing:.12em;color:var(--muted);margin:1.5rem 0 .6rem}}
.page-kicker {{font-size:.72rem;font-weight:750;letter-spacing:.12em;color:var(--accent);text-transform:uppercase}}
.page-title {{font-size:2rem;font-weight:760;letter-spacing:-.035em;color:var(--text);margin-top:.16rem}}
.page-version {{font-size:.8rem;font-weight:600;color:var(--muted);margin-top:.2rem}}
.page-note {{font-size:.95rem;color:var(--muted);margin:.3rem 0 1.6rem}}
.card-title {{font-size:1.15rem;font-weight:700;color:var(--text)}}
.card-note {{font-size:.82rem;color:var(--muted);margin-top:.15rem}}
[data-testid="stMetric"] {{background:var(--card);border:1px solid var(--border);padding:1.05rem 1.2rem;border-radius:16px;box-shadow:{colors['shadow']};min-height:124px;}}
[data-testid="stMetricLabel"] {{color:var(--muted);font-size:.78rem;font-weight:650;letter-spacing:.02em}}
[data-testid="stMetricValue"] {{color:var(--text);font-size:1.72rem;font-weight:720;letter-spacing:-.03em}}
[data-testid="stMetricDelta"] {{color:var(--muted);background:var(--card-alt);border-radius:999px;padding:.18rem .45rem;width:max-content;font-size:.72rem}}
[data-testid="stVerticalBlockBorderWrapper"] {{background:var(--card);border:1px solid var(--border)!important;border-radius:18px;box-shadow:{colors['shadow']};}}
.stButton>button {{border-radius:10px;border:1px solid var(--border);font-weight:650;min-height:2.65rem;}}
.stButton>button[kind="primary"] {{background:var(--accent);border-color:var(--accent);color:white;}}
.stButton>button[kind="primary"]:hover {{background:{colors['accent_hover']};border-color:{colors['accent_hover']};}}
.stDownloadButton>button {{border-radius:10px;border:1px solid var(--border);font-weight:650;min-height:2.65rem;background:var(--card-alt);color:var(--text)}}
[data-baseweb="select"]>div,[data-baseweb="input"]>div,.stTextInput input {{background:var(--card-alt)!important;border-color:var(--border)!important;color:var(--text)!important;border-radius:10px!important;}}
[data-testid="stFileUploaderDropzone"] {{background:var(--card-alt);border:1px dashed var(--border);border-radius:12px;}}
[data-testid="stExpander"] {{border:1px solid var(--border);border-radius:12px;background:var(--card);}}
[data-baseweb="tag"],[data-testid="stMultiSelect"] [data-tag] {{background:{colors['tag_bg']}!important;color:{colors['tag_text']}!important;border:1px solid {colors['tag_border']}!important;border-radius:8px!important;box-shadow:none!important;}}
[data-baseweb="tag"] span,[data-testid="stMultiSelect"] [data-tag] span {{color:{colors['tag_text']}!important;font-weight:600!important;}}
[data-baseweb="tag"] svg,[data-testid="stMultiSelect"] [data-tag] svg {{color:{colors['muted']}!important;fill:{colors['muted']}!important;}}
[data-testid="stSidebar"] [data-testid="stButtonGroup"] button {{padding-left:.55rem!important;padding-right:.55rem!important;font-size:.85rem;}}
[data-baseweb="select"] {{color:var(--text)!important;}}
[data-testid="stSelectbox"] div:has(> input),[data-testid="stMultiSelect"] div:has(> input),[data-testid="stNumberInput"] div:has(> input),[data-testid="stTextInputRootElement"] {{background:var(--card-alt)!important;border-color:var(--border)!important;border-radius:10px!important;}}
[data-testid="stSelectbox"] input,[data-testid="stNumberInput"] input,[data-testid="stTextInputField"] {{color:var(--text)!important;-webkit-text-fill-color:var(--text)!important;}}
[data-testid="stExpander"] summary {{background:var(--card)!important;color:var(--text)!important;border-radius:12px;}}
[data-testid="stExpander"] summary p {{color:var(--text)!important;}}
[data-testid="stButtonGroup"] button {{background:var(--card-alt)!important;border:1px solid var(--border)!important;}}
[data-testid="stButtonGroup"] button p {{color:var(--text)!important;}}
[data-testid="stButtonGroup"] button[aria-checked="true"] {{background:var(--accent)!important;border-color:var(--accent)!important;}}
[data-testid="stButtonGroup"] button[aria-checked="true"] p {{color:#fff!important;}}
[data-testid="stMetricDelta"] svg {{display:none;}}
[data-testid="stSidebar"] .stButton button {{box-shadow:none!important;}}
[data-testid="stSidebar"] .stButton button:not([kind="primary"]) {{background:transparent;color:var(--text);}}
[data-testid="stSidebar"] hr {{margin:1rem 0;}}
[data-testid="stColorPicker"] button {{border-radius:999px!important;width:2.4rem!important;height:2.4rem!important;border:2px solid var(--card)!important;box-shadow:0 0 0 1px var(--border)!important;}}
hr {{border-color:var(--border)!important;}}
</style>''', unsafe_allow_html=True)

settings = {'alignment': alignment, 'theme': theme, 'grid': grid, 'legend': legend, 'width': width, 'smoothing_minutes': smoothing_minutes}
st.markdown(f'<div class="page-kicker">Cook profile studio</div><div class="page-title">Cook Profile Dashboard</div><div class="page-version">Version {VERSION}</div><div class="page-note">Compare uploaded temperature profiles in a clean, consistent workspace. All temperatures are in degrees Celsius.</div>', unsafe_allow_html=True)

if not P:
    st.info('Upload one or more CSV or Excel files from the sidebar to begin.')
    st.stop()

profile_by_id = {p.profile_id: p for p in P}
profile_ids = list(profile_by_id)
if st.session_state.get('selected_profile_id') not in profile_by_id:
    st.session_state.selected_profile_id = profile_ids[0]
if 'visible_profile_ids' not in st.session_state:
    st.session_state.visible_profile_ids = [p.profile_id for p in P if p.visible]
st.session_state.visible_profile_ids = [i for i in st.session_state.visible_profile_ids if i in profile_by_id]
shown_ids = st.multiselect('Profiles shown', profile_ids, format_func=lambda pid: profile_by_id[pid].name, key='visible_profile_ids')
visible = [profile_by_id[pid] for pid in shown_ids if pid in profile_by_id]
for profile in P:
    profile.visible = profile.profile_id in shown_ids

channels = len({p.channel for p in visible})
durations = [p.duration_hours for p in visible]
mins = [p.minimum_c for p in visible]
maxs = [p.maximum_c for p in visible]

c1, c2, c3, c4 = st.columns(4)
c1.metric('PROFILES', len(visible), f'{len(P)} loaded', delta_color='off')
c2.metric('CHANNELS', channels, 'Unique labels', delta_color='off')
c3.metric('DURATION RANGE', f'{min(durations):.1f} - {max(durations):.1f} h' if durations else 'No data', 'Visible profiles', delta_color='off')
c4.metric('TEMPERATURE RANGE', f'{min(mins):.1f} - {max(maxs):.1f} °C' if mins else 'No data', 'Visible profiles', delta_color='off')

st.write('')
main, side = st.columns([4.0, 1.0], gap='large')
with side:
    with st.container(border=True):
        st.markdown('<div class="card-title">Profile details</div><div class="card-note">Select and customize one profile</div>', unsafe_allow_html=True)
        selected_id = st.selectbox('Profile', profile_ids, format_func=lambda pid: profile_by_id[pid].name, key='selected_profile_id')
        selected = profile_by_id[selected_id]
        st.caption(f'{selected.source_file}  |  {len(selected.plotted_data):,} of {len(selected.data):,} samples shown')
        edit_key = f'edit_{selected.profile_id}'
        name_key = f'{edit_key}_name'
        st.text_input('Display name', selected.name, key=name_key, on_change=rename_profile, args=(selected.profile_id, name_key))
        if st.session_state.get('rename_error'):
            st.warning(st.session_state.rename_error)
        channel = st.text_input('Channel label', selected.channel, key=f'{edit_key}_channel')
        offset = st.slider('Time offset (hours)', -24.0, 24.0, float(selected.offset_hours), .25, key=f'{edit_key}_offset')
        color = st.color_picker('Line color', selected.color, key=f'{edit_key}_color')
        selected.is_setpoint = st.checkbox('This is a setpoint (dashed line)', selected.is_setpoint, key=f'{edit_key}_setpoint',
                                           help='Use for a temperature the cooker was set to hold. It is drawn dashed, never smoothed, and can be compared with a probe below.')
        selected.channel, selected.offset_hours, selected.color = channel, offset, color

        st.markdown('<div class="section-label">VISIBLE DATA WINDOW</div>', unsafe_allow_html=True)
        total_points = len(selected.data)
        current_start, current_end = selected.trim_bounds()
        if total_points > 1:
            trim_key = f'{edit_key}_trim'
            if trim_key not in st.session_state:
                st.session_state[trim_key] = (current_start, current_end)
            trim_start, trim_end = st.slider(
                'Trim profile edges',
                min_value=0,
                max_value=total_points - 1,
                step=1,
                key=trim_key,
                help='Move the left handle right to remove leading points. Move the right handle left to remove trailing points.',
            )
            selected.trim_start, selected.trim_end = trim_start, trim_end
            shown_points = trim_end - trim_start + 1
            removed_left = trim_start
            removed_right = total_points - trim_end - 1
            st.caption(f'Showing {shown_points:,} of {total_points:,} points  |  Hidden left: {removed_left:,}  |  Hidden right: {removed_right:,}')
            st.button('Reset data window', width='stretch', key=f'{edit_key}_reset_trim', on_click=reset_trim, args=(selected, trim_key))
        else:
            st.caption('This profile does not contain enough points to trim.')
        st.divider()
        st.button('Remove selected profile', width='stretch', key=f'remove_{selected.profile_id}', on_click=remove_profile, args=(selected.profile_id,))
        st.download_button('Download visible data', profiles_to_zip(visible), 'cook_profiles_export.zip', 'application/zip', width='stretch', disabled=not visible, key='download_visible_profiles')

with main:
    with st.container(border=True):
        st.markdown('<div class="card-title">Temperature profile comparison</div>', unsafe_allow_html=True)
        if visible:
            st.markdown(f'<div class="card-note">{len(visible)} profiles  |  {channels} channels  |  {min(durations):.1f} - {max(durations):.1f} h duration range</div>', unsafe_allow_html=True)
        st.plotly_chart(comparison(visible, settings), width='stretch', config={'displaylogo': False, 'toImageButtonOptions': {'format': 'png', 'filename': 'cook_profiles'}})

st.write('')
setpoints = [p for p in P if p.is_setpoint]
measured_profiles = [p for p in P if not p.is_setpoint]
with st.container(border=True):
    st.markdown('<div class="card-title">Setpoint vs measured</div><div class="card-note">How closely a probe followed the temperature the cooker was set to hold</div>', unsafe_allow_html=True)
    if not setpoints or not measured_profiles:
        st.info('Tick "This is a setpoint" for a profile in Profile details, for example the cooker\'s own temperature setting. It can then be compared with a measured probe here.')
    else:
        setpoint_ids = [p.profile_id for p in setpoints]
        probe_ids = [p.profile_id for p in measured_profiles]
        if st.session_state.get('compare_setpoint_id') not in setpoint_ids:
            st.session_state.compare_setpoint_id = setpoint_ids[0]
        if st.session_state.get('compare_probe_id') not in probe_ids:
            st.session_state.compare_probe_id = probe_ids[0]
        k1, k2, k3, k4 = st.columns(4)
        setpoint_id = k1.selectbox('Setpoint', setpoint_ids, format_func=lambda pid: profile_by_id[pid].name, key='compare_setpoint_id')
        probe_id = k2.selectbox('Measured probe', probe_ids, format_func=lambda pid: profile_by_id[pid].name, key='compare_probe_id')
        band = k3.number_input('Accepted band (± °C)', min_value=1.0, max_value=100.0, value=10.0, step=1.0, key='compare_band')
        skip = k4.number_input('Ignore first (minutes)', min_value=0, max_value=600, value=0, step=5, key='compare_skip', help='Leave out the warm-up phase.')
        result, problem = compare(profile_by_id[setpoint_id], profile_by_id[probe_id], band, smoothing_minutes, skip)
        if problem:
            st.warning(problem)
        else:
            m1, m2, m3, m4 = st.columns(4)
            m1.metric('AVERAGE VS SETPOINT', f"{result['mean_diff']:+.1f} °C", 'Probe minus setpoint', delta_color='off')
            m2.metric('LOWEST TO HIGHEST', f"{result['min_diff']:+.0f} to {result['max_diff']:+.0f} °C", 'Difference from setpoint', delta_color='off')
            m3.metric('TIME WITHIN BAND', f"{result['within_share'] * 100:.0f} %", f"Within ±{band:g} °C", delta_color='off')
            m4.metric('TIME ANALYSED', f"{result['minutes']:.0f} min", 'Overlap of both profiles', delta_color='off')
            note = 'Samples are matched by clock time and the time offsets, whatever timeline alignment is selected. The visible data windows (trim) are respected.'
            if smoothing_minutes:
                note += f' The probe is smoothed over {smoothing_minutes} min.'
            st.caption(note)
            st.plotly_chart(deviation(result, settings), width='stretch', config={'displaylogo': False})

st.write('')
st.markdown('<div class="card-title">Selected profile statistics</div><div class="card-note">Key characteristics of the active profile</div>', unsafe_allow_html=True)
a, b, c, d = st.columns(4)
a.metric('PROFILE', selected.name)
b.metric('DURATION', f'{selected.duration_hours:.1f} h')
c.metric('MAXIMUM TEMPERATURE', f'{selected.maximum_c:.1f} °C')
d.metric('VISIBLE SAMPLES', f'{len(selected.plotted_data):,}', f'{len(selected.data):,} total', delta_color='off')
with st.container(border=True):
    st.plotly_chart(single(selected, settings), width='stretch', config={'displaylogo': False})
    with st.expander('Preview imported data'):
        st.dataframe(selected.export_frame().head(500), width='stretch')
