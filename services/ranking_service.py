from db.db import *

from typing import Any
from collections import defaultdict

def clean_player_name(name: str) -> str:
    return name.split("#")[0]

async def compute_team_ranking(event_id: int, scope: str = "global", lobby_id: int | None = None, top_n: int = 16):
    query = """
        SELECT 
            ts.team_id,
            t.name,
            ts.placement,
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

    rows = await fetch_all(query, tuple(params))
    team_matches = defaultdict(list)
    team_names = {}
    team_kills = defaultdict(int)

    penalties = await fetch_all("""
        SELECT team_id, penalty_points
        FROM teams
        WHERE event_id = ?
    """, (event_id,))
    penalty_map = {
        team_id: penalty or 0
        for team_id, penalty in penalties
    }

    settings = await fetch_one("""
        SELECT kill_points, drop_worst_match FROM events_settings WHERE event_id = ?
    """, (event_id,))

    if settings:
        kill_points, drop_worst_match = settings
    else:
        kill_points = 1
        drop_worst_match = False

    placement_map = await fetch_all("""
        SELECT position, points
        FROM placement_points
        WHERE event_id = ?
    """, (event_id,))

    placement_dict = {p: pts for p, pts in placement_map}

    for team_id, name, placement, kills in rows:
        team_names[team_id] = clean_player_name(name)

        placement_pts = placement_dict.get(placement, 0)
        match_score = (kills * kill_points) + placement_pts

        team_matches[team_id].append(match_score)
        team_kills[team_id] += kills
    
    final = []

    for team_id, matches in team_matches.items():
        if not matches:
            continue

        if drop_worst_match and len(matches) > 1:
            matches = sorted(matches)[1:]

        score = sum(matches)
        score -= penalty_map.get(team_id, 0)

        final.append({
            "team_id": team_id,
            "name": team_names[team_id],
            "score": score,
            "kills": team_kills[team_id]
        })

    return sorted(final, key=lambda x: x["score"], reverse=True)[:top_n]

async def compute_mvp_ranking(
        event_id: int,
        scope: str = "global",
        lobby_id: int | None = None,
        top_n: int = 5
    ) -> list[dict[str, Any]]:
    query = """
        SELECT 
            ps.member_name,
            ps.kills
        FROM player_scores ps
        JOIN team_scores ts ON ts.id = ps.team_score_id
        JOIN teams t ON t.team_id = ts.team_id
        WHERE ts.event_id = ? AND ts.status = 'accepted'
    """

    params = [event_id]

    if scope == "lobby":
        query += " AND t.lobby_id = ?"
        params.append(lobby_id)

    rows = await fetch_all(query, tuple(params))
    player_kills = defaultdict(int)
    for name, kills in rows:
        player_kills[name] += kills
    final = [
        {
            "player": clean_player_name(name),
            "kills": kills
        }
        for name, kills in player_kills.items()
    ]

    return sorted(final, key=lambda x: x["kills"], reverse=True)[:top_n]