import discord
from discord.ext import commands
from discord import app_commands

from typing import Literal

from ui.embeds.event_builders import *
from ui.selects.event_select import build_event_selector
from ui.modals.nome_evento import NomeEventoModal
from ui.views.elimina_evento import EliminaEventoView
from ui.views.setup_view import SetupView, DeleteServerView
from ui.views.team_selector import TeamsSelectorView
from ui.resolvers.lobby_config_cb import start_lobby_config
from ui.resolvers.start_event_cb import start_event_callback
from ui.resolvers.controlla_risultati_cb import controlla_risultati_callback
from ui.resolvers.delete_team_cb import delete_team_callback
from ui.resolvers.termina_evento_cb import termina_evento_callback
from services.event_service import *
from services.event_flow import resolve_event
from services.server_service import *
from services.team_service import *
from services.lobby_service import get_lobbies
from services.ranking_service import *
from services.image_service import *

    
class Events(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        super().__init__()
        self.bot = bot
    
    async def check_admin_role(self, interaction: discord.Interaction):
        admin_role_id = await get_admin_role_id(interaction.guild_id)
        if not admin_role_id:
            return False

        admin_role = interaction.guild.get_role(admin_role_id)
        if admin_role is None:
            return False
        return admin_role in interaction.user.roles

    @app_commands.command(name="setup_server", description="Imposta il bot per questo server")
    @app_commands.checks.has_permissions(ban_members=True)
    async def setup_server(self, interaction: discord.Interaction):
        exists = await check_server_registered(interaction.guild_id)

        if exists:
            await interaction.response.send_message(
                "Il tuo server è già registrato!",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            view=SetupView(),
            ephemeral=True
        )

    @app_commands.command(name="elimina_config_server", description="Elimina la configurazione di questo server")
    @app_commands.checks.has_permissions(ban_members=True)
    async def delete_server(self, interaction: discord.Interaction):
        exists = await check_server_registered(interaction.guild_id)
        if not exists:
            await interaction.response.send_message("Il tuo server non è registrato!", ephemeral=True)
            return
        await interaction.response.send_message(view=DeleteServerView(), ephemeral=True)

    @app_commands.command(name="crea_evento", description="Crea un nuovo evento")
    async def crea_evento(self, interaction: discord.Interaction):
        if not await self.check_admin_role(interaction):
            await interaction.response.send_message("Non hai il ruolo necessario a creare un nuovo evento!", ephemeral=True)
            return
        await interaction.response.send_modal(NomeEventoModal())
    
    @app_commands.command(name="config_lobby", description="Configura le lobby di un evento programmato")
    async def config_lobby(self, interaction: discord.Interaction):
        if not await self.check_admin_role(interaction):
            await interaction.response.send_message("Non hai il ruolo necessario per configurare le lobby di un evento!", ephemeral=True)
            return
        embed = discord.Embed(
            title="Configura lobby",
            description="Hai già configurato i seguenti eventi.\nAssicurati che tutti i capoteam abbiano iscritto la propria squadra!"
        )
        events = await get_events_for_guild(interaction.guild_id, ["ready"])
        await resolve_event(interaction, embed, events, start_lobby_config)

    @app_commands.command(name="sposta_team", description="Sposta un team in un'altra lobby")
    async def sposta_team(self, interaction: discord.Interaction):
        if not await self.check_admin_role(interaction):
            await interaction.response.send_message(
                "Non hai il ruolo necessario per spostare un team in un'altra lobby in un evento!",
                ephemeral=True
            )
            return
        events = await get_events_for_guild(interaction.guild_id, ["setup"])
        embed = discord.Embed(
            title="Avvia evento",
            description="Hai già configurato le lobby dei seguenti eventi.\nScegli l'evento in cui vuoi spostare un team!"
        )
        async def event_selector_callback(interaction: discord.Interaction, event: Event):
            teams = await get_teams(event.event_id)
            await interaction.response.send_message(
                embed=embed,
                view=TeamsSelectorView(teams, event.event_id, "switch"),
                ephemeral=True
            )
        await resolve_event(interaction, embed, events, event_selector_callback)

    @app_commands.command(name="avvia_evento", description="Avvia un evento configurato")
    async def avvia_evento(self, interaction: discord.Interaction):
        if not await self.check_admin_role(interaction):
            await interaction.response.send_message("Non hai il ruolo necessario ad avviare un evento!", ephemeral=True)
            return
        events = await get_events_for_guild(interaction.guild_id, ["setup"])
        embed = discord.Embed(
            title="Avvia evento",
            description="Hai già configurato i seguenti eventi.\nAssicurati di aver configurato correttamente le lobby!"
        )
        await resolve_event(interaction, embed, events, start_event_callback)

    @app_commands.command(name="info_evento", description="Ricevi informazioni su un certo evento")
    async def info_evento(self, interaction: discord.Interaction):
        if not await self.check_admin_role(interaction):
            await interaction.response.send_message("Non hai il ruolo necessario a ricevere informazioni su un evento!", ephemeral=True)
            return
        events = await get_events_for_guild(interaction.guild_id)
        embed = discord.Embed(
            title="Info eventi",
            description="Seleziona l'evento di cui vuoi controllare le informazioni"
        )
        async def event_selector_callback(interaction: discord.Interaction, event: Event):
            placement_points = await get_placement_points(event.event_id)
            teams = await get_teams_by_event(event.event_id)
            embed = build_event_embed(event, placement_points, teams)
            await interaction.response.send_message(embed=embed, ephemeral=True)
        await resolve_event(interaction, embed, events, event_selector_callback)
        
    
    @app_commands.command(name="info_lobby", description="Ricevi informazioni sulle lobby di un certo evento")
    async def info_lobby(self, interaction: discord.Interaction):
        if not await self.check_admin_role(interaction):
            await interaction.response.send_message("Non hai il ruolo necessario a ricevere informazioni sulle lobby di un evento!", ephemeral=True)
            return
        events = await get_events_for_guild(interaction.guild_id, ["setup", "running"])
        embed = discord.Embed(
            title="Info eventi",
            description="Seleziona l'evento di cui vuoi controllare le lobby"
        )
        async def event_selector_callback(interaction: discord.Interaction, event: Event):
            lobbies = await get_lobbies(event.event_id)
            embed = discord.Embed(
                title=f"Lobby {event.name}",
                color=discord.Color.red()
            )
            emb_description = f"Numero lobby: {len(lobbies)}\n\nLobby:\n\n"
            for i, lobby in enumerate(lobbies):
                emb_description += f"**{i+1}. {lobby.name} ({len(lobby.teams)} team)**\n*Team:*\n- {'\n- '.join(f"{team.name} (K/D {team.kd:.2f})" for team in lobby.teams)}\n\n"
            embed.description = emb_description
            await interaction.response.send_message(embed=embed, ephemeral=True)
        await resolve_event(interaction, embed, events, event_selector_callback)
        
    
    @app_commands.command(name="elimina_evento", description="Elimina un evento creato")
    async def elimina_evento(self, interaction: discord.Interaction):
        if not await self.check_admin_role(interaction):
            await interaction.response.send_message("Non hai il ruolo necessario per eliminare un evento!", ephemeral=True)
            return
        events = await get_events_for_guild(interaction.guild_id)
        embed = discord.Embed(
            title="Elimina evento",
            description="Questa è una lista degli eventi del tuo server.\nScegli l'evento da eliminare.",
            color=discord.Colour.red()
        )
        async def event_selector_callback(interaction: discord.Interaction, event: Event):
            event_id = event.event_id
            placement_points = await get_placement_points(event_id)
            teams = await get_teams_by_event(event_id)
            embed = build_event_embed(event, placement_points, teams, embed_title="Elimina evento")
            await interaction.response.send_message(embed=embed, view=EliminaEventoView(event_id), ephemeral=True)
        
        await resolve_event(interaction, embed, events, event_selector_callback)
    
    @app_commands.command(name="info_team", description="Controlla informazioni su un team")
    async def info_team(self, interaction: discord.Interaction):
        if not await self.check_admin_role(interaction):
            await interaction.response.send_message("Non hai il ruolo necessario per avere info su un team!", ephemeral=True)
            return
        events = await get_events_for_guild(interaction.guild_id, ["ready", "setup", "running"])
        embed = discord.Embed(
            title="Info team",
            color=discord.Colour.red(),
            description="Questa è una lista degli eventi attivi e in corso.\nScegli l'evento in cui il team è presente."
        )
        async def event_selector_callback(interaction: discord.Interaction, event: Event):
            event_id = event.event_id
            teams = await get_teams_by_event(event_id)
            if not teams:
                await interaction.response.send_message("Non sono presenti team iscritti a questo evento", ephemeral=True)
                return
            view = TeamsSelectorView(teams, event_id, "info")
            embed = discord.Embed(
                title="Info team",
                color=discord.Colour.red(),
                description="Seleziona il team su cui vuoi informazioni"
            )
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
        await resolve_event(interaction, embed, events, event_selector_callback)

    @app_commands.command(name="elimina_team", description="Elimina un team da un evento")
    async def elimina_team(self, interaction: discord.Interaction):
        if not await self.check_admin_role(interaction):
            await interaction.response.send_message("Non hai il ruolo necessario per eliminare un team!", ephemeral=True)
            return
        events: list[Event] = await get_events_for_guild(interaction.guild_id, ["ready", "setup", "running"])
        embed = discord.Embed(
            title="Iscrizione team",
            color=discord.Colour.red(),
            description="Questa è una lista degli eventi attivi.\nScegli l'evento di cui vuoi eliminare un team."
        )
        
        await resolve_event(interaction, embed, events, delete_team_callback)
    
    @app_commands.command(name="penalizza_team", description="Penalizza un team")
    async def penalizza_team(self, interaction: discord.Interaction):
        if not await self.check_admin_role(interaction):
            await interaction.response.send_message("Non hai il ruolo necessario per eliminare un team!", ephemeral=True)
            return
        events: list[Event] = await get_events_for_guild(interaction.guild_id, ["running"])
        embed = discord.Embed(
            title="Iscrizione team",
            color=discord.Colour.red(),
            description="Questa è una lista degli eventi attivi.\nScegli l'evento in cui vuoi penalizzare un team."
        )
        async def event_selector_callback(interaction: discord.Interaction, event: Event):
            event_id = event.event_id
            teams = await get_teams(event_id)
            embed = discord.Embed(
                title="Penalizza team",
                color=discord.Color.red(),
                description="Seleziona il team che vuoi penalizzare"
            )
            await interaction.response.send_message(
                embed=embed,
                view=TeamsSelectorView(teams, event_id, "penalize")
            )
        
        await resolve_event(interaction, embed, events, event_selector_callback)

    @app_commands.command(name="controlla_risultati", description="Controlla i risultati dei team")
    @app_commands.describe(status="Lo stato dei risultati che vuoi controllare", page="La pagina di risultati da cui partire")
    async def controlla_risultati(
        self,
        interaction: discord.Interaction,
        status: Literal["pending", "accepted", "rejected", "edited"],
        page: int = 1
    ):
        if not await self.check_admin_role(interaction):
            await interaction.response.send_message("Non hai il ruolo necessario per eliminare un team!", ephemeral=True)
            return
        events: list[Event] = await get_events_for_guild(interaction.guild_id, ["running"])
        embed = discord.Embed(
            title="Controlla risultati",
            color=discord.Colour.red(),
            description="Questa è una lista degli eventi in corso.\nScegli l'evento di cui vuoi controllare i risultati."
        )
        async def wrapper(interaction: discord.Interaction, event: Event):
            await controlla_risultati_callback(interaction, event, status, page)
        
        await resolve_event(interaction, embed, events, wrapper)

    @app_commands.command(name="termina_evento", description="Termina un evento")
    async def termina_evento(self, interaction: discord.Interaction):
        if not await self.check_admin_role(interaction):
            await interaction.response.send_message("Non hai il ruolo necessario per eliminare un team!", ephemeral=True)
            return
        ranking_channel_id = await get_ranking_channel_id(interaction.guild_id)
        if ranking_channel_id is None:
            await interaction.response.send_message(
                "Non è stato impostato un canale per le classifiche!",
                ephemeral=True
            )
            return
        ranking_channel = interaction.guild.get_channel(ranking_channel_id)
        if ranking_channel is None:
            await interaction.response.send_message(
                f"Il canale con id {ranking_channel_id} non esiste o è stato eliminato!",
                ephemeral=True
            )
            return
        permissions = ranking_channel.permissions_for(interaction.guild.me)

        if not permissions.view_channel:
            await interaction.response.send_message(
                "Non posso vedere il canale delle classifiche configurato.",
                ephemeral=True
            )
            return

        if not permissions.send_messages:
            await interaction.response.send_message(
                "Non ho il permesso di inviare messaggi nel canale delle classifiche.",
                ephemeral=True
            )
            return
        events: list[Event] = await get_events_for_guild(interaction.guild_id, ["running"])
        embed = discord.Embed(
            title="Termina evento",
            color=discord.Colour.blurple(),
            description="Questa è una lista degli eventi in corso.\nScegli l'evento che vuoi terminare e ottenere i risultati finali."
        )
        async def wrapper(interaction: discord.Interaction, event: Event):
            await termina_evento_callback(interaction, event, ranking_channel)
        await resolve_event(interaction, embed, events, wrapper)


async def setup(bot: commands.Bot):
    await bot.add_cog(Events(bot))