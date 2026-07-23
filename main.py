import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

import asyncio
import sys
import logging

load_dotenv(".env")

from db.db import *
from config.config import TOKEN
from ui.views.server_panel import ServerPanelView
from ui.views.registra_team_view import RegistraTeamView
from cogs.events import build_member_cache
from services.server_service import is_blacklisted, init_blacklist_cache
from services.event_service import get_active_events


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

DEV_GUILDS = [
    discord.Object(id=1493505736523907102),
    discord.Object(id=1043217543604748290)
]

extensions = [
    "cogs.events",
    "cogs.teams",
    "cogs.debug",
    "cogs.blacklist"
]

intents = discord.Intents.default()
intents.members = True

class CustomTree(app_commands.CommandTree):
    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.guild_id and is_blacklisted(interaction.guild_id):
            raise app_commands.CheckFailure()

        return True

class Bot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents, tree_cls=CustomTree)

    async def on_ready(self):
        if self.user is not None:
            logger.info(f"Bot online come {self.user.display_name}")
    
    async def error_handler(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        msg = None

        if isinstance(error, app_commands.MissingPermissions):
            msg = "Non hai i permessi per farlo."
        elif isinstance(error, app_commands.CheckFailure):
            msg = "Questo server non può usare questo bot."
        if msg is not None:
            if interaction.response.is_done():
                await interaction.followup.send(
                    msg,
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    msg,
                    ephemeral=True
                )

    async def setup_hook(self):
        await init_db()
        logger.info("DB OK")
        await init_blacklist_cache()

        logger.info("BLACKLIST OK")

        for guild in DEV_GUILDS:
            self.tree.copy_global_to(guild=guild)
            commands = await self.tree.sync(guild=guild)
            logger.info(f"Sincronizzati {len(commands)} comandi su {guild.id}")
        
        logger.info("SYNC DEV OK")

        await self.tree.sync()
        logger.info("SYNC GLOBAL OK")

        self.tree.on_error = self.error_handler

        for guild in self.guilds:
            await build_member_cache(guild)
        
        logger.info("CACHE OK")
        logger.info("Sincronizzo le view...")
        self.add_view(ServerPanelView())
        active_events = await get_active_events()
        logger.info(active_events)
        for event in active_events:
            self.add_view(RegistraTeamView(event.event_id))

        logger.info("VIEWS OK")

    async def close(self):
        logger.warning("BOT CLOSE CHIAMATO")
        await close_db()
        await super().close()


bot = Bot()

async def main():
    for ext in extensions:
        await bot.load_extension(ext)
    await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
