import discord
from discord.ext import commands
from discord import app_commands

from typing import Literal

from ui.embeds.event_builders import *
from ui.embeds.lobby_builders import build_info_lobby_embed
from ui.embeds.panel_embed_builder import build_panel_embed
from ui.modals.nome_evento import NomeEventoModal
from ui.views.elimina_evento import EliminaEventoView
from ui.views.setup_view import SetupView, DeleteServerView
from ui.views.team_selector import TeamsSelectorView
from ui.views.server_panel import ServerPanelView
from ui.resolvers.lobby_config_cb import start_lobby_config
from ui.resolvers.start_event_cb import start_event_callback
from ui.resolvers.controlla_risultati_cb import controlla_risultati_callback
from ui.resolvers.delete_team_cb import delete_team_callback, delete_team_callback_personal
from ui.resolvers.termina_evento_cb import termina_evento_callback
from ui.resolvers.info_lobby_cb import info_lobbies_callback
from ui.resolvers.send_lobby_codes_cb import send_lobby_codes_callback
from ui.resolvers.set_lobbies_codes_cb import set_lobby_codes_callback
from services.event_service import *
from services.event_flow import resolve_event
from services.server_service import *
from services.lobby_service import get_lobbies
from services.team_service import *
from services.ranking_service import *
from services.image_service import *
from services.live_ranking_service import stop_live

member_cache: dict[int, list[discord.Member]] = {}

async def build_member_cache(guild: discord.Guild):
    member_cache[guild.id] = [
        m async for m in guild.fetch_members(limit=None)
    ]

def score(m: discord.Member, query: str):
    dn = m.display_name.lower()
    un = m.name.lower()

    if dn == query or un == query:
        return 100
    if dn.startswith(query):
        return 50
    if query in dn:
        return 20
    if query in un:
        return 10
    return 0


