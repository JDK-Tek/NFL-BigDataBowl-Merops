"""Plotly visualizations for the NFL broadcast dashboard."""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from src.components import TEAM_COLORS

PLOT_BG = "#091523"
GRID = "rgba(214,235,255,.12)"
TEXT = "#DDEBFA"
MUTED = "#8299AF"
CYAN = "#16D9E3"
ORANGE = "#FF9F43"
GREEN = "#5CE1A4"
RED = "#FF637D"


def build_instant_field(
    enriched: pd.DataFrame,
    play: pd.Series,
    frame_id: int,
    target_id: int | None,
) -> go.Figure:
    frame = enriched.loc[enriched["frameId"] == int(frame_id)]
    history = enriched.loc[enriched["frameId"] <= int(frame_id)]
    direction = _direction(enriched)
    fig = go.Figure()
    _decorate_field(fig, play, direction)

    for nfl_id, color, width in [(_qb_id(enriched), "#F7D154", 2.5), (target_id, CYAN, 3.2)]:
        if nfl_id is None:
            continue
        path = history.loc[history["nflId"].eq(nfl_id)].sort_values("frameId")
        if not path.empty:
            fig.add_trace(go.Scatter(
                x=path["x"], y=path["y"], mode="lines", hoverinfo="skip",
                line=dict(color=color, width=width), opacity=.7, showlegend=False,
            ))

    for trace in _frame_traces(frame, play, target_id):
        fig.add_trace(trace)
    fig.update_layout(height=545, margin=dict(l=18, r=18, t=46, b=16), title=dict(
        text=f"INSTANT T · FRAME {int(frame_id)}", font=dict(size=13, color=MUTED), x=.02, y=.97
    ))
    return fig


def build_replay(enriched: pd.DataFrame, play: pd.Series, target_id: int | None) -> go.Figure:
    frame_ids = sorted(enriched["frameId"].unique().tolist())
    if not frame_ids:
        return go.Figure()
    direction = _direction(enriched)
    initial = enriched.loc[enriched["frameId"] == frame_ids[0]]
    fig = go.Figure(data=_frame_traces(initial, play, target_id))
    _decorate_field(fig, play, direction)

    animation_frames = []
    for frame_id in frame_ids:
        frame = enriched.loc[enriched["frameId"] == frame_id]
        event = _event_label(frame)
        animation_frames.append(go.Frame(
            name=str(frame_id),
            data=_frame_traces(frame, play, target_id),
            layout=go.Layout(title=dict(
                text=f"REPLAY AÉRIEN · FRAME {frame_id} · {event}",
                font=dict(size=13, color=MUTED), x=.02, y=.97,
            )),
        ))
    fig.frames = animation_frames

    steps = [
        dict(
            method="animate",
            args=[[str(frame_id)], {"mode": "immediate", "frame": {"duration": 0, "redraw": False}, "transition": {"duration": 0}}],
            label=str(frame_id) if index % 10 == 0 else "",
        )
        for index, frame_id in enumerate(frame_ids)
    ]
    fig.update_layout(
        height=590,
        margin=dict(l=18, r=18, t=46, b=82),
        title=dict(text="REPLAY AÉRIEN", font=dict(size=13, color=MUTED), x=.02, y=.97),
        updatemenus=[dict(
            type="buttons", direction="left", showactive=False, x=.01, y=-.08,
            bgcolor="#13273B", bordercolor="rgba(255,255,255,.14)", font=dict(color=TEXT),
            buttons=[
                dict(label="▶  LECTURE", method="animate", args=[None, {"fromcurrent": True, "frame": {"duration": 100, "redraw": False}, "transition": {"duration": 35}}]),
                dict(label="Ⅱ  PAUSE", method="animate", args=[[None], {"mode": "immediate", "frame": {"duration": 0, "redraw": False}, "transition": {"duration": 0}}]),
            ],
        )],
        sliders=[dict(
            active=0, x=.28, y=-.065, len=.70, pad={"t": 10, "b": 0},
            currentvalue={"prefix": "FRAME ", "font": {"color": CYAN, "size": 11}},
            tickcolor="rgba(0,0,0,0)", font={"color": MUTED, "size": 9}, steps=steps,
        )],
    )
    return fig


