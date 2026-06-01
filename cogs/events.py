import discord
from discord.ext import commands
from discord import app_commands

from typing import Literal
import math

from ui.embeds.lobby_builders import build_config_lobbies_embed
from ui.embeds.event_builders import *
from ui.selects.event_select import build_event_selector
from ui.modals.nome_evento import NomeEventoModal
from ui.views.elimina_evento import EliminaEventoView
from ui.views.lobbies_views import LobbyConfigView
from ui.views.setup_view import SetupView, DeleteServerView
from ui.views.team_selector import TeamsSelectorView
from ui.views.controlla_risultati import ControllaRisultatiView
from services.event_service import *
from services.server_service import *
from services.team_service import *
from services.lobby_service import create_lobbies_db, get_lobbies

    
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
    
    @app_commands.command(name="avvia_evento", description="Configura le lobby di un evento programmato e avvialo")
    async def avvia_evento(self, interaction: discord.Interaction):
        if not await self.check_admin_role(interaction):
            await interaction.response.send_message("Non hai il ruolo necessario ad avviare un evento!", ephemeral=True)
            return
        
        view = discord.ui.View()
        events = await get_events_for_guild(interaction.guild_id, ["ready"])
        event_selector = build_event_selector(events)
        if not event_selector:
            await interaction.response.send_message("Non ci sono eventi configurati per il tuo server!", ephemeral=True)
            return
        async def event_selector_callback(interaction: discord.Interaction):
            event_id = int(interaction.data["values"][0])
            event = await get_event_info(event_id, interaction.guild_id)
            if event is None:
                await interaction.response.send_message(
                    "Evento non valido",
                    ephemeral=True
                )
                return
            teams = await get_teams_by_event(event_id)
            teams_count = len(teams)
            if teams_count < 2:
                await interaction.response.send_message("Non ci sono abbastanza team per iniziare un evento!", ephemeral=True)
                return

            lobby_mode = event.lobby_mode
            if lobby_mode == "kd":
                lobbies_number = min(5, max(1, math.ceil(teams_count / 15)))
            else:
                lobbies_number = event.lobbies_number
                if lobbies_number is None:
                    lobbies_number = 1
            lobby_ids: list[int] = await create_lobbies_db(event_id, [f"Lobby {i+1}" for i in range(lobbies_number)])
            embed = await build_config_lobbies_embed(
                event_id,
                lobbies_number,
                teams_count
            )
            await interaction.response.send_message(
                embed=embed,
                view=LobbyConfigView(event_id, teams_count, lobby_mode, lobby_ids, lobbies_number),
                ephemeral=True
            )

        event_selector.callback = event_selector_callback
        view.add_item(event_selector)
        embed = discord.Embed(
            title="Avvia evento",
            description="Hai già configurato i seguenti eventi.\nAssicurati che tutti i capoteam abbiano iscritto la propria squadra!"
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @app_commands.command(name="info_evento", description="Ricevi informazioni su un certo evento")
    async def info_evento(self, interaction: discord.Interaction):
        if not await self.check_admin_role(interaction):
            await interaction.response.send_message("Non hai il ruolo necessario a ricevere informazioni su un evento!", ephemeral=True)
            return
        view = discord.ui.View()
        events = await get_events_for_guild(interaction.guild_id)
        event_selector = build_event_selector(events)
        if not event_selector:
            await interaction.response.send_message("Non ci sono eventi configurati per il tuo server!", ephemeral=True)
            return
        async def event_selector_callback(interaction: discord.Interaction):
            event_id = int(event_selector.values[0])
            event = await get_event_info(event_id, interaction.guild_id)
            placement_points = await get_placement_points(event_id)
            teams = await get_teams_by_event(event_id)
            embed = build_event_embed(event, placement_points, teams)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        event_selector.callback = event_selector_callback
        view.add_item(event_selector)
        embed = discord.Embed(
            title="Info eventi",
            description="Seleziona l'evento di cui vuoi controllare le informazioni"
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @app_commands.command(name="info_lobby", description="Ricevi informazioni sulle lobby di un certo evento")
    async def info_lobby(self, interaction: discord.Interaction):
        if not await self.check_admin_role(interaction):
            await interaction.response.send_message("Non hai il ruolo necessario a ricevere informazioni sulle lobby di un evento!", ephemeral=True)
            return
        view = discord.ui.View()
        events = await get_events_for_guild(interaction.guild_id)
        event_selector = build_event_selector(events)
        if not event_selector:
            await interaction.response.send_message("Non ci sono eventi configurati per il tuo server!", ephemeral=True)
            return
        async def event_selector_callback(interaction: discord.Interaction):
            event_id = int(event_selector.values[0])
            event = await get_event_info(event_id, interaction.guild_id)
            if event is None:
                await interaction.response.send_message("Questo evento non esiste!", ephemeral=True)
                return
            lobbies = await get_lobbies(event_id)
            embed = discord.Embed(
                title=f"Lobby {event.name}",
                color=discord.Color.red()
            )
            emb_description = f"Numero lobby: {len(lobbies)}\n\nLobby:\n\n"
            for i, lobby in enumerate(lobbies):
                emb_description += f"**{i+1}. {lobby.name} ({len(lobby.teams)} team)**\n*Team:*\n- {'\n- '.join(f"{team.name} (K/D {team.kd:.2f})" for team in lobby.teams)}\n\n"
            embed.description = emb_description
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        event_selector.callback = event_selector_callback
        view.add_item(event_selector)
        embed = discord.Embed(
            title="Info eventi",
            description="Seleziona l'evento di cui vuoi controllare le lobby"
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @app_commands.command(name="elimina_evento", description="Elimina un evento creato")
    async def elimina_evento(self, interaction: discord.Interaction):
        if not await self.check_admin_role(interaction):
            await interaction.response.send_message("Non hai il ruolo necessario per eliminare un evento!", ephemeral=True)
            return
        view = discord.ui.View()
        events = await get_events_for_guild(interaction.guild_id)
        event_selector = build_event_selector(events)
        if not event_selector:
            await interaction.response.send_message("Non ci sono eventi configurati per il tuo server!", ephemeral=True)
            return
        async def event_selector_callback(interaction: discord.Interaction):
            event_id = int(event_selector.values[0])
            event = await get_event_info(event_id, interaction.guild_id)
            placement_points = await get_placement_points(event_id)
            teams = await get_teams_by_event(event_id)
            embed = build_event_embed(event, placement_points, teams, embed_title="Elimina evento")
            await interaction.response.send_message(embed=embed, view=EliminaEventoView(event_id), ephemeral=True)
        event_selector.callback = event_selector_callback
        view.add_item(event_selector)
        embed = discord.Embed(
            title="Elimina evento",
            description="Questa è una lista degli eventi del tuo server.\nScegli l'evento da eliminare.",
            color=discord.Colour.red()
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @app_commands.command(name="info_team", description="Controlla informazioni su un team")
    async def info_team(self, interaction: discord.Interaction):
        if not await self.check_admin_role(interaction):
            await interaction.response.send_message("Non hai il ruolo necessario per avere info su un team!", ephemeral=True)
            return
        view = discord.ui.View()
        events = await get_events_for_guild(interaction.guild_id, ["ready", "running"])
        event_selector = build_event_selector(events)
        if not event_selector:
            await interaction.response.send_message("Non ci sono eventi configurati per il tuo server!", ephemeral=True)
            return
        async def event_selector_callback(interaction: discord.Interaction):
            event_id = int(event_selector.values[0])
            teams = await get_teams_by_event(event_id)
            if not teams:
                await interaction.response.send_message("Non sono presenti team iscritti a questo evento", ephemeral=True)
                return
            view = TeamsSelectorView(teams, event_id)
            embed = discord.Embed(
                title="Info team",
                color=discord.Colour.red(),
                description="Seleziona il team su cui vuoi informazioni"
            )
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            
        event_selector.callback = event_selector_callback
        view.add_item(event_selector)
        embed = discord.Embed(
            title="Info team",
            color=discord.Colour.red(),
            description="Questa è una lista degli eventi attivi e in corso.\nScegli l'evento in cui il team è presente."
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @app_commands.command(name="elimina_team", description="Elimina un team da un evento")
    async def elimina_team(self, interaction: discord.Interaction):
        if not await self.check_admin_role(interaction):
            await interaction.response.send_message("Non hai il ruolo necessario per eliminare un team!", ephemeral=True)
            return
        view = discord.ui.View()
        event_selector = await build_event_selector(interaction, ["ready", "running"])
        if not event_selector:
            await interaction.response.send_message("Non ci sono eventi configurati per il tuo server!", ephemeral=True)
            return
        async def event_selector_callback(interaction: discord.Interaction):
            event_id = int(event_selector.values[0])
            row = await get_teams_by_event(event_id)
            if not row:
                await interaction.response.send_message("Non sono presenti team iscritti a questo evento", ephemeral=True)
                return
            view = discord.ui.View()
            teams_selector = discord.ui.Select(
                placeholder="Seleziona il team da eliminare",
                options=[
                    discord.SelectOption(
                        label=name, value=str(team_id), description=f"Capoteam: {interaction.guild.get_member(leader_discord_id)}"
                    ) for team_id, name, leader_discord_id in row
                ],
                min_values=1,
                max_values=1
            )
            async def teams_selector_callback(interaction: discord.Interaction):
                team_id = teams_selector.values[0]
                await delete_team(team_id)
                await interaction.response.send_message("Team eliminato con successo!", ephemeral=True)
            teams_selector.callback = teams_selector_callback
            view.add_item(teams_selector)
            embed = discord.Embed(
                title="Elimina team",
                color=discord.Colour.red(),
                description="Seleziona il team da eliminare"
            )
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            
        event_selector.callback = event_selector_callback
        view.add_item(event_selector)
        embed = discord.Embed(
            title="Iscrizione team",
            color=discord.Colour.red(),
            description="Questa è una lista degli eventi attivi.\nScegli l'evento di cui vuoi eliminare un team."
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @app_commands.command(name="controlla_risultati", description="Controlla i risultati dei team")
    async def controlla_risultati(
        self,
        interaction: discord.Interaction,
        status: Literal["pending", "accepted", "rejected", "edited"]
    ):
        if not await self.check_admin_role(interaction):
            await interaction.response.send_message("Non hai il ruolo necessario per eliminare un team!", ephemeral=True)
            return
        view = discord.ui.View()
        events: list[Event] = await get_events_for_guild(interaction.guild_id, ["running"])
        if not events:
            await interaction.response.send_message("Non ci sono eventi configurati per il tuo server!", ephemeral=True)
            return
        event_selector = build_event_selector(events)
        async def event_selector_callback(interaction: discord.Interaction):
            event_id = int(event_selector.values[0])
            team_scores = await get_event_results(event_id, status)
            embed = build_results_embed(0, len(team_scores), team_scores[0].team_name, team_scores[0])
            if embed is None:
                await interaction.response.send_message(
                    "C'è stato un errore con il controllo dei risultati dell'embed",
                    ephemeral=True
                )
                return
            await interaction.response.send_message(
                embeds=embed,
                view=ControllaRisultatiView(event_id, team_scores),
                ephemeral=True
            )
        event_selector.callback = event_selector_callback
        view.add_item(event_selector)
        embed = discord.Embed(
            title="Controlla risultati",
            color=discord.Colour.red(),
            description="Questa è una lista degli eventi in corso.\nScegli l'evento di cui vuoi controllare i risultati."
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(Events(bot))