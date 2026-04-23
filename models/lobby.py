from dataclasses import dataclass
from models.team import Team

@dataclass
class Lobby:
    index: int
    teams: list[Team]
    lobby_id: int | None = None
    name: str | None = None