def _frame_traces(frame: pd.DataFrame, play: pd.Series, target_id: int | None) -> list[go.Scatter]:
    offense_team = str(play["possessionTeam"])
    defense_team = str(play["defensiveTeam"])
    traces: list[go.Scatter] = []
    specs = [
        ("offense", offense_team, TEAM_COLORS.get(offense_team, "#247CFF"), "circle"),
        ("defense", defense_team, TEAM_COLORS.get(defense_team, "#FF637D"), "diamond"),
    ]
    for side, team, color, symbol in specs:
        rows = frame.loc[frame["side"] == side].copy()
        border_colors = [CYAN if (target_id is not None and not pd.isna(v) and int(v) == target_id) else "#F7FBFF" for v in rows["nflId"]]
        custom = np.stack([
            rows["displayName"].astype(str), rows["pff_role"].astype(str),
            rows["s"].round(2).astype(str), rows["a"].round(2).astype(str),
        ], axis=-1) if not rows.empty else np.empty((0, 4))
        traces.append(go.Scatter(
            x=rows["x"], y=rows["y"], mode="markers+text", name=team,
            text=rows["jerseyLabel"], textposition="middle center",
            textfont=dict(color="white", size=9, family="Arial Black"),
            marker=dict(size=24, color=color, symbol=symbol, line=dict(color=border_colors, width=2)),
            customdata=custom,
            hovertemplate="<b>%{customdata[0]}</b><br>%{customdata[1]}<br>Vitesse %{customdata[2]} yd/s<br>Accélération %{customdata[3]} yd/s²<extra></extra>",
        ))
    ball = frame.loc[frame["side"] == "football"]
    traces.append(go.Scatter(
        x=ball["x"], y=ball["y"], mode="markers", name="Football",
        marker=dict(size=13, color="#9A5A2B", symbol="diamond", line=dict(color="#FFFFFF", width=1.5)),
        hovertemplate="<b>Football</b><extra></extra>",
    ))
    return traces


def _decorate_field(fig: go.Figure, play: pd.Series, direction: str) -> None:
    shapes: list[dict] = [
        dict(type="rect", x0=0, x1=120, y0=0, y1=53.3, fillcolor="#0C5137", line=dict(color="#678B7B", width=1), layer="below"),
        dict(type="rect", x0=0, x1=10, y0=0, y1=53.3, fillcolor="#17314A", line=dict(width=0), layer="below"),
        dict(type="rect", x0=110, x1=120, y0=0, y1=53.3, fillcolor="#17314A", line=dict(width=0), layer="below"),
    ]
    annotations: list[dict] = []
    for x in range(10, 111, 5):
        major = x % 10 == 0
        shapes.append(dict(
            type="line", x0=x, x1=x, y0=0, y1=53.3,
            line=dict(color="rgba(255,255,255,.32)" if major else "rgba(255,255,255,.13)", width=1), layer="below",
        ))
        if major and x not in (10, 110):
            yard = x - 10 if x <= 60 else 110 - x
            annotations.extend([
                dict(x=x, y=4.0, text=str(yard), showarrow=False, font=dict(size=10, color="rgba(255,255,255,.42)")),
                dict(x=x, y=49.3, text=str(yard), showarrow=False, font=dict(size=10, color="rgba(255,255,255,.42)")),
            ])
    try:
        los = float(play["absoluteYardlineNumber"])
        if direction == "left":
            los = 120 - los
        first_down = los + float(play["yardsToGo"]) * (1 if direction == "right" else -1)
        shapes.extend([
            dict(type="line", x0=los, x1=los, y0=0, y1=53.3, line=dict(color="#27A9FF", width=3), layer="below"),
            dict(type="line", x0=first_down, x1=first_down, y0=0, y1=53.3, line=dict(color="#F7D154", width=3, dash="dot"), layer="below"),
        ])
    except (TypeError, ValueError):
        pass
    fig.update_layout(
        paper_bgcolor=PLOT_BG, plot_bgcolor=PLOT_BG, font=dict(color=TEXT),
        xaxis=dict(range=[0, 120], visible=False, fixedrange=True),
        yaxis=dict(range=[-1, 54.3], visible=False, fixedrange=True, scaleanchor="x", scaleratio=1),
        shapes=shapes, annotations=annotations, hovermode="closest",
        legend=dict(orientation="h", x=.5, xanchor="center", y=1.01, yanchor="bottom", bgcolor="rgba(0,0,0,0)"),
    )


