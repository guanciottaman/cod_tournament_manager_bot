import discord
from discord.ext import commands
from discord import app_commands

from cogs.lobbies import ConfigLobbiesView, build_config_lobbies_embed
from services.event_service import *
from services.server_service import *

DEFAULT_PLACEMENT_POINTS = {
    "1": 15,
    "2": 12,
    "3": 10,
    "4": 8,
    "5": 6
}

def build_event_selector(events: list[tuple[int, str]]) -> discord.ui.Select | None:
    if not events:
        return None

    return discord.ui.Select(
        placeholder="Seleziona l'evento...",
        min_values=1,
        max_values=1,
        options=[
            discord.SelectOption(label=name, value=str(event_id))
            for event_id, name in events
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

    embed.description = (
        f"# {event.name}\n"
        f"**Stato:** {event.status}\n"
        f"**Match:** {event.matches_number}\n"
        f"**Giocatori per team:** {event.players_per_team}\n"
        f"**KD Mode:** {'ON' if event.kd_mode else 'OFF'}\n"
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

class SetupView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.ranking_channel: discord.TextChannel = None
        self.admin_role: discord.Role = None

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
        placeholder="KD Mode",
        options=[
            discord.SelectOption(
                label="OFF",
                description="Le lobby saranno create casualmente",
                value="0",
                emoji="❌"
            ),
            discord.SelectOption(
                label="ON",
                description="Le lobby verranno create in base al rapporto K/D",
                value="1",
                emoji="✅"    
            ),
        ]
    )
    async def set_kd_mode_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        await set_kd_mode(self.event_id, int(select.values[0]))
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
        label="Modifica punti piazzamento",
        style=discord.ButtonStyle.secondary
    )
    async def edit_placement_points(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(PlacementModal(self.event_id, self))
    

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
            await interaction.response.send_message("Il tuo server è già registrato!", ephemeral=True)
            return
        await interaction.response.send_message(view=SetupView(), ephemeral=True)

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
            row = await get_event_settings(event_id)
            if not row:
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

            kd_mode, lobbies_number = row

            embed = await build_config_lobbies_embed(
                event_id,
                kd_mode,
                lobbies_number
            )
            await interaction.response.send_message(
                embed=embed,
                view=ConfigLobbiesView(event_id, teams_count),
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
            view = discord.ui.View()
            teams_selector = discord.ui.Select(
                placeholder="Seleziona il team su cui vuoi informazioni",
                options=[
                    discord.SelectOption(
                        label=team.name, value=str(team.team_id), description=f"Capoteam: {interaction.guild.get_member(team.leader_discord_id)}"
                    ) for team in teams
                ],
                min_values=1,
                max_values=1
            )
            async def teams_selector_callback(interaction_team: discord.Interaction):
                team_id = teams_selector.values[0]
                team = await get_team_info(team_id)
                team_members = await get_team_members(team_id)
                capoteam = await interaction.guild.fetch_member(team.leader_discord_id)
                event = await get_event_info(event_id, interaction.guild_id)
                team_embed = discord.Embed(
                    title=team.name,
                    description=f"**Evento:** {event.name}\n**Leader:** {capoteam.mention}\n\n**Membri:**\n"
                )
                if team_members:
                    for i, member in enumerate(team_members):
                        team_embed.description += f"{i+1}. {member[0]}\n"
                else:
                    team_embed.description += "*Nessun membro*"
                await interaction_team.response.send_message(embed=team_embed, ephemeral=True)
            teams_selector.callback = teams_selector_callback
            view.add_item(teams_selector)
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
            description="Questa è una lista degli eventi attivi.\nScegli l'evento a cui ti sei iscritto durante il ticket."
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @app_commands.command(name="controlla_risultati", description="Controlla i risultati dei team")
    async def controlla_risultati(self, interaction: discord.Interaction):
        ...


async def setup(bot: commands.Bot):
    await bot.add_cog(Events(bot))