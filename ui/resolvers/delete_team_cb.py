import discord

from models.event import Event
from services.event_service import get_teams_by_event
from services.team_service import get_teams
from ui.views.team_selector import TeamsSelectorView

async def delete_team_callback(interaction: discord.Interaction, event: Event):
    event_id = event.event_id
    row = await get_teams_by_event(event_id)
    if not row:
        await interaction.response.send_message("Non sono presenti team iscritti a questo evento", ephemeral=True)
        return
    if event.status == "setup":
        teams = await get_teams(event_id, True)
    else:
        teams = await get_teams(event_id)
    embed = discord.Embed(
        title="Elimina team",
        color=discord.Colour.red(),
        description="Seleziona il team da eliminare"
    )
    await interaction.response.send_message(
        embed=embed,
        view=TeamsSelectorView(teams, event_id, "delete", interaction=interaction),
        ephemeral=True
    )