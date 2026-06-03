import discord
from discord.ext import commands
from discord import app_commands

from typing import Literal, Optional
import math

from ui.embeds.lobby_builders import build_config_lobbies_embed, build_event_start_summary
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
        
        view = discord.ui.View()
        events = await get_events_for_guild(interaction.guild_id, ["ready"])
        if not events:
            await interaction.response.send_message("Non ci sono eventi configurati per il tuo server!", ephemeral=True)
            return
        event_selector = build_event_selector(events)
        if not event_selector:
            await interaction.response.send_message("C'è stato un errore!", ephemeral=True)
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
            if lobby_mode in ("kd", "random_max"):
                lobbies_number = min(5, max(1, math.ceil(teams_count / 15)))
            else:
                lobbies_number = event.lobbies_number
                if lobbies_number is None:
                    lobbies_number = 1
            lobby_ids: list[int] = await create_lobbies_db(event_id, [f"{i+1}" for i in range(lobbies_number)])
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
            title="Configura lobby",
            description="Hai già configurato i seguenti eventi.\nAssicurati che tutti i capoteam abbiano iscritto la propria squadra!"
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @app_commands.command(name="sposta_team", description="Sposta un team in un'altra lobby")
    async def sposta_team(self, interaction: discord.Interaction):
        if not await self.check_admin_role(interaction):
            await interaction.response.send_message(
                "Non hai il ruolo necessario per spostare un team in un'altra lobby in un evento!",
                ephemeral=True
            )
            return
        view = discord.ui.View()
        events = await get_events_for_guild(interaction.guild_id, ["setup"])
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
            teams = await get_teams(event_id)
            await interaction.response.send_message(
                embed=embed,
                view=TeamsSelectorView(teams, event_id, switch_teams=True),
                ephemeral=True
            )
        event_selector.callback = event_selector_callback
        view.add_item(event_selector)
        embed = discord.Embed(
            title="Avvia evento",
            description="Hai già configurato le lobby dei seguenti eventi.\nScegli l'evento in cui vuoi spostare un team!"
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @app_commands.command(name="avvia_evento", description="Avvia un evento configurato")
    async def avvia_evento(self, interaction: discord.Interaction):
        if not await self.check_admin_role(interaction):
            await interaction.response.send_message("Non hai il ruolo necessario ad avviare un evento!", ephemeral=True)
            return
        view = discord.ui.View()
        events = await get_events_for_guild(interaction.guild_id, ["setup"])
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
            lobbies = await get_lobbies(event_id)
            embed = await build_event_start_summary(lobbies)
            embed.title = "Avvia evento"
            view = discord.ui.View()
            start_event_btn = discord.ui.Button(
                label="Avvia evento",
                style=discord.ButtonStyle.green
            )
            async def start_event_callback(interaction: discord.Interaction):
                await set_event_status(event_id, "running")
                await interaction.response.send_message("L'evento è stato avviato con successo!", ephemeral=True)
            start_event_btn.callback = start_event_callback
            view.add_item(start_event_btn)
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        event_selector.callback = event_selector_callback
        view.add_item(event_selector)
        embed = discord.Embed(
            title="Avvia evento",
            description="Hai già configurato i seguenti eventi.\nAssicurati di aver configurato correttamente le lobby!"
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
        events = await get_events_for_guild(interaction.guild_id, ["setup", "running"])
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
        events: list[Event] = await get_events_for_guild(interaction.guild_id, ["ready", "running"])
        event_selector = await build_event_selector(events)
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
    @app_commands.describe(status="Lo stato dei risultati che vuoi controllare", page="La pagina di risultati da cui partire")
    async def controlla_risultati(
        self,
        interaction: discord.Interaction,
        status: Literal["pending", "accepted", "rejected", "edited"],
        page: Optional[int]=1
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
            if not team_scores:
                await interaction.response.send_message(f"Non ci sono risultati con status {status}.", ephemeral=True)
                return
            if page is not None and not (0 < page < len(team_scores)):
                await interaction.response.send_message("Pagina non valida!", ephemeral=True)
                return
            embed = build_results_embed(
                page-1 if page is not None else 0,
                len(team_scores),
                team_scores[0].team_name,
                team_scores[0]
            )
            if embed is None:
                await interaction.response.send_message(
                    "C'è stato un errore con il controllo dei risultati dell'embed",
                    ephemeral=True
                )
                return
            await interaction.response.send_message(
                embeds=embed,
                view=ControllaRisultatiView(event_id, team_scores, page-1 if page is not None else 0),
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
        view = discord.ui.View()
        events: list[Event] = await get_events_for_guild(interaction.guild_id, ["running"])
        event_selector = build_event_selector(events)
        if not event_selector:
            await interaction.response.send_message("Non ci sono eventi configurati per il tuo server!", ephemeral=True)
            return
        async def event_selector_callback(interaction: discord.Interaction):
            await interaction.response.defer(thinking=True, ephemeral=True)
            event_id = int(event_selector.values[0])
            event = await get_event_info(event_id, interaction.guild_id)
            if event is None:
                await interaction.followup.send("Questo evento non esiste!")
                return
            teams_ranking_global = await compute_team_ranking(event_id, "global")
            if not teams_ranking_global:
                await interaction.followup.send("Nessun risultato è stato accettato!", ephemeral=True)
                return
            lobbies = await get_lobbies(event_id)
            files: list[discord.File] = []
            mvp_ranking_global = await compute_mvp_ranking(event_id)
            files.append(
                discord.File(
                    await build_leaderboard_image(teams_ranking_global), filename="teams_ranking_global.png"
                )
            )
            files.append(
                discord.File(
                    build_mvp_image(mvp_ranking_global), filename="mvp_ranking_global.png"
                )
            )
            embed = discord.Embed(
                title="Evento terminato",
                color=discord.Color.blurple(),
            )
            emb_description = f"Hai terminato l'evento **{event.name}**.\nEcco le classifiche finali globali:\n\n**Claassifica team:**\n"
            for i, r in enumerate(teams_ranking_global):
                team_name = r["name"]
                team_score = r["score"]
                emb_description += f"{i+1}. {team_name} | {team_score} punti\n"
            emb_description += "\n**MVPs:**\n"
            for i, p in enumerate(mvp_ranking_global):
                player_name = clean_player_name(p.get("player", "Unknown"))
                player_kills = p.get("kills")
                emb_description += f"{i+1}. {player_name} | {player_kills} kill\n"
            emb_description += "\n**Classifiche Lobby**\n"
            for i, lobby in enumerate(lobbies):
                emb_description += f"\n**Lobby {lobby.name}**\n*Classifica team:*\n"
                lobby_ranking = await compute_team_ranking(event_id, "lobby", lobby_id=lobby.lobby_id)
                lobby_image = await build_leaderboard_image(lobby_ranking, lobby_name=lobby.name)
                files.append(
                    discord.File(
                        lobby_image, filename=f"lobby{i+1}.png"
                    )
                )
                for j, r in enumerate(lobby_ranking):
                    team_name = r["name"]
                    team_score = r["score"]
                    emb_description += f"{j+1}. {team_name} | {team_score} punti\n"
                mvp_lobby_ranking = await compute_mvp_ranking(event_id, "lobby", lobby_id=lobby.lobby_id)
                mvp_lobby_image = build_mvp_image(mvp_lobby_ranking, lobby_name=lobby.name)
                files.append(
                    discord.File(
                        mvp_lobby_image, filename=f"lobby_mvp{i+1}.png"
                    )
                )
                emb_description += "\n*MVP:*\n"
                for j, r in enumerate(mvp_lobby_ranking):
                    player_name = r["player"]
                    player_kills = r["kills"]
                    emb_description += f"{j+1}. {player_name} | {player_kills} kill\n"
            embed.description = emb_description
            
            await ranking_channel.send(
                embed=embed,
                files=files
            )
            await interaction.followup.send(f"La classifica è stata mandata su {ranking_channel.mention}")
            await delete_event(interaction.guild_id, event_id)
        event_selector.callback = event_selector_callback
        view.add_item(event_selector)
        embed = discord.Embed(
            title="Termina evento",
            color=discord.Colour.blurple(),
            description="Questa è una lista degli eventi in corso.\nScegli l'evento che vuoi terminare e ottenere i risultati finali."
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(Events(bot))