from db.db import *
from models.team import Team
from dataclasses import dataclass

@dataclass
class EventResult:
    team_score_id: int
    event_id: int
    team_id: int
    team_name: str
    match_number: int
    placement: int
    status: str
    created_at: str
    screenshots: list[str]

async def get_teams(event_id: int) -> list[Team]:
    teams = await fetch_all("SELECT team_id, name, leader_discord_id, kd FROM teams WHERE event_id = ?", (event_id,))

    if not teams:
        return []
    teams_list: list[Team] = []
    for team in teams:
        teams_list.append(Team(team[0], team[1], team[2], team[3]))
    return teams_list

async def get_team_id(event_id: int, leader_discord_id: int):
    row = await fetch_one(
        "SELECT team_id FROM teams WHERE event_id = ? AND leader_discord_id = ?",
        (event_id, leader_discord_id)
    )
    return row[0] if row else None


async def insert_teams(event_id: int, name: str, leader_discord_id: int, players_names: list[str]):
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
        for player_name in players_names:
            await execute(
                "INSERT INTO team_members (team_id, member_name) VALUES (?, ?)",
                (team_id, player_name)
            )
    except Exception as e:
        await execute("DELETE FROM teams WHERE team_id = ?", (team_id,))
        print(f"Error: {e}")
    return team_id

async def edit_teams(event_id: int, name: str, leader_discord_id: int, players_names: list[str]):
    team_id = await fetch_one("SELECT team_id FROM teams WHERE event_id = ? AND leader_discord_id = ?",
        (event_id, leader_discord_id))
    if not team_id:
        return
    team_id = team_id[0]
    await execute("UPDATE teams SET name = ? WHERE team_id = ?", (name, team_id))
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

async def insert_results(
    event_id: int,
    team_id: int,
    placement: int,
    match: int,
    players_kills: dict[str, int],
    prove: list[str]
):
    team_score_id = await execute("""
        INSERT INTO team_scores (
            event_id, team_id, placement, match_number, created_at
        )
        VALUES (?, ?, ?, ?, datetime('now'))
    """, (event_id, team_id, placement, match))

    for player_name, kills in players_kills.items():
        await execute("""
            INSERT INTO player_scores (team_score_id, player_name, kills)
            VALUES (?, ?, ?)
        """, (team_score_id, player_name, kills))

    for url in prove:
        await execute("""
            INSERT INTO score_screenshots (team_score_id, image_url)
            VALUES (?, ?)
        """, (team_score_id, url))


async def get_event_results(event_id: int, status: str) -> list[EventResult]:
    team_scores = await fetch_all("""
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

    if not team_scores:
        return []

    ids: tuple[int] = tuple([r[0] for r in team_scores])

    placeholders = ",".join(["?"] * len(ids))

    screenshots_rows = await fetch_all(f"""
        SELECT team_score_id, image_url
        FROM score_screenshots
        WHERE team_score_id IN ({placeholders})
    """, ids)

    screenshots_map: dict[int, list[str]] = {}
    for ts_id, url in screenshots_rows:
        screenshots_map.setdefault(ts_id, []).append(url)

    results: list[EventResult] = []

    for r in team_scores:
        ts_id = r[0]
        results.append(EventResult(
            team_score_id=ts_id,
            event_id=r[1],
            team_id=r[2],
            team_name=r[3],
            match_number=r[4],
            placement=r[5],
            status=r[6],
            created_at=r[7],
            screenshots=screenshots_map.get(ts_id, [])
        ))

    return results

async def get_inserted_matches(event_id: int, team_id: int) -> set[int]:
    rows = await fetch_all(
        "SELECT match_number FROM team_scores WHERE event_id = ? AND team_id = ?",
        (event_id, team_id)
    )
    return {r[0] for r in rows}