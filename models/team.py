from dataclasses import dataclass

@dataclass
class Team:
    team_id: int
    name: str
    leader_discord_id: int
    kd: float = 0.0
    lobby: int | None = None


@dataclass
class PlayerScore:
    player_score_id: int
    team_score_id: int
    member_id: int
    member_name: str
    kills: int

@dataclass
class TeamScore:
    team_score_id: int
    event_id: int
    team_id: int
    team_name: str
    match_number: int
    placement: int
    status: str
    created_at: str
    player_scores: list[PlayerScore]
    screenshots: list[str]