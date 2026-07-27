from dataclasses import dataclass
from typing import Literal

@dataclass
class PlacementSettings:
    system: Literal["points", "multipliers"]
    points: dict[int, int] | None = None
    multipliers: dict[tuple[int, int | None], float] | None = None