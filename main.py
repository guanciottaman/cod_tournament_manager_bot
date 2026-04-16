import discord
from discord.ext import commands
from dotenv import load_dotenv

import os
import asyncio
import logging
import sqlite3


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
        print("Aprendo il database...")
        db = sqlite3.connect("db.sqlite3")
        print("Connesso")
        c = db.cursor()
        c.execute("""CREATE TABLE IF NOT EXISTS server_configs(
                  server_id INTEGER PRIMARY KEY,
                  ranking_channel_id INTEGER,
                  members_commands_channel_id INTEGER,
                  admin_role_id INTEGER
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
