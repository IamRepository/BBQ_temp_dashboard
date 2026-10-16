import numpy as np
import pandas as pd
import plotly.graph_objects as go

from analysis import smooth

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
    line = {'color': profile.color, 'width': settings['width']}
    if profile.is_setpoint:
        line['dash'] = 'dash'
    return line


def _palette(mode):
    if mode == 'Dark':
        return {'bg': '#111827', 'plot': '#111827', 'text': '#E5E7EB', 'muted': '#9CA3AF', 'grid': 'rgba(148,163,184,0.12)', 'border': '#263244'}
    return {'bg': '#FFFFFF', 'plot': '#FFFFFF', 'text': '#172033', 'muted': '#64748B', 'grid': 'rgba(100,116,139,0.11)', 'border': '#E2E8F0'}


def _layout(fig, settings, title, height=None, x_title=None, y_title='Temperature (°C)', subtitle=None):
    # No height: the page sizes the comparison and single-profile charts at 16:9 to the card width.
    colors = _palette(settings['theme'])
    heading = {'text': title, 'x': 0.02, 'xanchor': 'left', 'font': {'size': 18}}
    if subtitle:
        heading['subtitle'] = {'text': subtitle, 'font': {'size': 12, 'color': colors['muted']}}
    fig.update_layout(
        title=heading,
        height=height,
        paper_bgcolor=colors['bg'],
        plot_bgcolor=colors['plot'],
        font={'color': colors['text'], 'family': 'Inter, Arial, sans-serif'},
        hovermode='x unified',
        showlegend=settings['legend'],
        legend={'orientation': 'h', 'y': 1.02, 'yanchor': 'bottom', 'x': 0.02, 'font': {'size': 11, 'color': colors['muted']}, 'bgcolor': 'rgba(0,0,0,0)'},
        hoverlabel={'bgcolor': colors['bg'], 'bordercolor': colors['border'], 'font': {'color': colors['text']}},
        margin={'l': 64, 'r': 30, 't': 122 if subtitle else 86, 'b': 58},
    )
    axis = dict(showgrid=settings['grid'], gridcolor=colors['grid'], zeroline=False, linecolor=colors['border'], tickfont={'color': colors['muted']}, title_font={'color': colors['muted']})
    if x_title is None:
        x_title = 'Time' if settings['alignment'] == 'Clock time' else 'Aligned time (hours)'
    fig.update_xaxes(title=x_title, **axis)
    fig.update_yaxes(title=y_title, **axis)
    return fig


def _target(fig, settings):
    """The target line: a dotted line across the chart at the temperature the cook aimed for, labelled at the left.
    In the page's text colour, so it never looks like one of the profiles."""
    value = settings.get('target')
    if value is None:
        return fig
    colors = _palette(settings['theme'])
    fig.add_hline(y=value, line={'color': colors['text'], 'width': 2, 'dash': 'dot'}, layer='above',
                  annotation={'text': f'Target {value:g} °C', 'font': {'color': colors['text'], 'size': 12},
                              'bgcolor': colors['bg'], 'borderpad': 2},
                  annotation_position='top left')
    return fig


def without_clock(profiles):
    """Profiles that have no clock times, so cannot be placed in Clock alignment."""
    return [p for p in profiles if 'timestamp' not in p.data]


def comparison(profiles, settings, subtitle=None):
    fig = go.Figure()
    if settings['alignment'] == 'Clock time':
        # A profile with only elapsed time has no time of day; the page names the ones left out.
        profiles = [p for p in profiles if p not in without_clock(profiles)]
    for profile in profiles:
        frame = _frame(profile)
        y = _y(profile, frame, settings)
        x = _x(profile, settings['alignment'], y)
        keep = thin(x, y)
        label = f'{profile.name} (setpoint)' if profile.is_setpoint else profile.name
        fig.add_trace(go.Scatter(
            x=_pick(x, keep), y=_pick(y, keep), mode='lines', name=label,
            line=_line(profile, settings),
            meta=[profile.name, profile.channel],
            hovertemplate='<b>%{meta[0]}</b><br>Channel: %{meta[1]}<br>Temperature: %{y:.1f} °C<br>Time: %{x}<extra></extra>',
        ))
    return _target(_layout(fig, settings, 'Temperature profiles', subtitle=subtitle), settings)


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
