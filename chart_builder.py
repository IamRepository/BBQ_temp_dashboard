import plotly.graph_objects as go

def _x(profile,mode):
    if mode=='Clock time' and 'timestamp' in profile.data: return profile.data.timestamp
    x=profile.data.elapsed_hours+profile.offset_hours
    if mode=='Align peak': x=x-float(x.loc[profile.data.temperature_c.idxmax()])
    elif mode=='Align end': x=x-float(x.max())
    return x

def _layout(fig,s,title):
    dark=s['theme']=='Dark'; bg='#091523' if dark else '#fff'; text='#dbe7f3' if dark else '#172033'; grid='#233247' if dark else '#dbe2ea'
    fig.update_layout(title=title,height=590,paper_bgcolor=bg,plot_bgcolor=bg,font={'color':text},hovermode='x unified',showlegend=s['legend'],legend={'orientation':'h','y':1.08},margin={'l':55,'r':25,'t':80,'b':55})
    fig.update_xaxes(title='Time' if s['alignment']=='Clock time' else 'Aligned time (hours)',showgrid=s['grid'],gridcolor=grid)
    fig.update_yaxes(title='Temperature (°C)',showgrid=s['grid'],gridcolor=grid)
    return fig

def comparison(profiles,s):
    fig=go.Figure()
    for p in profiles:
        fig.add_trace(go.Scatter(x=_x(p,s['alignment']),y=p.data.temperature_c,mode='lines',name=p.name,line={'color':p.color,'width':s['width']},hovertemplate='%{y:.1f} °C<br>%{x}<extra></extra>'))
    return _layout(fig,s,'Temperature profile comparison')

def single(profile,s):
    fig=go.Figure(go.Scatter(x=_x(profile,s['alignment']),y=profile.data.temperature_c,mode='lines',name=profile.name,line={'color':profile.color,'width':s['width']}))
    return _layout(fig,s,profile.name)
