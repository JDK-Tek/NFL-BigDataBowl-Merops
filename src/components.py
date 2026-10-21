"""Reusable Streamlit presentation components."""

from __future__ import annotations

from html import escape

import streamlit as st


GLOBAL_CSS = """
<style>
:root {
  --bg: #07101d;
  --panel: rgba(13, 25, 41, .94);
  --panel-2: #101f32;
  --line: rgba(148, 176, 205, .16);
  --text: #edf5ff;
  --muted: #8fa5bb;
  --cyan: #16d9e3;
  --orange: #ff9f43;
  --green: #5ce1a4;
  --red: #ff637d;
}
.stApp { background: radial-gradient(circle at 80% -10%, #123657 0, #07101d 35%, #050b14 100%); }
.block-container { max-width: 1640px; padding-top: 1.2rem; padding-bottom: 2rem; }
[data-testid="stSidebar"] { background: linear-gradient(180deg, #0b1727 0%, #07101d 100%); border-right: 1px solid var(--line); }
[data-testid="stSidebar"] .block-container { padding-top: 1.4rem; }
[data-testid="stMetric"] { background: var(--panel); border: 1px solid var(--line); border-radius: 14px; padding: .8rem 1rem; }
[data-testid="stMetricLabel"] { color: var(--muted); }
[data-testid="stMetricValue"] { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; letter-spacing: -.04em; }
[data-testid="stPlotlyChart"] { background: var(--panel); border: 1px solid var(--line); border-radius: 18px; overflow: hidden; }
.stTabs [data-baseweb="tab-list"] { gap: .35rem; padding: .3rem; background: rgba(13,25,41,.8); border: 1px solid var(--line); border-radius: 13px; }
.stTabs [data-baseweb="tab"] { border-radius: 9px; color: var(--muted); padding: .65rem 1rem; }
.stTabs [aria-selected="true"] { background: #17324a !important; color: var(--text) !important; }
.stSelectbox label, .stSlider label, .stRadio label { color: #b7c8d8 !important; font-weight: 600 !important; }
hr { border-color: var(--line); }
.broadcast-brand { display:flex; align-items:center; gap:.75rem; margin-bottom:1.2rem; }
.brand-mark { width:37px; height:37px; border-radius:11px; background:linear-gradient(135deg,var(--cyan),#247cff); box-shadow:0 0 26px rgba(22,217,227,.3); }
.brand-title { color:var(--text); font-size:1rem; font-weight:850; letter-spacing:.08em; }
.brand-sub { color:var(--muted); font-size:.68rem; letter-spacing:.12em; text-transform:uppercase; }
.live-pill { display:inline-flex; align-items:center; gap:.42rem; background:rgba(255,99,125,.12); border:1px solid rgba(255,99,125,.35); color:#ff8ca0; border-radius:100px; padding:.28rem .62rem; font-size:.68rem; font-weight:800; letter-spacing:.09em; }
.live-dot { width:7px; height:7px; background:#ff637d; border-radius:50%; box-shadow:0 0 12px #ff637d; }
.scorebug { display:grid; grid-template-columns:1fr auto 1fr; align-items:center; min-height:116px; background:linear-gradient(120deg,rgba(16,31,50,.98),rgba(8,19,32,.98)); border:1px solid var(--line); border-radius:18px; overflow:hidden; box-shadow:0 16px 50px rgba(0,0,0,.22); margin-bottom:1rem; }
.score-team { display:flex; align-items:center; gap:1rem; padding:1.25rem 1.5rem; }
.score-team.away { justify-content:flex-end; text-align:right; }
.team-token { display:grid; place-items:center; width:58px; height:58px; border-radius:16px; background:var(--team); color:white; font-weight:900; font-size:1.15rem; border:1px solid rgba(255,255,255,.18); box-shadow:inset 0 0 24px rgba(0,0,0,.2); }
.team-name { color:var(--muted); font-size:.72rem; letter-spacing:.1em; font-weight:800; }
.team-score { color:var(--text); font-size:2.55rem; line-height:1; font-weight:900; letter-spacing:-.06em; }
.score-center { min-width:190px; text-align:center; padding:1rem 1.4rem; border-left:1px solid var(--line); border-right:1px solid var(--line); }
.game-state { color:var(--cyan); font-size:.77rem; font-weight:900; letter-spacing:.08em; }
.game-down { color:var(--text); font-size:1.05rem; font-weight:800; margin-top:.24rem; }
.game-meta { color:var(--muted); font-size:.68rem; margin-top:.28rem; }
.panel { background:var(--panel); border:1px solid var(--line); border-radius:16px; padding:1rem 1.1rem; height:100%; }
.panel-title { color:var(--text); font-weight:820; font-size:.84rem; letter-spacing:.06em; text-transform:uppercase; margin-bottom:.8rem; }
.callout { background:linear-gradient(120deg,rgba(22,217,227,.08),rgba(36,124,255,.07)); border-left:3px solid var(--cyan); border-radius:0 12px 12px 0; color:#dceaf5; padding:.8rem 1rem; margin:.55rem 0; font-size:.88rem; line-height:1.45; }
.data-row { display:flex; justify-content:space-between; gap:1rem; padding:.55rem 0; border-bottom:1px solid var(--line); font-size:.8rem; }
.data-row:last-child { border-bottom:0; }
.data-label { color:var(--muted); }
.data-value { color:var(--text); font-weight:720; text-align:right; }
.event-chip { display:inline-block; background:#16283b; border:1px solid var(--line); color:#bcd1e3; padding:.24rem .5rem; border-radius:7px; font-size:.67rem; margin:.15rem .12rem .15rem 0; }
.section-kicker { color:var(--cyan); font-size:.68rem; letter-spacing:.13em; text-transform:uppercase; font-weight:850; margin-bottom:.2rem; }
.section-title { color:var(--text); font-size:1.5rem; font-weight:880; letter-spacing:-.03em; margin-bottom:.15rem; }
.section-copy { color:var(--muted); font-size:.83rem; margin-bottom:.85rem; }
.confidence { color:var(--muted); font-size:.7rem; }
</style>
"""

