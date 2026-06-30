from dataclasses import dataclass


@dataclass
class ServerConfig:
    guild_id: int
    ranking_channel_id: int
    admin_role_id: int
    live_ranking_channel_id: int