import discord
from discord.ext import commands
from discord import app_commands

from datetime import datetime
from zoneinfo import ZoneInfo

from services.server_service import *

@app_commands.guilds(discord.Object(id=1493505736523907102), discord.Object(id=1043217543604748290))
class Blacklist(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="blacklist", description="Controlla la blacklist")
    @app_commands.checks.has_permissions(ban_members=True)
    async def blacklist(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        if interaction.guild.id not in (1493505736523907102, 1043217543604748290):
            await interaction.followup.send("Questo comando è riservato.", ephemeral=True)
            return
        rome = ZoneInfo("Europe/Rome")
        embed = discord.Embed(
            title="Blacklist servers",
            color=discord.Color.red()
        )
        emb_description = "Questi sono i server che non possono usare il bot:\n"
        blacklist = await get_blacklist()
        for b_id, b in blacklist.items():
            try:
                guild = await self.bot.fetch_guild(b_id)
            except (discord.HTTPException, discord.NotFound, discord.Forbidden):
                guild = None
            if guild:
                guild_name = guild.name
            else:
                guild_name = "Nome sconosciuto"
            dt = datetime.strptime(b["blacklisted_at"], "%Y-%m-%d %H:%M:%S")
            dt = dt.replace(tzinfo=ZoneInfo("UTC")).astimezone(rome)
            blacklisted_at = dt.strftime("%d/%m/%Y %H:%M")
            blacklisted_by = interaction.guild.get_member(b["blacklisted_by"])
            emb_description += f"{guild_name} | {b_id} | {blacklisted_at} | {blacklisted_by.mention}\n"
        embed.description = emb_description
        await interaction.followup.send(embed=embed, ephemeral=True)


    @app_commands.command(name="blacklist_add", description="Metti un server in blacklist")
    @app_commands.describe(server_id="Server da blacklistare")
    @app_commands.checks.has_permissions(ban_members=True)
    async def blacklist_add(self, interaction: discord.Interaction, server_id: str):
        await interaction.response.defer(ephemeral=True)
        if interaction.guild.id not in (1493505736523907102, 1043217543604748290):
            await interaction.followup.send("Questo comando è riservato.", ephemeral=True)
            return
        if not server_id.isdigit():
            await interaction.followup.send("L'id del server deve essere numerico!", ephemeral=True)
            return
        guild_id = int(server_id)
        if is_blacklisted(guild_id):
            await interaction.followup.send("Questo server è già blacklistato!", ephemeral=True)
            return
        await blacklist_guild(guild_id, interaction.user.id)
        try:
            guild = await self.bot.fetch_guild(guild_id)
        except (discord.HTTPException, discord.NotFound, discord.Forbidden):
            guild = None
        if guild:
            guild_name = guild.name
        else:
            guild_name = "Nome sconosciuto"
        await interaction.followup.send(
            f"Il server {guild_name} ({guild_id}) è stato blacklistato!",
            ephemeral=True
        )
    
    @app_commands.command(name="blacklist_remove", description="Togli un server dalla blacklist")
    @app_commands.describe(server_id="Server da rimuovere dalla blacklist")
    @app_commands.checks.has_permissions(ban_members=True)
    async def blacklist_remove(self, interaction: discord.Interaction, server_id: str):
        await interaction.response.defer(ephemeral=True)
        if interaction.guild.id not in (1493505736523907102, 1043217543604748290):
            await interaction.followup.send("Questo comando è riservato.", ephemeral=True)
            return
        if not server_id.isdigit():
            await interaction.followup.send("L'id del server deve essere numerico!", ephemeral=True)
            return
        guild_id = int(server_id)
        await unblacklist_guild(guild_id)
        try:
            guild = await self.bot.fetch_guild(guild_id)
        except (discord.HTTPException, discord.NotFound, discord.Forbidden):
            guild = None
        if guild:
            guild_name = guild.name
        else:
            guild_name = "Nome sconosciuto"
        await interaction.followup.send(
            f"Il server {guild_name} ({guild_id}) è stato rimosso dalla blacklist!",
            ephemeral=True
        )
    

    @app_commands.command(
        name="lista_server",
        description="Mostra i server in cui è presente il bot"
    )
    @app_commands.checks.has_permissions(ban_members=True)
    async def lista_server(self, interaction: discord.Interaction):
        if interaction.guild.id not in (1493505736523907102, 1043217543604748290):
            await interaction.response.send_message("Questo comando è riservato.", ephemeral=True)
            return
        embed = discord.Embed(
            title="Server del bot",
            color=discord.Color.blue()
        )

        description = ""

        for guild in sorted(self.bot.guilds, key=lambda g: g.name.lower()):
            description += (
                f"**{guild.name}**\n"
                f"ID: `{guild.id}` | Membri: {guild.member_count}\n\n"
            )

        embed.description = description or "Il bot non è in nessun server."

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )

async def setup(bot: commands.Bot):
    await bot.add_cog(Blacklist(bot))