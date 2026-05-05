import datetime

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

async def check_team_exists(event_id: int, leader_discord_id: int):
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
    team_id = await execute("INSERT INTO teams (event_id, name, leader_discord_id) VALUES (?, ?, ?)", (event_id, name, leader_discord_id))
    for player_name in players_names:
        await execute(
            "INSERT INTO team_members (team_id, member_name) VALUES (?, ?)",
            (team_id, player_name)
        )

async def edit_teams(event_id: int, name: str, leader_discord_id: int, players_names: list[str]):
    team_id = await fetch_one("SELECT team_id FROM teams WHERE event_id = ? AND leader_discord_id = ?",
        (event_id, leader_discord_id))
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
    

async def insert_results(
    event_id: int,
    team_id: int,
    placement: int,
    match: int,
    players_kills: dict[str, int],
    prove: list[str]
):
    team_score_id = await execute("""
        INSERT INTO team_scores (event_id, team_id, placement, match_number, created_at) VALUES (?, ?, ?, ?, ?)
    """, (event_id, team_id, placement, match, datetime.datetime.now()))
    for player_name, kills in players_kills.items():
        await execute("""
            INSERT INTO player_scores (team_score_id, player_name, kills) VALUES (?, ?, ?)
        """, (team_score_id, player_name, kills))
    for prova in prove:
        await execute(
            "INSERT INTO score_screenshots (team_score_id, image_url) VALUES (?, ?)", 
            (team_score_id, prova)
        )