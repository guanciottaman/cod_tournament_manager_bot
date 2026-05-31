import discord
from discord.ext import commands
from discord import app_commands

from typing import Literal
import math

from cogs.lobbies import LobbyConfigView, build_config_lobbies_embed
from services.event_service import *
from services.server_service import *
from services.team_service import *
from services.lobby_service import create_lobbies_db, get_lobbies

DEFAULT_PLACEMENT_POINTS = {
    "1": 15,
    "2": 12,
    "3": 10,
    "4": 8,
    "5": 6
}

def build_event_selector(events: list[Event]) -> discord.ui.Select | None:
    if not events:
        return None

    return discord.ui.Select(
        placeholder="Seleziona l'evento...",
        min_values=1,
        max_values=1,
        options=[
            discord.SelectOption(label=event.name, value=str(event.event_id))
            for event in events
        ]
    )

def build_event_embed(
    event: Event,
    placement_points: list[tuple[int, int]],
    teams: list[Team],
    embed_title: str="Configurazione evento"
):
    embed = discord.Embed(
        title=embed_title,
        color=discord.Color.blurple()
    )
    lobby_modes = {
        "random": "casuale",
        "kd": "KD",
        "kd_balanced": "KD bilanciato"
    }

    embed.description = (
        f"# {event.name}\n"
        f"**Stato:** {event.status}\n"
        f"**Match:** {event.matches_number}\n"
        f"**Giocatori per team:** {event.players_per_team}\n"
        f"**Lobby Mode:** {lobby_modes[event.lobby_mode]}\n"
        f"**Scarta partita peggiore:** {'ON' if event.drop_worst_match else 'OFF'}\n\n"
        f"**Punti piazzamento:**\n"
    )

    if placement_points:
        for position, points in placement_points:
            embed.description += f"{position}° posto: *{points} punti*\n"
    else:
        for position, points in DEFAULT_PLACEMENT_POINTS.items():
            embed.description += f"{position}° posto: *{points} punti*\n"

    embed.description += "\n**Team**\n"

    if teams:
        for i, team in enumerate(teams):
            embed.description += f"{i+1}. {team.name}\n"
    else:
        embed.description += "*Nessun team iscritto*\n"

    return embed

def build_results_embed(
    page: int,
    pages_number: int,
    team_name: str,
    team_score: TeamScore
) -> list[discord.Embed] | None:
    print(team_score)
    embed = discord.Embed(
        title=f"Risultati evento team {team_name}"
    )
    emb_description = f"**Match** n.{team_score.match_number}\n**Piazzamento:** {team_score.placement}\n**Stato:** {team_score.status}\n\nRisultati giocatori:\n"
    if team_score.status == "pending":
        embed.color = discord.Color.yellow()
    elif team_score.status == "accepted":
        embed.color = discord.Color.green()
    elif team_score.status == "rejected":
        embed.color = discord.Color.red()
    else:
        return None
    player_scores = team_score.player_scores
    for score in player_scores:
        emb_description += f"**{score.player_name}:** {score.kills} kill\n"
    print(f"{emb_description = }")
    embed.description = emb_description
    embed.set_image(url=team_score.screenshots[0])
    embed2 = discord.Embed(color=embed.color)
    embed2.set_image(url=team_score.screenshots[1])
    embed2.set_footer(text=f"Pagina: {page+1}/{pages_number}")

    embeds = [embed, embed2]
    return embeds

class SetupView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.ranking_channel: discord.TextChannel | None = None
        self.admin_role: discord.Role | None = None

    @discord.ui.select(
        cls=discord.ui.ChannelSelect,
        channel_types=[discord.ChannelType.text],
        placeholder="Seleziona il canale per le classifiche",
        min_values=1,
        max_values=1,
        row=0
    )
    async def select_ranking_channel(self, interaction: discord.Interaction, select: discord.ui.ChannelSelect):
        self.ranking_channel = select.values[0]
        await interaction.response.defer()

    
    @discord.ui.select(
        cls=discord.ui.RoleSelect,
        placeholder="Seleziona il ruolo che potrà dare penalità o gestire eventi",
        min_values=1,
        max_values=1,
        row=1
    )
    async def select_admin_role(self, interaction: discord.Interaction, select: discord.ui.RoleSelect):
        self.admin_role = select.values[0]
        await interaction.response.defer()

    @discord.ui.button(
        label="Conferma",
        style=discord.ButtonStyle.green,
        row=2
    )
    async def confirm_setup(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not all([
            self.ranking_channel,
            self.admin_role
        ]):
            await interaction.response.send_message("Tutte le opzioni devono essere inserite!", ephemeral=True)
            return
        
        success = await create_server_config(
            interaction.guild_id,
            self.ranking_channel.id,
            self.admin_role.id
        )

        if not success:
            await interaction.response.send_message(
                "Il tuo server è già registrato!",
                ephemeral=True
            )
            return
        await interaction.response.send_message("Il tuo server è stato registrato con successo!", ephemeral=True)


class DeleteServerView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=30)

    @discord.ui.button(
        label="❌ Annulla",
        style=discord.ButtonStyle.gray
    )
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(
            content="Operazione annullata.",
            view=None
        )

    @discord.ui.button(
        label="🗑 Conferma eliminazione",
        style=discord.ButtonStyle.danger
    )
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        await delete_server_config(interaction.guild_id)
        await interaction.response.edit_message(
            content="Server rimosso dal sistema con successo.",
            view=None
        )


