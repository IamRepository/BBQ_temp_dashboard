import datetime as dt
import html

import pandas as pd
import streamlit as st
import uuid

from profile_loader import COLORS, load_uploaded_files
from roles import LINE_STYLES, ROLES, ROLE_HELP, line_dash, line_style_name, default_probe, default_role, probe_colours, profile_name, unique_names
from chart_builder import comparison, single, deviation, without_clock
from analysis import compare
from export_utils import EXPORT_INTERVALS, export_filename, profiles_to_excel
from version import VERSION
import re

st.set_page_config(page_title='Cook Profile Dashboard', page_icon='CP', layout='wide', initial_sidebar_state='expanded')

if 'profiles' not in st.session_state:
    st.session_state.profiles = []
P = st.session_state.profiles
for _p in P:   # profiles from before v1.7.0 (or made in tests) get a role and a probe label
    if not _p.role:
        role = default_role(_p.channel)
        _p.role = 'Setpoint' if _p.is_setpoint else ('Other' if role == 'Setpoint' else role)
    if not _p.probe:
        _p.probe = default_probe(_p.source_file, _p.channel, _p.metadata.get('sheet', ''))


def reset_trim(profile, widget_key):
    # Runs as a button callback, i.e. before the slider is created in the next run.
    last = max(len(profile.data) - 1, 0)
    profile.trim_start, profile.trim_end = 0, last
    st.session_state[widget_key] = (0, last)


def group_trim_range(profiles):
    """Slider range for trimming every profile at once: clock time when all profiles have it, else hours.
    Returns (clock, low, high, step)."""
    clock = all('timestamp' in p.data for p in profiles)
    axes = [p.time_axis(clock) for p in profiles if len(p.data)]
    low, high = min(a.min() for a in axes), max(a.max() for a in axes)
    if clock:
        low, high = pd.Timestamp(low).floor('min').to_pydatetime(), pd.Timestamp(high).ceil('min').to_pydatetime()
        return True, low, high, dt.timedelta(minutes=1)
    low, high = float(low) - float(low) % (1 / 60), float(high) + (-float(high)) % (1 / 60)
    return False, round(low, 6), round(high, 6), 1 / 60


def group_window(profiles, clock, low, high):
    """The window that covers every profile's current data window, kept inside the slider range."""
    windows = [p.window(clock) for p in profiles if len(p.data)]
    start, end = min(w[0] for w in windows), max(w[1] for w in windows)
    if clock:
        start, end = pd.Timestamp(start).floor('min').to_pydatetime(), pd.Timestamp(end).ceil('min').to_pydatetime()
    else:
        start, end = float(start), float(end)
    return max(low, min(start, high)), max(low, min(end, high))


def apply_group_trim(widget_key, clock):
    # Runs when the shared slider moves: every profile shows only the readings inside the chosen window.
    start, end = st.session_state[widget_key]
    untouched = []
    for profile in st.session_state.profiles:
        if not profile.trim_to(start, end, clock):
            untouched.append(profile.name)
        st.session_state.pop(f'edit_{profile.profile_id}_trim', None)   # the single-profile slider re-reads it
    st.session_state.group_trim_note = untouched


def reset_all_trims(widget_key, low, high):
    for profile in st.session_state.profiles:
        profile.trim_start, profile.trim_end = 0, max(len(profile.data) - 1, 0)
        st.session_state.pop(f'edit_{profile.profile_id}_trim', None)
    st.session_state[widget_key] = (low, high)
    st.session_state.group_trim_note = []


def apply_import():
    # "Add" in Check the import: keep the ticked columns with their role and probe label.
    pending = st.session_state.pop('pending_import', None)
    if not pending:
        return
    batch = pending['batch']
    existing = st.session_state.profiles if pending['keep'] else []
    chosen = []
    for i, profile in enumerate(pending['profiles']):
        if not st.session_state.get(f'imp_{batch}_{i}_use', True):
            continue
        role = st.session_state.get(f'imp_{batch}_{i}_role')
        profile.role = role if role in ROLES else default_role(profile.channel)
        probe = str(st.session_state.get(f'imp_{batch}_{i}_probe') or '').strip()
        profile.probe = probe or default_probe(profile.source_file, profile.channel, profile.metadata.get('sheet', ''))
        profile.is_setpoint = profile.role == 'Setpoint'
        chosen.append(profile)
    names = unique_names([profile_name(p.probe, p.role) for p in chosen], taken={p.name for p in existing})
    colours = probe_colours([p.probe for p in chosen], [(p.probe, p.color) for p in existing], COLORS)
    for profile, name in zip(chosen, names):
        profile.name, profile.color = name, colours[profile.probe]
    left_out = len(pending['profiles']) - len(chosen)
    st.session_state.profiles = existing + chosen
    shown = st.session_state.get('visible_profile_ids', []) if pending['keep'] else []
    st.session_state.visible_profile_ids = shown + [p.profile_id for p in chosen]
    st.session_state.import_messages = pending['messages'] + [f'Imported {len(chosen)} profile(s)' + (f'; {left_out} column(s) left out.' if left_out else '.')]
    if not pending['keep']:
        st.session_state.selected_profile_id = None


