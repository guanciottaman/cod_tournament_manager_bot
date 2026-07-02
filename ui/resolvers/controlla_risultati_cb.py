import discord

import traceback

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
    try:
        event_id = event.event_id
        team_scores = await get_event_results(event_id, status)

        if not team_scores:
            await interaction.response.send_message(
                f"Non ci sono risultati con status {status}.",
                ephemeral=True
            )
            return

        if page < 1 or page > len(team_scores):
            await interaction.response.send_message(
                "Pagina non valida!",
                ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)

        current = team_scores[page - 1]

        warnings: list[str] = []
        if await has_duplicate_placement(current.team_score_id):
            warnings.append("QUESTO PIAZZAMENTO È DUPLICATO!")

        embeds = build_results_embed(
            page - 1,
            len(team_scores),
            current.team_name,
            current,
            warnings
        )

        if not embeds:
            await interaction.followup.send(
                "Errore generazione embed",
                ephemeral=True
            )
            return

        await interaction.followup.send(
            embeds=embeds,
            view=ControllaRisultatiView(event_id, team_scores, status, page - 1),
            ephemeral=True
        )

    except Exception as e:
        print("ERROR controlla_risultati:", e)
        traceback.print_exc()

        if interaction.response.is_done():
            await interaction.followup.send(
                "Errore interno.",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "Errore interno.",
                ephemeral=True
            )