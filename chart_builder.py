import html

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from analysis import smooth
from roles import ROLES, line_dash

# Most points drawn per line. A long cook logged every second has tens of thousands of readings, more than a
# chart can show; drawing all of them made every click slow. Statistics, the setpoint comparison and the Excel
# export always use every reading.
MAX_POINTS = 4000


def thin(x, y, limit=MAX_POINTS):
    """Positions of the points to draw: in each of limit/2 equal stretches, the lowest and the highest reading,
    so short spikes (a lid opening) and dips still show. Lines with up to `limit` points are drawn in full."""
    n = len(y)
    if n <= limit:
        return np.arange(n)
    values = pd.Series(np.asarray(y, dtype=float))
    bucket = np.arange(n) * (limit // 2) // n
    groups = values.groupby(bucket)
    keep = np.concatenate([groups.idxmin().dropna().to_numpy(), groups.idxmax().dropna().to_numpy(), [0, n - 1]])
    return np.unique(keep.astype(int))


def _pick(series, positions):
    return pd.Series(series).reset_index(drop=True).iloc[positions]


def _frame(profile):
    return profile.plotted_data


def _y(profile, frame, settings):
    """Temperatures as drawn. Setpoints are never smoothed."""
    if profile.is_setpoint:
        return frame.temperature_c
    return smooth(frame, settings.get('smoothing_minutes', 0))


def _x(profile, mode, y=None):
    frame = _frame(profile)
    if mode == 'Clock time' and 'timestamp' in frame:
        return frame.timestamp + pd.to_timedelta(profile.offset_hours, unit='h')
    x = frame.elapsed_hours + profile.offset_hours
    if frame.empty:
        return x
    if mode == 'Align peak':
        temperatures = (frame.temperature_c if y is None else y).reset_index(drop=True)
        x = x.reset_index(drop=True) - float(x.reset_index(drop=True).iloc[temperatures.idxmax()])
    elif mode == 'Align end':
        x = x - float(x.max())
    return x


def _line(profile, settings):
    # Colour and line style are the profile's own (Profile details); solid unless chosen, a setpoint starts dashed.
    line = {'color': profile.color, 'width': settings['width']}
    dash = line_dash(profile)
    if dash != 'solid':
        line['dash'] = dash
    return line


def _palette(mode):
    if mode == 'Dark':
        return {'bg': '#111827', 'plot': '#111827', 'text': '#E5E7EB', 'muted': '#9CA3AF', 'grid': 'rgba(148,163,184,0.12)', 'border': '#263244'}
    return {'bg': '#FFFFFF', 'plot': '#FFFFFF', 'text': '#172033', 'muted': '#64748B', 'grid': 'rgba(100,116,139,0.11)', 'border': '#E2E8F0'}


# Chart text size choices (sidebar, Chart options): label -> scale factor for every text in the charts.
TEXT_SIZES = {'100%': 1.0, '125%': 1.25, '150%': 1.5, '175%': 1.75}


def _legend_extra(fig, settings, s):
    """Extra top margin when the legend row above the plot (up to 4 lines) wraps at a larger text size,
    estimated for a chart about 900 px wide (the narrowest common case, with the sidebar open)."""
    if not settings.get('legend') or not fig.data or _legend_beside(fig):
        return 0
    width = sum(len(str(t.name)) * 6.2 * s + 46 for t in fig.data)
    rows = int(width // 860) + 1
    return round((rows - 1) * 21 * s)


def _legend_beside(fig):
    """The legend goes to the right of the plot with more than 4 lines, or when it is grouped by role (its role
    headings make it too tall for the row above the plot)."""
    return len(fig.data) > 4 or any(getattr(t, 'legendgroup', None) for t in fig.data)


def text_scale(settings):
    return TEXT_SIZES.get(settings.get('text_size', '100%'), 1.0)


def _layout(fig, settings, title, height=None, x_title=None, y_title='Temperature (°C)', subtitle=None):
    # No height: the page sizes the comparison and single-profile charts at 16:9 to the card width.
    colors = _palette(settings['theme'])
    s = text_scale(settings)   # Chart text size: 1.0 = 100 %
    heading = {'text': title, 'x': 0.02, 'xanchor': 'left', 'font': {'size': round(18 * s)}}
    if subtitle:
        heading['subtitle'] = {'text': subtitle, 'font': {'size': round(12 * s), 'color': colors['muted']}}
    fig.update_layout(
        title=heading,
        height=height,
        paper_bgcolor=colors['bg'],
        plot_bgcolor=colors['plot'],
        font={'color': colors['text'], 'family': 'Inter, Arial, sans-serif', 'size': round(12 * s)},
        hovermode='x unified',
        showlegend=settings['legend'],
        # A row above the plot for up to 4 ungrouped lines; otherwise (many lines, or grouped by role) a column to
        # the right, so the legend never runs into the title.
        legend=({'orientation': 'h', 'y': 1.02, 'yanchor': 'bottom', 'x': 0.02} if not _legend_beside(fig) else
                {'orientation': 'v', 'y': 1, 'yanchor': 'top', 'x': 1.01, 'xanchor': 'left'})
               | {'font': {'size': round(11 * s), 'color': colors['muted']}, 'bgcolor': 'rgba(0,0,0,0)'},
        hoverlabel={'bgcolor': colors['bg'], 'bordercolor': colors['border'], 'font': {'color': colors['text'], 'size': round(13 * s)}},
        # Room for the title, subtitle and legend grows with the text; the axes make their own room (automargin).
        margin={'l': round(64 * s), 'r': 30, 't': round((122 if subtitle else 86) * s) + _legend_extra(fig, settings, s), 'b': round(58 * s)},
    )
    axis = dict(showgrid=settings['grid'], gridcolor=colors['grid'], zeroline=False, linecolor=colors['border'], automargin=True,
                tickfont={'color': colors['muted'], 'size': round(12 * s)}, title_font={'color': colors['muted'], 'size': round(14 * s)})
    if x_title is None:
        x_title = 'Time' if settings['alignment'] == 'Clock time' else 'Aligned time (hours)'
    fig.update_xaxes(title=x_title, **axis)
    fig.update_yaxes(title=y_title, **axis)
    return fig


def _target(fig, settings):
    """Target lines: dotted lines across the chart at temperatures the cook aimed for, each labelled with its own
    name and temperature ("Pit 120 °C"). In the page's text colour, so they never look like one of the profiles.
    All labels sit at the left end, above their line; a label that would run into the one above it goes below its line."""
    targets = list(settings.get('targets') or [])
    if not targets and settings.get('target') is not None:      # single target, as in v1.6.10
        targets = [('Target', settings['target'])]
    if not targets:
        return fig
    colors = _palette(settings['theme'])
    s = text_scale(settings)
    # Temperature range of the chart, to judge when two labels are too close (a label is about 6 % of the
    # plot height at 100 % text on a 16:9 chart).
    values = [float(v) for trace in fig.data for v in (trace.y if trace.y is not None else []) if v == v]
    values += [float(v) for _, v in targets]
    span = (max(values) - min(values)) or 1.0
    room = 0.065 * s * span
    above_line = []                                              # values whose label is above the line
    for name, value in sorted(targets, key=lambda item: -item[1]):
        crowded = any(0 < other - value < room for other in above_line)
        position = 'bottom left' if crowded else 'top left'
        if not crowded:
            above_line.append(value)
        label = html.escape(f'{name} {value:g} °C')
        fig.add_hline(y=value, line={'color': colors['text'], 'width': 2, 'dash': 'dot'}, layer='above',
                      annotation={'text': label, 'font': {'color': colors['text'], 'size': round(12 * s)},
                                  'bgcolor': colors['bg'], 'borderpad': 2},
                      annotation_position=position)
    return fig


def without_clock(profiles):
    """Profiles that have no clock times, so cannot be placed in Clock alignment."""
    return [p for p in profiles if 'timestamp' not in p.data]


def comparison(profiles, settings, subtitle=None):
    fig = go.Figure()
    if settings['alignment'] == 'Clock time':
        # A profile with only elapsed time has no time of day; the page names the ones left out.
        profiles = [p for p in profiles if p not in without_clock(profiles)]
    # The legend is grouped by role, with the role as a heading ("Pit", "Ambient", "Meat"), in the order of ROLES,
    # so a saved image shows which roles are drawn.
    order = {role: i for i, role in enumerate(ROLES)}
    profiles = sorted(profiles, key=lambda p: order.get(getattr(p, 'role', ''), len(ROLES)))
    colors = _palette(settings['theme'])
    for profile in profiles:
        frame = _frame(profile)
        y = _y(profile, frame, settings)
        x = _x(profile, settings['alignment'], y)
        keep = thin(x, y)
        label = f'{profile.name} (setpoint)' if profile.is_setpoint else profile.name
        role = getattr(profile, 'role', '')
        group = {'legendgroup': role, 'legendgrouptitle': {'text': role, 'font': {'size': round(12 * text_scale(settings)), 'color': colors['text']}}} if role else {}
        fig.add_trace(go.Scatter(
            x=_pick(x, keep), y=_pick(y, keep), mode='lines', name=label,
            line=_line(profile, settings),
            meta=[profile.name, profile.channel],
            hovertemplate='<b>%{meta[0]}</b><br>Channel: %{meta[1]}<br>Temperature: %{y:.1f} °C<br>Time: %{x}<extra></extra>',
            **group,
        ))
    fig = _layout(fig, settings, 'Temperature profiles', subtitle=subtitle)
    fig.update_layout(legend={'traceorder': 'grouped', 'groupclick': 'toggleitem'})
    return _target(fig, settings)


def single(profile, settings):
    if settings['alignment'] == 'Clock time' and 'timestamp' not in profile.data:
        settings = dict(settings, alignment='Original timeline')   # no time of day: draw it on its own hours
    frame = _frame(profile)
    y = _y(profile, frame, settings)
    x = _x(profile, settings['alignment'], y)
    fig = go.Figure()
    if settings.get('smoothing_minutes', 0) and not profile.is_setpoint:
        # Keep the raw readings visible, faintly, behind the smoothed line.
        raw = thin(x, frame.temperature_c)
        fig.add_trace(go.Scatter(
            x=_pick(x, raw), y=_pick(frame.temperature_c, raw), mode='lines', name='Raw readings', opacity=0.28,
            line={'color': profile.color, 'width': 1},
            hovertemplate='Raw: %{y:.1f} °C<extra></extra>',
        ))
    keep = thin(x, y)
    fig.add_trace(go.Scatter(
        x=_pick(x, keep), y=_pick(y, keep), mode='lines', name=profile.name,
        line=_line(profile, settings),
        hovertemplate='Temperature: %{y:.1f} °C<br>Time: %{x}<extra></extra>',
    ))
    return _target(_layout(fig, settings, profile.name), settings)


def deviation(result, settings):
    """Probe minus setpoint over time, with the accepted band shaded."""
    frame, band = result['frame'], result['band_c']
    fig = go.Figure()
    fig.add_hrect(y0=-band, y1=band, fillcolor='rgba(34,197,94,0.14)', line_width=0, layer='below')
    fig.add_hline(y=0, line={'color': _palette(settings['theme'])['muted'], 'width': 1, 'dash': 'dot'})
    keep = thin(frame.x, frame.difference_c)
    fig.add_trace(go.Scatter(
        x=_pick(frame.x, keep), y=_pick(frame.difference_c, keep), mode='lines', name='Probe minus setpoint',
        line={'color': '#2563EB', 'width': settings['width']},
        hovertemplate='Difference: %{y:+.1f} °C<extra></extra>',
    ))
    return _layout(
        fig, settings, f'Difference from setpoint (green band: ±{band:g} °C)', height=380,
        x_title='Time' if result['uses_clock_time'] else 'Time (hours)', y_title='Probe minus setpoint (°C)',
    )