def change_line_style(profile_id, widget_key):
    profile = next((p for p in st.session_state.profiles if p.profile_id == profile_id), None)
    if profile is not None:
        profile.line_style = LINE_STYLES[st.session_state[widget_key]]


def cancel_import():
    st.session_state.pop('pending_import', None)


def change_role(profile_id, widget_key, name_key):
    # A new role changes the setpoint flag (and so the default line style); a name still in the default form follows it.
    profile = next((p for p in st.session_state.profiles if p.profile_id == profile_id), None)
    if profile is None:
        return
    old, new = profile.role, st.session_state[widget_key]
    profile.role, profile.is_setpoint = new, new == 'Setpoint'
    if profile.name == profile_name(profile.probe, old):
        candidate = unique_names([profile_name(profile.probe, new)], taken={p.name for p in st.session_state.profiles if p is not profile})[0]
        profile.name = candidate
        st.session_state[name_key] = candidate


def remove_profile(profile_id):
    remaining = [p for p in st.session_state.profiles if p.profile_id != profile_id]
    st.session_state.profiles = remaining
    st.session_state.visible_profile_ids = [i for i in st.session_state.get('visible_profile_ids', []) if i != profile_id]
    st.session_state.selected_profile_id = remaining[0].profile_id if remaining else None


def clear_profiles():
    st.session_state.profiles = []
    st.session_state.visible_profile_ids = []
    st.session_state.selected_profile_id = None


def clear_rename_error():
    st.session_state.rename_error = None


def offset_readout(hours):
    # +0:03:20 style, for the offset box
    seconds = round(abs(hours) * 3600)
    return f"{'-' if hours < 0 else '+'}{seconds // 3600}:{seconds % 3600 // 60:02d}:{seconds % 60:02d}"


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
    st.markdown('<div class="section-label" style="margin-top:.3rem">DATA</div>', unsafe_allow_html=True)
    files = st.file_uploader('Upload CSV or Excel files', type=['csv', 'xlsx', 'xls'], accept_multiple_files=True, key='uploaded_profile_files')
    keep = st.checkbox('Keep existing profiles', True, key='keep_existing_profiles')
    if st.button('Import uploaded files', type='primary', width='stretch', disabled=not files, key='import_profiles_button'):
        try:
            # Read the files, then let the user check columns, roles and probes before anything is added.
            new, messages = load_uploaded_files(files, existing=P if keep else [])
            st.session_state.pending_import = {'profiles': new, 'messages': messages, 'keep': keep, 'batch': uuid.uuid4().hex[:8]}
            st.rerun()
        except Exception as exc:
            st.error(f'Import failed: {exc}')
    st.button('Clear all profiles', width='stretch', key='clear_profiles_button', on_click=clear_profiles)

    st.markdown('<div class="section-label">APPEARANCE</div>', unsafe_allow_html=True)
    theme = st.segmented_control('Theme', ['Light', 'Dark'], default='Dark', key='theme_selector') or 'Dark'
    alignment_modes = {'Start': 'Original timeline', 'Peak': 'Align peak', 'End': 'Align end', 'Clock': 'Clock time'}
    alignment_help = (
        '**Start**: every profile starts at zero.\n\n'
        '**Peak**: every profile is centred on its own highest point.\n\n'
        '**End**: every profile ends at zero.\n\n'
        '**Clock**: real time of day, so profiles from different devices line up.'
    )
    alignment_choice = st.segmented_control('Timeline alignment', list(alignment_modes), default='Start', key='alignment_selector', help=alignment_help) or 'Start'
    alignment = alignment_modes[alignment_choice]
    smoothing_options = {'Off': 0, '1 min': 1, '5 min': 5, '10 min': 10}
    smoothing_help = (
        'Rolling average over the chosen time, applied to measured lines.\n\n'
        '**Off** shows readings exactly as logged.\n\n'
        'Setpoints and exported data are never smoothed.'
    )
    smoothing_choice = st.segmented_control('Smoothing', list(smoothing_options), default='Off', key='smoothing_selector', help=smoothing_help) or 'Off'
    smoothing_minutes = smoothing_options[smoothing_choice]

    st.markdown('<div class="section-label">CHART OPTIONS</div>', unsafe_allow_html=True)
    grid = st.toggle('Grid lines', True, key='grid_lines_toggle')
    legend = st.toggle('Legend', True, key='legend_toggle')
    width = st.number_input('Line width', min_value=1.0, max_value=5.0, value=3.5, step=0.5, format='%.1f', key='line_width_input')
    show_target = st.toggle('Target line', False, key='target_line_toggle',
                            help='A straight line across the chart at the temperature the cook aimed for, for example 200 °C. '
                                 'Drawn on the comparison chart and the selected profile\'s chart, and included in saved chart images.')
    target = st.number_input('Target temperature (°C)', min_value=-50.0, max_value=500.0, value=200.0, step=1.0, format='%.0f',
                             key='target_value') if show_target else None
    image_format = st.segmented_control('Image download', ['PNG', 'JPEG'], default='JPEG', key='image_format_selector',
                                        help='File type saved by the camera icon in the top right of each chart.') or 'JPEG'
    if st.session_state.get('import_messages'):
        with st.expander('Import notes', expanded=True):
            for message in st.session_state.import_messages:
                st.caption(message)