async def member_search(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    if not interaction.guild:
        return []

    query = " ".join(current.split()).lower()

    members = member_cache.get(interaction.guild.id)

    if not members:
        members = interaction.guild.members

    results = [
        m for m in members
        if query in m.display_name.lower()
        or query in m.name.lower()
    ]

    results.sort(key=lambda m: score(m, query), reverse=True)

    return [
        app_commands.Choice(
            name=m.display_name,
            value=str(m.id)
        )
        for m in results[:25]
    ]

class Events(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        super().__init__()
        self.bot = bot

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        await build_member_cache(guild)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        member_cache.setdefault(member.guild.id, []).append(member)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        if member.guild.id in member_cache:
            member_cache[member.guild.id] = [
                m for m in member_cache[member.guild.id]
                if m.id != member.id
            ]

    @app_commands.command(name="setup_server", description="Imposta il bot per questo server")
    @app_commands.checks.has_permissions(ban_members=True)
    async def setup_server(self, interaction: discord.Interaction):
        if interaction.guild is None:
            await interaction.response.send_message("Non puoi usarmi dai DM")
            return
        exists = await check_server_registered(interaction.guild.id)

        if exists:
            await interaction.response.send_message(
                "Il tuo server è già registrato!",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            embed=build_server_config_embed(
                interaction.guild,
                ServerConfig(interaction.guild.id)
            ),
            view=SetupView(interaction.guild.id),
            ephemeral=True
        )
    
    @app_commands.command(name="modifica_config_server", description="Modifica la configurazione di questo server")
    @app_commands.checks.has_permissions(ban_members=True)
    async def modifica_config_server(self, interaction: discord.Interaction):
        if interaction.guild is None:
            await interaction.response.send_message("Non puoi usarmi dai DM")
            return
        exists = await check_server_registered(interaction.guild.id)

        if not exists:
            await interaction.response.send_message(
                "Il tuo server non è ancora registrato!",
                ephemeral=True
            )
            return
        await interaction.response.defer(ephemeral=True)
        config = await get_server_config(interaction.guild.id)
        if config is None:
            await interaction.followup.send("C'è stato un problema!", ephemeral=True)
            return
        view = SetupView(interaction.guild.id, config=config, edit_mode=True)
        embed = build_server_config_embed(
            interaction.guild,
            ServerConfig(
                interaction.guild.id,
                config.ranking_channel_id,
                config.admin_role_id,
                config.live_ranking_channel_id,
                config.lobbies_channel_id
            )
        )
        await interaction.followup.send(
            embed=embed,
            view=view,
            ephemeral=True
        )

    @app_commands.command(name="elimina_config_server", description="Elimina la configurazione di questo server")
    @app_commands.checks.has_permissions(ban_members=True)
    async def delete_server(self, interaction: discord.Interaction):
        if interaction.guild is None:
            await interaction.response.send_message("Non puoi usarmi dai DM")
            return
        exists = await check_server_registered(interaction.guild.id)
        if not exists:
            await interaction.response.send_message("Il tuo server non è registrato!", ephemeral=True)
            return
        await interaction.response.send_message(view=DeleteServerView(), ephemeral=True)

    @app_commands.command(name="crea_evento", description="Crea un nuovo evento")
    async def crea_evento(self, interaction: discord.Interaction):
        if not await check_admin_role(interaction):
            await interaction.response.send_message("Non hai il ruolo necessario a creare un nuovo evento!", ephemeral=True)
            return
        await interaction.response.send_modal(NomeEventoModal())
    
    @app_commands.command(name="config_lobby", description="Configura le lobby di un evento programmato")
    async def config_lobby(self, interaction: discord.Interaction):
        if interaction.guild is None:
            return
        if not await check_admin_role(interaction):
            await interaction.response.send_message("Non hai il ruolo necessario per configurare le lobby di un evento!", ephemeral=True)
            return
        embed = discord.Embed(
            title="Configura lobby",
            description="Hai già configurato i seguenti eventi.\nAssicurati che tutti i capoteam abbiano iscritto la propria squadra!"
        )
        events = await get_events_for_guild(interaction.guild.id, ["ready"])
        await resolve_event(interaction, embed, events, start_lobby_config)

    @app_commands.command(name="sposta_team", description="Sposta un team in un'altra lobby")
    async def sposta_team(self, interaction: discord.Interaction):
        if interaction.guild is None:
            return
        if not await check_admin_role(interaction):
            await interaction.response.send_message(
                "Non hai il ruolo necessario per spostare un team in un'altra lobby in un evento!",
                ephemeral=True
            )
            return
        events = await get_events_for_guild(interaction.guild.id, ["setup"])
        embed = discord.Embed(
            title="Avvia evento",
            description="Hai già configurato le lobby dei seguenti eventi.\nScegli l'evento in cui vuoi spostare un team!"
        )
        async def event_selector_callback(interaction: discord.Interaction, event: Event):
            teams = await get_teams(event.event_id, setup_mode=True)

            await interaction.response.send_message(
                embed=embed,
                view=TeamsSelectorView(
                    teams,
                    event,
                    "switch",
                    use_lobbies=False if event.status not in ("setup", "running") else True,
                    lobbies=None if event.status not in ("setup", "running") else await get_lobbies(event.event_id),
                    interaction=interaction,
                ),
                ephemeral=True
            )
        await resolve_event(interaction, embed, events, event_selector_callback)

    @app_commands.command(name="avvia_evento", description="Avvia un evento configurato")
    async def avvia_evento(self, interaction: discord.Interaction):
        if interaction.guild is None:
            return
        if not await check_admin_role(interaction):
            await interaction.response.send_message("Non hai il ruolo necessario ad avviare un evento!", ephemeral=True)
            return
        events = await get_events_for_guild(interaction.guild.id, ["setup"])
        embed = discord.Embed(
            title="Avvia evento",
            description="Hai già configurato i seguenti eventi.\nAssicurati di aver configurato correttamente le lobby!"
        )
        await resolve_event(interaction, embed, events, start_event_callback)

    @app_commands.command(name="manda_codice_lobby", description="Manda il codice lobby ai capoteam di una certa lobby")
    @app_commands.describe(code="Il codice da mandare")
    async def manda_codice_lobby(self, interaction: discord.Interaction, code: str):
        if interaction.guild is None:
            return
        events = await get_events_for_guild(interaction.guild.id, ["running"])
        embed = discord.Embed(
            title="Manda codici lobby",
            color=discord.Color.blue(),
            description="I seguenti eventi sono in corso. Scegli quello che ti interessa."
        )
        async def wrapper(interaction: discord.Interaction, event: Event):
            if not (
                await is_event_host(event.event_id, interaction.user.id)
                or await check_admin_role(interaction)
            ):
                await interaction.response.send_message("Solo gli host possono mandare i codici lobby!", ephemeral=True)
                return
            lobbies = await get_lobbies(event.event_id)
            await send_lobby_codes_callback(interaction, event, lobbies, code)
        await resolve_event(interaction, embed, events, wrapper)

    @app_commands.command(name="info_evento", description="Ricevi informazioni su un certo evento")
    async def info_evento(self, interaction: discord.Interaction):
        if not await check_admin_role(interaction):
            await interaction.response.send_message("Non hai il ruolo necessario a ricevere informazioni su un evento!", ephemeral=True)
            return
        if interaction.guild is None:
            return
        events = await get_events_for_guild(interaction.guild.id)
        embed = discord.Embed(
            title="Info eventi",
            description="Seleziona l'evento di cui vuoi controllare le informazioni"
        )
        async def event_selector_callback(interaction: discord.Interaction, event: Event):
            if interaction.guild is None:
                return
            placement_settings = await get_placement_settings(event.event_id)
            teams = await get_teams_by_event(event.event_id)
            embed = build_event_embed(event, interaction.guild, placement_settings, teams)
            await interaction.response.send_message(embed=embed, ephemeral=True)
        await resolve_event(interaction, embed, events, event_selector_callback)
        
    
    @app_commands.command(name="info_lobby", description="Ricevi informazioni sulle lobby di un certo evento")
    async def info_lobby(self, interaction: discord.Interaction):
        if interaction.guild is None:
            return
        if not await check_admin_role(interaction):
            await interaction.response.send_message("Non hai il ruolo necessario a ricevere informazioni sulle lobby di un evento!", ephemeral=True)
            return
        events = await get_events_for_guild(interaction.guild.id, ["setup", "running"])
        embed = discord.Embed(
            title="Info eventi",
            description="Seleziona l'evento di cui vuoi controllare le lobby"
        )
        await resolve_event(interaction, embed, events, info_lobbies_callback)
        
    
    @app_commands.command(name="elimina_evento", description="Elimina un evento creato")
    async def elimina_evento(self, interaction: discord.Interaction):
        if interaction.guild is None:
            return
        if not await check_admin_role(interaction):
            await interaction.response.send_message("Non hai il ruolo necessario per eliminare un evento!", ephemeral=True)
            return
        events = await get_events_for_guild(interaction.guild.id)
        embed = discord.Embed(
            title="Elimina evento",
            description="Questa è una lista degli eventi del tuo server.\nScegli l'evento da eliminare.",
            color=discord.Colour.red()
        )
        async def event_selector_callback(interaction: discord.Interaction, event: Event):
            if interaction.guild is None:
                return
            event_id = event.event_id
            placement_settings = await get_placement_settings(event.event_id)
            teams = await get_teams_by_event(event.event_id)
            embed = build_event_embed(event, interaction.guild, placement_settings, teams, embed_title="Elimina evento")
            await interaction.response.send_message(embed=embed, view=EliminaEventoView(event_id), ephemeral=True)
        
        await resolve_event(interaction, embed, events, event_selector_callback)
    
    @app_commands.command(name="info_team", description="Controlla informazioni su un team")
    async def info_team(self, interaction: discord.Interaction):
        if interaction.guild is None:
            return
        events = await get_events_for_guild(interaction.guild.id, ["ready", "setup", "running"])
        embed = discord.Embed(
            title="Info team",
            color=discord.Colour.red(),
            description="Questa è una lista degli eventi attivi e in corso.\nScegli l'evento in cui il team è presente."
        )
        async def event_selector_callback(interaction: discord.Interaction, event: Event):
            if interaction.guild is None:
                return
            event_id = event.event_id
            if not await check_admin_role(interaction):
                team = await get_team_from_leader(event_id, interaction.user.id)
                if team is None:
                    await interaction.response.send_message(
                        "Non hai iscritto nessun team a questo evento",
                        ephemeral=True
                    )
                    return
                team_members = await get_team_members(team.team_id)
                embed = discord.Embed(
                    title=team.name,
                    color=discord.Color.blue()
                )
                leader_discord_id = team.leader_discord_id
                capoteam = interaction.guild.get_member(leader_discord_id) if leader_discord_id > 10e16 else None

                emb_description = f"**Evento:** {event.name}\n**Leader:** {capoteam.mention if capoteam is not None else leader_discord_id}\nK/D {team.kd:.2f}\n\n**Membri:**\n"

                if team_members:
                    kds = await get_team_kds(team.team_id)
                    for i, m in enumerate(team_members):
                        emb_description += f"{i+1}. {m[0]}{f' K/D {kds[i]}' if kds else ''}\n"
                else:
                    emb_description += "*Nessun membro*"
                embed.description = emb_description
                await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                if event.status == "setup":
                    teams = await get_teams(event_id, setup_mode=True)
                else:
                    teams = await get_teams(event_id)
                if not teams:
                    await interaction.response.send_message("Non sono presenti team iscritti a questo evento", ephemeral=True)
                    return
                view = TeamsSelectorView(
                    teams,
                    event,
                    "info",
                    use_lobbies=False if event.status not in ("setup", "running") else True,
                    lobbies=None if event.status not in ("setup", "running") else await get_lobbies(event_id),
                    interaction=interaction
                )
                embed = discord.Embed(
                    title="Info team",
                    color=discord.Colour.red(),
                    description="Seleziona il team su cui vuoi informazioni"
                )
                await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
        await resolve_event(interaction, embed, events, event_selector_callback)

    @app_commands.command(name="elimina_team", description="Elimina un team da un evento")
    async def elimina_team(self, interaction: discord.Interaction):
        if interaction.guild is None:
            return
        events: list[Event] = await get_events_for_guild(interaction.guild.id, ["ready", "setup", "running"])
        embed = discord.Embed(
            title="Elimina team",
            color=discord.Colour.red(),
            description="Questa è una lista degli eventi attivi.\nScegli l'evento di cui vuoi eliminare un team."
        )
        if not await check_admin_role(interaction):
            await resolve_event(interaction, embed, events, delete_team_callback_personal)
        else:
            await resolve_event(interaction, embed, events, delete_team_callback)
    
    @app_commands.command(name="penalizza_team", description="Penalizza un team")
    async def penalizza_team(self, interaction: discord.Interaction):
        if interaction.guild is None:
            return
        if not await check_admin_role(interaction):
            await interaction.response.send_message("Non hai il ruolo necessario per eliminare un team!", ephemeral=True)
            return
        events: list[Event] = await get_events_for_guild(interaction.guild.id, ["running"])
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
                view=TeamsSelectorView(
                    teams,
                    event,
                    "penalize",
                    use_lobbies=False if event.status not in ("setup", "running") else True,
                    lobbies=None if event.status not in ("setup", "running") else await get_lobbies(event_id),
                    interaction=interaction
                ),
                ephemeral=True
            )
        
        await resolve_event(interaction, embed, events, event_selector_callback)
    
    @app_commands.command(name="invia_lobby", description="Invia le lobby ai capoteam e agli admin (solo in setup mode)")
    async def invia_lobby(self, interaction: discord.Interaction):
        if interaction.guild is None:
            return
        if not await check_admin_role(interaction):
            await interaction.response.send_message("Non hai il ruolo necessario per inviare le lobby!", ephemeral=True)
            return
        events: list[Event] = await get_events_for_guild(interaction.guild.id, ["setup"])
        embed = discord.Embed(
            title="Invia lobby",
            color=discord.Colour.blue(),
            description="Questa è una lista degli eventi in corso.\nScegli l'evento di cui vuoi inviare le lobby."
        )
        async def event_selector_callback(interaction: discord.Interaction, event: Event):
            await interaction.response.defer(ephemeral=True)
            lobbies = await get_lobbies(event.event_id)
            embed = build_info_lobby_embed(event.name, lobbies, show_kd=False)

            guild = interaction.guild
            if guild is None:
                return

            lobbies_channel_id = await get_lobbies_channel_id(guild.id)
            if lobbies_channel_id is None:
                await interaction.followup.send("Non hai impostato un canale dove mandare le lobby!", ephemeral=True)
                return
            lobbies_channel = guild.get_channel(lobbies_channel_id)
            if not isinstance(lobbies_channel, discord.TextChannel):
                await interaction.followup.send(
                    "Devi selezionare un canale testuale!",
                    ephemeral=True
                )
                return
            await lobbies_channel.send(embed=embed)
            await interaction.followup.send(f"Lobby mandate nel canale {lobbies_channel.mention}", ephemeral=True)
        await resolve_event(interaction, embed, events, event_selector_callback)
    
    @app_commands.command(name="add_event_host", description="Aggiungi un host dell'evento che potrà mandare i codici lobby")
    @app_commands.describe(member="Il membro da aggiungere")
    @app_commands.autocomplete(member=member_search)
    async def add_event_host(self, interaction: discord.Interaction, member: str):
        if interaction.guild is None:
            return
        if not await check_admin_role(interaction):
            await interaction.response.send_message("Non hai il ruolo necessario per aggiungere un host!", ephemeral=True)
            return
        events: list[Event] = await get_events_for_guild(interaction.guild.id, ["ready", "setup", "running"])
        embed = discord.Embed(
            title="Aggiungi host evento",
            color=discord.Colour.blue(),
            description="Questa è una lista degli eventi in corso.\nScegli l'evento in cui vuoi aggiungere un host."
        )
        async def event_selector_callback(interaction: discord.Interaction, event: Event):
            if interaction.guild is None:
                return
            await add_event_host_db(event.event_id, int(member))
            m = interaction.guild.get_member(int(member))
            if m is None:
                await interaction.response.send_message("Membro non trovato!", ephemeral=True)
                return
            await interaction.response.send_message(
                f"Il membro {m.mention} è stato aggiunto agli host!",
                ephemeral=True
            )
        await resolve_event(interaction, embed, events, event_selector_callback)
    
    @app_commands.command(name="remove_event_host", description="Rimuovi un host dell'evento che non potrà più mandare i codici lobby")
    @app_commands.describe(member="Il membro da rimuovere")
    @app_commands.autocomplete(member=member_search)
    async def remove_event_host(self, interaction: discord.Interaction, member: str):
        if interaction.guild is None:
            return
        if not await check_admin_role(interaction):
            await interaction.response.send_message("Non hai il ruolo necessario per rimuovere un host!", ephemeral=True)
            return
        events: list[Event] = await get_events_for_guild(interaction.guild.id, ["ready", "setup", "running"])
        embed = discord.Embed(
            title="Rimuovi host evento",
            color=discord.Colour.red(),
            description="Questa è una lista degli eventi in corso.\nScegli l'evento in cui vuoi rimuovere un host."
        )
        async def event_selector_callback(interaction: discord.Interaction, event: Event):
            if interaction.guild is None:
                return
            await remove_event_host_db(event.event_id, int(member))
            m = interaction.guild.get_member(int(member))
            if m is None:
                await interaction.response.send_message(
                    "Membro non trovato!",
                    ephemeral=True
                )
                return
            await interaction.response.send_message(
                f"Il membro {m.mention} è stato rimosso dagli host!",
                ephemeral=True
            )
        await resolve_event(interaction, embed, events, event_selector_callback)
    
    @app_commands.command(name="get_event_host", description="Controlla gli host dell'evento che possono mandare i codici lobby")
    async def get_event_host(self, interaction: discord.Interaction):
        if interaction.guild is None:
            return
        if not await check_admin_role(interaction):
            await interaction.response.send_message("Non hai il ruolo necessario per controllare gli host!", ephemeral=True)
            return
        events: list[Event] = await get_events_for_guild(interaction.guild.id, ["ready", "setup", "running"])
        embed = discord.Embed(
            title="Controlla host evento",
            color=discord.Colour.blue(),
            description="Questa è una lista degli eventi in corso.\nScegli l'evento in cui vuoi controllare gli host."
        )
        async def event_selector_callback(interaction: discord.Interaction, event: Event):
            if interaction.guild is None:
                return
            hosts = await get_event_hosts_db(event.event_id)
            embed = discord.Embed(
                title=f"Host {event.name}",
                color=discord.Color.blue()
            )
            emb_description = "Ecco gli host dell'evento:\n"
            for i, host in enumerate(hosts):
                host_member = interaction.guild.get_member(host)
                emb_description += f"{i+1}. {host_member.mention if host_member else host}\n"
            embed.description = emb_description
            await interaction.response.send_message(
                embed=embed,
                ephemeral=True
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
        if interaction.guild is None:
            return
        if not await check_admin_role(interaction):
            await interaction.response.send_message("Non hai il ruolo necessario per eliminare un team!", ephemeral=True)
            return
        events: list[Event] = await get_events_for_guild(interaction.guild.id, ["running"])
        embed = discord.Embed(
            title="Controlla risultati",
            color=discord.Colour.red(),
            description="Questa è una lista degli eventi in corso.\nScegli l'evento di cui vuoi controllare i risultati."
        )
        async def wrapper(interaction: discord.Interaction, event: Event):
            await controlla_risultati_callback(interaction, event, status, page)
        
        await resolve_event(interaction, embed, events, wrapper)
    
    @app_commands.command(
        name="set_lobbies_codes_channels",
        description="Imposta i canali dove mandare i codici lobby per un certo evento"
    )
    async def set_lobbies_codes_channels(self, interaction: discord.Interaction):
        if interaction.guild is None:
            return
        if not await check_admin_role(interaction):
            await interaction.response.send_message("Non hai il ruolo necessario per impostare i canali dove mandare i codici lobby!", ephemeral=True)
            return
        events: list[Event] = await get_events_for_guild(interaction.guild.id, ["setup", "running"])
        embed = discord.Embed(
            title="Imposta canali codici lobby",
            color=discord.Colour.blue(),
            description="Questa è una lista degli eventi in corso.\nScegli l'evento di cui vuoi impostare i canali codici lobby."
        )
        
        await resolve_event(interaction, embed, events, set_lobby_codes_callback)

    @app_commands.command(name="termina_evento", description="Termina un evento")
    async def termina_evento(self, interaction: discord.Interaction):
        if interaction.guild is None:
            return
        if not await check_admin_role(interaction):
            await interaction.response.send_message("Non hai il ruolo necessario per eliminare un team!", ephemeral=True)
            return
        ranking_channel_id = await get_ranking_channel_id(interaction.guild.id)
        if ranking_channel_id is None:
            await interaction.response.send_message(
                "Non è stato impostato un canale per le classifiche!",
                ephemeral=True
            )
            return
        ranking_channel = interaction.guild.get_channel(ranking_channel_id)
        if not isinstance(ranking_channel, discord.TextChannel):
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
        events: list[Event] = await get_events_for_guild(interaction.guild.id, ["running"])
        embed = discord.Embed(
            title="Termina evento",
            color=discord.Colour.blurple(),
            description="Questa è una lista degli eventi in corso.\nScegli l'evento che vuoi terminare e ottenere i risultati finali."
        )
        async def wrapper(interaction: discord.Interaction, event: Event):
            await termina_evento_callback(interaction, event, ranking_channel)
        await resolve_event(interaction, embed, events, wrapper)
    
    @app_commands.command(name="stop_live", description="Ferma le classifiche live")
    async def stop_live(self, interaction: discord.Interaction):
        if interaction.guild is None:
            return
        if not await check_admin_role(interaction):
            await interaction.response.send_message("Non hai il ruolo necessario per fermare le classifiche live!", ephemeral=True)
            return
        async def event_selector_callback(interaction: discord.Interaction, event: Event):
            await stop_live(event.event_id)
            await interaction.response.send_message("Le classifiche live sono state fermate con successo!", ephemeral=True)
        embed = discord.Embed(
            title="Ferma classifiche live",
            color=discord.Color.red(),
            description="Scegli l'evento per cui fermare le classifiche live"
        )
        events = await get_events_for_guild(interaction.guild.id, ["running"])
        await resolve_event(interaction, embed, events, event_selector_callback)

    @app_commands.command(name="load_panel", description="Manda il pannello nel canale configurato")
    async def load_panel(self, interaction: discord.Interaction):
        if interaction.guild is None:
            await interaction.response.send_message("Non puoi usarmi dai DM!", ephemeral=True)
            return
        panel_channel_id = await get_panel_channel_id(interaction.guild.id)
        if panel_channel_id is None:
            await interaction.response.send_message("Il canale non è stato creato correttamente!", ephemeral=True)
            return
        panel_channel = interaction.guild.get_channel(panel_channel_id)
        if panel_channel is None:
            await interaction.response.send_message("Canale non trovato!", ephemeral=True)
            return
        if not isinstance(panel_channel, discord.TextChannel):
            await interaction.response.send_message(
                "Devi selezionare un canale testuale!",
                ephemeral=True
            )
            return

        await panel_channel.send(
            embed=build_panel_embed(interaction.guild),
            view=ServerPanelView()
        )
        await interaction.response.send_message(f"Pannello mandato su {panel_channel.mention}!", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Events(bot))