import discord

from services.event_service import *
from ui.embeds.event_builders import build_event_embed, DEFAULT_PLACEMENT_POINTS

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
        btn = discord.ui.Button(style=discord.ButtonStyle.green, label="Modifica punti piazzamento")
        async def btn_callback(ak_interaction: discord.Interaction):
            await ak_interaction.response.send_modal(PlacementModal(self.event_id, self.view))
        btn.callback = btn_callback
        placement_view.add_item(btn)
        await interaction.response.send_message(
            "# ATTENZIONE\nHai impostato i punti per le kill, ora clicca il bottone per impostare i punti di piazzamento!",
            view=placement_view,
            ephemeral=True
        )