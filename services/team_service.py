from db.db import *
from models.team import Team, TeamScore, PlayerScore


async def get_teams(event_id: int, setup_mode: bool = False) -> list[Team]:
    query = "SELECT team_id, name, leader_discord_id, kd, lobby_id FROM teams WHERE event_id = ?"
    if setup_mode:
        query += " AND lobby_id IS NOT NULL"
    params = (event_id,)
    teams = await fetch_all(query, params)
    if not teams:
        return []
    teams_list: list[Team] = []
    for team in teams:
        teams_list.append(Team(team[0], team[1], team[2], team[3], team[4]))
    return teams_list

async def get_team_id(event_id: int, leader_discord_id: int):
    row = await fetch_one(
        "SELECT team_id FROM teams WHERE event_id = ? AND leader_discord_id = ?",
        (event_id, leader_discord_id)
    )
    return row[0] if row else None


async def insert_teams(
    event_id: int,
    name: str,
    leader_discord_id: int,
    players_names: list[str]
) -> tuple[int, list[int]] | None:
    existing = await fetch_one(
        "SELECT team_id FROM teams WHERE event_id = ? AND leader_discord_id = ?",
        (event_id, leader_discord_id)
    )

    if existing:
        raise ValueError("USER_ALREADY_HAS_TEAM")
    team_id = await execute(
        "INSERT INTO teams (event_id, name, leader_discord_id) VALUES (?, ?, ?)",
        (event_id, name, leader_discord_id))
    try:
        player_ids: list[int] = []
        for player_name in players_names:
            player_id = await execute(
                "INSERT INTO team_members (team_id, member_name) VALUES (?, ?)",
                (team_id, player_name)
            )
            player_ids.append(player_id)
    except Exception as e:
        await execute("DELETE FROM teams WHERE team_id = ?", (team_id,))
        print(f"Error: {e}")
        return None
    return (team_id, player_ids)

async def assign_free_slot(
    event_id: int,
    team_name: str,
    leader_discord_id: int,
    players_names: list[str]
) -> int | None:
    print(".")
    team_id = await fetch_one("SELECT team_id FROM teams WHERE lobby_id IS NULL AND event_id = ?", (event_id,))
    if team_id is None:
        return
    team_id = team_id[0]
    await execute("""
        UPDATE teams SET 
            lobby_id = previous_lobby_id,
            name = ?,
            leader_discord_id = ?,
        WHERE team_id = ? AND event_id = ?
        """,
        (team_name, leader_discord_id, team_id, event_id)
    )
    await execute("DELETE FROM team_members WHERE team_id = ?", (team_id,))
    for n in players_names:
        await execute(
            "INSERT INTO team_members (team_id, member_name) VALUES (?, ?)",
            (team_id, n)
        )
    return team_id

async def edit_teams(team_id: int, players_names: list[str]):
    await execute("DELETE FROM team_members WHERE team_id = ?", (team_id,))
    for player_name in players_names:
        await execute(
            "INSERT INTO team_members (team_id, member_name) VALUES (?, ?)",
            (team_id, player_name)
        )

async def get_players_names(team_id: int):
    rows = await fetch_all("SELECT member_name FROM team_members WHERE team_id = ?", (team_id,))
    if rows:
        players = [r[0] for r in rows]
    else:
        players = []
    return players

def compute_team_kd(players_kd: list[float]) -> float:
    if not players_kd:
        return 0.0
    return sum(players_kd) / len(players_kd)

async def update_team_kd(team_id: int, players_kd: list[float]):
    kd = compute_team_kd(players_kd)

    await execute(
        "UPDATE teams SET kd = ? WHERE team_id = ?",
        (kd, team_id)
    )
    return kd

async def get_team_player_ids(
    team_id: int
) -> list[int]:
    rows = await fetch_all(
        "SELECT member_id FROM team_members WHERE team_id = ?",
        (team_id,)
    )
    return [r[0] for r in rows]

