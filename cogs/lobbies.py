import discord
from discord.ext import commands

from services.lobby_service import *
from services.event_service import *


async def build_config_lobbies_embed(event_id: int, kd_mode: bool, lobbies_number: int):
    names = await get_lobbies_names(event_id)
    defaults = ["Easy", "Medium", "Hard"]

    if not names:
        if kd_mode:
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
    def __init__(self, event_id: int, kd_mode: bool, lobbies_number: int):
        super().__init__()
        self.event_id = event_id
        self.kd_mode = kd_mode
        self.lobbies_number = lobbies_number

        self.inputs: list[discord.ui.TextInput] = []

        default_names = ["easy", "medium", "hard"]

        for i in range(lobbies_number):
            default = default_names[i] if kd_mode else f"Lobby {i+1}"

            name_input = discord.ui.TextInput(
                label=f"Lobby {i+1}",
                default=default,
                max_length=20
            )

            self.inputs.append(name_input)
            self.add_item(name_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        await create_lobbies_db(self.event_id, [inp.value for inp in self.inputs])
        await interaction.response.edit_message(
            embed=await build_config_lobbies_embed(self.event_id, self.kd_mode, self.lobbies_number)
        )

class AvviaEventoView(discord.ui.View):
    def __init__(self, event_id: int):
        super().__init__(timeout=None)
        self.event_id = event_id
    
    @discord.ui.button(
        label="Avvia evento",
        style=discord.ButtonStyle.green
    )
    async def start_event(self, interaction: discord.Interaction, button: discord.ui.Button):
        set_event_status(self.event_id, "running")
        await interaction.response.send_message("Evento avviato!", ephemeral=True)

class ConfigLobbiesView(discord.ui.View):
    def __init__(self, event_id: int, teams_count: int):
        super().__init__(timeout=None)
        self.event_id = event_id
        self.teams_count = teams_count
    
    @discord.ui.select(
        placeholder="Inserisci il numero di lobby...",
        min_values=1,
        max_values=1,
        options=[
            discord.SelectOption(label=str(i), value=str(i), description=f"Numero di lobby: {i}")
                for i in range(1, 4)
        ],
        row=0
    )
    async def set_lobbies_number_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        max_lobbies = self.teams_count // 2
        selected = int(select.values[0])

        if selected > max_lobbies:
            await interaction.response.send_message(
                f"Massimo lobby possibili con {self.teams_count} team: {max_lobbies}",
                ephemeral=True
            )
            return

        await set_lobbies_number(self.event_id, selected)
        await interaction.response.defer()
    
    @discord.ui.button(
        label="Modifica nomi delle lobby",
        style=discord.ButtonStyle.secondary,
        row=1
    )
    async def edit_lobbies_names(self, interaction: discord.Interaction, button: discord.ui.Button):
        row = await get_event_settings(self.event_id)
        if not row:
            kd_mode = False
            lobbies_number = 1
        else:
            kd_mode = row[0]
            lobbies_number = row[1]
        await interaction.response.send_modal(LobbiesNamesModal(self.event_id, kd_mode, lobbies_number))
    
    @discord.ui.button(
        label="Crea le lobby",
        style=discord.ButtonStyle.green,
        row=2
    )
    async def create_lobbies_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        row = await get_event_settings(self.event_id)

        if not row:
            await interaction.response.send_message(
                "Evento non configurato correttamente.",
                ephemeral=True
            )
            return

        kd_mode, lobbies_number = row

        lobbies = await create_lobbies(self.event_id, bool(kd_mode), lobbies_number)

        if not lobbies:
            await interaction.response.send_message(
                "Non ci sono team registrati.",
                ephemeral=True
            )
            return

        await recreate_lobbies(self.event_id, lobbies)

        embed = discord.Embed(
            title="Lobby create",
            color=discord.Color.blurple()
        )

        for lobby in lobbies:
            teams_text = "\n".join(f"- {t.name}" for t in lobby.teams) if lobby.teams else "*Nessun team*"

            embed.add_field(
                name=lobby.name,
                value=teams_text,
                inline=False
            )

        await interaction.response.send_message(
            embed=embed,
            view=AvviaEventoView(self.event_id),
            ephemeral=True
        )

class Lobbies(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        super().__init__()
        self.bot = bot


async def setup(bot: commands.Bot):
    await bot.add_cog(Lobbies(bot))