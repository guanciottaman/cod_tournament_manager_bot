import discord

from models.placement_settings import PlacementSettings
from services.event_service import *
from ui.embeds.event_builders import build_event_embed, DEFAULT_PLACEMENT_POINTS, DEFAULT_PLACEMENT_MULTIPLIERS

class MultiplierModal(discord.ui.Modal, title="Moltiplicatori piazzamento"):
    first: discord.ui.TextInput[Any] = discord.ui.TextInput(
        label="1° posto",
        placeholder="Inserisci il moltiplicatore punti per il primo posto...",
        default=str(DEFAULT_PLACEMENT_MULTIPLIERS[(1, 1)])
    )
    second_third: discord.ui.TextInput[Any] = discord.ui.TextInput(
        label="2°-3° posto",
        placeholder="Inserisci il moltiplicatore punti per il posti 2° e 3°...",
        default=str(DEFAULT_PLACEMENT_MULTIPLIERS[(2, 3)])
    )
    fourt_sixth: discord.ui.TextInput[Any] = discord.ui.TextInput(
        label="4°-6° posto",
        placeholder="Inserisci il moltiplicatore punti per i posti da 4° a 6°...",
        default=str(DEFAULT_PLACEMENT_MULTIPLIERS[(4, 6)])
    )
    seventh_tenth: discord.ui.TextInput[Any] = discord.ui.TextInput(
        label="7°-10° posto",
        placeholder="Inserisci il moltiplicatore punti per i posti da 7° a 10°...",
        default=str(DEFAULT_PLACEMENT_MULTIPLIERS[(7, 10)])
    )
    eleventh_plus: discord.ui.TextInput[Any] = discord.ui.TextInput(
        label="11+° posto",
        placeholder="Inserisci il moltiplicatore punti per i posti dall'11° in poi...",
        default=str(DEFAULT_PLACEMENT_MULTIPLIERS[(11, None)])
    )
    def __init__(self, event_id: int, view: discord.ui.View):
            super().__init__()
            self.event_id = event_id
            self.view = view
    
    async def on_submit(self, interaction: discord.Interaction):
        if interaction.guild is None:
            return
        values: dict[tuple[int, int | None], str] = {
            (1, 1): self.first.value,
            (2, 3): self.second_third.value,
            (4, 6): self.fourt_sixth.value,
            (7, 10): self.seventh_tenth.value,
            (11, None): self.eleventh_plus.value
        }
        try:
            values_float = {
                k: float(v.replace(",", "."))
                for k, v in values.items()
            }
        except ValueError:
            await interaction.response.send_message(
                "Tutti i valori devono essere numeri!",
                ephemeral=True
            )
            return

        await set_placement_multipliers(self.event_id, values_float)
        event = await get_event_info(self.event_id, interaction.guild.id)
        if event is None:
            await interaction.response.send_message("C'è stato un errore!", ephemeral=True)
            return
        placement_multipliers = await get_placement_multipliers(self.event_id)
        placement_settings = PlacementSettings(
            "multipliers",
            multipliers=placement_multipliers
        )
        teams = await get_teams_by_event(self.event_id)
        embed = build_event_embed(event, interaction.guild, placement_settings, teams)
        await interaction.response.edit_message(embed=embed, view=self.view)

class PlacementModal(discord.ui.Modal, title="Moltiplicatori piazzamento"):

    first: discord.ui.TextInput[Any] = discord.ui.TextInput(
        label="1° posto",
        placeholder="Inserisci il punteggio per il primo posto...",
        default=str(DEFAULT_PLACEMENT_POINTS[1])
    )
    second: discord.ui.TextInput[Any] = discord.ui.TextInput(
        label="2° posto",
        placeholder="Inserisci il punteggio per il secondo posto...",
        default=str(DEFAULT_PLACEMENT_POINTS[2])
    )
    third: discord.ui.TextInput[Any] = discord.ui.TextInput(
        label="3° posto",
        placeholder="Inserisci il punteggio per il terzo posto...",
        default=str(DEFAULT_PLACEMENT_POINTS[3])
    )
    fourth: discord.ui.TextInput[Any] = discord.ui.TextInput(
        label="4° posto",
        placeholder="Inserisci il punteggio per il quarto posto...",
        default=str(DEFAULT_PLACEMENT_POINTS[4])
    )
    fifth: discord.ui.TextInput[Any] = discord.ui.TextInput(
        label="5° posto",
        placeholder="Inserisci il punteggio per il quinto posto...",
        default=str(DEFAULT_PLACEMENT_POINTS[5])
    )

    def __init__(self, event_id: int, view: discord.ui.View):
        super().__init__()
        self.event_id = event_id
        self.view = view

    async def on_submit(self, interaction: discord.Interaction):
        if interaction.guild is None:
            return
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
        event = await get_event_info(self.event_id, interaction.guild.id)
        if event is None:
            await interaction.response.send_message("C'è stato un errore!", ephemeral=True)
            return
        placement_points = await get_placement_points(self.event_id)
        placement_settings = PlacementSettings(
            "points",
            points=placement_points
        )
        teams = await get_teams_by_event(self.event_id)
        embed = build_event_embed(event, interaction.guild, placement_settings, teams)
        await interaction.response.edit_message(embed=embed, view=self.view)


class PlacementPointsButton(discord.ui.Button[discord.ui.View]):
    def __init__(self, event_id: int, view: discord.ui.View):
        super().__init__(
            label="Modifica punti piazzamento",
            style=discord.ButtonStyle.green
        )
        self.event_id = event_id
        self.modal_view = view

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(
            PlacementModal(self.event_id, self.modal_view)
        )

class PlacementMultipliersButton(discord.ui.Button[discord.ui.View]):
    def __init__(self, event_id: int, view: discord.ui.View):
        super().__init__(
            label="Modifica moltiplicatori piazzamento",
            style=discord.ButtonStyle.green
        )
        self.event_id = event_id
        self.modal_view = view

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(
            MultiplierModal(self.event_id, self.modal_view)
        )

class KillPointsModal(discord.ui.Modal, title="Punti per kill"):
    kill_points: discord.ui.TextInput[Any] = discord.ui.TextInput(
        label="Punti per kill",
        placeholder="es. 1, 2, 3...",
        max_length=2
    )

    def __init__(self, event_id: int, view: discord.ui.View):
        super().__init__()
        self.event_id = event_id
        self.view = view

    async def on_submit(self, interaction: discord.Interaction):
        if interaction.guild is None:
            return
        await set_kill_points_db(self.event_id, int(self.kill_points.value))
        placement_view = discord.ui.View()
        event = await get_event_info(self.event_id, interaction.guild.id)
        if event is None:
            return
        if event.placement_system == "points":
            placement_view.add_item(PlacementPointsButton(self.event_id, self.view))
        elif event.placement_system == "multipliers":
            placement_view.add_item(PlacementMultipliersButton(self.event_id, self.view))
        await interaction.response.send_message(
            f"# ATTENZIONE\nHai impostato i punti per le kill, ora clicca il bottone per impostare i {'punti' if event.placement_system == "points" else 'moltiplicatori'} di piazzamento!",
            view=placement_view,
            ephemeral=True
        )