async def insert_results(
    event_id: int,
    team_id: int,
    placement: int,
    match: int,
    players: list[tuple[int, str, int]],
    prove: list[str]
):
    team_score_id = await execute("""
        INSERT INTO team_scores (
            event_id, team_id, placement, match_number, created_at
        )
        VALUES (?, ?, ?, ?, datetime('now'))
    """, (event_id, team_id, placement, match))
    for player_id, player_name, kills in players:
        await execute("""
            INSERT INTO player_scores (
                team_score_id, member_id, member_name, kills
            )
            VALUES (?, ?, ?, ?)
        """, (team_score_id, player_id, player_name, kills))

    for url in prove:
        await execute("""
            INSERT INTO score_screenshots (team_score_id, image_url)
            VALUES (?, ?)
        """, (team_score_id, url))

async def edit_results(
    event_id: int,
    team_id: int,
    team_score_id: int,
    placement: int,
    players_kills: list[tuple[int, str, int]],
):
    await execute("""
        UPDATE team_scores SET 
            placement = ?,
            status = 'edited'
        WHERE event_id = ? AND team_id = ? AND id = ?
    """, (placement, event_id, team_id, team_score_id))
    for player_id, _, kills in players_kills:
        await execute("""
            UPDATE player_scores SET kills = ?
            WHERE team_score_id = ? AND member_id = ?
        """, (kills, team_score_id, player_id))

async def get_event_results(event_id: int, status: str) -> list[TeamScore]:
    team_rows = await fetch_all("""
        SELECT
            ts.id,
            ts.event_id,
            ts.team_id,
            t.name,
            ts.match_number,
            ts.placement,
            ts.status,
            ts.created_at
        FROM team_scores ts
        JOIN teams t ON t.team_id = ts.team_id
        WHERE ts.status = ?
        AND ts.event_id = ?
        ORDER BY ts.created_at ASC
    """, (status, event_id))

    if not team_rows:
        return []

    team_score_ids = [r[0] for r in team_rows]

    if not team_score_ids:
        return []

    placeholders = ",".join(["?"] * len(team_score_ids))

    player_rows = await fetch_all(f"""
        SELECT
            id,
            team_score_id,
            member_id,
            member_name,
            kills
        FROM player_scores
        WHERE team_score_id IN ({placeholders})
    """, tuple(team_score_ids))

    players_map: dict[int, list[PlayerScore]] = {}
    for r in player_rows:
        ps = PlayerScore(
            player_score_id=r[0],
            team_score_id=r[1],
            member_id=r[2],
            member_name=r[3],
            kills=r[4]
        )
        players_map.setdefault(r[1], []).append(ps)

    screenshots_rows = await fetch_all(f"""
        SELECT team_score_id, image_url
        FROM score_screenshots
        WHERE team_score_id IN ({placeholders})
    """, tuple(team_score_ids))

    screenshots_map: dict[int, list[str]] = {}
    for ts_id, url in screenshots_rows:
        screenshots_map.setdefault(ts_id, []).append(url)

    results: list[TeamScore] = []

    for r in team_rows:
        ts_id = r[0]

        results.append(TeamScore(
            team_score_id=ts_id,
            event_id=r[1],
            team_id=r[2],
            team_name=r[3],
            match_number=r[4],
            placement=r[5],
            status=r[6],
            created_at=r[7],
            player_scores=players_map.get(ts_id, []),
            screenshots=screenshots_map.get(ts_id, [])
        ))

    return results

async def set_result_status(result_id: int, status: str):
    await execute(
        "UPDATE team_scores SET status = ? WHERE id = ?",
        (status, result_id)
    )

async def get_inserted_matches(event_id: int, team_id: int) -> set[int]:
    rows = await fetch_all(
        "SELECT match_number FROM team_scores WHERE event_id = ? AND team_id = ?",
        (event_id, team_id)
    )
    return {r[0] for r in rows}


async def get_inserted_match_numbers(event_id: int) -> set[int]:
    rows = await fetch_all(
        "SELECT DISTINCT match_number FROM team_scores WHERE event_id = ?",
        (event_id,)
    )
    return {r[0] for r in rows}

async def get_leader_discord_id(team_id: int) -> int | None:
    row = await fetch_one(
        "SELECT leader_discord_id FROM teams WHERE team_id = ?",
        (team_id,)
    )
    if row is None:
        return None
    else:
        return row[0]

async def penalize_team(team_id: int, penalty_points: int):
    await execute(
        "UPDATE teams SET penalty_points = penalty_points + ? WHERE team_id = ?",
        (penalty_points, team_id)
    )