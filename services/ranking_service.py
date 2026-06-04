from db.db import *

from typing import Any
from collections import defaultdict

def clean_player_name(name: str) -> str:
    return name.split("#")[0]

async def get_team_match_data(event_id: int, scope: str = "global", lobby_id: int | None = None):
    query = """
        SELECT 
            ts.team_id,
            t.name,
            ts.placement,
            ps.member_name,
            ps.kills
        FROM team_scores ts
        JOIN teams t ON t.team_id = ts.team_id
        JOIN player_scores ps ON ps.team_score_id = ts.id
        WHERE ts.event_id = ? AND ts.status IN ('accepted', 'edited')
    """

    params = [event_id]

    if scope == "lobby" and lobby_id is not None:
        query += " AND t.lobby_id = ?"
        params.append(lobby_id)

    return await fetch_all(query, tuple(params))

async def compute_team_ranking(event_id: int, scope: str = "global", lobby_id: int | None = None):
    rows = await get_team_match_data(event_id, scope, lobby_id)

    settings = await fetch_one("""
        SELECT kill_points, drop_worst_match 
        FROM events_settings WHERE event_id = ?
    """, (event_id,))

    kill_points, drop_worst_match = settings if settings else (1, False)

    placement_map = await fetch_all("""
        SELECT position, points
        FROM placement_points
        WHERE event_id = ?
    """, (event_id,))

    placement_dict = {p: pts for p, pts in placement_map}

    team_matches = defaultdict(list)
    team_kills = defaultdict(int)
    team_names = {}

    for team_id, team_name, placement, _, kills in rows:
        team_names[team_id] = clean_player_name(team_name)

        match_score = (kills * kill_points) + placement_dict.get(placement, 0)

        team_matches[team_id].append(match_score)
        team_kills[team_id] += kills

    final = []

    for team_id, matches in team_matches.items():
        if drop_worst_match and len(matches) > 1:
            matches.remove(min(matches))

        final.append({
            "team_id": team_id,
            "name": team_names[team_id],
            "score": sum(matches),
            "kills": team_kills[team_id]
        })

    return sorted(final, key=lambda x: x["score"], reverse=True)

async def compute_mvp_ranking(event_id: int, scope: str = "global", lobby_id: int | None = None, top_n: int = 5):
    rows = await get_team_match_data(event_id, scope, lobby_id)

    settings = await fetch_one("""
        SELECT kill_points, drop_worst_match 
        FROM events_settings WHERE event_id = ?
    """, (event_id,))

    kill_points, drop_worst_match = settings if settings else (1, False)

    placement_map = await fetch_all("""
        SELECT position, points
        FROM placement_points
        WHERE event_id = ?
    """, (event_id,))

    placement_dict = {p: pts for p, pts in placement_map}

    # struttura: player -> list of match contributions
    player_matches = defaultdict(list)

    for team_id, team_name, placement, player_name, kills in rows:
        match_score = (kills * kill_points) + placement_dict.get(placement, 0)

        player_matches[player_name].append(kills)

    final_players = []

    for player, matches in player_matches.items():
        if drop_worst_match and len(matches) > 1:
            matches.remove(min(matches))

        final_players.append({
            "player": clean_player_name(player),
            "kills": sum(matches)
        })

    return sorted(final_players, key=lambda x: x["kills"], reverse=True)[:top_n]