def chart_config(filename, wide=False):
    # The camera icon in each chart's toolbar saves the picture in the format chosen in the sidebar.
    # 16:9 charts are saved at 1600 x 900 (3200 x 1800 pixels at scale 2), whatever the window size.
    safe = re.sub(r'[^A-Za-z0-9._-]+', '_', filename).strip('_') or 'chart'
    image = {'format': image_format.lower(), 'filename': safe, 'scale': 2}
    if wide:
        image.update(width=1600, height=900)
    return {'displaylogo': False, 'displayModeBar': True, 'responsive': True, 'toImageButtonOptions': image}


def readable_ink(hex_color):
    # Dark or white text, whichever has the higher contrast on the given background colour.
    r, g, b = (int(hex_color[i:i + 2], 16) / 255 for i in (1, 3, 5))
    lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in (r, g, b)]
    lum = 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]
    dark_contrast = (lum + 0.05) / (0.0092 + 0.05)   # text #0F172A
    white_contrast = 1.05 / (lum + 0.05)
    return '#0F172A' if dark_contrast >= white_contrast else '#FFFFFF'


def line_colour(profile):
    # The colour the line is drawn in right now (the picker's value wins over the stored one).
    value = st.session_state.get(f'edit_{profile.profile_id}_color', profile.color)
    return value if isinstance(value, str) and re.fullmatch(r'#[0-9a-fA-F]{6}', value) else profile.color


def profile_dropdown_style(label, profiles):
    # Open list of a profile picker: a swatch in each profile's line colour, and wide enough for the full names.
    # Streamlit labels the open list with the widget label and numbers its entries (data-key) in option order.
    if not profiles:
        return
    lst = f'[role="listbox"][aria-label="{label}"]'
    width = min(480, max(len(p.name) for p in profiles) * 8 + 72)
    css = (
        # wider than the box when needed; Streamlit's own positioning then keeps the list on screen
        f'[data-testid="stSelectboxVirtualDropdown"]:has({lst}) {{width:max(var(--trigger-width), {width}px)!important;}}'
        f'{lst} > div, {lst} > div > div {{width:100%!important;}}'
        f'{lst} [role="option"] > div {{white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}}'
        f'{lst} [role="option"] > div::before {{content:"";display:inline-block;width:.8rem;height:.8rem;border-radius:3px;'
        f'margin-right:.6rem;vertical-align:-.1rem;box-shadow:0 0 0 1px rgba(127,127,127,.35);}}'
    )
    for index, profile in enumerate(profiles):
        css += f'{lst} [role="option"][data-key="{index}"] > div::before {{background:{line_colour(profile)};}}'
    st.markdown(f'<style>{css}</style>', unsafe_allow_html=True)


# Profile details: the profile picker, display name and channel label take the selected line's colour.
tint_css = ''
active_profile = next((p for p in P if p.profile_id == st.session_state.get('selected_profile_id')), P[0] if P else None)
if active_profile is not None:
    tint = st.session_state.get(f'edit_{active_profile.profile_id}_color', active_profile.color)
    if isinstance(tint, str) and re.fullmatch(r'#[0-9a-fA-F]{6}', tint):
        ink = readable_ink(tint)
        for key in ('selected_profile_id', f'edit_{active_profile.profile_id}_name', f'edit_{active_profile.profile_id}_channel'):
            k = f'.st-key-{key}'
            tint_css += (
                f'{k} div:has(> input),{k} [data-testid="stTextInputRootElement"] {{background:{tint}!important;border-color:{tint}!important;}}'
                f'{k} input {{background:transparent!important;}}'
                f'{k} div:has(> input) *,{k} [data-testid="stTextInputRootElement"] input {{color:{ink}!important;-webkit-text-fill-color:{ink}!important;}}'
                f'{k} div:has(> input) svg {{color:{ink}!important;fill:{ink}!important;}}\n'
            )

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
    'kicker': '#60A5FA' if is_dark else '#2563EB',
    'accent_hover': '#1D4ED8',
    'danger': '#DC2626',
    'tag_bg': '#1F2937' if is_dark else '#E8EEF7',
    'tag_border': '#374151' if is_dark else '#D7E0EC',
    'tag_text': '#E5E7EB' if is_dark else '#334155',
    'shadow': '0 8px 24px rgba(0,0,0,.16)' if is_dark else '0 4px 16px rgba(15,23,42,.055)',
}

