import discord
from discord.ext import commands
from dotenv import load_dotenv

import os
import asyncio
import logging
import sqlite3

from db import get_db


logging.basicConfig(level=logging.INFO)


load_dotenv(".env")

TOKEN = os.environ["TOKEN"]

extensions = ["cogs.events"]

intents = discord.Intents.default()
intents.members = False

class Bot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def on_ready(self):
        print(f"Bot online come {self.user.display_name}")

    async def setup_hook(self):
        commands = await self.tree.sync()
        print(f"Sono stati caricati {len(commands)} comandi:\n/{'\n/'.join([cmd.name for cmd in commands])}")
        await self.init_db()

    async def init_db(self):
        print("Aprendo il database...")
        db = get_db()
        print("Connesso")
        c = db.cursor()
        c.execute("""CREATE TABLE IF NOT EXISTS server_configs(
            guild_id INTEGER PRIMARY KEY,
            ranking_channel_id INTEGER,
            members_commands_channel_id INTEGER,
            admin_role_id INTEGER
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS events(
            event_id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER,
            name TEXT,
            status TEXT DEFAULT 'active',
            lobbies_number INTEGER,
            created_at DATETIME,
            ending_at DATETIME
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS events_settings(
            event_id INTEGER PRIMARY KEY,
            kill_points INTEGER,
            players_per_team INTEGER,
            drop_worst_match BOOLEAN DEFAULT 0,
            matches_number INTEGER DEFAULT 5,
            kd_mode BOOLEAN DEFAULT 0,
            
            FOREIGN KEY (event_id) REFERENCES events(event_id) ON DELETE CASCADE
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS placement_points(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER,
            position INTEGER,
            points INTEGER,
                  
            FOREIGN KEY (event_id) REFERENCES events(event_id) ON DELETE CASCADE
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS lobbies (
            lobby_id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER,
            name TEXT,
            status TEXT DEFAULT 'open',

            FOREIGN KEY (event_id) REFERENCES events(event_id) ON DELETE CASCADE
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS teams(
            team_id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER,
            name TEXT,
            lobby INTEGER,
            penalty_points INTEGER DEFAULT 0,
            
            FOREIGN KEY (event_id) REFERENCES events(event_id) ON DELETE CASCADE,
            FOREIGN KEY (lobby) REFERENCES lobbies(lobby_id) ON DELETE SET NULL
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS team_members(
            member_id INTEGER PRIMARY KEY AUTOINCREMENT,
            team_id INTEGER,
            member_name TEXT,

            FOREIGN KEY (team_id) REFERENCES teams(team_id) ON DELETE CASCADE
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS team_scores(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER,
            team_id INTEGER,
            kills INTEGER,
            placement INTEGER,
            match_number INTEGER,

            FOREIGN KEY (event_id) REFERENCES events(event_id) ON DELETE CASCADE,
            FOREIGN KEY (team_id) REFERENCES teams(team_id) ON DELETE CASCADE,
            
            UNIQUE(event_id, team_id, match_number)
        )""")

        db.commit()
        db.close()
        print("Tabella(e) create/controllate")


bot = Bot()

async def main():
    for ext in extensions:
        await bot.load_extension(ext)
    await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
