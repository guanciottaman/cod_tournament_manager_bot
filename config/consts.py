DEFAULT_PLACEMENT_POINTS: dict[int, int] = {
    1: 15,
    2: 12,
    3: 10,
    4: 8,
    5: 6
}

DEFAULT_PLACEMENT_MULTIPLIERS: dict[tuple[int, int | None], float] = {
    (1, 1): 2.0,
    (2, 3): 1.8,
    (4, 6): 1.6,
    (7, 10): 1.4,
    (11, None): 1.0
}

LOBBY_MODES = {
    "random": "Casuale",
    "random_max": "Casuale (massimo 16 team/lobby)",
    "kd": "KD",
    "kd_balanced": "KD bilanciato"
}

STATUSES = {
    "draft": "In creazione",
    "ready": "Registrazione team",
    "setup": "Lobby create",
    "running": "In corso"
}
