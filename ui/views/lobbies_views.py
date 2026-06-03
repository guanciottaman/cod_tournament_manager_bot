import discord

from ui.embeds.lobby_builders import *
from ui.modals.lobbies_names import LobbiesNamesModal
from services.lobby_service import *
from services.team_service import get_teams
from services.event_service import set_event_status


class LobbyConfigView(discord.ui.View):
    def __init__(self, event_id: int, teams_count: int, lobby_mode: str, lobby_ids: list[int], lobbies_number: int):
        super().__init__(timeout=None)

        self.event_id = event_id
        self.teams_count = teams_count
        self.lobby_mode = lobby_mode
        self.lobby_ids = lobby_ids
        self.lobbies_number = lobbies_number
        
        self._build_select()

    def _build_select(self):
        if self.lobby_mode in ("kd", "random_max"):
            return

        possible_lobbies: list[int] = []

        possible_lobbies.append(math.ceil(self.teams_count / 16))

        # prova anche +1 e +2 per flessibilità
        possible_lobbies.append(math.ceil(self.teams_count / 16) + 1)
        possible_lobbies.append(math.ceil(self.teams_count / 16) + 2)

        # limite superiore UI
        possible_lobbies = [c for c in possible_lobbies if 1 <= c <= 5]
        options = [
            discord.SelectOption(
                label=str(i),
                value=str(i),
                description=f"{i} lobby"
            )
            for i in possible_lobbies
        ]
        select = discord.ui.Select(
            placeholder="Numero lobby",
            min_values=1,
            max_values=1,
            options=options,
            row=0
        )
        async def set_lobbies_number_select(interaction: discord.Interaction):
            selected = int(select.values[0])

            self.lobbies_number = selected
            await interaction.response.defer(ephemeral=True)
            await set_lobbies_number(self.event_id, selected)

            self.lobby_ids, _ = await rebuild_lobbies(self.event_id, selected)

            embed = await build_config_lobbies_embed(
                self.event_id,
                self.lobbies_number,
                self.teams_count
            )

            await interaction.followup.edit_message(
                interaction.message.id,
                embed=embed,
                view=self
            )

        select.callback = set_lobbies_number_select
        self.add_item(select)


    @discord.ui.button(
        label="Modifica nomi",
        style=discord.ButtonStyle.secondary,
        row=1
    )
    async def edit_lobbies_names(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(
            LobbiesNamesModal(
                event_id=self.event_id,
                lobby_mode=self.lobby_mode,
                lobbies_number=self.lobbies_number,
                lobby_ids=self.lobby_ids,
                view=self,
                teams_count=self.teams_count,
                msg_id=interaction.message.id
            )
        )
    
    @discord.ui.button(
        label="Conferma",
        style=discord.ButtonStyle.green,
        row=2
    )
    async def start_event(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        event = await get_event_info(self.event_id, interaction.guild_id)

        if not event:
            await interaction.response.send_message("Evento non valido", ephemeral=True)
            return

        if event.status != "ready":
            await interaction.response.send_message(
                "Le lobby sono già state create.",
                ephemeral=True
            )
            return

        teams = await get_teams(self.event_id)
        lobbies_structure = generate_lobbies(
            teams,
            event.lobby_mode,
            self.lobbies_number
        )
        for lobby in lobbies_structure:
            lobby.sort(key=lambda t: t.kd or 0, reverse=True)
        if not lobbies_structure:
            await interaction.response.send_message(
                "Errore creazione lobby",
                ephemeral=True
            )
            return
        
        await apply_lobbies(self.lobby_ids, lobbies_structure)
        lobbies = await get_lobbies(self.event_id)

        await set_event_status(self.event_id, "setup")

        embed = await build_event_start_summary(lobbies)

        await interaction.edit_original_response(embed=embed, view=None)