st.markdown(f'''<style>
:root {{--page:{colors['page']};--sidebar:{colors['sidebar']};--card:{colors['card']};--card-alt:{colors['card_alt']};--text:{colors['text']};--muted:{colors['muted']};--border:{colors['border']};--accent:{colors['accent']};--kicker:{colors['kicker']};}}
.stApp {{background:var(--page); color:var(--text);}}
[data-testid="stHeader"] {{background:color-mix(in srgb, var(--page) 88%, transparent);}}
[data-testid="stSidebar"] {{background:var(--sidebar); border-right:1px solid var(--border);}}
[data-testid="stSidebar"] > div:first-child {{padding-top:.9rem;}}
[data-testid="stSidebarHeader"] {{position:absolute;top:.6rem;right:.5rem;height:auto;width:auto;padding:0;margin:0;z-index:5;}}
.block-container {{max-width:1600px; padding-top:4.4rem; padding-bottom:3rem;}}
h1,h2,h3,p,label,[data-testid="stMarkdownContainer"] {{color:var(--text);}}
.side-brand {{font-size:1.15rem;font-weight:750;color:var(--text);letter-spacing:-.02em}}
.side-sub {{font-size:.78rem;color:var(--muted);margin-bottom:.2rem}}
.section-label {{font-size:.68rem;font-weight:750;letter-spacing:.12em;color:var(--muted);margin:1.5rem 0 .6rem}}
.page-kicker {{font-size:.72rem;font-weight:750;letter-spacing:.12em;color:var(--kicker);text-transform:uppercase}}
.page-title {{font-size:2rem;font-weight:760;letter-spacing:-.035em;color:var(--text);margin-top:.16rem}}
.page-version {{font-size:.8rem;font-weight:600;color:var(--muted);margin-top:.2rem}}
.page-note {{font-size:.95rem;color:var(--muted);margin:.3rem 0 1.6rem}}
.card-title {{font-size:1.15rem;font-weight:700;color:var(--text)}}
.card-note {{font-size:.82rem;color:var(--muted);margin-top:.15rem}}
.card-title.compact {{font-size:1rem;margin-bottom:-.35rem}}
.import-head {{font-size:.72rem;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);margin-bottom:-.6rem}}
.import-column {{font-size:.9rem;color:var(--text);line-height:1.25}}
.import-column span {{color:var(--muted);margin-right:.35rem}}
.st-key-import_review_card [data-testid="stVerticalBlock"] {{gap:.45rem;}}
/* The comparison and single-profile charts keep a 16:9 shape at any window width */
.st-key-chart_comparison [data-testid="stElementContainer"],.st-key-chart_comparison [data-testid="stFullScreenFrame"],
.st-key-chart_single [data-testid="stElementContainer"],.st-key-chart_single [data-testid="stFullScreenFrame"] {{height:auto!important;flex:0 0 auto!important;}}
.st-key-chart_comparison [data-testid="stPlotlyChart"],.st-key-chart_single [data-testid="stPlotlyChart"] {{aspect-ratio:16/9;height:auto!important;}}
.st-key-chart_comparison [data-testid="stPlotlyChart"] > div,.st-key-chart_comparison .js-plotly-plot,.st-key-chart_comparison .plot-container,.st-key-chart_comparison .svg-container,
.st-key-chart_single [data-testid="stPlotlyChart"] > div,.st-key-chart_single .js-plotly-plot,.st-key-chart_single .plot-container,.st-key-chart_single .svg-container {{height:100%!important;}}
[data-testid="stMetric"] {{background:var(--card);border:1px solid var(--border);padding:1.05rem 1.2rem;border-radius:16px;box-shadow:{colors['shadow']};min-height:124px;}}
[data-testid="stMetricLabel"] {{color:var(--muted);font-size:.78rem;font-weight:650;letter-spacing:.02em}}
[data-testid="stMetricValue"] {{color:var(--text);font-size:1.72rem;font-weight:720;letter-spacing:-.03em}}
[data-testid="stMetricDelta"] {{color:var(--muted);background:var(--card-alt);border-radius:999px;padding:.18rem .45rem;width:max-content;font-size:.72rem}}
[data-testid="stVerticalBlockBorderWrapper"] {{background:var(--card);border:1px solid var(--border)!important;border-radius:18px;box-shadow:{colors['shadow']};}}
/* Buttons: every action button gets explicit colours, so text never inherits a colour meant for another background */
[data-testid="stBaseButton-secondary"],[data-testid="stBaseButton-primary"],.stDownloadButton>button {{border-radius:10px!important;font-weight:650;min-height:2.65rem;box-shadow:none!important;}}
[data-testid="stBaseButton-secondary"],.stDownloadButton>button {{background:var(--card-alt)!important;border:1px solid var(--border)!important;color:var(--text)!important;}}
[data-testid="stBaseButton-secondary"] *,.stDownloadButton>button * {{color:var(--text)!important;}}
[data-testid="stBaseButton-secondary"]:hover,.stDownloadButton>button:hover {{border-color:var(--accent)!important;}}
[data-testid="stBaseButton-primary"] {{background:var(--accent)!important;border:1px solid var(--accent)!important;color:#fff!important;}}
[data-testid="stBaseButton-primary"] * {{color:#fff!important;}}
[data-testid="stBaseButton-primary"]:hover {{background:{colors['accent_hover']}!important;border-color:{colors['accent_hover']}!important;}}
[data-testid="stSidebar"] [data-testid="stBaseButton-secondary"] {{background:transparent!important;}}
/* Help tooltips and open dropdown lists follow the theme */
[data-testid="stTooltipContent"] {{background:var(--card)!important;color:var(--text)!important;border:1px solid var(--border);box-shadow:{colors['shadow']};}}
[data-testid="stTooltipContent"] * {{color:var(--text)!important;}}
[data-baseweb="popover"] [role="listbox"],[data-baseweb="popover"] ul,[data-baseweb="popover"] [data-baseweb="menu"],[data-testid="stSelectboxVirtualDropdown"] {{background:var(--card)!important;}}
[data-testid="stSelectboxVirtualDropdown"] {{border:1px solid var(--border)!important;border-radius:10px!important;box-shadow:{colors['shadow']}!important;}}
[data-baseweb="popover"] [role="option"],[data-baseweb="popover"] [role="option"] *,[data-testid="stSelectboxVirtualDropdown"] [role="option"],[data-testid="stSelectboxVirtualDropdown"] [role="option"] * {{color:var(--text)!important;}}
[data-baseweb="popover"] [role="option"]:hover,[data-baseweb="popover"] [role="option"][aria-selected="true"],[data-testid="stSelectboxVirtualDropdown"] [role="option"][data-hovered="true"] > div,[data-testid="stSelectboxVirtualDropdown"] [role="option"][data-focused="true"] > div,[data-testid="stSelectboxVirtualDropdown"] [role="option"][aria-selected="true"] > div {{background:var(--card-alt)!important;}}
/* Uploaded file chips and the uploader's add icon */
[data-testid="stSelectbox"] svg,[data-testid="stMultiSelect"] svg {{color:var(--muted);fill:var(--muted);}}
[data-testid="stFileChip"] {{background:var(--card)!important;border:1px solid var(--border)!important;}}
[data-testid="stFileChip"] * {{color:var(--text)!important;}}
[data-testid="stFileUploader"] [data-testid="stBaseButton-minimal"],[data-testid="stFileUploader"] [data-testid="stIconMaterial"] {{color:var(--text)!important;}}
[data-baseweb="select"]>div,[data-baseweb="input"]>div,.stTextInput input {{background:var(--card-alt)!important;border-color:var(--border)!important;color:var(--text)!important;border-radius:10px!important;}}
[data-testid="stFileUploaderDropzone"] {{background:var(--card-alt);border:1px dashed var(--border);border-radius:12px;}}
[data-testid="stExpander"] {{border:1px solid var(--border);border-radius:12px;background:var(--card);}}
[data-baseweb="tag"],[data-testid="stMultiSelect"] [data-tag] {{background:{colors['tag_bg']}!important;color:{colors['tag_text']}!important;border:1px solid {colors['tag_border']}!important;border-radius:8px!important;box-shadow:none!important;}}
[data-baseweb="tag"] span,[data-testid="stMultiSelect"] [data-tag] span {{color:{colors['tag_text']}!important;font-weight:600!important;}}
[data-baseweb="tag"] svg,[data-testid="stMultiSelect"] [data-tag] svg {{color:{colors['muted']}!important;fill:{colors['muted']}!important;}}
[data-testid="stSidebar"] [data-testid="stButtonGroup"] button[role="radio"] {{padding-left:.55rem!important;padding-right:.55rem!important;font-size:.85rem;}}
[data-baseweb="select"] {{color:var(--text)!important;}}
[data-testid="stSelectbox"] div:has(> input),[data-testid="stMultiSelect"] div:has(> input),[data-testid="stNumberInput"] div:has(> input),[data-testid="stTextInputRootElement"] {{background:var(--card-alt)!important;border-color:var(--border)!important;border-radius:10px!important;}}
[data-testid="stSelectbox"] input,[data-testid="stNumberInput"] input,[data-testid="stTextInputField"] {{color:var(--text)!important;-webkit-text-fill-color:var(--text)!important;}}
[data-testid="stTooltipIcon"],[data-testid="stSidebarHeader"] button,[data-testid="stSidebarCollapseButton"] button,[data-testid="stSidebarCollapseButton"] span,[data-testid="stNumberInput"] button {{color:var(--muted)!important;}}
[data-testid="stTooltipIcon"] svg,[data-testid="stSidebarHeader"] svg,[data-testid="stSidebarCollapseButton"] svg,[data-testid="stNumberInput"] button svg {{color:var(--muted)!important;fill:var(--muted)!important;}}
[data-testid="stExpander"] summary {{background:var(--card)!important;color:var(--text)!important;border-radius:12px;}}
[data-testid="stExpander"] summary p {{color:var(--text)!important;}}
[data-testid="stButtonGroup"] button[role="radio"] {{background:var(--card-alt)!important;border:1px solid var(--border)!important;}}
[data-testid="stButtonGroup"] button[role="radio"] p {{color:var(--text)!important;}}
[data-testid="stButtonGroup"] button[role="radio"][aria-checked="true"] {{background:var(--accent)!important;border-color:var(--accent)!important;}}
[data-testid="stButtonGroup"] button[role="radio"][aria-checked="true"] p {{color:#fff!important;}}
[data-testid="stCheckbox"] label:has(input[role="switch"]:checked) > div:not([data-testid="stWidgetLabel"]) {{background:var(--accent)!important;}}
[data-testid="stMetricDelta"] svg {{display:none;}}
[data-testid="stSidebar"] hr {{margin:1rem 0;}}
[data-testid="stColorPicker"] button {{border-radius:999px!important;width:2.4rem!important;height:2.4rem!important;border:2px solid var(--card)!important;box-shadow:0 0 0 1px var(--border)!important;}}
hr {{border-color:var(--border)!important;}}
{tint_css}</style>''', unsafe_allow_html=True)

