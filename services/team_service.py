from db import db
from db.db import execute, fetch_one, fetch_all
from models.team import Team, TeamScore, PlayerScore, TeamChannel


team_channels: dict[int, TeamChannel]

async def init_team_channels_cache():
    global team_channels_cache

    rows = await fetch_all("""
        SELECT
            channel_id,
            team_id,
            event_id,
            leader_discord_id
        FROM teams
        WHERE channel_id IS NOT NULL
    """)

    team_channels_cache = {
        row["channel_id"]: TeamChannel(
            team_id=row["team_id"],
            event_id=row["event_id"],
            leader_id=row["leader_discord_id"],
        )
        for row in rows
    }

def get_team_channel(channel_id: int) -> TeamChannel | None:
    return team_channels_cache.get(channel_id)

def is_team_channel(channel_id: int) -> bool:
    return channel_id in team_channels_cache

async def get_teams(event_id: int, lobby_id: int | None = None, setup_mode: bool = False) -> list[Team]:
    query = """
        SELECT team_id, name, leader_discord_id, channel_id, kd, lobby_id
        FROM teams
        WHERE event_id = $1
    """
    params = [event_id]

    if setup_mode:
        query += " AND lobby_id IS NOT NULL"
    elif lobby_id is not None:
        query += " AND lobby_id = $2"
        params.append(lobby_id)

    query += " ORDER BY team_id"

    teams = await fetch_all(query, tuple(params))
    if not teams:
        return []
    teams_list: list[Team] = []
    for team in teams:
        teams_list.append(
            Team(
                team["team_id"],
                team["name"],
                team["leader_discord_id"],
                team["kd"],
                team["lobby_id"],
                team["channel_id"]
            )
        )
    return teams_list

async def get_team_id(event_id: int, leader_discord_id: int):
    row = await fetch_one(
        "SELECT team_id FROM teams WHERE event_id = $1 AND leader_discord_id = $2",
        (event_id, leader_discord_id)
    )
    return row["team_id"] if row else None


async def already_has_team(
    event_id: int,
    leader_discord_id: int
) -> bool:
    existing = await fetch_one(
        "SELECT 1 FROM teams WHERE event_id = $1 AND leader_discord_id = $2 LIMIT 1",
        (event_id, leader_discord_id)
    )
    return existing is not None

async def insert_teams(
    event_id: int,
    name: str,
    leader_discord_id: int,
    players_names: list[str]
) -> tuple[int, list[int]] | None:

    if await already_has_team(event_id, leader_discord_id):
        raise ValueError("USER_ALREADY_HAS_TEAM")
    if db.pool is None:
        return
    async with db.pool.acquire() as conn:
        async with conn.transaction():
            team_id = await conn.fetchval(
                """
                INSERT INTO teams 
                (event_id, name, leader_discord_id)
                VALUES ($1, $2, $3)
                RETURNING team_id
                """,
                event_id,
                name,
                leader_discord_id
            )

            player_ids: list[int] = []

            for player_name in players_names:
                player_id = await conn.fetchval(
                    """
                    INSERT INTO team_members
                    (team_id, member_name)
                    VALUES ($1, $2)
                    RETURNING member_id
                    """,
                    team_id,
                    player_name
                )

                player_ids.append(player_id)

    return team_id, player_ids

async def set_team_channel_id(
    event_id: int,
    team_id: int,
    channel_id: int
) -> bool:
    row = await fetch_one(
        """
        UPDATE teams
        SET channel_id = $1
        WHERE event_id = $2
          AND team_id = $3
        RETURNING leader_discord_id
        """,
        (channel_id, event_id, team_id)
    )

    if row is None:
        return False

    team_channels_cache[channel_id] = TeamChannel(
        team_id=team_id,
        event_id=event_id,
        leader_id=row["leader_discord_id"]
    )

    return True

async def get_team_channel_id(event_id: int, team_id: int) -> int | None:
    row = await fetch_one(
        "SELECT channel_id FROM teams WHERE event_id = $1 AND team_id = $2",
        (event_id, team_id)
    )
    return row["channel_id"] if row is not None else None

