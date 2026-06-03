import discord

from services.lobby_service import *
from ui.embeds.lobby_builders import *

class LobbiesNamesModal(discord.ui.Modal, title="Configura Lobby"):
    def __init__(
            self,
            event_id: int,
            lobby_mode: str,
            lobbies_number: int,
            lobby_ids: list[int],
            view: discord.ui.View,
            teams_count: int,
            msg_id: int
        ):
        super().__init__()
        self.event_id = event_id
        self.lobby_mode = lobby_mode
        self.lobbies_number = lobbies_number
        self.lobby_ids = lobby_ids
        self.view = view
        self.teams_count = teams_count
        self.msg_id = msg_id

        self.inputs: list[discord.ui.TextInput] = []


        for i in range(lobbies_number):
            default = f"{i+1}"

            name_input = discord.ui.TextInput(
                label=f"{i+1}",
                default=default,
                max_length=20
            )

            self.inputs.append(name_input)
            self.add_item(name_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        await update_lobbies_db(self.event_id, self.lobby_ids, [inp.value for inp in self.inputs])
        await interaction.followup.edit_message(
            self.msg_id,
            embed=await build_config_lobbies_embed(self.event_id, self.lobbies_number, self.teams_count),
            view=self.view
        )