settings = {'alignment': alignment, 'theme': theme, 'grid': grid, 'legend': legend, 'width': width, 'smoothing_minutes': smoothing_minutes, 'target': target}
st.markdown(f'<div class="page-kicker">Cook profile studio</div><div class="page-title">Cook Profile Dashboard</div><div class="page-version">Version {VERSION}</div><div class="page-note">Compare uploaded temperature profiles in a clean, consistent workspace. All temperatures are in degrees Celsius.</div>', unsafe_allow_html=True)

pending = st.session_state.get('pending_import')
if pending:
    with st.container(border=True, key='import_review_card'):
        st.markdown('<div class="card-title">Check the import</div><div class="card-note">Choose which columns to add, what each one measures and which probe it comes from. '
                    'Profiles of one probe share a colour. Colour and line style can be changed per profile afterwards.</div>', unsafe_allow_html=True)
        new_profiles = pending['profiles']
        if not new_profiles:
            st.warning('No new temperature columns were found. Import notes in the sidebar say why.')
            st.button('Close', key='cancel_import', on_click=cancel_import)
        else:
            batch = pending['batch']
            widths = [0.55, 2.7, 1.9, 1.3]
            head = st.columns(widths, gap='small')
            for column, text, tip in zip(head, ['Import', 'File and column', 'Probe', 'Role'],
                                         ['Untick to leave a column out.', '', 'Which probe or device the column comes from. Columns with the same probe share a colour, for example "Typhur 2".',
                                          'What the column measures. Sets the name in the Excel export; Setpoint also makes it a setpoint.']):
                column.markdown(f'<div class="import-head" title="{tip}">{text}</div>', unsafe_allow_html=True)
            for i, p in enumerate(new_profiles):
                c1, c2, c3, c4 = st.columns(widths, gap='small', vertical_alignment='center')
                use_key, probe_key, role_key = f'imp_{batch}_{i}_use', f'imp_{batch}_{i}_probe', f'imp_{batch}_{i}_role'
                c1.checkbox('Import', True, key=use_key, label_visibility='collapsed')
                sheet = f" ({p.metadata.get('sheet')})" if p.metadata.get('sheet') else ''
                c2.markdown(f'<div class="import-column"><span>{html.escape(p.source_file + sheet)}</span> {html.escape(p.channel)}</div>', unsafe_allow_html=True)
                c3.text_input('Probe', default_probe(p.source_file, p.channel, p.metadata.get('sheet', '')), key=probe_key, label_visibility='collapsed')
                role = default_role(p.channel)
                c4.selectbox('Role', ROLES, index=ROLES.index(role), key=role_key, label_visibility='collapsed')
            chosen = [i for i in range(len(new_profiles)) if st.session_state.get(f'imp_{batch}_{i}_use', True)]
            taken = {p.name for p in P} if pending['keep'] else set()
            names = unique_names([profile_name(str(st.session_state.get(f'imp_{batch}_{i}_probe', '')).strip() or 'Probe',
                                               st.session_state.get(f'imp_{batch}_{i}_role', 'Other')) for i in chosen], taken=taken)
            st.caption('Will be added as: ' + (', '.join(names) if names else 'nothing, every column is unticked'))
            b1, b2, _ = st.columns([1.3, 0.8, 4.0], gap='small')
            b1.button(f'Add {len(names)} profile(s)', type='primary', width='stretch', key='apply_import', on_click=apply_import, disabled=not names)
            b2.button('Cancel', width='stretch', key='cancel_import', on_click=cancel_import)
    st.write('')

