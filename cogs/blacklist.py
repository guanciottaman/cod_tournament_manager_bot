import discord
from discord.ext import commands
from discord import app_commands

from datetime import datetime
from zoneinfo import ZoneInfo

from services.server_service import *

@app_commands.guilds(discord.Object(id=1493505736523907102))
class Blacklist(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="blacklist", description="Controlla la blacklist")
    @app_commands.checks.has_permissions(ban_members=True)
    async def blacklist(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        rome = ZoneInfo("Europe/Rome")
        embed = discord.Embed(
            title="Blaclist servers",
            color=discord.Color.red()
        )
        emb_description = "Questi sono i server che non possono usare il bot:\n"
        blacklist = await get_blacklist()
        for b_id, b in blacklist.items():
            guild = await self.bot.fetch_guild(b_id)
            if guild:
                guild_name = guild.name
            else:
                guild_name = "Nome sconosciuto"
            dt = datetime.strptime(b["blacklisted_at"], "%Y-%m-%d %H:%M:%S")
            dt = dt.replace(tzinfo=ZoneInfo("UTC")).astimezone(rome)
            blacklisted_at = dt.strftime("%d/%m/%Y %H:%M")
            blacklisted_by = interaction.guild.get_member(b["blacklisted_by"])
            emb_description += f"{guild_name} | {blacklisted_at} | {blacklisted_by.mention}\n"
        embed.description = emb_description
        await interaction.followup.send(embed=embed, ephemeral=True)


    @app_commands.command(name="blacklist_add", description="Metti un server in blacklist")
    @app_commands.describe(server_id="Server da blacklistare")
    @app_commands.checks.has_permissions(ban_members=True)
    async def blacklist_add(self, interaction: discord.Interaction, server_id: int):
        await blacklist_guild(server_id, interaction.user.id)
        guild = await self.bot.fetch_guild(server_id)
        if guild:
            guild_name = guild.name
        else:
            guild_name = "Nome sconosciuto"
        await interaction.response.send_message(
            f"Il server {guild_name} è stato blacklistato!",
            ephemeral=True
        )
    
    @app_commands.command(name="blacklist_remove", description="Togli un server dalla blacklist")
    @app_commands.describe(server_id="Server da rimuovere dalla blacklist")
    @app_commands.checks.has_permissions(ban_members=True)
    async def blacklist_remove(self, interaction: discord.Interaction, server_id: int):
        await unblacklist_guild(server_id)
        guild = await self.bot.fetch_guild(server_id)
        if guild:
            guild_name = guild.name
        else:
            guild_name = "Nome sconosciuto"
        await interaction.response.send_message(
            f"Il server {guild_name} è stato rimosso dalla blacklist!",
            ephemeral=True
        )