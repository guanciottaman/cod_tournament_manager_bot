import discord

from models.event import Event
from services.event_service import has_duplicate_placement
from services.team_service import get_event_results
from ui.embeds.event_builders import build_results_embed
from ui.views.controlla_risultati import ControllaRisultatiView

async def controlla_risultati_callback(
    interaction: discord.Interaction,
    event: Event,
    status: str = "pending",
    page: int = 1
):
    event_id = event.event_id
    team_scores = await get_event_results(event_id, status)
    if not team_scores:
        await interaction.response.send_message(f"Non ci sono risultati con status {status}.", ephemeral=True)
        return
    if page < 1 or page > len(team_scores):
        await interaction.response.send_message("Pagina non valida!", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    warnings: list[str] = []
    current = team_scores[page - 1]
    if await has_duplicate_placement(current.team_score_id):
        warnings.append("Questo piazzamento è duplicato!")
    embeds = build_results_embed(
        page-1,
        len(team_scores),
        team_scores[0].team_name,
        team_scores[0],
        warnings
    )
    if embeds is None:
        await interaction.followup.send(
            "C'è stato un errore con il controllo dei risultati dell'embed",
            ephemeral=True
        )
        return
    await interaction.followup.send(
        embeds=embeds,
        view=ControllaRisultatiView(event_id, team_scores, status, page-1),
        ephemeral=True
    )