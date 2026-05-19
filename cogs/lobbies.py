import discord
from discord.ext import commands

from services.lobby_service import *
from services.event_service import *


async def build_config_lobbies_embed(event_id: int, lobby_mode: str, lobbies_number: int):
    names = await get_lobbies_names(event_id)
    defaults = ["Easy", "Medium", "Hard"]

    if not names:
        if lobby_mode in ("kd", "kd_balanced"):
            names_list = defaults[:lobbies_number]
        else:
            names_list = [f"Lobby {i+1}" for i in range(lobbies_number)]
    else:
        names_list = names

    embed = discord.Embed(
        title="Configura le lobby",
        description="Configura le lobby prima di avviare.\nI giocatori verranno inseriti automaticamente secondo le impostazioni da te selezionate\n\n",
        color=discord.Color.blurple()
    )

    lobby_text = "\n".join(
        f"{i+1}. {name}" for i, name in enumerate(names_list)
    )

    embed.description += (
        f"**Numero lobby:** {lobbies_number}\n\n"
        f"**Nomi lobby:**\n{lobby_text}"
    )

    return embed


class LobbiesNamesModal(discord.ui.Modal, title="Configura Lobby"):
    def __init__(self, event_id: int, lobby_mode: str, lobbies_number: int):
        super().__init__()
        self.event_id = event_id
        self.lobby_mode = lobby_mode
        self.lobbies_number = lobbies_number

        self.inputs: list[discord.ui.TextInput] = []

        default_names = ["easy", "medium", "hard"]

        for i in range(lobbies_number):
            default = default_names[i] if lobby_mode in ("kd", "kd_balanced") else f"Lobby {i+1}"

            name_input = discord.ui.TextInput(
                label=f"Lobby {i+1}",
                default=default,
                max_length=20
            )

            self.inputs.append(name_input)
            self.add_item(name_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        await create_lobbies_db(self.event_id, [inp.value for inp in self.inputs])
        await interaction.response.defer()
        await interaction.message.edit(
            embed=await build_config_lobbies_embed(self.event_id, self.lobby_mode, self.lobbies_number)
        )

class LobbyConfigView(discord.ui.View):
    def __init__(self, event_id: int, teams_count: int, lobby_mode: str, lobbies_number: int):
        super().__init__(timeout=None)

        self.event_id = event_id
        self.teams_count = teams_count
        self.lobby_mode = lobby_mode
        self.lobbies_number = lobbies_number

        self._build_select()

    async def set_lobbies_number_select(
        self,
        interaction: discord.Interaction,
        select: discord.ui.Select
    ):
        selected = int(select.values[0])
        self.lobbies_number = selected

        await set_lobbies_number(self.event_id, selected)

        embed = await build_config_lobbies_embed(
            self.event_id,
            self.lobby_mode,
            selected
        )

        await interaction.response.edit_message(
            embed=embed,
            view=self
        )

    def _build_select(self):
        if self.lobby_mode == "kd_sequential":
            return

        max_lobbies = self.teams_count // 2
        max_lobbies = max(1, max_lobbies)

        options = [
            discord.SelectOption(
                label=str(i),
                value=str(i),
                description=f"{i} lobby"
            )
            for i in range(1, max_lobbies + 1)
        ]
        select = discord.ui.Select(
            placeholder="Numero lobby",
            min_values=1,
            max_values=1,
            options=options,
            row=0
        )

        select.callback = self.set_lobbies_number_select
        self.add_item(select)


    @discord.ui.button(
        label="Modifica nomi",
        style=discord.ButtonStyle.secondary,
        row=1
    )
    async def edit_lobbies_names(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(
            LobbiesNamesModal(
                self.event_id,
                self.lobby_mode,
                self.lobbies_number
            )
        )
    
    @discord.ui.button(
        label="Avvia evento",
        style=discord.ButtonStyle.green,
        row=2
    )
    async def start_event(self, interaction: discord.Interaction, button: discord.ui.Button):

        event = await get_event_info(self.event_id, interaction.guild_id)

        if not event:
            await interaction.response.send_message("Evento non valido", ephemeral=True)
            return

        existing = await get_lobbies(self.event_id)
        if existing or event.status == "running":
            await interaction.response.send_message(
                "Le lobby sono già state create.",
                ephemeral=True
            )
            return

        lobbies = await create_lobbies(
            self.event_id,
            event.lobby_mode,
            event.lobbies_number
        )

        if not lobbies:
            await interaction.response.send_message("Errore creazione lobby", ephemeral=True)
            return

        await recreate_lobbies(self.event_id, lobbies)
        await set_event_status(self.event_id, "running")

        await interaction.response.edit_message(
            embed=discord.Embed(
                title="Evento avviato",
                description="Lobby create e evento partito.",
                color=discord.Color.green()
            ),
            view=None
        )

class Lobbies(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        super().__init__()
        self.bot = bot


async def setup(bot: commands.Bot):
    await bot.add_cog(Lobbies(bot))