async def assign_free_slot(
    event_id: int,
    team_name: str,
    leader_discord_id: int,
    players_names: list[str]
) -> tuple[int, int, list[int]] | None:
    team_id = await fetch_one("""
        SELECT team_id 
        FROM teams 
        WHERE lobby_id IS NULL AND event_id = $1
        ORDER BY team_id ASC
        LIMIT 1
    """, (event_id,))
    if team_id is None:
        return None
    team_id = team_id["team_id"]
    row = await fetch_one(
        "SELECT previous_lobby_id FROM teams WHERE team_id = $1 AND event_id = $2",
        (team_id, event_id)
    )

    if not row or row["previous_lobby_id"] is None:
        return None
    
    await execute("""
        UPDATE teams SET 
            lobby_id = previous_lobby_id,
            name = $1,
            leader_discord_id = $2
        WHERE team_id = $3 AND event_id = $4
            AND previous_lobby_id IS NOT NULL
        """,
        (team_name, leader_discord_id, team_id, event_id)
    )
    row = await fetch_one(
        "SELECT lobby_id FROM teams WHERE team_id = $1",
        (team_id,)
    )
    if row is None:
        return None
    lobby_id = row["lobby_id"]
    await execute("DELETE FROM team_members WHERE team_id = $1", (team_id,))
    member_ids: list[int] = []
    for n in players_names:
        member_id = await fetch_one(
            """
            INSERT INTO team_members
            (team_id, member_name)
            VALUES ($1, $2)
            RETURNING member_id
            """,
            (team_id, n)
        )
        if member_id is None:
            raise ValueError("Error with member_id")

        member_ids.append(member_id["member_id"])

    return (team_id, lobby_id, member_ids)

async def delete_team(team_id: int, status: str):
    row = await fetch_one(
        "SELECT channel_id FROM teams WHERE team_id = $1",
        (team_id,)
    )

    channel_id = row["channel_id"] if row else None
    team_channels_cache.pop(channel_id)
    if status == "setup":
        await execute("""
            UPDATE teams
            SET previous_lobby_id = lobby_id,
                lobby_id = NULL,
                leader_discord_id = NULL,
                channel_id = NULL
            WHERE team_id = $1
        """, (team_id,))
    else:
        await execute("DELETE FROM teams WHERE team_id = $1", (team_id,))
    

async def edit_teams(team_id: int, players_names: list[str], team_name: str | None = None) -> list[int]:
    if team_name is not None:
        await execute("UPDATE teams SET name = $1 WHERE team_id = $2", (team_name, team_id))
    rows = await fetch_all(
        "SELECT member_id FROM team_members WHERE team_id = $1 ORDER BY member_id",
        (team_id,)
    )

    member_ids = [r["member_id"] for r in rows]
    for member_id, name in zip(member_ids, players_names):
        await execute(
            "UPDATE team_members SET member_name = $1 WHERE member_id = $2",
            (name, member_id)
        )

    return member_ids

async def get_players_names(team_id: int):
    rows = await fetch_all(
        "SELECT member_name FROM team_members WHERE team_id = $1 ORDER BY member_id",
        (team_id,)
    )
    if rows:
        players = [r["member_name"] for r in rows]
    else:
        players = []
    return players

def compute_team_kd(players_kd: list[float]) -> float:
    if not players_kd:
        return 0.0
    return sum(players_kd) / len(players_kd)

async def update_team_kd(team_id: int, players_kd: dict[int, float]):
    for member_id, kd in players_kd.items():
        await execute(
            "UPDATE team_members SET kd = $1 WHERE member_id = $2",
            (kd, member_id)
        )

    avg_kd = compute_team_kd(list(players_kd.values()))

    await execute(
        "UPDATE teams SET kd = $1 WHERE team_id = $2",
        (avg_kd, team_id)
    )

    return avg_kd

async def get_team_player_ids(
    team_id: int
) -> list[int]:
    rows = await fetch_all(
        "SELECT member_id FROM team_members WHERE team_id = $1 ORDER BY member_id",
        (team_id,)
    )
    return [r["member_id"] for r in rows]

async def insert_results(
    event_id: int,
    team_id: int,
    placement: int,
    match: int,
    players: list[tuple[int, str, int]],
    prove: tuple[str, str]
) -> int | None:
    row = await fetch_one("""
        INSERT INTO team_scores (
            event_id, team_id, placement, match_number
        )
        VALUES ($1, $2, $3, $4)
        RETURNING id
    """, (event_id, team_id, placement, match))
    if row is None:
        raise ValueError("Error with team score id")
    team_score_id = row["id"]
    for player_id, player_name, kills in players:
        await execute("""
            INSERT INTO player_scores (
                team_score_id, member_id, member_name, kills
            )
            VALUES ($1, $2, $3, $4)
        """, (team_score_id, player_id, player_name, kills))

    for url in prove:
        await execute("""
            INSERT INTO score_screenshots (team_score_id, image_url)
            VALUES ($1, $2)
        """, (team_score_id, url))
    return team_score_id

async def edit_results(
    event_id: int,
    team_id: int,
    team_score_id: int,
    placement: int,
    players_kills: list[tuple[int, str, int]],
):
    await execute("""
        UPDATE team_scores SET 
            placement = $1,
            status = 'edited'
        WHERE event_id = $2 AND team_id = $3 AND id = $4 AND status = 'pending'
    """, (placement, event_id, team_id, team_score_id))
    for player_id, _, kills in players_kills:
        await execute("""
            UPDATE player_scores SET kills = $1
            WHERE team_score_id = $2 AND member_id = $3
        """, (kills, team_score_id, player_id))

