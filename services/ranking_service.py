from db.db import *

from collections import defaultdict
import re

def extract_clan(team_name: str):
    match = re.search(r"\(([^)]+)\)$", team_name)
    return match.group(1) if match else None

def clean_player_name(name: str) -> str:
    return name.split("#")[0]


async def get_team_match_data(
    event_id: int,
    scope: str = "global",
    lobby_id: int | None = None,
    include_pending: bool = False
):
    statuses = ["accepted", "edited"]

    if include_pending:
        statuses.append("pending")
    placeholders = ",".join(["?"] * len(statuses))
    query = f"""
        SELECT 
            ts.team_id,
            t.name,
            ts.placement,
            ps.member_name,
            ps.kills
        FROM team_scores ts
        JOIN teams t ON t.team_id = ts.team_id
        JOIN player_scores ps ON ps.team_score_id = ts.id
        WHERE ts.event_id = ? AND ts.status IN ({placeholders})
    """

    params = [event_id] + statuses

    if scope == "lobby" and lobby_id is not None:
        query += " AND t.lobby_id = ?"
        params.append(lobby_id)

    return await fetch_all(query, tuple(params))

async def compute_team_ranking(
    event_id: int,
    scope: str = "global", 
    lobby_id: int | None = None,
    include_pending: bool = False
):
    statuses = ["accepted", "edited"]

    if include_pending:
        statuses.append("pending")
    # 1. match base data
    placeholders = ",".join(["?"] * len(statuses))

    query = f"""
        SELECT 
            ts.id,
            ts.team_id,
            t.name,
            ts.placement
            FROM team_scores ts
            JOIN teams t ON t.team_id = ts.team_id
            WHERE ts.event_id = ?
        AND ts.status IN ({placeholders})
    """

    params = [event_id] + statuses

    if scope == "lobby" and lobby_id is not None:
        query += " AND t.lobby_id = ?"
        params.append(lobby_id)

    rows = await fetch_all(query, tuple(params))

    teams_query = """
        SELECT team_id, name
        FROM teams
        WHERE event_id = ?
    """
    teams_params = [event_id]
    if scope == "lobby" and lobby_id is not None:
        teams_query += " AND lobby_id = ?"
        teams_params.append(lobby_id)

    teams = await fetch_all(teams_query, tuple(teams_params))

    penalties = await fetch_all(
        """
            SELECT team_id, COALESCE(penalty_points, 0)
            FROM teams
            WHERE event_id = ?
        """,
        (event_id,)
    )
    team_penalties = {
        pen[0]: pen[1] for pen in penalties
    }

    settings = await fetch_one("""
        SELECT kill_points, drop_worst_match 
        FROM events_settings 
        WHERE event_id = ?
    """, (event_id,))

    kill_points, drop_worst_match = settings if settings else (1, False)

    placement_map = await fetch_all("""
        SELECT position, points
        FROM placement_points
        WHERE event_id = ?
    """, (event_id,))

    placement_dict = {p: pts for p, pts in placement_map}

    match_kills = defaultdict(int)

    player_rows_query = """
        SELECT ps.team_score_id, ps.kills
        FROM player_scores ps
        JOIN team_scores ts ON ts.id = ps.team_score_id
        JOIN teams t ON t.team_id = ts.team_id
        WHERE ts.event_id = ?
    """
    player_rows_params = [event_id]
    if scope == "lobby" and lobby_id is not None:
        player_rows_query += " AND t.lobby_id = ?"
        player_rows_params.append(lobby_id)
    player_rows = await fetch_all(player_rows_query, tuple(player_rows_params))

    for ts_id, kills in player_rows:
        match_kills[ts_id] += kills

    # 5. build per-team ranking
    team_matches: dict[int, list[dict[str, int]]] = defaultdict(list)
    
    team_names: dict[int, str] = {}

    for team_id, name in teams:
        team_names[team_id] = name
        team_matches[team_id] = []

    for ts_id, team_id, team_name, placement in rows:
        team_names[team_id] = team_name

        kills = match_kills.get(ts_id, 0)

        match_score = (
            (kills * kill_points)
            + placement_dict.get(placement, 0)
        )

        team_matches[team_id].append({
            "score": match_score,
            "kills": kills
        })

    final = []

    for team_id, name in teams:
        matches = team_matches.get(team_id, [])

        if drop_worst_match and len(matches) > 1:
            matches = sorted(matches, key=lambda m: m["score"])[1:]

        score = sum(m["score"] for m in matches) - team_penalties.get(team_id, 0)
        kills = sum(m["kills"] for m in matches)

        final.append({
            "team_id": team_id,
            "name": name,
            "score": score,
            "kills": kills
        })
    return sorted(final, key=lambda x: x["score"], reverse=True)

async def compute_mvp_ranking(
    event_id: int,
    scope: str = "global",
    lobby_id: int | None = None, 
    top_n: int = 5,
    include_pending: bool = False
):
    rows = await get_team_match_data(event_id, scope, lobby_id, include_pending)

    row = await fetch_one("""
        SELECT drop_worst_match 
        FROM events_settings WHERE event_id = ?
    """, (event_id,))

    drop_worst_match = bool(row[0]) if row else False

    # struttura: player -> list of match contributions
    player_matches: dict[str, list[int]] = defaultdict(list)

    for _, team_name, _, player_name, kills in rows:
        clan = extract_clan(team_name)

        formatted_player = (
            f"{clean_player_name(player_name)} ({clan})"
            if clan else clean_player_name(player_name)
        )

        player_matches[formatted_player].append(kills)

    final_players = []

    for player, matches in player_matches.items():
        if drop_worst_match and len(matches) > 1:
            matches = sorted(matches)[1:]

        final_players.append({
            "player": player,
            "kills": sum(matches)
        })

    return sorted(final_players, key=lambda x: x["kills"], reverse=True)[:top_n]