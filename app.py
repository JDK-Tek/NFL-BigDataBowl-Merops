"""Gridiron IQ — professional NFL broadcast intelligence dashboard."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import streamlit as st

from src.analytics import (
    aggregate_team_context,
    build_commentator_insights,
    compute_frame_series,
    compute_play_metrics,
    enrich_tracking,
    get_qb_id,
    identify_key_frames,
    infer_target,
    instantaneous_metrics,
    pass_rushers,
    player_play_summary,
    protection_matchups,
)
from src.components import (
    fmt,
    inject_css,
    panel_html,
    render_brand,
    render_insights,
    render_scorebug,
    section_header,
)
from src.data_loader import (
    format_play_label,
    get_play_scouting,
    get_play_tracking,
    load_games,
    load_players,
    load_plays,
    load_scouting,
    load_tracking,
)
from src.visualizations import (
    build_coverage_chart,
    build_instant_field,
    build_player_path,
    build_pressure_window_chart,
    build_replay,
)

st.set_page_config(
    page_title="Gridiron IQ · NFL Broadcast Intelligence",
    page_icon="🏈",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_css()

OUTCOMES = {
    "C": "Passe complétée",
    "I": "Passe incomplète",
    "S": "Sack",
    "IN": "Interception",
    "R": "Scramble",
}


def safe_int(value: object, fallback: int = 0) -> int:
    try:
        return int(float(value)) if not pd.isna(value) else fallback
    except (TypeError, ValueError):
        return fallback


def compact_description(value: object, limit: int = 260) -> str:
    text = str(value).strip()
    return text if len(text) <= limit else text[: limit - 1] + "…"


@st.cache_data(show_spinner=False)
def game_pass_rush_leaderboard(
    game_scouting: pd.DataFrame,
    players: pd.DataFrame,
) -> pd.DataFrame:
    rush = game_scouting.loc[game_scouting["pff_role"].str.lower().eq("pass rush")].copy()
    if rush.empty:
        return pd.DataFrame()
    for column in ("pff_hurry", "pff_hit", "pff_sack"):
        rush[column] = rush[column].fillna(0)
    board = (
        rush.groupby("nflId")
        .agg(
            RushSnaps=("playId", "nunique"),
            Hurries=("pff_hurry", "sum"),
            Hits=("pff_hit", "sum"),
            Sacks=("pff_sack", "sum"),
        )
        .reset_index()
        .merge(players[["nflId", "displayName", "officialPosition"]], on="nflId", how="left")
    )
    board["Pressures"] = board[["Hurries", "Hits", "Sacks"]].sum(axis=1)
    board["PressurePct"] = 100 * board["Pressures"] / board["RushSnaps"].clip(lower=1)
    return board.sort_values(["Pressures", "Sacks"], ascending=False)[
        ["displayName", "officialPosition", "RushSnaps", "Pressures", "Sacks", "PressurePct"]
    ].rename(
        columns={
            "displayName": "Joueur",
            "officialPosition": "Poste",
            "RushSnaps": "Rush snaps",
            "Pressures": "Pressions",
            "Sacks": "Sacks",
            "PressurePct": "Pression %",
        }
    )


# --- Data and navigation ----------------------------------------------------
try:
    games = load_games()
    plays = load_plays()
    players = load_players()
    scouting = load_scouting()
except Exception as exc:
    st.error(f"Impossible de charger les données principales : {exc}")
    st.stop()

with st.sidebar:
    render_brand()
    st.markdown(
        '<span class="live-pill"><span class="live-dot"></span> SIMULATION DIRECT</span>',
        unsafe_allow_html=True,
    )
    st.write("")
    selected_week = st.selectbox(
        "SEMAINE",
        sorted(games["week"].unique()),
        format_func=lambda value: f"Week {value} · Saison 2021",
    )
    week_games = games.loc[games["week"] == selected_week].sort_values(
        ["gameDate", "gameTimeEastern"]
    )
    game_ids = week_games["gameId"].tolist()
    game_labels = week_games.set_index("gameId")["gameLabel"].to_dict()
    selected_game_id = st.selectbox(
        "MATCH",
        game_ids,
        format_func=lambda value: game_labels[value],
    )

    match_plays = plays.loc[plays["gameId"] == selected_game_id].copy()
    play_ids = match_plays["playId"].tolist()
    play_labels = {
        int(row["playId"]): format_play_label(row)
        for _, row in match_plays.iterrows()
    }
    selected_play_id = st.selectbox(
        "ACTION",
        play_ids,
        format_func=lambda value: play_labels[int(value)],
    )
    st.caption(f"{len(match_plays)} dropbacks disponibles sur ce match")

try:
    game_tracking = load_tracking(int(selected_game_id))
except Exception as exc:
    st.error(f"Impossible de charger le tracking : {exc}")
    st.stop()

play = match_plays.loc[match_plays["playId"] == selected_play_id].iloc[0]
game = games.loc[games["gameId"] == selected_game_id].iloc[0]
tracking = get_play_tracking(game_tracking, int(selected_play_id))
play_scouting = get_play_scouting(scouting, int(selected_game_id), int(selected_play_id))
game_scouting = scouting.loc[scouting["gameId"] == selected_game_id].copy()

if tracking.empty:
    st.warning("Aucune position de tracking n’est disponible pour cette action.")
    st.stop()

enriched = enrich_tracking(tracking, play, play_scouting, players)
key_frames = identify_key_frames(enriched)
target = infer_target(enriched, key_frames, str(play.get("passResult", "")))
qb_id = get_qb_id(enriched)
series = compute_frame_series(enriched, key_frames, target.nfl_id, qb_id)
play_metrics = compute_play_metrics(
    play, enriched, play_scouting, key_frames, series, target
)
team_metrics, coverage_table, formation_table = aggregate_team_context(
    plays, games, scouting, str(play["possessionTeam"]), int(selected_week)
)

with st.sidebar:
    st.divider()
    st.markdown("#### CONTRÔLE INSTANT T")
    selected_frame = st.slider(
        "Frame analysée",
        min_value=key_frames["start"],
        max_value=key_frames["end"],
        value=min(max(key_frames["pass"], key_frames["start"]), key_frames["end"]),
        step=1,
        help="Une frame représente environ 0,1 seconde.",
    )
    if st.button("Revenir au lancer", width="stretch"):
        selected_frame = key_frames["pass"]
    st.caption(
        f"Snap {key_frames['snap']} · Lancer {key_frames['pass']} · "
        f"Résultat {key_frames['outcome']}"
    )
    st.divider()
    st.caption("GRIDIRON IQ 1.0 · NFL BDB 2023\n\nDonnées 2021 · Weeks 1–8")

instant = instantaneous_metrics(series, selected_frame)
insights = build_commentator_insights(
    play, play_metrics, instant, team_metrics, coverage_table
)

# --- Broadcast header ------------------------------------------------------
render_scorebug(game, play)

kpi_columns = st.columns(6)
kpis = [
    ("TIME TO THROW", fmt(play_metrics["timeToThrow"], " s")),
    ("PRESSION PFF", "OUI" if play_metrics["hasPressure"] else "NON"),
    ("SÉPARATION AU LANCER", fmt(play_metrics["passSeparation"], " yd")),
    ("FENÊTRE OUVERTE", fmt(play_metrics["windowDuration"], " s")),
    ("RÉSULTAT", f"{safe_int(play.get('playResult')):+d} yd"),
    ("COUVERTURE", str(play.get("pff_passCoverage", "—"))),
]
for column, (label, value) in zip(kpi_columns, kpis):
    column.metric(label, value)

st.write("")
tabs = st.tabs([
    "◉  DIRECT & REPLAY",
    "⌁  TENDANCES",
    "⚔  DUELS & PROTECTION",
    "◎  JOUEURS",
    "ⓘ  MÉTHODE",
])

# --- Live and replay --------------------------------------------------------
with tabs[0]:
    section_header(
        "Analyse broadcast",
        "Comprendre le jeu en un regard",
        "Passez du replay automatique à l’analyse synchronisée d’un instant précis.",
    )
    display_mode = st.radio(
        "Mode d’affichage",
        ["Replay automatique", "Analyse Instant T"],
        horizontal=True,
        label_visibility="collapsed",
    )

    field_column, analysis_column = st.columns([2.2, 1], gap="large")
    with field_column:
        if display_mode == "Replay automatique":
            replay = build_replay(enriched, play, target.nfl_id)
            st.plotly_chart(
                replay,
                width="stretch",
                config={"displayModeBar": False, "scrollZoom": False},
                key=f"replay-{selected_game_id}-{selected_play_id}",
            )
            st.caption(
                "Utilisez Lecture/Pause ou la timeline Plotly. La cible probable est cerclée en cyan."
            )
        else:
            instant_field = build_instant_field(
                enriched, play, selected_frame, target.nfl_id
            )
            st.plotly_chart(
                instant_field,
                width="stretch",
                config={"displayModeBar": False, "scrollZoom": False},
                key=f"instant-{selected_game_id}-{selected_play_id}-{selected_frame}",
            )
            st.caption(
                "Jaune : trajectoire du quarterback · Cyan : trajectoire de la cible probable."
            )

    with analysis_column:
        event_name = str(instant.get("event", "Tracking"))
        st.markdown(
            panel_html(
                "LECTURE TACTIQUE",
                [
                    ("Événement", event_name),
                    ("Temps depuis snap", fmt(instant.get("time"), " s")),
                    ("Formation", play.get("offenseFormation", "—")),
                    ("Personnel attaque", play.get("personnelO", "—")),
                    ("Personnel défense", play.get("personnelD", "—")),
                    ("Défenseurs dans la box", safe_int(play.get("defendersInBox"), 0)),
                    ("Couverture", play.get("pff_passCoverage", "—")),
                    ("Famille", play.get("pff_passCoverageType", "—")),
                    ("Play action", "Oui" if play.get("pff_playAction") == 1 else "Non"),
                ],
            ),
            unsafe_allow_html=True,
        )
        st.write("")
        st.markdown(
            panel_html(
                "CAPTEURS INSTANT T",
                [
                    ("Rusher le plus proche", instant.get("rusherName", "—")),
                    ("Distance rusher → QB", fmt(instant.get("rusherDistance"), " yd")),
                    ("Cible probable", target.name),
                    ("Séparation", fmt(instant.get("separation"), " yd")),
                    ("Vitesse de fermeture", fmt(instant.get("closingSpeed"), " yd/s")),
                    ("Score de fenêtre", fmt(instant.get("windowScore"), "")),
                    ("Vitesse du QB", fmt(instant.get("qbSpeed"), " yd/s")),
                ],
                footer=(
                    f"Cible inférée par proximité au ballon · confiance {target.confidence:.0%}"
                    if target.nfl_id is not None
                    else "Cible non inférable sur ce jeu"
                ),
            ),
            unsafe_allow_html=True,
        )

    timeline_column, insight_column = st.columns([1.55, 1], gap="large")
    with timeline_column:
        timeline = build_pressure_window_chart(series, key_frames)
        st.plotly_chart(
            timeline,
            width="stretch",
            config={"displayModeBar": False},
            key=f"timeline-{selected_game_id}-{selected_play_id}",
        )
    with insight_column:
        render_insights(insights)

    with st.expander("🎙️ Description officielle du jeu", expanded=False):
        st.write(compact_description(play.get("playDescription", ""), 1200))
        if bool(play.get("isNoPlay", False)):
            st.warning("Jeu annulé (« No Play ») : ne pas l’inclure dans les statistiques officielles.")
        if not pd.isna(play.get("penaltyYards")):
            st.info(
                f"Pénalité : {play.get('foulName1', '—')} · "
                f"{safe_int(play.get('penaltyYards')):+d} yards officiels."
            )

# --- Trends ----------------------------------------------------------------
with tabs[1]:
    section_header(
        "Préparation antenne",
        f"Tendances {play['possessionTeam']} jusqu’à la Week {selected_week}",
        "Les jeux annulés sont exclus. Les semaines futures ne sont jamais utilisées.",
    )
    metric_columns = st.columns(6)
    trend_kpis = [
        ("DROPBACKS", f"{safe_int(team_metrics['dropbacks'])}"),
        ("COMPLÉTION", fmt(team_metrics["completionPct"], "%")),
        ("YARDS / DROPBACK", fmt(team_metrics["yardsPerDropback"])),
        ("SUCCÈS CONVERSION", fmt(team_metrics["successRate"], "%")),
        ("PRESSION SUBIE", fmt(team_metrics["pressureRate"], "%")),
        ("PLAY ACTION", fmt(team_metrics["playActionRate"], "%")),
    ]
    for column, (label, value) in zip(metric_columns, trend_kpis):
        column.metric(label, value)

    coverage_column, table_column = st.columns([1.15, 1], gap="large")
    with coverage_column:
        st.plotly_chart(
            build_coverage_chart(coverage_table),
            width="stretch",
            config={"displayModeBar": False},
            key=f"coverage-{play['possessionTeam']}-{selected_week}",
        )
    with table_column:
        st.markdown("#### EFFICACITÉ PAR COUVERTURE")
        shown_coverage = coverage_table.copy()
        for column in ("CompletionPct", "YardsPerPlay", "PressurePct", "SuccessPct"):
            shown_coverage[column] = shown_coverage[column].round(1)
        st.dataframe(
            shown_coverage,
            width="stretch",
            hide_index=True,
            height=350,
            column_config={
                "CompletionPct": st.column_config.NumberColumn("Complétion", format="%.1f%%"),
                "YardsPerPlay": st.column_config.NumberColumn("Yds/jeu", format="%.1f"),
                "PressurePct": st.column_config.NumberColumn("Pression", format="%.1f%%"),
                "SuccessPct": st.column_config.NumberColumn("Succès", format="%.1f%%"),
            },
        )

    st.markdown("#### FORMATIONS OFFENSIVES")
    shown_formations = formation_table.copy()
    for column in ("YardsPerPlay", "SuccessPct"):
        shown_formations[column] = shown_formations[column].round(1)
    st.dataframe(
        shown_formations,
        width="stretch",
        hide_index=True,
        column_config={
            "YardsPerPlay": st.column_config.NumberColumn("Yds/jeu", format="%.1f"),
            "SuccessPct": st.column_config.NumberColumn("Succès", format="%.1f%%"),
        },
    )

# --- Matchups ---------------------------------------------------------------
with tabs[2]:
    section_header(
        "Dans les tranchées",
        "Responsabilités et création de pression",
        "Reliez chaque bloqueur à son premier adversaire assigné et à l’impact PFF observé.",
    )
    rusher_table = pass_rushers(play_scouting, players)
    blocker_table = protection_matchups(play_scouting, players)
    left, right = st.columns([.85, 1.4], gap="large")
    with left:
        st.markdown("#### PASS RUSHERS SUR CE JEU")
        if rusher_table.empty:
            st.info("Aucun pass rusher annoté.")
        else:
            st.dataframe(rusher_table, width="stretch", hide_index=True)
    with right:
        st.markdown("#### ASSIGNATIONS DE PROTECTION")
        if blocker_table.empty:
            st.info("Aucune assignation de pass protection sur ce jeu.")
        else:
            st.dataframe(blocker_table, width="stretch", hide_index=True)

    st.markdown("#### LEADERS DE PRESSION DU MATCH")
    leaderboard = game_pass_rush_leaderboard(game_scouting, players)
    if not leaderboard.empty:
        leaderboard["Pression %"] = leaderboard["Pression %"].round(1)
        st.dataframe(
            leaderboard.head(12),
            width="stretch",
            hide_index=True,
            column_config={
                "Pression %": st.column_config.ProgressColumn(
                    "Pression %", format="%.1f%%", min_value=0, max_value=max(25.0, float(leaderboard["Pression %"].max()))
                )
            },
        )
    st.caption(
        "Une pression est comptée lorsqu’un hurry, hit ou sack est crédité par PFF. "
        "Le taux affiché est calculé sur les rush snaps présents dans ce corpus."
    )

# --- Players ---------------------------------------------------------------
with tabs[3]:
    section_header(
        "Tracking individuel",
        "Trajectoire, vitesse et effort",
        "Sélectionnez n’importe quel joueur présent sur l’action.",
    )
    player_rows = (
        enriched.loc[enriched["side"].isin(["offense", "defense"]), ["nflId", "displayName", "team", "pff_role"]]
        .dropna(subset=["nflId"])
        .drop_duplicates("nflId")
        .sort_values(["team", "displayName"])
    )
    player_ids = [int(value) for value in player_rows["nflId"].tolist()]
    player_label_map = {
        int(row["nflId"]): f"{row['team']} · {row['displayName']} · {row['pff_role']}"
        for _, row in player_rows.iterrows()
    }
    default_player_index = player_ids.index(target.nfl_id) if target.nfl_id in player_ids else 0
    selected_player_id = st.selectbox(
        "Joueur",
        player_ids,
        index=default_player_index,
        format_func=lambda value: player_label_map[value],
    )
    player_summary = player_play_summary(enriched, selected_player_id)
    cards = st.columns(5)
    player_kpis = [
        ("RÔLE", str(player_summary.get("role", "—"))),
        ("ALIGNEMENT", str(player_summary.get("linedUp", "—"))),
        ("VITESSE MAX", fmt(player_summary.get("maxSpeed"), " yd/s")),
        ("DISTANCE", fmt(player_summary.get("distance"), " yd")),
        ("ACCÉLÉRATION MAX", fmt(player_summary.get("maxAcceleration"), " yd/s²")),
    ]
    for column, (label, value) in zip(cards, player_kpis):
        column.metric(label, value)
    st.plotly_chart(
        build_player_path(enriched, selected_player_id, play),
        width="stretch",
        config={"displayModeBar": False},
        key=f"player-{selected_game_id}-{selected_play_id}-{selected_player_id}",
    )

# --- Methodology ------------------------------------------------------------
with tabs[4]:
    section_header(
        "Transparence analytique",
        "Définitions, provenance et limites",
        "Chaque insight doit rester explicable à l’antenne.",
    )
    method_left, method_right = st.columns(2, gap="large")
    with method_left:
        st.markdown(
            panel_html(
                "DONNÉES STRUCTURÉES",
                [
                    ("Matchs", "122 · Weeks 1–8, 2021"),
                    ("Jeux", "8 557 dropbacks"),
                    ("Tracking", "22 joueurs + ballon · ≈10 Hz"),
                    ("Tactique", "Formation, personnel, box, couverture"),
                    ("Scouting", "Rôles et impacts PFF"),
                    ("Résultats", "Avant et après pénalité"),
                ],
            ),
            unsafe_allow_html=True,
        )
    with method_right:
        st.markdown(
            panel_html(
                "MÉTRIQUES INFÉRÉES",
                [
                    ("Cible probable", "Route runner le plus proche du ballon à l’issue"),
                    ("Séparation", "Distance cible → défenseur de couverture le plus proche"),
                    ("Temps", "Écart de frames × 0,1 seconde"),
                    ("Pression géométrique", "Distance rusher → QB"),
                    ("Fenêtre ouverte", "Séparation ≥ 3 yards"),
                    ("Window Score", "Séparation pénalisée par la vitesse de fermeture"),
                ],
                footer="Métriques internes expérimentales · pas des statistiques NFL officielles",
            ),
            unsafe_allow_html=True,
        )

    st.markdown("### Garde-fous éditoriaux")
    st.markdown(
        """
- Le corpus contient les **passes et dropbacks**, pas tous les snaps : aucune conclusion complète sur le jeu de course ou les drives.
- Les jeux marqués **No Play** sont exclus des tendances, mais restent visualisables dans le replay.
- La cible, la fenêtre et certaines temporalités sont des **inférences** ; leur confiance doit rester visible.
- Les comparaisons historiques n’utilisent que les semaines allant jusqu’au match sélectionné.
- `time` étant arrondi à la seconde, l’ordre et les durées reposent sur `frameId`.
- L’EPA, le WPA et la probabilité de victoire nécessiteraient un play-by-play complet supplémentaire.
        """
    )
    st.info(
        "Mode direct : cette version rejoue des rencontres historiques. Pour une production réellement live, "
        "la même interface peut être alimentée par un flux de tracking et de play-by-play temps réel."
    )
