from __future__ import annotations

import plotly.graph_objects as go


def _layout(fig, settings, title: str):
    dark = settings["theme"] == "Dark"
    paper = "#091523" if dark else "#ffffff"
    text = "#dbe7f3" if dark else "#172033"
    grid = "#233247" if dark else "#dbe2ea"
    fig.update_layout(
        title=title,
        height=590,
        paper_bgcolor=paper,
        plot_bgcolor=paper,
        font={"color": text},
        hovermode="x unified",
        legend={"orientation": "h", "y": 1.08, "x": 0},
        showlegend=settings["show_legend"],
        margin={"l": 55, "r": 25, "t": 80, "b": 55},
    )
    fig.update_xaxes(title="Elapsed time (hours)" if settings["align_mode"] == "Elapsed time" else "Time", showgrid=settings["show_grid"], gridcolor=grid)
    fig.update_yaxes(title=f"Temperature (°{settings['unit']})", showgrid=settings["show_grid"], gridcolor=grid)
    return fig


def _xy(profile, settings):
    unit = settings["unit"]
    y = profile.data["temperature_c"] * 9 / 5 + 32 if unit == "F" else profile.data["temperature_c"]
    if settings["align_mode"] == "Clock time" and "timestamp" in profile.data.columns:
        x = profile.data["timestamp"]
    else:
        x = profile.data["elapsed_hours"] + profile.offset_hours
    return x, y


def build_comparison_chart(profiles, settings):
    fig = go.Figure()
    for profile in profiles:
        x, y = _xy(profile, settings)
        fig.add_trace(go.Scatter(x=x, y=y, mode="lines", name=profile.name, line={"color": profile.color, "width": settings["line_width"]}, customdata=[profile.channel] * len(y), hovertemplate="%{y:.1f}°<br>%{x}<br>%{customdata}<extra></extra>"))
    return _layout(fig, settings, "Cook profile comparison")


def build_single_profile_chart(profile, settings):
    fig = go.Figure()
    x, y = _xy(profile, settings)
    fig.add_trace(go.Scatter(x=x, y=y, mode="lines", name=profile.name, line={"color": profile.color, "width": settings["line_width"]}))
    return _layout(fig, settings, profile.name)
