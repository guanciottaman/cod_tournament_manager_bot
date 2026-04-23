from dataclasses import dataclass

@dataclass
class Team:
    team_id: int
    name: str
    leader_discord_id: int
    kd: float = 0.0
    lobby: int | None = None
    