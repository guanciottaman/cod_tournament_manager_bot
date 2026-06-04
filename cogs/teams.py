import discord
from discord.ext import commands
from discord import app_commands

from ui.resolvers.inserisci_risultato_cb import inserisci_risultato_callback
from ui.modals.registra_team import RegistraTeamModal
from services.team_service import *
from services.event_service import *
from services.event_flow import resolve_event
from services.server_service import *


class Teams(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        super().__init__()
        self.bot = bot
    
    @app_commands.command(name="registra_team", description="Registra il tuo team a un evento")
    async def registra_team(self, interaction: discord.Interaction):
        events = await get_events_for_guild(interaction.guild_id, ["ready"])
        embed = discord.Embed(
            title="Scegli l'evento a cui iscriverti",
            color=discord.Colour.red(),
            description="Questa è una lista degli eventi attivi.\nScegli l'evento a cui ti sei iscritto durante il ticket."
        )
        async def event_selector_callback(interaction: discord.Interaction, event: Event):
            players_per_team = event.players_per_team
            is_kd_mode = True if event.lobby_mode in ("kd", "kd_balanced") else False
            await interaction.response.send_modal(
                RegistraTeamModal(event_id=event.event_id, members_number=players_per_team, is_kd_mode=is_kd_mode)
            )
        
        await resolve_event(interaction, embed, events, event_selector_callback)

    @app_commands.command(name="modifica_team", description="Modifica il tuo team")
    async def modifica_team(self, interaction: discord.Interaction):
        events = await get_events_for_guild(interaction.guild_id, ["ready", "setup"])
        embed = discord.Embed(
            title="Scegli l'evento a cui ti sei iscritto",
            color=discord.Colour.red(),
            description="Questa è una lista degli eventi attivi.\nScegli l'evento del team che hai iscritto."
        )
        async def event_selector_callback(interaction: discord.Interaction, event: Event):
            event_id = event.event_id
            lobby_mode = event.lobby_mode
            members_number = event.players_per_team
            is_kd_mode = True if lobby_mode in ("kd", "kd_balanced") else False
            team_id = await get_team_id(event_id, interaction.user.id)
            if team_id is None:
                await interaction.response.send_message(
                    "Non hai registrato nessun team per questo evento!\nUsa /registra_team per farlo.",
                    ephemeral=True
                )
                return
            await interaction.response.send_modal(
                RegistraTeamModal(
                    event_id=event_id,
                    members_number=members_number,
                    is_kd_mode=is_kd_mode,
                    edit_mode=True,
                    team_id=team_id
                )
            )
        await resolve_event(interaction, embed, events, event_selector_callback)
    
    @app_commands.command(name="inserisci_risultato", description="Inserisci i risultati di un match")
    @app_commands.describe(prova1="Prima prova dei risultati", prova2="Seconda prova dei risultati")
    async def inserisci_risultato(
        self,
        interaction: discord.Interaction,
        prova1: discord.Attachment,
        prova2: discord.Attachment
    ):
        events = await get_events_for_guild(interaction.guild_id, ["running"])
        embed = discord.Embed(
            title="Scegli l'evento a cui ti sei iscritto",
            color=discord.Colour.red(),
            description="Questa è una lista degli eventi attivi.\nScegli l'evento del team che hai iscritto."
        )
        async def wrapper(interaction: discord.Interaction, event: Event):
            await inserisci_risultato_callback(interaction, event, prova1, prova2)
        await resolve_event(interaction, embed, events, wrapper)


async def setup(bot: commands.Bot):
    await bot.add_cog(Teams(bot))