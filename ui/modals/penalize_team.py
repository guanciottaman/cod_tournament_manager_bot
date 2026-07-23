import discord

from typing import Any

from services.team_service import penalize_team


class PenalizzaTeam(discord.ui.Modal, title="Penalizza team"):
    penalty_points: discord.ui.TextInput[Any] = discord.ui.TextInput(
        label="Punti di penalità",
        placeholder="Inserisci i punti da togliere al team...",
        min_length=1,
        max_length=4
    )
    def __init__(self, event_id: int, team_id: int):
        super().__init__()
        self.event_id = event_id
        self.team_id = team_id

    async def on_submit(self, interaction: discord.Interaction) -> None:
        points = self.penalty_points.value
        if not points.isdigit():
            await interaction.response.send_message("Valore non valido!", ephemeral=True)
            return
        await penalize_team(self.team_id, int(points))
        await interaction.response.send_message(f"Il team è stato penalizzato di {points} punti!", ephemeral=True)