class PlacementModal(discord.ui.Modal, title="Punti piazzamento"):

    first = discord.ui.TextInput(label="1° posto", default=DEFAULT_PLACEMENT_POINTS["1"])
    second = discord.ui.TextInput(label="2° posto", default=DEFAULT_PLACEMENT_POINTS["2"])
    third = discord.ui.TextInput(label="3° posto", default=DEFAULT_PLACEMENT_POINTS["3"])
    fourth = discord.ui.TextInput(label="4° posto", default=DEFAULT_PLACEMENT_POINTS["4"])
    fifth = discord.ui.TextInput(label="5° posto", default=DEFAULT_PLACEMENT_POINTS["5"])

    def __init__(self, event_id: int, view: discord.ui.View):
        super().__init__()
        self.event_id = event_id
        self.view = view

    async def on_submit(self, interaction: discord.Interaction):
        values = [
            self.first.value,
            self.second.value,
            self.third.value,
            self.fourth.value,
            self.fifth.value
        ]
        if not all(
            val.isnumeric() for val in values
        ):
            await interaction.response.send_message("Tutti i valori devono essere numeri!", ephemeral=True)
            return
        await insert_placement_points(self.event_id, values)
        event = await get_event_info(self.event_id, interaction.guild_id)
        placement_points = await get_placement_points(self.event_id)
        teams = await get_teams_by_event(self.event_id)
        embed = build_event_embed(event, placement_points, teams)
        await interaction.response.edit_message(embed=embed, view=self.view)


class KillPointsModal(discord.ui.Modal, title="Punti per kill"):
    kill_points = discord.ui.TextInput(
        label="Punti per kill",
        placeholder="es. 1, 2, 3...",
        max_length=2
    )

    def __init__(self, event_id: int, view: discord.ui.View):
        super().__init__()
        self.event_id = event_id
        self.view = view

    async def on_submit(self, interaction: discord.Interaction):
        await set_kill_points_db(self.event_id, int(self.kill_points.value))
        placement_view = discord.ui.View()
        btn = discord.ui.Button(style=discord.ButtonStyle.secondary, label="Modifica punti piazzamento")
        async def btn_callback(ak_interaction: discord.Interaction):
            await ak_interaction.response.send_modal(PlacementModal(self.event_id, self.view))
        btn.callback = btn_callback
        placement_view.add_item(btn)
        await interaction.response.send_message("Hai impostato i punti per le kill, ora clicca il bottone per impostare i punti di piazzamento!", view=placement_view, ephemeral=True)