TEAM_COLORS = {
    "ARI": "#97233F", "ATL": "#A71930", "BAL": "#241773", "BUF": "#00338D",
    "CAR": "#0085CA", "CHI": "#0B162A", "CIN": "#FB4F14", "CLE": "#311D00",
    "DAL": "#003594", "DEN": "#FB4F14", "DET": "#0076B6", "GB": "#203731",
    "HOU": "#03202F", "IND": "#002C5F", "JAX": "#006778", "KC": "#E31837",
    "LA": "#003594", "LAC": "#0080C6", "LV": "#000000", "MIA": "#008E97",
    "MIN": "#4F2683", "NE": "#002244", "NO": "#D3BC8D", "NYG": "#0B2265",
    "NYJ": "#125740", "PHI": "#004C54", "PIT": "#FFB612", "SEA": "#002244",
    "SF": "#AA0000", "TB": "#D50A0A", "TEN": "#0C2340", "WAS": "#5A1414",
}


def inject_css() -> None:
    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)


def render_brand() -> None:
    st.markdown(
        """
        <div class="broadcast-brand">
          <div class="brand-mark"></div>
          <div><div class="brand-title">GRIDIRON IQ</div>
          <div class="brand-sub">Broadcast Intelligence</div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_scorebug(game, play) -> None:
    home = str(game["homeTeamAbbr"])
    away = str(game["visitorTeamAbbr"])
    home_score = int(play["preSnapHomeScore"])
    away_score = int(play["preSnapVisitorScore"])
    quarter = int(play["quarter"])
    down = int(play["down"])
    ordinal = {1: "1ER", 2: "2E", 3: "3E", 4: "4E"}.get(down, str(down))
    html = f"""
    <div class="scorebug">
      <div class="score-team away">
        <div><div class="team-name">EXTÉRIEUR</div><div class="team-score">{away_score}</div></div>
        <div class="team-token" style="--team:{TEAM_COLORS.get(away, '#334155')}">{escape(away)}</div>
      </div>
      <div class="score-center">
        <div class="game-state">Q{quarter} · {escape(str(play['gameClock']))}</div>
        <div class="game-down">{ordinal} &amp; {int(play['yardsToGo'])}</div>
        <div class="game-meta">PLAY #{int(play['playId'])} · SIMULATION LIVE</div>
      </div>
      <div class="score-team">
        <div class="team-token" style="--team:{TEAM_COLORS.get(home, '#334155')}">{escape(home)}</div>
        <div><div class="team-name">DOMICILE</div><div class="team-score">{home_score}</div></div>
      </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def section_header(kicker: str, title: str, copy: str = "") -> None:
    st.markdown(
        f'<div class="section-kicker">{escape(kicker)}</div>'
        f'<div class="section-title">{escape(title)}</div>'
        f'<div class="section-copy">{escape(copy)}</div>',
        unsafe_allow_html=True,
    )


def panel_html(title: str, rows: list[tuple[str, object]], footer: str = "") -> str:
    body = "".join(
        f'<div class="data-row"><span class="data-label">{escape(str(label))}</span>'
        f'<span class="data-value">{escape(str(value))}</span></div>'
        for label, value in rows
    )
    footer_html = f'<div class="confidence">{escape(footer)}</div>' if footer else ""
    return f'<div class="panel"><div class="panel-title">{escape(title)}</div>{body}{footer_html}</div>'


def render_insights(insights: list[str]) -> None:
    st.markdown('<div class="panel-title">INSIGHTS COMMENTATEUR</div>', unsafe_allow_html=True)
    for insight in insights:
        st.markdown(f'<div class="callout">{escape(insight)}</div>', unsafe_allow_html=True)


def fmt(value: object, suffix: str = "", decimals: int = 1, fallback: str = "—") -> str:
    try:
        if value is None or value != value:
            return fallback
        return f"{float(value):.{decimals}f}{suffix}"
    except (TypeError, ValueError):
        return fallback
