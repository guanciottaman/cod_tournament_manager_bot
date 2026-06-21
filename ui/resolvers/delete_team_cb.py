import discord

from models.event import Event
from services.event_service import get_teams_by_event, get_team_from_leader, delete_team
from services.server_service import get_admin_role_id
from services.team_service import get_teams
from ui.views.team_selector import TeamsSelectorView

async def delete_team_callback(interaction: discord.Interaction, event: Event):
    event_id = event.event_id
    row = await get_teams_by_event(event_id)
    if not row:
        await interaction.response.send_message("Non sono presenti team iscritti a questo evento", ephemeral=True)
        return
    if event.status == "setup":
        teams = await get_teams(event_id, setup_mode=True)
    else:
        teams = await get_teams(event_id)
    embed = discord.Embed(
        title="Elimina team",
        color=discord.Colour.red(),
        description="Seleziona il team da eliminare"
    )
    await interaction.response.send_message(
        embed=embed,
        view=TeamsSelectorView(teams, event, "delete", interaction=interaction),
        ephemeral=True
    )


async def delete_team_callback_personal(interaction: discord.Interaction, event: Event):
    event_id = event.event_id
    team = await get_team_from_leader(event_id, interaction.user.id)
    if team is None:
        await interaction.response.send_message("Non hai nessun team iscritto a questo evento!", ephemeral=True)
        return
    if event.status not in ("ready", "setup"):
        await interaction.response.send_message("Non puoi eliminare il tuo team in questo momento!", ephemeral=True)
        return
    view = discord.ui.View()
    delete_btn = discord.ui.Button(
        label="Conferma",
        style=discord.ButtonStyle.red
    )
    async def delete_callback(interaction: discord.Interaction):
        await delete_team(team.team_id, event.status)
        await interaction.response.send_message("Team eliminato con successo!", ephemeral=True)
        admin_role_id = await get_admin_role_id(interaction.guild_id)
        admin_role = interaction.guild.get_role(admin_role_id)
        if admin_role is None:
            return
        for admin in admin_role.members:
            if admin.id == interaction.user.id:
                continue
            try:
                await admin.send(
                f"{interaction.user.name} ha eliminato il suo team {team.name} nell'evento {event.name}!"
            )
            except discord.Forbidden:
                continue
    delete_btn.callback = delete_callback
    view.add_item(delete_btn)
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