import plotly.graph_objects as go


def _x(profile, mode):
    if mode == 'Clock time' and 'timestamp' in profile.data:
        return profile.data.timestamp
    x = profile.data.elapsed_hours + profile.offset_hours
    if mode == 'Align peak':
        x = x - float(x.loc[profile.data.temperature_c.idxmax()])
    elif mode == 'Align end':
        x = x - float(x.max())
    return x


def _palette(mode):
    if mode == 'Dark':
        return {'bg': '#111827', 'plot': '#111827', 'text': '#E5E7EB', 'muted': '#9CA3AF', 'grid': 'rgba(148,163,184,0.16)', 'border': '#263244'}
    return {'bg': '#FFFFFF', 'plot': '#FFFFFF', 'text': '#162033', 'muted': '#64748B', 'grid': 'rgba(100,116,139,0.14)', 'border': '#E2E8F0'}


def _layout(fig, settings, title):
    colors = _palette(settings['theme'])
    fig.update_layout(
        title={'text': title, 'x': 0.02, 'xanchor': 'left', 'font': {'size': 18}},
        height=560,
        paper_bgcolor=colors['bg'],
        plot_bgcolor=colors['plot'],
        font={'color': colors['text'], 'family': 'Inter, Arial, sans-serif'},
        hovermode='x unified',
        showlegend=settings['legend'],
        legend={'orientation': 'h', 'y': 1.09, 'x': 0.02, 'font': {'size': 11, 'color': colors['muted']}},
        hoverlabel={'bgcolor': colors['bg'], 'bordercolor': colors['border'], 'font': {'color': colors['text']}},
        margin={'l': 64, 'r': 30, 't': 86, 'b': 58},
    )
    axis = dict(showgrid=settings['grid'], gridcolor=colors['grid'], zeroline=False, linecolor=colors['border'], tickfont={'color': colors['muted']}, title_font={'color': colors['muted']})
    fig.update_xaxes(title='Time' if settings['alignment'] == 'Clock time' else 'Aligned time (hours)', **axis)
    fig.update_yaxes(title='Temperature (°C)', **axis)
    return fig


def comparison(profiles, settings):
    fig = go.Figure()
    for profile in profiles:
        fig.add_trace(go.Scatter(
            x=_x(profile, settings['alignment']),
            y=profile.data.temperature_c,
            mode='lines',
            name=profile.name,
            line={'color': profile.color, 'width': settings['width']},
            customdata=[[profile.name, profile.channel]] * len(profile.data),
            hovertemplate='<b>%{customdata[0]}</b><br>Channel: %{customdata[1]}<br>Temperature: %{y:.1f} °C<br>Time: %{x}<extra></extra>',
        ))
    return _layout(fig, settings, 'Temperature profiles')


def single(profile, settings):
    fig = go.Figure(go.Scatter(
        x=_x(profile, settings['alignment']),
        y=profile.data.temperature_c,
        mode='lines',
        name=profile.name,
        line={'color': profile.color, 'width': settings['width']},
        hovertemplate='Temperature: %{y:.1f} °C<br>Time: %{x}<extra></extra>',
    ))
    return _layout(fig, settings, profile.name)