def build_pressure_window_chart(series: pd.DataFrame, key_frames: dict[str, int]) -> go.Figure:
    fig = go.Figure()
    if not series.empty:
        fig.add_trace(go.Scatter(
            x=series["timeFromSnap"], y=series["nearestRusherDistance"], mode="lines",
            name="Distance rusher → QB", line=dict(color=ORANGE, width=3),
            hovertemplate="%{x:.1f} s · %{y:.2f} yd<extra></extra>",
        ))
        fig.add_trace(go.Scatter(
            x=series["timeFromSnap"], y=series["targetSeparation"], mode="lines",
            name="Séparation cible", line=dict(color=CYAN, width=3),
            hovertemplate="%{x:.1f} s · %{y:.2f} yd<extra></extra>",
        ))
        for label, frame, color in [
            ("SNAP", key_frames["snap"], GREEN), ("LANCER", key_frames["pass"], "#F7D154"),
            ("RÉSULTAT", key_frames["outcome"], RED),
        ]:
            x = (frame - key_frames["snap"]) * .1
            fig.add_vline(x=x, line_dash="dot", line_color=color, opacity=.75)
            fig.add_annotation(x=x, y=1.08, yref="paper", text=label, showarrow=False, font=dict(size=9, color=color))
    _chart_layout(fig, "DYNAMIQUE DE LA POCHE ET DE LA FENÊTRE", "Secondes depuis le snap", "Distance (yards)", 340)
    return fig


def build_coverage_chart(coverage: pd.DataFrame) -> go.Figure:
    top = coverage.head(8).sort_values("Plays")
    fig = go.Figure(go.Bar(
        x=top["Plays"], y=top["Coverage"], orientation="h",
        marker=dict(color=top["YardsPerPlay"], colorscale=[[0, "#17324A"], [.5, CYAN], [1, ORANGE]], colorbar=dict(title="Yds/jeu", thickness=10)),
        text=top["Plays"], textposition="outside", hovertemplate="<b>%{y}</b><br>%{x} jeux<extra></extra>",
    ))
    _chart_layout(fig, "COUVERTURES AFFRONTÉES", "Nombre de jeux", "", 385)
    fig.update_layout(yaxis=dict(gridcolor="rgba(0,0,0,0)"))
    return fig


def build_player_path(enriched: pd.DataFrame, nfl_id: int, play: pd.Series) -> go.Figure:
    rows = enriched.loc[enriched["nflId"].eq(int(nfl_id))].sort_values("frameId")
    fig = go.Figure()
    _decorate_field(fig, play, _direction(enriched))
    if not rows.empty:
        fig.add_trace(go.Scatter(
            x=rows["x"], y=rows["y"], mode="lines+markers", name=str(rows.iloc[0]["displayName"]),
            line=dict(color=CYAN, width=4), marker=dict(size=5, color=rows["s"], colorscale="Turbo", showscale=True, colorbar=dict(title="yd/s", thickness=10)),
            customdata=np.stack([rows["frameId"], rows["s"].round(2)], axis=-1),
            hovertemplate="Frame %{customdata[0]}<br>Vitesse %{customdata[1]} yd/s<extra></extra>",
        ))
    fig.update_layout(height=480, margin=dict(l=18, r=18, t=45, b=16), title=dict(text="TRAJECTOIRE ET VITESSE", font=dict(size=13, color=MUTED), x=.02))
    return fig


def _chart_layout(fig: go.Figure, title: str, x_title: str, y_title: str, height: int) -> None:
    fig.update_layout(
        title=dict(text=title, font=dict(size=13, color=MUTED), x=.035), height=height,
        paper_bgcolor=PLOT_BG, plot_bgcolor=PLOT_BG, font=dict(color=TEXT),
        margin=dict(l=54, r=28, t=62, b=45), hovermode="x unified",
        xaxis=dict(title=x_title, gridcolor=GRID, zeroline=False),
        yaxis=dict(title=y_title, gridcolor=GRID, zeroline=False),
        legend=dict(orientation="h", x=0, y=1.18, bgcolor="rgba(0,0,0,0)"),
    )


def _direction(enriched: pd.DataFrame) -> str:
    values = enriched["playDirection"].dropna()
    return str(values.iloc[0]) if not values.empty else "right"


def _qb_id(enriched: pd.DataFrame) -> int | None:
    values = enriched.loc[enriched["pff_role"].str.lower().eq("pass"), "nflId"].dropna()
    return int(values.iloc[0]) if not values.empty else None


def _event_label(frame: pd.DataFrame) -> str:
    values = frame.loc[~frame["event"].str.lower().isin(["none", "nan", ""]), "event"].drop_duplicates()
    return " · ".join(values.astype(str).tolist()).upper() if not values.empty else "TRACKING"
