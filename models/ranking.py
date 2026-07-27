from dataclasses import dataclass

@dataclass
class TeamRankingEntry:
    team_id: int
    name: str
    score: float
    kills: int

@dataclass
class MVPRanking:
    player: str
    kills: int