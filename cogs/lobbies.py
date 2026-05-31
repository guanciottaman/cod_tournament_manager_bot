import discord
from discord.ext import commands

from services.lobby_service import *
from services.event_service import *


async def build_config_lobbies_embed(event_id: int, lobbies_number: int, teams_count: int):
    names = await get_lobbies_names(event_id)
    defaults = ["Easy", "Medium", "Hard"]

    if names:
        names_list = names
    else:
        names_list = [
            (defaults[i] if i < 3 else f"Lobby {i+1}")
            for i in range(lobbies_number)
        ]

    embed = discord.Embed(
        title="Configura le lobby",
        description=f"Configura le lobby prima di avviare.\nI giocatori verranno inseriti automaticamente secondo le impostazioni da te selezionate\nTeam attualmente iscritti: {teams_count}\n\n",
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


async def build_event_start_summary(lobbies: list[Lobby]) -> discord.Embed:
    embed = discord.Embed(
        title="Evento avviato",
        color=discord.Color.green()
    )

    embed.add_field(
        name="Numero lobby",
        value=str(len(lobbies)),
        inline=True
    )

    description_lines: list[str] = []

    for i, lobby in enumerate(lobbies, start=1):
        description_lines.append(
            f"**{i}.{lobby.name}** → {len(lobby.teams)} team"
        )

    embed.add_field(
        name="Distribuzione team",
        value="\n".join(description_lines),
        inline=False
    )

    return embed


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
        await interaction.response.defer(ephemeral=True)
        await update_lobbies_db(self.event_id, self.lobby_ids, [inp.value for inp in self.inputs])
        await interaction.followup.edit_message(
            self.msg_id,
            embed=await build_config_lobbies_embed(self.event_id, self.lobbies_number, self.teams_count),
            view=self.view
        )

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
        if self.lobby_mode == "kd":
            return

        max_lobbies = self.teams_count // 2
        max_lobbies = max(1, max_lobbies)
        max_lobbies = min(5, max_lobbies)

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
        label="Avvia evento",
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
        print(teams)
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
        print(lobbies)
        
        await set_event_status(self.event_id, "running")

        embed = await build_event_start_summary(lobbies)

        await interaction.edit_original_response(embed=embed, view=None)


class Lobbies(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        super().__init__()
        self.bot = bot


async def setup(bot: commands.Bot):
    await bot.add_cog(Lobbies(bot))