from dataclasses import dataclass
from models.team import Team

@dataclass
class Lobby:
    lobby_id: int
    teams: list[Team]
    index: int | None = None
    name: str | None = None