async def get_event_results(event_id: int, status: str, team: Team | None = None) -> list[TeamScore]:
    query = """
        SELECT
            ts.id AS team_score_id,
            ts.event_id,
            ts.team_id AS team_id,
            t.name AS team_name,
            ts.match_number,
            ts.placement,
            ts.status,
            ts.created_at
        FROM team_scores ts
        JOIN teams t ON t.team_id = ts.team_id
        WHERE ts.status = $1
        AND ts.event_id = $2
    """
    params = [status, event_id]
    if team is not None:
        query += " AND t.team_id = $3"
        params.append(team.team_id)
    query += " ORDER BY ts.team_id ASC, ts.created_at ASC"
    
    team_rows = await fetch_all(query, tuple(params))

    if not team_rows:
        return []

    team_score_ids = [r["team_score_id"] for r in team_rows]

    if not team_score_ids:
        return []

    placeholders = ",".join(
        [f"${i}" for i in range(1, len(team_score_ids) + 1)]
    )

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
            player_score_id=r["id"],
            team_score_id=r["team_score_id"],
            member_id=r["member_id"],
            member_name=r["member_name"],
            kills=r["kills"]
        )
        players_map.setdefault(r["team_score_id"], []).append(ps)

    screenshots_rows = await fetch_all(f"""
        SELECT team_score_id, image_url
        FROM score_screenshots
        WHERE team_score_id IN ({placeholders})
    """, tuple(team_score_ids))

    screenshots_map: dict[int, list[str]] = {}
    for row in screenshots_rows:
        screenshots_map.setdefault(row["team_score_id"], []).append(row["image_url"])

    results: list[TeamScore] = []

    for r in team_rows:
        ts_id = r["team_score_id"]

        results.append(TeamScore(
            team_score_id=ts_id,
            event_id=event_id,
            team_id=r["team_id"],
            team_name=r["team_name"],
            match_number=r["match_number"],
            placement=r["placement"],
            status=r["status"],
            created_at=r["created_at"],
            player_scores=players_map.get(ts_id, []),
            screenshots=screenshots_map.get(ts_id, [])
        ))

    return results

async def set_result_status(result_id: int, status: str, old_status: str = "pending") -> int:
    result = await execute(
        """
        UPDATE team_scores
        SET status = $1
        WHERE id = $2
        AND status = $3
        """,
        (status, result_id, old_status)
    )

    return int(result.split()[-1])

async def get_team_score_by_id(team_score_id: int):
    return await fetch_one(
        "SELECT id, team_id, status, match_number FROM team_scores WHERE id = $1",
        (team_score_id,)
    )

async def get_inserted_matches(event_id: int, team_id: int) -> set[int]:
    rows = await fetch_all(
        "SELECT match_number FROM team_scores WHERE event_id = $1 AND team_id = $2 ORDER BY id",
        (event_id, team_id)
    )
    return {r["match_number"] for r in rows}


async def get_inserted_match_numbers(event_id: int) -> set[int]:
    rows = await fetch_all(
        """
        SELECT match_number
        FROM team_scores
        WHERE event_id = $1
        GROUP BY match_number
        """,
        (event_id,)
    )

    return {r["match_number"] for r in rows}

async def get_inserted_matches_count(event_id: int) -> dict[int, int]:
    rows = await fetch_all("""
        SELECT 
            team_id,
            COUNT(DISTINCT match_number) AS count
        FROM team_scores
        WHERE event_id = $1
        GROUP BY team_id
    """, (event_id,))

    return {
        r["team_id"]: r["count"]
        for r in rows
    }

async def get_inserted_matches_count_per_team(event_id: int, team_id: int) -> int:
    row = await fetch_one("""
        SELECT COUNT(DISTINCT match_number) AS count
        FROM team_scores
        WHERE event_id = $1 AND team_id = $2
    """, (event_id, team_id))

    return row["count"] if row else 0

async def get_leader_discord_id(team_id: int) -> int | None:
    row = await fetch_one(
        "SELECT leader_discord_id FROM teams WHERE team_id = $1",
        (team_id,)
    )
    if row is None:
        return None
    else:
        return row["leader_discord_id"]

async def penalize_team(team_id: int, penalty_points: int):
    await execute(
        "UPDATE teams SET penalty_points = penalty_points + $1 WHERE team_id = $2",
        (penalty_points, team_id)
    )

async def get_team_kds(team_id: int) -> list[float] | None:
    rows = await fetch_all(
        "SELECT kd FROM team_members WHERE team_id = $1 ORDER BY member_id",
        (team_id,)
    )

    if not rows:
        return None

    return [row["kd"] for row in rows]