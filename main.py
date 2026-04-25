import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

import os
import asyncio
import logging

from db.db import *


logging.basicConfig(level=logging.INFO)


load_dotenv(".env")

TOKEN = os.environ["TOKEN"]

extensions = [
    "cogs.events",
    "cogs.teams",
    "cogs.lobbies"
]

intents = discord.Intents.default()
intents.members = True

class Bot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def on_ready(self):
        print(f"Bot online come {self.user.display_name}")
    
    async def error_handler(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(
                "Non hai i permessi per farlo.",
                ephemeral=True
            )

    async def setup_hook(self):
        commands = await self.tree.sync()
        print(f"Sono stati caricati {len(commands)} comandi:\n/{'\n/'.join([cmd.name for cmd in commands])}")
        self.tree.on_error = self.error_handler
        await self.init_db()

    async def init_db(self):
        await execute("""CREATE TABLE IF NOT EXISTS server_configs(
            guild_id INTEGER PRIMARY KEY,
            ranking_channel_id INTEGER,
            admin_role_id INTEGER
        )""")
        await execute("""CREATE TABLE IF NOT EXISTS events(
            event_id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER,
            name TEXT,
            status TEXT DEFAULT 'active',
            created_at DATETIME,

            FOREIGN KEY (guild_id) REFERENCES server_configs(guild_id) ON DELETE CASCADE
        )""")
        await execute("""CREATE TABLE IF NOT EXISTS events_settings(
            event_id INTEGER PRIMARY KEY,
            kill_points INTEGER,
            players_per_team INTEGER,
            drop_worst_match BOOLEAN DEFAULT 0,
            matches_number INTEGER DEFAULT 5,
            kd_mode BOOLEAN DEFAULT 0,
            lobbies_number INTEGER,
            
            FOREIGN KEY (event_id) REFERENCES events(event_id) ON DELETE CASCADE
        )""")
        await execute("""CREATE TABLE IF NOT EXISTS placement_points(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER,
            position INTEGER,
            points INTEGER,
                  
            FOREIGN KEY (event_id) REFERENCES events(event_id) ON DELETE CASCADE
        )""")
        await execute("""CREATE TABLE IF NOT EXISTS lobbies (
            lobby_id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER,
            name TEXT,

            FOREIGN KEY (event_id) REFERENCES events(event_id) ON DELETE CASCADE
        )""")
        await execute("""CREATE TABLE IF NOT EXISTS teams(
            team_id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER,
            name TEXT,
            lobby_id INTEGER,
            leader_discord_id INTEGER,
            penalty_points INTEGER DEFAULT 0,
            
            FOREIGN KEY (event_id) REFERENCES events(event_id) ON DELETE CASCADE,
            FOREIGN KEY (lobby_id) REFERENCES lobbies(lobby_id) ON DELETE SET NULL,
            UNIQUE(event_id, leader_discord_id)
        )""")
        await execute("""CREATE TABLE IF NOT EXISTS team_members(
            member_id INTEGER PRIMARY KEY AUTOINCREMENT,
            team_id INTEGER,
            member_name TEXT,

            FOREIGN KEY (team_id) REFERENCES teams(team_id) ON DELETE CASCADE
        )""")
        await execute("""CREATE TABLE IF NOT EXISTS team_scores(
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
        print("Tabella(e) create/controllate")


bot = Bot()

async def main():
    for ext in extensions:
        await bot.load_extension(ext)
    await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
