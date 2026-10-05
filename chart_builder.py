import pandas as pd
import plotly.graph_objects as go

from analysis import smooth


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


def _layout(fig, settings, title, height=650, x_title=None, y_title='Temperature (°C)'):
    colors = _palette(settings['theme'])
    fig.update_layout(
        title={'text': title, 'x': 0.02, 'xanchor': 'left', 'font': {'size': 18}},
        height=height,
        paper_bgcolor=colors['bg'],
        plot_bgcolor=colors['plot'],
        font={'color': colors['text'], 'family': 'Inter, Arial, sans-serif'},
        hovermode='x unified',
        showlegend=settings['legend'],
        legend={'orientation': 'h', 'y': 1.08, 'x': 0.02, 'font': {'size': 11, 'color': colors['muted']}, 'bgcolor': 'rgba(0,0,0,0)'},
        hoverlabel={'bgcolor': colors['bg'], 'bordercolor': colors['border'], 'font': {'color': colors['text']}},
        margin={'l': 64, 'r': 30, 't': 86, 'b': 58},
    )
    axis = dict(showgrid=settings['grid'], gridcolor=colors['grid'], zeroline=False, linecolor=colors['border'], tickfont={'color': colors['muted']}, title_font={'color': colors['muted']})
    if x_title is None:
        x_title = 'Time' if settings['alignment'] == 'Clock time' else 'Aligned time (hours)'
    fig.update_xaxes(title=x_title, **axis)
    fig.update_yaxes(title=y_title, **axis)
    return fig


def comparison(profiles, settings):
    fig = go.Figure()
    for profile in profiles:
        frame = _frame(profile)
        y = _y(profile, frame, settings)
        label = f'{profile.name} (setpoint)' if profile.is_setpoint else profile.name
        fig.add_trace(go.Scatter(
            x=_x(profile, settings['alignment'], y), y=y, mode='lines', name=label,
            line=_line(profile, settings),
            customdata=[[profile.name, profile.channel]] * len(frame),
            hovertemplate='<b>%{customdata[0]}</b><br>Channel: %{customdata[1]}<br>Temperature: %{y:.1f} °C<br>Time: %{x}<extra></extra>',
        ))
    return _layout(fig, settings, 'Temperature profiles')


def single(profile, settings):
    frame = _frame(profile)
    y = _y(profile, frame, settings)
    x = _x(profile, settings['alignment'], y)
    fig = go.Figure()
    if settings.get('smoothing_minutes', 0) and not profile.is_setpoint:
        # Keep the raw readings visible, faintly, behind the smoothed line.
        fig.add_trace(go.Scatter(
            x=x, y=frame.temperature_c, mode='lines', name='Raw readings', opacity=0.28,
            line={'color': profile.color, 'width': 1},
            hovertemplate='Raw: %{y:.1f} °C<extra></extra>',
        ))
    fig.add_trace(go.Scatter(
        x=x, y=y, mode='lines', name=profile.name,
        line=_line(profile, settings),
        hovertemplate='Temperature: %{y:.1f} °C<br>Time: %{x}<extra></extra>',
    ))
    return _layout(fig, settings, profile.name)


def deviation(result, settings):
    """Probe minus setpoint over time, with the accepted band shaded."""
    frame, band = result['frame'], result['band_c']
    fig = go.Figure()
    fig.add_hrect(y0=-band, y1=band, fillcolor='rgba(34,197,94,0.14)', line_width=0, layer='below')
    fig.add_hline(y=0, line={'color': _palette(settings['theme'])['muted'], 'width': 1, 'dash': 'dot'})
    fig.add_trace(go.Scatter(
        x=frame.x, y=frame.difference_c, mode='lines', name='Probe minus setpoint',
        line={'color': '#2563EB', 'width': settings['width']},
        hovertemplate='Difference: %{y:+.1f} °C<extra></extra>',
    ))
    return _layout(
        fig, settings, f'Difference from setpoint (green band: ±{band:g} °C)', height=380,
        x_title='Time' if result['uses_clock_time'] else 'Time (hours)', y_title='Probe minus setpoint (°C)',
    )
