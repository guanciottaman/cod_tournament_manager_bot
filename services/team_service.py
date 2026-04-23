from db.db import *
from models.team import Team

async def get_teams(event_id: int) -> list[Team] | None:
    teams = await execute("SELECT team_id, name FROM teams WHERE event_id = ?", (event_id,))

    if not teams:
        return None
    teams_list = []
    for team in teams:
        teams_list.append(Team(team[0], team[1]))
    return teams_list

async def insert_teams(event_id: int, name: str, leader_discord_id: int, players_names: list[str]):
    existing = await fetch_one(
        "SELECT team_id FROM teams WHERE event_id = ? AND leader_discord_id = ?",
        (event_id, leader_discord_id)
    )

    if existing:
        raise ValueError("USER_ALREADY_HAS_TEAM")
    team_id = await execute("INSERT INTO teams (event_id, name, leader_discord_id) VALUES (?, ?, ?)", (event_id, name, leader_discord_id))
    for player_name in players_names:
        await execute(
            "INSERT INTO team_members (team_id, member_name) VALUES (?, ?)",
            (team_id, player_name)
        )