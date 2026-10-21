"""Cached access to the NFL Big Data Bowl CSV files."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "data" / "data"
TRACKING_DIR = DATA_DIR / "tracking"


@st.cache_data(show_spinner=False)
def load_games() -> pd.DataFrame:
    games = pd.read_csv(DATA_DIR / "games.csv")
    games["gameId"] = games["gameId"].astype("int64")
    games["gameDate"] = pd.to_datetime(games["gameDate"], format="%m/%d/%Y")
    games["gameLabel"] = (
        "W" + games["week"].astype(str)
        + " · " + games["visitorTeamAbbr"] + " @ " + games["homeTeamAbbr"]
        + " · " + games["gameDate"].dt.strftime("%d %b")
    )
    return games


@st.cache_data(show_spinner=False)
def load_plays() -> pd.DataFrame:
    plays = pd.read_csv(DATA_DIR / "plays.csv", low_memory=False)
    plays["gameId"] = plays["gameId"].astype("int64")
    plays["playId"] = plays["playId"].astype("int64")
    plays["isNoPlay"] = plays["playDescription"].str.contains(
        "No Play", case=False, na=False
    )
    return plays


@st.cache_data(show_spinner=False)
def load_players() -> pd.DataFrame:
    players = pd.read_csv(DATA_DIR / "players.csv", low_memory=False)
    players["nflId"] = pd.to_numeric(players["nflId"], errors="coerce").astype("Int64")
    players["heightInches"] = players["height"].apply(_height_to_inches)
    players["birthDateParsed"] = pd.to_datetime(
        players["birthDate"], errors="coerce", format="mixed"
    )
    return players


@st.cache_data(show_spinner=False)
def load_scouting() -> pd.DataFrame:
    scouting = pd.read_csv(DATA_DIR / "pffScoutingData.csv", low_memory=False)
    for column in ("nflId", "pff_nflIdBlockedPlayer"):
        scouting[column] = pd.to_numeric(
            scouting[column], errors="coerce"
        ).astype("Int64")
    scouting["gameId"] = scouting["gameId"].astype("int64")
    scouting["playId"] = scouting["playId"].astype("int64")
    return scouting


@st.cache_data(show_spinner="Chargement du tracking du match…", max_entries=4)
def load_tracking(game_id: int) -> pd.DataFrame:
    path = TRACKING_DIR / f"tracking_{int(game_id)}.csv"
    if not path.exists():
        raise FileNotFoundError(f"Fichier de tracking introuvable : {path.name}")

    tracking = pd.read_csv(path, low_memory=False)
    tracking["gameId"] = tracking["gameId"].astype("int64")
    tracking["playId"] = tracking["playId"].astype("int64")
    tracking["frameId"] = tracking["frameId"].astype("int64")
    tracking["nflId"] = pd.to_numeric(tracking["nflId"], errors="coerce").astype("Int64")
    tracking["event"] = tracking["event"].fillna("None").astype(str)
    return tracking


def get_play_tracking(tracking: pd.DataFrame, play_id: int) -> pd.DataFrame:
    """Return one play without mutating the cached game dataframe."""
    return tracking.loc[tracking["playId"] == int(play_id)].copy()


def get_play_scouting(scouting: pd.DataFrame, game_id: int, play_id: int) -> pd.DataFrame:
    return scouting.loc[
        (scouting["gameId"] == int(game_id))
        & (scouting["playId"] == int(play_id))
    ].copy()


def format_play_label(play: pd.Series) -> str:
    outcome = {
        "C": "COMPLÉTÉE",
        "I": "INCOMPLÈTE",
        "S": "SACK",
        "IN": "INTERCEPTION",
        "R": "SCRAMBLE",
    }.get(str(play.get("passResult", "")), "JEU")
    return (
        f"Q{int(play['quarter'])} {play['gameClock']} · "
        f"{int(play['down'])}e & {int(play['yardsToGo'])} · {outcome} · #{int(play['playId'])}"
    )


def _height_to_inches(value: object) -> float | None:
    try:
        feet, inches = str(value).split("-")
        return int(feet) * 12 + int(inches)
    except (ValueError, TypeError):
        return None
