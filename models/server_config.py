from dataclasses import dataclass


@dataclass
class ServerConfig:
    guild_id: int
    ranking_channel_id: int | None = None
    admin_role_id: int | None = None
    live_ranking_channel_id: int | None = None
    lobbies_channel_id: int | None = None