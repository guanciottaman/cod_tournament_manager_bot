from db.db import *
from models.ranking import TeamRankingEntry, MVPRanking
from models.placement_settings import PlacementSettings
from services.event_service import get_placement_settings
from config.consts import DEFAULT_PLACEMENT_MULTIPLIERS, DEFAULT_PLACEMENT_POINTS

from collections import defaultdict
import re

def extract_clan(team_name: str):
    match = re.search(r"\(([^)]+)\)$", team_name)
    return match.group(1) if match else None

def clean_player_name(name: str) -> str:
    return name.split("#")[0]

def get_multiplier(
    placement: int,
    multipliers: dict[tuple[int, int | None], float]
) -> float:

    for (min_place, max_place), multiplier in multipliers.items():
        if min_place <= placement and (
            max_place is None or placement <= max_place
        ):
            return multiplier

    return 1.0

def calculate_match_score(
    kills: int,
    kill_points: int,
    placement: int,
    placement_settings: PlacementSettings
) -> float:
    placement_system = placement_settings.system
    if placement_system == "points":
        if placement_settings.points:
            return kills * kill_points + placement_settings.points.get(placement, 0)
        else:
            return kills * kill_points + DEFAULT_PLACEMENT_POINTS.get(placement, 0)
    elif placement_system == "multipliers":
        if placement_settings.multipliers:
            return kills * kill_points * get_multiplier(placement, placement_settings.multipliers)
        else:
            return kills * kill_points * get_multiplier(
                placement,
                DEFAULT_PLACEMENT_MULTIPLIERS
            )
    else:
        return 0

async def get_team_match_data(
    event_id: int,
    scope: str = "global",
    lobby_id: int | None = None,
    include_pending: bool = False
):
    statuses = ["accepted", "edited"]

    if include_pending:
        statuses.append("pending")
    query = f"""
        SELECT 
            ts.team_id,
            t.name AS team_name,
            ts.placement,
            ps.member_name,
            ps.kills
        FROM team_scores ts
        JOIN teams t ON t.team_id = ts.team_id
        JOIN player_scores ps ON ps.team_score_id = ts.id
        WHERE ts.event_id = $1 AND ts.status = ANY($2)
    """

    params: list[Any] = [event_id, statuses]

    if scope == "lobby" and lobby_id is not None:
        params.append(lobby_id)
        query += f" AND t.lobby_id = ${len(params)}"

    return await fetch_all(query, tuple(params))

async def compute_team_ranking(
    event_id: int,
    scope: str = "global", 
    lobby_id: int | None = None,
    include_pending: bool = False
) -> list[TeamRankingEntry]:
    statuses = ["accepted", "edited"]

    if include_pending:
        statuses.append("pending")
    # 1. match base data

    query = """
        SELECT 
            ts.id AS team_score_id,
            ts.team_id,
            t.name AS team_name,
            ts.placement
        FROM team_scores ts
        JOIN teams t ON t.team_id = ts.team_id
        WHERE ts.event_id = $1
        AND ts.status = ANY($2)
    """

    params = [event_id, statuses]

    if scope == "lobby" and lobby_id is not None:
        query += " AND t.lobby_id = $3"
        params.append(lobby_id)

    rows = await fetch_all(query, tuple(params))

    teams_query = """
        SELECT team_id, name
        FROM teams
        WHERE event_id = $1
    """
    teams_params = [event_id]
    if scope == "lobby" and lobby_id is not None:
        teams_query += " AND lobby_id = $2"
        teams_params.append(lobby_id)

    teams = await fetch_all(teams_query, tuple(teams_params))

    penalties = await fetch_all(
        """
            SELECT team_id, COALESCE(penalty_points, 0) AS penalty_points
            FROM teams
            WHERE event_id = $1
        """,
        (event_id,)
    )
    team_penalties = {
        pen["team_id"]: pen["penalty_points"] for pen in penalties
    }

    settings = await fetch_one("""
        SELECT kill_points, drop_worst_match 
        FROM events_settings 
        WHERE event_id = $1
    """, (event_id,))

    kill_points, drop_worst_match = (settings["kill_points"], settings["drop_worst_match"]) if settings else (1, False)

    match_kills: defaultdict[int, int] = defaultdict(int)

    player_rows_query = """
        SELECT ps.team_score_id, ps.kills
        FROM player_scores ps
        JOIN team_scores ts ON ts.id = ps.team_score_id
        JOIN teams t ON t.team_id = ts.team_id
        WHERE ts.event_id = $1
    """
    player_rows_params = [event_id]
    if scope == "lobby" and lobby_id is not None:
        player_rows_query += " AND t.lobby_id = $2"
        player_rows_params.append(lobby_id)
    player_rows = await fetch_all(player_rows_query, tuple(player_rows_params))

    for row in player_rows:
        match_kills[row["team_score_id"]] += row["kills"]

    # 5. build per-team ranking
    team_matches: dict[int, list[dict[str, Any]]] = defaultdict(list)
    

    for row in teams:
        team_matches[row["team_id"]] = []

    placement_settings = await get_placement_settings(event_id)

    for row in rows:

        kills = match_kills.get(row["team_score_id"], 0)

        match_score = calculate_match_score(kills, kill_points, row["placement"], placement_settings)

        team_matches[row["team_id"]].append({
            "score": match_score,
            "kills": kills
        })

    final: list[TeamRankingEntry] = []

    for row in teams:
        matches = team_matches.get(row["team_id"], [])

        if drop_worst_match and len(matches) > 1:
            matches = sorted(matches, key=lambda m: m["score"])[1:]

        score = sum(m["score"] for m in matches) - team_penalties.get(row["team_id"], 0)
        kills = sum(m["kills"] for m in matches)

        final.append(
            TeamRankingEntry(
                team_id=row["team_id"],
                name=row["name"],
                score=score,
                kills=kills
            )
        )
    return sorted(final, key=lambda x: x.score, reverse=True)

async def compute_mvp_ranking(
    event_id: int,
    scope: str = "global",
    lobby_id: int | None = None, 
    top_n: int = 5,
    include_pending: bool = False
) -> list[MVPRanking]:
    rows = await get_team_match_data(event_id, scope, lobby_id, include_pending)

    row = await fetch_one("""
        SELECT drop_worst_match 
        FROM events_settings WHERE event_id = $1
    """, (event_id,))

    drop_worst_match = bool(row["drop_worst_match"]) if row else False

    # struttura: player -> list of match contributions
    player_matches: dict[str, list[int]] = defaultdict(list)

    for row in rows:
        clan = extract_clan(row["team_name"])

        formatted_player = (
            f"{clean_player_name(row['member_name'])} ({clan})"
            if clan else clean_player_name(row["member_name"])
        )

        player_matches[formatted_player].append(row["kills"])

    final_players: list[MVPRanking] = []

    for player, matches in player_matches.items():
        if drop_worst_match and len(matches) > 1:
            matches = sorted(matches)[1:]

        final_players.append(
            MVPRanking(
                player=player,
                kills=sum(matches)
            )
        )

    return sorted(final_players, key=lambda x: x.kills, reverse=True)[:top_n]