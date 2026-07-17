CREATE TABLE IF NOT EXISTS server_configs(
    guild_id BIGINT PRIMARY KEY,
    ranking_channel_id BIGINT,
    admin_role_id BIGINT,
    live_ranking_channel_id BIGINT,
    lobbies_channel_id BIGINT
);

CREATE TABLE IF NOT EXISTS events(
    event_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    guild_id BIGINT,
    name TEXT,
    status TEXT DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (guild_id) REFERENCES server_configs(guild_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS events_settings(
    event_id INTEGER PRIMARY KEY,
    kill_points INTEGER,
    players_per_team INTEGER,
    drop_worst_match BOOLEAN DEFAULT FALSE,
    matches_number INTEGER DEFAULT 5,
    lobby_mode TEXT DEFAULT 'random',
    lobbies_number INTEGER,

    FOREIGN KEY (event_id) REFERENCES events(event_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS placement_points(
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    event_id INTEGER,
    position INTEGER,
    points INTEGER,

    FOREIGN KEY (event_id) REFERENCES events(event_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS event_hosts(
    member_id BIGINT,
    event_id INTEGER,
    role TEXT DEFAULT 'host',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (event_id) REFERENCES events(event_id) ON DELETE CASCADE,
    UNIQUE(event_id, member_id)
);

CREATE TABLE IF NOT EXISTS lobby_codes_channels(
    channel_id BIGINT,
    event_id INTEGER,
    lobby_id INTEGER,

    FOREIGN KEY (event_id) REFERENCES events(event_id) ON DELETE CASCADE,
    UNIQUE(event_id, lobby_id)
);

CREATE TABLE IF NOT EXISTS lobbies(
    lobby_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    event_id INTEGER,
    name TEXT,

    FOREIGN KEY (event_id) REFERENCES events(event_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS lobbies_roles(
    role_id BIGINT PRIMARY KEY,
    lobby_id INTEGER NOT NULL,
    event_id INTEGER NOT NULL,

    FOREIGN KEY (event_id) REFERENCES events(event_id) ON DELETE CASCADE,
    FOREIGN KEY (lobby_id) REFERENCES lobbies(lobby_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS teams(
    team_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    event_id INTEGER,
    name TEXT,
    lobby_id INTEGER,
    leader_discord_id BIGINT,
    penalty_points INTEGER DEFAULT 0,
    kd REAL DEFAULT 0,
    previous_lobby_id INTEGER,
    slot INTEGER NOT NULL DEFAULT -1,

    FOREIGN KEY (event_id) REFERENCES events(event_id) ON DELETE CASCADE,
    FOREIGN KEY (lobby_id) REFERENCES lobbies(lobby_id) ON DELETE SET NULL,
    UNIQUE(event_id, leader_discord_id)
);

CREATE TABLE IF NOT EXISTS team_members(
    member_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    team_id INTEGER NOT NULL,
    member_name TEXT NOT NULL,
    kd REAL NOT NULL DEFAULT 0,

    FOREIGN KEY (team_id) REFERENCES teams(team_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS team_scores(
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    event_id INTEGER,
    team_id INTEGER,
    placement INTEGER,
    match_number INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'pending',

    FOREIGN KEY (event_id) REFERENCES events(event_id) ON DELETE CASCADE,
    FOREIGN KEY (team_id) REFERENCES teams(team_id) ON DELETE CASCADE,

    UNIQUE(event_id, team_id, match_number)
);

CREATE TABLE IF NOT EXISTS player_scores(
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    team_score_id INTEGER,
    member_id INTEGER,
    member_name TEXT,
    kills INTEGER,

    FOREIGN KEY (team_score_id) REFERENCES team_scores(id) ON DELETE CASCADE,
    FOREIGN KEY (member_id) REFERENCES team_members(member_id),

    UNIQUE(team_score_id, member_id)
);

CREATE TABLE IF NOT EXISTS score_screenshots(
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    team_score_id INTEGER,
    image_url TEXT,

    FOREIGN KEY (team_score_id) REFERENCES team_scores(id) ON DELETE CASCADE,

    UNIQUE(team_score_id, image_url)
);

CREATE TABLE IF NOT EXISTS blacklisted_servers(
    guild_id BIGINT PRIMARY KEY,
    blacklisted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    blacklisted_by BIGINT,

    FOREIGN KEY (guild_id) REFERENCES server_configs(guild_id) ON DELETE CASCADE
);