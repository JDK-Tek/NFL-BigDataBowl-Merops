"""Analytics and transparent inferences for pass-play tracking data."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

FRAME_SECONDS = 0.1


@dataclass(frozen=True)
class TargetInference:
    nfl_id: int | None
    name: str
    distance_to_ball: float | None
    confidence: float
    frame_id: int | None


def enrich_tracking(
    tracking: pd.DataFrame,
    play: pd.Series,
    play_scouting: pd.DataFrame,
    players: pd.DataFrame,
) -> pd.DataFrame:
    """Attach player identity, role and offensive/defensive side."""
    player_columns = ["nflId", "displayName", "officialPosition", "height", "weight"]
    scout_columns = ["nflId", "pff_role", "pff_positionLinedUp"]
    enriched = tracking.merge(players[player_columns], on="nflId", how="left")
    enriched = enriched.merge(play_scouting[scout_columns], on="nflId", how="left")
    enriched["displayName"] = enriched["displayName"].fillna("Football")
    enriched["officialPosition"] = enriched["officialPosition"].fillna("BALL")
    enriched["pff_role"] = enriched["pff_role"].fillna("Ball")
    enriched["side"] = np.select(
        [
            enriched["team"].eq("football"),
            enriched["team"].eq(str(play["possessionTeam"])),
            enriched["team"].eq(str(play["defensiveTeam"])),
        ],
        ["football", "offense", "defense"],
        default="other",
    )
    enriched["jerseyLabel"] = enriched["jerseyNumber"].apply(
        lambda value: "" if pd.isna(value) else str(int(float(value)))
    )
    return enriched


def identify_key_frames(tracking: pd.DataFrame) -> dict[str, int]:
    events = (
        tracking.loc[~tracking["event"].str.lower().isin(["none", "nan", ""]), ["frameId", "event"]]
        .drop_duplicates()
        .sort_values("frameId")
    )
    if tracking.empty:
        return {"start": 1, "snap": 1, "pass": 1, "outcome": 1, "end": 1}

    start = int(tracking["frameId"].min())
    end = int(tracking["frameId"].max())
    snap = _event_frame(events, ["ball_snap", "snap_direct", "autoevent_ballsnap"], start)
    pass_frame = _event_frame(
        events,
        ["pass_forward", "forward_pass", "autoevent_passforward", "pass_shovel"],
        snap,
    )
    outcome = _event_frame(
        events,
        [
            "pass_outcome_caught", "pass_arrived", "pass_outcome_incomplete",
            "pass_outcome_interception", "interception", "touchdown", "tackle",
            "out_of_bounds", "qb_sack",
        ],
        end,
        minimum=pass_frame,
    )
    return {"start": start, "snap": snap, "pass": pass_frame, "outcome": outcome, "end": end}


def _event_frame(
    events: pd.DataFrame,
    candidates: list[str],
    fallback: int,
    minimum: int | None = None,
) -> int:
    if events.empty:
        return int(fallback)
    normalized = events["event"].str.lower()
    for candidate in candidates:
        rows = events.loc[normalized.eq(candidate)]
        if minimum is not None:
            rows = rows.loc[rows["frameId"] >= minimum]
        if not rows.empty:
            return int(rows.iloc[0]["frameId"])
    return int(fallback)


def infer_target(
    enriched: pd.DataFrame,
    key_frames: dict[str, int],
    pass_result: str | None = None,
) -> TargetInference:
    """Infer the intended receiver from ball proximity at the outcome frame."""
    if pass_result in {"S", "R"}:
        return TargetInference(None, "Aucune cible (pas de passe)", None, 0.0, None)
    candidate_frames = [key_frames["outcome"], key_frames["end"]]
    for frame_id in candidate_frames:
        frame = enriched.loc[enriched["frameId"] == frame_id]
        football = frame.loc[frame["side"] == "football"]
        routes = frame.loc[frame["pff_role"].str.lower().eq("pass route")]
        if football.empty or routes.empty:
            continue
        ball = football.iloc[0]
        distances = np.hypot(routes["x"] - ball["x"], routes["y"] - ball["y"])
        best_index = distances.idxmin()
        best = routes.loc[best_index]
        distance = float(distances.loc[best_index])
        nfl_id = None if pd.isna(best["nflId"]) else int(best["nflId"])
        confidence = float(np.clip(1.0 - distance / 8.0, 0.05, 0.99))
        return TargetInference(
            nfl_id=nfl_id,
            name=str(best["displayName"]),
            distance_to_ball=distance,
            confidence=confidence,
            frame_id=int(frame_id),
        )
    return TargetInference(None, "Cible non déterminée", None, 0.0, None)


def get_qb_id(enriched: pd.DataFrame) -> int | None:
    rows = enriched.loc[enriched["pff_role"].str.lower().eq("pass"), "nflId"].dropna()
    return int(rows.iloc[0]) if not rows.empty else None


def compute_frame_series(
    enriched: pd.DataFrame,
    key_frames: dict[str, int],
    target_id: int | None,
    qb_id: int | None,
) -> pd.DataFrame:
    records: list[dict[str, float | int | str]] = []
    for frame_id, frame in enriched.groupby("frameId", sort=True):
        qb = frame.loc[frame["nflId"].eq(qb_id)] if qb_id is not None else frame.iloc[0:0]
        rushers = frame.loc[frame["pff_role"].str.lower().eq("pass rush")]
        nearest_rusher_distance = np.nan
        nearest_rusher_name = "—"
        qb_speed = np.nan
        if not qb.empty:
            qb_row = qb.iloc[0]
            qb_speed = float(qb_row["s"])
            if not rushers.empty:
                distances = np.hypot(rushers["x"] - qb_row["x"], rushers["y"] - qb_row["y"])
                nearest_index = distances.idxmin()
                nearest_rusher_distance = float(distances.loc[nearest_index])
                nearest_rusher_name = str(rushers.loc[nearest_index, "displayName"])

        separation = np.nan
        if target_id is not None:
            target = frame.loc[frame["nflId"].eq(target_id)]
            defenders = frame.loc[frame["pff_role"].str.lower().eq("coverage")]
            if not target.empty and not defenders.empty:
                target_row = target.iloc[0]
                separation = float(
                    np.hypot(
                        defenders["x"] - target_row["x"],
                        defenders["y"] - target_row["y"],
                    ).min()
                )

        event_values = frame.loc[
            ~frame["event"].str.lower().isin(["none", "nan", ""]), "event"
        ].drop_duplicates()
        records.append(
            {
                "frameId": int(frame_id),
                "timeFromSnap": (int(frame_id) - key_frames["snap"]) * FRAME_SECONDS,
                "nearestRusherDistance": nearest_rusher_distance,
                "nearestRusherName": nearest_rusher_name,
                "targetSeparation": separation,
                "qbSpeed": qb_speed,
                "event": " · ".join(event_values.astype(str).tolist()),
            }
        )

    series = pd.DataFrame(records)
    if series.empty:
        return series
    series["closingSpeed"] = -series["targetSeparation"].diff() / FRAME_SECONDS
    series["closingSpeed"] = series["closingSpeed"].clip(-12, 12)
    series["windowScore"] = (
        series["targetSeparation"] - 0.35 * series["closingSpeed"].clip(lower=0)
    ).clip(lower=0)
    return series


def instantaneous_metrics(
    series: pd.DataFrame,
    frame_id: int,
) -> dict[str, object]:
    if series.empty:
        return {}
    row = series.loc[series["frameId"] == int(frame_id)]
    if row.empty:
        row = series.iloc[[-1]]
    item = row.iloc[0]
    return {
        "time": float(item["timeFromSnap"]),
        "rusherDistance": item["nearestRusherDistance"],
        "rusherName": item["nearestRusherName"],
        "separation": item["targetSeparation"],
        "closingSpeed": item["closingSpeed"],
        "windowScore": item["windowScore"],
        "qbSpeed": item["qbSpeed"],
        "event": item["event"] or "Tracking",
    }


def compute_play_metrics(
    play: pd.Series,
    enriched: pd.DataFrame,
    play_scouting: pd.DataFrame,
    key_frames: dict[str, int],
    series: pd.DataFrame,
    target: TargetInference,
) -> dict[str, object]:
    pass_frame = key_frames["pass"]
    outcome_frame = key_frames["outcome"]
    pass_result = str(play.get("passResult", ""))
    ttt = (
        np.nan
        if pass_result in {"S", "R"}
        else max(0.0, (pass_frame - key_frames["snap"]) * FRAME_SECONDS)
    )
    pass_row = series.loc[series["frameId"] == pass_frame]
    outcome_row = series.loc[series["frameId"] == outcome_frame]

    pressure_columns = ["pff_hurry", "pff_hit", "pff_sack"]
    pressure_mask = play_scouting[pressure_columns].fillna(0).sum(axis=1).gt(0)
    pressure_rows = play_scouting.loc[pressure_mask]
    open_window = series.loc[
        (series["frameId"] >= pass_frame)
        & (series["frameId"] <= outcome_frame)
        & (series["targetSeparation"] >= 3.0)
    ]
    offense = enriched.loc[enriched["side"] == "offense"]

    return {
        "timeToThrow": ttt,
        "passSeparation": _value(pass_row, "targetSeparation"),
        "outcomeSeparation": _value(outcome_row, "targetSeparation"),
        "rusherDistanceAtThrow": _value(pass_row, "nearestRusherDistance"),
        "windowDuration": len(open_window) * FRAME_SECONDS,
        "maxOffenseSpeed": float(offense["s"].max()) if not offense.empty else np.nan,
        "pressureCount": int(len(pressure_rows)),
        "hasPressure": not pressure_rows.empty,
        "targetName": target.name,
        "targetConfidence": target.confidence,
        "yards": float(play.get("playResult", 0) or 0),
        "outcome": str(play.get("passResult", "")),
    }


def _value(frame: pd.DataFrame, column: str) -> float:
    if frame.empty or pd.isna(frame.iloc[0][column]):
        return np.nan
    return float(frame.iloc[0][column])


def aggregate_team_context(
    plays: pd.DataFrame,
    games: pd.DataFrame,
    scouting: pd.DataFrame,
    team: str,
    through_week: int,
) -> tuple[dict[str, float], pd.DataFrame, pd.DataFrame]:
    eligible_games = games.loc[games["week"] <= int(through_week), "gameId"]
    sample = plays.loc[
        plays["gameId"].isin(eligible_games)
        & plays["possessionTeam"].eq(team)
        & ~plays["isNoPlay"]
    ].copy()
    attempts = sample["passResult"].isin(["C", "I", "IN"])
    completions = sample["passResult"].eq("C")
    pressure_plays = scouting.loc[
        scouting["gameId"].isin(eligible_games)
        & scouting[["pff_hurry", "pff_hit", "pff_sack"]].fillna(0).sum(axis=1).gt(0),
        ["gameId", "playId"],
    ].drop_duplicates()
    sample = sample.merge(pressure_plays.assign(hasPressure=True), on=["gameId", "playId"], how="left")
    sample["hasPressure"] = sample["hasPressure"].fillna(False).astype(bool)
    sample["isSuccess"] = sample["playResult"] >= sample["yardsToGo"]

    metrics = {
        "dropbacks": float(len(sample)),
        "completionPct": 100 * completions.sum() / max(1, attempts.sum()),
        "yardsPerDropback": sample["playResult"].mean() if len(sample) else np.nan,
        "successRate": 100 * sample["isSuccess"].mean() if len(sample) else np.nan,
        "pressureRate": 100 * sample["hasPressure"].mean() if len(sample) else np.nan,
        "sackRate": 100 * sample["passResult"].eq("S").mean() if len(sample) else np.nan,
        "playActionRate": 100 * sample["pff_playAction"].fillna(0).mean() if len(sample) else np.nan,
        "manRate": 100 * sample["pff_passCoverageType"].eq("Man").mean() if len(sample) else np.nan,
    }

    coverage = (
        sample.groupby("pff_passCoverage", dropna=False)
        .agg(
            Plays=("playId", "size"),
            CompletionPct=("passResult", lambda x: 100 * x.eq("C").sum() / max(1, x.isin(["C", "I", "IN"]).sum())),
            YardsPerPlay=("playResult", "mean"),
            PressurePct=("hasPressure", lambda x: 100 * x.mean()),
            SuccessPct=("isSuccess", lambda x: 100 * x.mean()),
        )
        .reset_index()
        .rename(columns={"pff_passCoverage": "Coverage"})
        .sort_values("Plays", ascending=False)
    )
    formations = (
        sample.groupby("offenseFormation", dropna=False)
        .agg(Plays=("playId", "size"), YardsPerPlay=("playResult", "mean"), SuccessPct=("isSuccess", lambda x: 100 * x.mean()))
        .reset_index()
        .rename(columns={"offenseFormation": "Formation"})
        .sort_values("Plays", ascending=False)
    )
    return metrics, coverage, formations


def protection_matchups(
    play_scouting: pd.DataFrame,
    players: pd.DataFrame,
) -> pd.DataFrame:
    blockers = play_scouting.loc[
        play_scouting["pff_role"].str.lower().eq("pass block")
    ].copy()
    if blockers.empty:
        return pd.DataFrame()
    names = players[["nflId", "displayName"]]
    blockers = blockers.merge(names.rename(columns={"displayName": "Bloqueur"}), on="nflId", how="left")
    blockers = blockers.merge(
        names.rename(columns={"nflId": "pff_nflIdBlockedPlayer", "displayName": "Rusher assigné"}),
        on="pff_nflIdBlockedPlayer",
        how="left",
    )
    blockers["Pression concédée"] = blockers[["pff_hurryAllowed", "pff_hitAllowed", "pff_sackAllowed"]].fillna(0).sum(axis=1).astype(int)
    blockers["Bloc perdu"] = blockers["pff_beatenByDefender"].fillna(0).astype(int)
    return blockers[[
        "Bloqueur", "pff_positionLinedUp", "Rusher assigné", "pff_blockType",
        "Bloc perdu", "Pression concédée",
    ]].rename(columns={"pff_positionLinedUp": "Alignement", "pff_blockType": "Type de bloc"})


def pass_rushers(play_scouting: pd.DataFrame, players: pd.DataFrame) -> pd.DataFrame:
    rushers = play_scouting.loc[
        play_scouting["pff_role"].str.lower().eq("pass rush")
    ].copy()
    if rushers.empty:
        return pd.DataFrame()
    rushers = rushers.merge(players[["nflId", "displayName"]], on="nflId", how="left")
    for column in ("pff_hurry", "pff_hit", "pff_sack"):
        rushers[column] = rushers[column].fillna(0).astype(int)
    rushers["Impact"] = np.select(
        [rushers["pff_sack"].eq(1), rushers["pff_hit"].eq(1), rushers["pff_hurry"].eq(1)],
        ["SACK", "HIT", "HURRY"],
        default="—",
    )
    return rushers[["displayName", "pff_positionLinedUp", "Impact"]].rename(
        columns={"displayName": "Pass rusher", "pff_positionLinedUp": "Alignement"}
    )


def player_play_summary(enriched: pd.DataFrame, nfl_id: int) -> dict[str, object]:
    rows = enriched.loc[enriched["nflId"].eq(int(nfl_id))].sort_values("frameId")
    if rows.empty:
        return {}
    first = rows.iloc[0]
    return {
        "name": first["displayName"],
        "position": first["officialPosition"],
        "linedUp": first["pff_positionLinedUp"],
        "role": first["pff_role"],
        "team": first["team"],
        "maxSpeed": rows["s"].max(),
        "avgSpeed": rows["s"].mean(),
        "distance": rows["dis"].sum(),
        "maxAcceleration": rows["a"].max(),
    }


def build_commentator_insights(
    play: pd.Series,
    play_metrics: dict[str, object],
    instant: dict[str, object],
    team_metrics: dict[str, float],
    coverage: pd.DataFrame,
) -> list[str]:
    insights: list[str] = []
    coverage_name = str(play.get("pff_passCoverage", "Couverture inconnue"))
    coverage_row = coverage.loc[coverage["Coverage"].eq(coverage_name)]
    if not coverage_row.empty:
        row = coverage_row.iloc[0]
        insights.append(
            f"Face à {coverage_name}, l’attaque produit {row['YardsPerPlay']:.1f} yards par jeu "
            f"sur {int(row['Plays'])} dropbacks dans l’échantillon disponible."
        )
    ttt_value = play_metrics.get("timeToThrow", np.nan)
    has_throw = not pd.isna(ttt_value)
    if play_metrics.get("hasPressure"):
        if has_throw:
            insights.append(
                f"La défense génère une pression créditée PFF sur ce jeu. Le ballon sort en "
                f"{ttt_value:.1f} s."
            )
        else:
            insights.append(
                "La défense génère une pression créditée PFF avant que le quarterback ne puisse lancer."
            )
    elif has_throw:
        insights.append(
            f"Aucune pression PFF créditée : temps de lancer de {ttt_value:.1f} s "
            f"et distance du rusher le plus proche au lancer de {_safe(play_metrics.get('rusherDistanceAtThrow'))} yd."
        )
    else:
        insights.append("Aucune passe déclenchée et aucune pression PFF créditée sur ce jeu.")
    if play_metrics.get("targetConfidence", 0) > 0:
        insights.append(
            f"Cible probable : {play_metrics['targetName']} ({play_metrics['targetConfidence']:.0%} de confiance). "
            f"Fenêtre ouverte estimée pendant {play_metrics['windowDuration']:.1f} s."
        )
    if instant and not pd.isna(instant.get("rusherDistance", np.nan)):
        insights.append(
            f"À l’instant sélectionné, {instant['rusherName']} est le rusher le plus proche, "
            f"à {instant['rusherDistance']:.1f} yards du quarterback."
        )
    return insights[:4]


def _safe(value: object) -> str:
    try:
        if value is None or pd.isna(value):
            return "—"
        return f"{float(value):.1f}"
    except (TypeError, ValueError):
        return "—"