if not P:
    if not pending:
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

devices = len({p.source_file for p in visible})
durations = [p.duration_hours for p in visible]
mins = [p.minimum_c for p in visible]
maxs = [p.maximum_c for p in visible]

c1, c2, c3, c4 = st.columns(4)
c1.metric('PROFILES', len(visible), f'{len(P)} loaded', delta_color='off')
c2.metric('DEVICES', devices, 'Source files', delta_color='off')
c3.metric('DURATION RANGE', f'{min(durations):.1f} - {max(durations):.1f} h' if durations else 'No data', 'Visible profiles', delta_color='off')
c4.metric('TEMPERATURE RANGE', f'{min(mins):.1f} - {max(maxs):.1f} °C' if mins else 'No data', 'Visible profiles', delta_color='off')

st.write('')
# Profile details and the comparison chart share one card, so a change to a profile is seen in the chart at once.
with st.container(border=True, key='profile_details_card'):
    st.markdown('<div class="card-title compact">Profile details</div>', unsafe_allow_html=True)
    profile_dropdown_style('Profile', [profile_by_id[pid] for pid in profile_ids])   # a style element: kept out of the columns so labels line up
    d1, d2, d3, d4, d5, d7, d6 = st.columns([1.85, 1.45, 1.15, 1.4, 0.5, 1.2, 1.3], gap='small', vertical_alignment='bottom')
    with d1:
        selected_id = st.selectbox('Profile', profile_ids, format_func=lambda pid: profile_by_id[pid].name, key='selected_profile_id', on_change=clear_rename_error)
        selected = profile_by_id[selected_id]
    edit_key = f'edit_{selected.profile_id}'
    name_key = f'{edit_key}_name'
    with d2:
        st.text_input('Display name', selected.name, key=name_key, on_change=rename_profile, args=(selected.profile_id, name_key))
    with d3:
        channel = st.text_input('Channel label', selected.channel, key=f'{edit_key}_channel')
    with d4:
        offset_minutes = st.number_input('Offset (min)', min_value=-1440.0, max_value=1440.0, value=float(selected.offset_hours) * 60,
                                         step=1.0, format='%.2f', key=f'{edit_key}_offset_min',
                                         help='Shifts this profile in time, for example to correct a device clock. Whole minutes, with decimals for seconds (3.5 = 3 min 30 s). Up to 24 hours either way. The offset is shown as h:mm:ss under the trim slider.')
        offset = offset_minutes / 60
    with d5:
        color = st.color_picker('Color', selected.color, key=f'{edit_key}_color')
    with d7:
        style_key = f'{edit_key}_style'
        st.session_state[style_key] = line_style_name(line_dash(selected))
        st.selectbox('Line style', list(LINE_STYLES), key=style_key, on_change=change_line_style, args=(selected.profile_id, style_key),
                     help='How this line is drawn. Every line is solid unless you choose otherwise; a setpoint starts dashed. '
                          'The style shows in the chart, the legend and saved images.')
    with d6:
        role_key = f'{edit_key}_role'
        if st.session_state.get(role_key) != selected.role:
            st.session_state[role_key] = selected.role
        st.selectbox('Role', ROLES, key=role_key, on_change=change_role, args=(selected.profile_id, role_key, name_key),
                     help='What this profile measures. Sets the name in the Excel export. '
                          'Setpoint: starts dashed, never smoothed, and compared with a probe under Setpoint vs measured.')
    selected.channel, selected.offset_hours, selected.color = channel, offset, color
    if st.session_state.get('rename_error'):
        st.warning(st.session_state.rename_error)

    total_points = len(selected.data)
    current_start, current_end = selected.trim_bounds()
    t1, t2, t3, t4 = st.columns([2.2, 4.3, 1.0, 1.3], gap='small', vertical_alignment='bottom')
    with t1:
        trim_all = st.checkbox('Trim all profiles together', key='trim_all',
                               help='One slider sets the same time window for every loaded profile, instead of trimming them one by one. '
                                    'Uses clock time when every profile has it, otherwise hours from each profile\'s start (with its time offset). '
                                    'Untick to fine-tune a single profile again.')
    window_note = ''
    with t2:
        if trim_all and any(len(p.data) > 1 for p in P):
            clock, low, high, step = group_trim_range(P)
            group_key = 'trim_all_clock' if clock else 'trim_all_hours'
            stored = st.session_state.get(group_key)
            if stored is None or not all(low <= v <= high for v in stored):
                st.session_state[group_key] = group_window(P, clock, low, high)
            one_day = clock and low.date() == high.date()
            window_start, window_end = st.slider(
                'Trim all profiles', min_value=low, max_value=high, step=step, key=group_key,
                format=('HH:mm' if one_day else 'DD/MM HH:mm') if clock else '%.2f h', on_change=apply_group_trim, args=(group_key, clock),
                help='Move the handles to hide the start and end of every profile at once.')
            if clock:
                shown = f"{window_start:%H:%M} to {window_end:%H:%M} on {window_start:%d/%m/%Y}" if window_start.date() == window_end.date() \
                    else f"{window_start:%d/%m %H:%M} to {window_end:%d/%m %H:%M}"
            else:
                shown = f'{window_start:.2f} h to {window_end:.2f} h'
            window_note = f'Window: {shown}, all {len(P)} profiles'
        elif total_points > 1:
            trim_key = f'{edit_key}_trim'
            if trim_key not in st.session_state:
                st.session_state[trim_key] = (current_start, current_end)
            trim_start, trim_end = st.slider(
                'Trim profile edges', min_value=0, max_value=total_points - 1, step=1, key=trim_key,
                help='Move the left handle right to remove leading points. Move the right handle left to remove trailing points.')
            selected.trim_start, selected.trim_end = trim_start, trim_end
            window_note = f'Hidden left: {trim_start:,}  |  Hidden right: {total_points - trim_end - 1:,}'
        else:
            window_note = 'Too few points to trim'
    with t3:
        if trim_all and any(len(p.data) > 1 for p in P):
            st.button('Reset all', width='stretch', key='reset_all_trims', on_click=reset_all_trims, args=(group_key, low, high),
                      help='Show every profile in full again.')
        elif total_points > 1:
            st.button('Reset', width='stretch', key=f'{edit_key}_reset_trim', on_click=reset_trim, args=(selected, trim_key),
                      help='Show this profile in full again.')
    with t4:
        st.button('Remove profile', width='stretch', key=f'remove_{selected.profile_id}', on_click=remove_profile, args=(selected.profile_id,))
    # One status line: the full name (the closed box can cut a long one), file, samples shown, window and offset.
    status = [selected.name, selected.source_file, f'{len(selected.plotted_data):,} of {total_points:,} samples shown', window_note]
    if offset:
        status.append(f'offset {offset_readout(offset)} (h:mm:ss)')
    if 'typed' in str(selected.metadata.get('start_source', '')).lower():
        status.append('start time typed in Chart to Data, check it')
    st.caption('  |  '.join(s for s in status if s))
    if trim_all and st.session_state.get('group_trim_note'):
        st.caption('No readings inside this window, left as they were: ' + ', '.join(st.session_state.group_trim_note))

    if alignment == 'Clock time' and without_clock(visible):
        st.caption('These profiles have no clock times, so they are not shown in Clock alignment: '
                   + ', '.join(p.name for p in without_clock(visible)) + '. Choose Start, Peak or End to see them.')
    summary = f'{len(visible)} profiles  |  {devices} devices  |  {min(durations):.1f} - {max(durations):.1f} h duration range' if visible else 'No profiles shown'
    with st.container(key='chart_comparison'):
        st.plotly_chart(comparison(visible, settings, summary), width='stretch', theme=None, config=chart_config('cook_profiles', wide=True))
    e1, e2, _ = st.columns([1.3, 1.3, 4.4], gap='small', vertical_alignment='bottom')
    export_interval = e1.selectbox('Export interval', list(EXPORT_INTERVALS), index=list(EXPORT_INTERVALS).index('1 min'), key='export_interval',
                                   help='Exports the visible profiles. Sheet "Cook profiles": Timestamp, then one column per visible profile. Profiles without clock times go on a second sheet, "Elapsed time". Readings are averaged within each interval. Trimming and time offsets are applied; smoothing is not.')
    # The file is built only when the button is clicked, not on every click elsewhere on the page.
    e2.download_button('Download Excel file', (lambda: profiles_to_excel(visible, export_interval)) if visible else b'', export_filename(visible),
                       'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', width='stretch', disabled=not visible, key='download_visible_profiles')

