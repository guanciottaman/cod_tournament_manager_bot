from dataclasses import dataclass
from models.team import Team

@dataclass
class Lobby:
    teams: list[Team]
    index: int | None = None
    lobby_id: int | None = None
    name: str | None = None
