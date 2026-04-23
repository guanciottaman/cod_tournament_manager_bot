from dataclasses import dataclass
import datetime

@dataclass
class Event:
    event_id: int
    guild_id: int
    name: str
    status: str
    created_at: datetime.datetime

    kill_points: int
    players_per_team: int
    drop_worst_match: bool
    matches_number: int
    kd_mode: bool
    lobbies_number: int