st.write('')
setpoints = [p for p in P if p.is_setpoint]
measured_profiles = [p for p in P if not p.is_setpoint]
with st.container(border=True):
    st.markdown('<div class="card-title">Setpoint vs measured</div><div class="card-note">How closely a probe followed the temperature the cooker was set to hold</div>', unsafe_allow_html=True)
    if not setpoints or not measured_profiles:
        st.info('Set the Role of a profile to "Setpoint" in Profile details (or at import), for example the cooker\'s own temperature setting. It can then be compared with a measured probe here.')
    else:
        setpoint_ids = [p.profile_id for p in setpoints]
        probe_ids = [p.profile_id for p in measured_profiles]
        if st.session_state.get('compare_setpoint_id') not in setpoint_ids:
            st.session_state.compare_setpoint_id = setpoint_ids[0]
        if st.session_state.get('compare_probe_id') not in probe_ids:
            st.session_state.compare_probe_id = probe_ids[0]
        k1, k2, k3, k4 = st.columns(4)
        profile_dropdown_style('Setpoint', setpoints)
        profile_dropdown_style('Measured probe', measured_profiles)
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
            st.plotly_chart(deviation(result, settings), width='stretch', theme=None, config=chart_config('setpoint_difference'))

st.write('')
st.markdown('<div class="card-title">Selected profile statistics</div><div class="card-note">Key characteristics of the active profile</div>', unsafe_allow_html=True)
a, b, c, d = st.columns(4)
a.metric('PROFILE', selected.name)
b.metric('DURATION', f'{selected.duration_hours:.1f} h')
c.metric('MAXIMUM TEMPERATURE', f'{selected.maximum_c:.1f} °C')
d.metric('VISIBLE SAMPLES', f'{len(selected.plotted_data):,}', f'{len(selected.data):,} total', delta_color='off')
with st.container(border=True):
    with st.container(key='chart_single'):
        st.plotly_chart(single(selected, settings), width='stretch', theme=None, config=chart_config(selected.name, wide=True))
    with st.expander('Preview imported data'):
        st.dataframe(selected.export_frame().head(500), width='stretch')
