from dataclasses import dataclass

@dataclass
class TeamRankingEntry:
    team_id: int
    name: str
    score: int
    kills: int

@dataclass
class MVPRanking:
    player: str
    kills: int