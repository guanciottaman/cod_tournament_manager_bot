import discord

from services.event_service import get_event_info, get_team_from_leader, delete_team
from services.team_service import (
    get_team_id, get_players_names, get_inserted_matches_count_per_team, get_team_kds, get_team_channel_id
)
from services.server_service import get_admin_role_id
from ui.modals.registra_team import RegistraTeamModal
from models.event import Event
from models.team import Team


class RegistraButton(discord.ui.Button[discord.ui.View]):
    def __init__(self, event_id: int):
        super().__init__(
            label="Registra il tuo team",
            emoji="📥",
            style=discord.ButtonStyle.green,
            custom_id=f"registra_team:registra:{event_id}"
        )
        self.event_id = event_id

    async def callback(self, interaction: discord.Interaction):
        if interaction.guild is None:
            return

        event = await get_event_info(
            self.event_id,
            interaction.guild.id
        )

        if event is None:
            await interaction.response.send_message(
                "Evento non trovato!",
                ephemeral=True
            )
            return

        await interaction.response.send_modal(
            RegistraTeamModal(
                event_id=self.event_id,
                members_number=event.players_per_team,
                is_kd_mode=event.lobby_mode in ("kd", "kd_balanced"),
                status=event.status
            )
        )


class ModificaButton(discord.ui.Button[discord.ui.View]):
    def __init__(self, event_id: int):
        super().__init__(
            label="Modifica il tuo team",
            emoji="✏️",
            row=1,
            style=discord.ButtonStyle.grey,
            custom_id=f"registra_team:modifica:{event_id}"
        )
        self.event_id = event_id

    async def callback(self, interaction: discord.Interaction):
        if interaction.guild is None:
            return
        event = await get_event_info(self.event_id, interaction.guild.id)
        if event is None:
            await interaction.response.send_message("C'è stato un errore!", ephemeral=True)
            return
        team_id = await get_team_id(self.event_id, interaction.user.id)
        if team_id is None:
            await interaction.response.send_message(
                "Non hai registrato nessun team per questo evento!\nUsa /registra_team per farlo.",
                ephemeral=True
            )
            return
        inserted_matches = await get_inserted_matches_count_per_team(self.event_id, team_id)
        if event.status == "running" and inserted_matches:
            await interaction.response.send_message(
                "Non puoi modificare il tuo team se hai già inserito risultati!",
                ephemeral=True
            )
            return
        players_names = await get_players_names(team_id)
        await interaction.response.send_modal(
            RegistraTeamModal(
                event_id=self.event_id,
                members_number=event.players_per_team,
                is_kd_mode=event.lobby_mode in ("kd", "kd_balanced"),
                status=event.status,
                edit_mode=True,
                team_id=team_id,
                players_names=players_names,
                kds=None if event.lobby_mode not in ("kd", "kd_balanced") else await get_team_kds(team_id)
            )
        )


class ConfermaEliminaTeamButton(discord.ui.Button[discord.ui.View]):
    def __init__(self, event: Event, team: Team):
        super().__init__(
            label="Conferma",
            style=discord.ButtonStyle.red
        )
        self.event = event
        self.team = team

    async def callback(self, interaction: discord.Interaction):
        if interaction.guild is None:
            return
        await delete_team(self.team.team_id, self.event.status)
        await interaction.response.send_message("Team eliminato con successo!", ephemeral=True)
        admin_role_id = await get_admin_role_id(interaction.guild.id)
        if admin_role_id is None:
            return
        admin_role = interaction.guild.get_role(admin_role_id)
        if admin_role is None:
            return
        if interaction.client.user is None:
            return
        for admin in admin_role.members:
            
            if admin.id == interaction.user.id or admin.id == interaction.client.user.id:
                continue
            try:
                await admin.send(
                f"{interaction.user.name} ha eliminato il suo team {self.team.name} nell'evento {self.event.name}!"
            )
            except (discord.Forbidden, discord.HTTPException):
                continue
        team_channel_id = await get_team_channel_id(self.event.event_id, self.team.team_id)
        if team_channel_id is not None:
            team_channel = interaction.guild.get_channel(team_channel_id)
            if team_channel is not None:
                await team_channel.delete()

class EliminaButton(discord.ui.Button[discord.ui.View]):
    def __init__(self, event_id: int):
        super().__init__(
            label="Elimina il tuo team",
            emoji="🗑️",
            row=2,
            style=discord.ButtonStyle.red,
            custom_id=f"registra_team:elimina:{event_id}"
        )
        self.event_id = event_id

    async def callback(self, interaction: discord.Interaction):
        if interaction.guild is None:
            return
        event = await get_event_info(self.event_id, interaction.guild.id)
        if event is None:
            await interaction.response.send_message("C'è stato un errore!", ephemeral=True)
            return
        team = await get_team_from_leader(self.event_id, interaction.user.id)
        if team is None:
            await interaction.response.send_message("Non hai nessun team iscritto a questo evento!", ephemeral=True)
            return
        if event.status not in ("ready", "setup"):
            await interaction.response.send_message("Non puoi eliminare il tuo team in questo momento!", ephemeral=True)
            return
        view = discord.ui.View()
        view.add_item(ConfermaEliminaTeamButton(event, team))
        embed = discord.Embed(
            title="Elimina team",
            color=discord.Color.red(),
            description=f"Sei sicuro di voler eliminare il tuo team {team.name}?"
        )
        await interaction.response.send_message(
            embed=embed,
            view=view,
            ephemeral=True
        )
        


class RegistraTeamView(discord.ui.View):
    def __init__(self, event_id: int):
        super().__init__(timeout=None)

        self.add_item(RegistraButton(event_id))
        self.add_item(ModificaButton(event_id))
        self.add_item(EliminaButton(event_id))

        