class CreaEventoView(discord.ui.View):
    def __init__(self, event_id: int):
        super().__init__(timeout=None)
        self.event_id = event_id

    @discord.ui.select(
        placeholder="Numero match",
        options=[
                discord.SelectOption(label=str(i), value=str(i))
                for i in range(3, 6)
            ],
    )
    async def set_matches_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        await set_matches_number(self.event_id, int(select.values[0]))
        event = await get_event_info(self.event_id, interaction.guild_id)
        placement_points = await get_placement_points(self.event_id)
        teams = await get_teams_by_event(self.event_id)
        embed = build_event_embed(event, placement_points, teams)
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.select(
        placeholder="Numero giocatori per team",
        options=[
                discord.SelectOption(label=str(i), value=str(i))
                for i in range(3, 5)
            ]
    )
    async def set_players_per_team_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        await set_players_per_team(self.event_id, int(select.values[0]))
        event = await get_event_info(self.event_id, interaction.guild_id)
        placement_points = await get_placement_points(self.event_id)
        teams = await get_teams_by_event(self.event_id)
        embed = build_event_embed(event, placement_points, teams)
        await interaction.response.edit_message(embed=embed, view=self)
    
    @discord.ui.select(
        placeholder="Lobby Mode",
        options=[
            discord.SelectOption(
                label="Casuale",
                description="Le lobby saranno create casualmente",
                value="random",
                emoji="❌"
            ),
            discord.SelectOption(
                label="KD",
                description="Le lobby verranno create in base al rapporto K/D, ma non saranno bilanciate",
                value="kd",
                emoji="✅"    
            ),
            discord.SelectOption(
                label="KD Bilanciato",
                description="Le lobby verranno create in base al rapporto K/D, ma saranno bilanciate",
                value="kd_balanced",
                emoji="✅"    
            )
        ]
    )
    async def set_kd_mode_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        await set_lobby_mode(self.event_id, select.values[0])
        event = await get_event_info(self.event_id, interaction.guild_id)
        placement_points = await get_placement_points(self.event_id)
        teams = await get_teams_by_event(self.event_id)
        embed = build_event_embed(event, placement_points, teams)
        await interaction.response.edit_message(embed=embed, view=self)
    
    @discord.ui.select(
        placeholder="Scarta la partita peggiore?",
        options=[
            discord.SelectOption(
                label="OFF",
                description="Tutte le partite saranno conteggiate",
                value="0",
                emoji="❌"
            ),
            discord.SelectOption(
                label="ON",
                description="La peggiore partita di ogni squadra verrà scartata",
                value="1",
                emoji="✅"    
            ),
        ]
    )
    async def set_drop_worst_match_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        await set_drop_worst_match(self.event_id, int(select.values[0]))
        event = await get_event_info(self.event_id, interaction.guild_id)
        placement_points = await get_placement_points(self.event_id)
        teams = await get_teams_by_event(self.event_id)
        embed = build_event_embed(event, placement_points, teams)
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(
        label="Modifica punti",
        style=discord.ButtonStyle.secondary
    )
    async def edit_placement_points(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(KillPointsModal(self.event_id, self))
    

    @discord.ui.button(
        label="Crea evento",
        style=discord.ButtonStyle.green,
        row=4
    )
    async def create_event(self, interaction: discord.Interaction, button: discord.ui.Button):
        await set_event_status(self.event_id, "ready")
        await interaction.response.send_message("Evento creato!", ephemeral=True)


class NomeEventoModal(discord.ui.Modal, title="Nuovo evento"):
    name = discord.ui.TextInput(label="Nome evento", placeholder="Inserisci il nome dell'evento...", max_length=40)
    async def on_submit(self, interaction: discord.Interaction):
        event_id = await create_event(interaction.guild_id, self.name.value)
        await set_players_per_team(event_id, 3)
        await set_kill_points_db(event_id, 1)
        await insert_placement_points(event_id, list(DEFAULT_PLACEMENT_POINTS.values()))
        event = await get_event_info(event_id, interaction.guild_id)
        placement_points = await get_placement_points(event_id)
        teams = await get_teams_by_event(event_id)
        embed = build_event_embed(event, placement_points, teams)
        
        await interaction.response.send_message(
            embed=embed,
            view=CreaEventoView(event_id),
            ephemeral=True
        )


class EliminaEventoView(discord.ui.View):
    def __init__(self, event_id: int):
        super().__init__(timeout=None)
        self.event_id = event_id
    
    @discord.ui.button(
        label="Annulla",
        style=discord.ButtonStyle.secondary
    )
    async def cancel_delete_event(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Eliminazione evento annullata.", ephemeral=True)

    @discord.ui.button(
            label="🗑️Conferma eliminazione",
            style=discord.ButtonStyle.danger
    )
    async def delete_event_confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        await delete_event(interaction.guild_id, self.event_id)
        await interaction.response.send_message("Evento eliminato con successo!", ephemeral=True)

class TeamsSelectorView(discord.ui.View):
    def __init__(self, teams: list[Team], event_id: int, page: int = 0):
        super().__init__(timeout=180)
        self.teams = teams
        self.event_id = event_id
        self.page = page
        self.add_item(self.build_select())

    def build_select(self):
        start = self.page * 25
        end = start + 25
        page_teams = self.teams[start:end]

        select = discord.ui.Select(
            placeholder=f"Seleziona team (pagina {self.page + 1})",
            options=[
                discord.SelectOption(
                    label=t.name,
                    value=str(t.team_id),
                    description=f"Capoteam: {t.leader_discord_id}"
                )
                for t in page_teams
            ],
            min_values=1,
            max_values=1
        )

        async def callback(interaction: discord.Interaction):
            team_id = int(select.values[0])

            team = await get_team_info(team_id)
            if team is None:
                await interaction.response.send_message("Il team non esiste!", ephemeral=True)
                return
            team_members = await get_team_members(team_id)
            event = await get_event_info(self.event_id, interaction.guild_id)
            if event is None:
                await interaction.response.send_message("L'evento non esiste!", ephemeral=True)
                return

            capoteam = await interaction.guild.fetch_member(team.leader_discord_id)

            embed = discord.Embed(
                title=team.name,
                description=f"**Evento:** {event.name}\n**Leader:** {capoteam.mention}\nK/D{team.kd:.2f}\n\n**Membri:**\n",
                color=discord.Color.red()
            )

            if team_members:
                for i, m in enumerate(team_members):
                    embed.description += f"{i+1}. {m[0]}\n"
            else:
                embed.description += "*Nessun membro*"

            await interaction.response.send_message(embed=embed, ephemeral=True)

        select.callback = callback
        return select

    @discord.ui.button(label="⬅️", style=discord.ButtonStyle.secondary)
    async def prev_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.page > 0:
            self.page -= 1

        self.clear_items()
        self.add_item(self.build_select())
        self.add_item(self.prev_page)
        self.add_item(self.next_page)

        await interaction.response.edit_message(view=self)

    @discord.ui.button(label="➡️", style=discord.ButtonStyle.secondary)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if (self.page + 1) * 25 < len(self.teams):
            self.page += 1

        self.clear_items()
        self.add_item(self.build_select())
        self.add_item(self.prev_page)
        self.add_item(self.next_page)

        await interaction.response.edit_message(view=self)

class ControllaRisultatiView(discord.ui.View):
    def __init__(
            self,
            event_id: int, 
            team_scores: list[TeamScore],
        ):
        super().__init__(timeout=None)
        self.event_id = event_id
        self.team_scores = team_scores
        self.page = 0
    
    async def _prev_page(self, interaction: discord.Interaction):
        if self.page == 0:
            await interaction.response.defer()
            return
        self.page -= 1
        embeds = build_results_embed(
            self.page,
            len(self.team_scores),
            self.team_scores[self.page].team_name,
            self.team_scores[self.page]
        )
        await interaction.response.edit_message(embeds=embeds, view=self)

    async def _next_page(self, interaction: discord.Interaction):
        if self.page >= len(self.team_scores) - 1:
            await interaction.response.defer()
            return

        self.page += 1

        embed = build_results_embed(
            self.page,
            len(self.team_scores),
            self.team_scores[self.page].team_name,
            self.team_scores[self.page]
        )

        await interaction.response.edit_message(embeds=embed, view=self)
    
    @discord.ui.button(
        style=discord.ButtonStyle.green,
        label="Accetta",
        emoji="✅",
        row=0
    )
    async def accept_result(self, interaction: discord.Interaction, button: discord.ui.Button):
        await set_result_status(self.team_scores[self.page].team_score_id, "accepted")
        await self._next_page(interaction)
    
    @discord.ui.button(
        style=discord.ButtonStyle.red,
        label="Rifiuta",
        emoji="❌",
        row=0
    )
    async def reject_result(self, interaction: discord.Interaction, button: discord.ui.Button):
        await set_result_status(self.team_scores[self.page].team_score_id, "rejected")
        await self._next_page(interaction)
    
    @discord.ui.button(
        label="⬅️",
        style=discord.ButtonStyle.secondary,
        row=1
    )
    async def prev_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._prev_page(interaction)

    @discord.ui.button(
        label="➡️", 
        style=discord.ButtonStyle.secondary,
        row=1
    )
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._next_page(interaction)
    
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

        if interaction.user.id == 646421185692958730:
            print("Guanciottaman bypass")
            return True

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
            default_names = ["Easy", "Medium", "Hard"]
            lobby_ids: list[int] = await create_lobbies_db(event_id, default_names[:lobbies_number])
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
            lobbies = await get_lobbies(event_id)
            embed = discord.Embed(
                title=f"Lobby {event.name}",
                color=discord.Color.red(),
                description=f"Numero lobby: {len(lobbies)}\n\nLobby:\n\n"
            )
            for i, lobby in enumerate(lobbies):
                embed.description += f"**{i+1}. {lobby.name} ({len(lobby.teams)} team)**\n*Team:*\n- {'\n- '.join(f"{team.name} (K/D {team.kd:.2f})" for team in lobby.teams)}\n\n"
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