import discord

from services.event_service import *
from ui.embeds.event_builders import build_event_embed, build_event_channels_embed
from ui.modals.placement_modal import KillPointsModal
from ui.views.registra_team_view import RegistraTeamView
from ui.views.event_channels_view import EventChannelsView

class CreaEventoView1(discord.ui.View):
    def __init__(self, event_id: int):
        super().__init__(timeout=None)
        self.event_id = event_id

    @discord.ui.select(
        placeholder="Numero match",
        options=[
                discord.SelectOption(label=str(i), value=str(i))
                for i in range(3, 6)
            ],
    )
    async def set_matches_select(self, interaction: discord.Interaction, select: discord.ui.Select[Any]):
        if interaction.guild is None:
            return
        await set_matches_number(self.event_id, int(select.values[0]))
        event = await get_event_info(self.event_id, interaction.guild.id)
        if event is None:
            await interaction.response.send_message("C'è stato un errore!", ephemeral=True)
            return
        placement_settings = await get_placement_settings(self.event_id)
        teams = await get_teams_by_event(self.event_id)
        embed = build_event_embed(event, interaction.guild, placement_settings, teams)
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.select(
        placeholder="Numero giocatori per team",
        options=[
                discord.SelectOption(label=str(i), value=str(i))
                for i in range(3, 5)
            ]
    )
    async def set_players_per_team_select(self, interaction: discord.Interaction, select: discord.ui.Select[Any]):
        if interaction.guild is None:
            return
        await set_players_per_team(self.event_id, int(select.values[0]))
        event = await get_event_info(self.event_id, interaction.guild.id)
        if event is None:
            return
        placement_settings = await get_placement_settings(self.event_id)
        teams = await get_teams_by_event(self.event_id)
        embed = build_event_embed(event, interaction.guild, placement_settings, teams)
        await interaction.response.edit_message(embed=embed, view=self)
    
    @discord.ui.select(
        placeholder="Lobby Mode",
        options=[
            discord.SelectOption(
                label="Casuale",
                description="Le lobby saranno create casualmente",
                value="random",
                emoji="🎲"
            ),
            discord.SelectOption(
                label="Casuale (16 Team/lobby)",
                description="Le lobby saranno create casualmente",
                value="random_max",
                emoji="🎯"
            ),
            discord.SelectOption(
                label="KD (16 Team/lobby)",
                description="Le lobby verranno create in base al rapporto K/D, ma si limiteranno a 16 team",
                value="kd",
                emoji="📊"    
            ),
            discord.SelectOption(
                label="KD Bilanciato",
                description="Le lobby verranno create in base al rapporto K/D, ma saranno bilanciate",
                value="kd_balanced",
                emoji="⚖️"    
            )
        ]
    )
    async def set_kd_mode_select(self, interaction: discord.Interaction, select: discord.ui.Select[Any]):
        if interaction.guild is None:
            return
        await set_lobby_mode(self.event_id, select.values[0])
        event = await get_event_info(self.event_id, interaction.guild.id)
        if event is None:
            await interaction.response.send_message("C'è stato un errore!", ephemeral=True)
            return
        placement_settings = await get_placement_settings(self.event_id)
        teams = await get_teams_by_event(self.event_id)
        embed = build_event_embed(event, interaction.guild, placement_settings, teams)
        await interaction.response.edit_message(embed=embed, view=self)
    
    @discord.ui.button(
        label="➡️",
        style=discord.ButtonStyle.blurple,
        row=3
    )
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button[Any]):
        if interaction.guild is None:
            return
        event = await get_event_info(self.event_id, interaction.guild.id)
        if event is None:
            await interaction.response.send_message("C'è stato un errore!", ephemeral=True)
            return
        placement_settings = await get_placement_settings(self.event_id)
        teams = await get_teams_by_event(self.event_id)
        embed = build_event_embed(event, interaction.guild, placement_settings, teams)
        await interaction.response.edit_message(
            embed=embed,
            view=CreaEventoView2(self.event_id)
        )

    @discord.ui.button(
        label="Modifica punti",
        style=discord.ButtonStyle.secondary,
        row=3
    )
    async def edit_placement_points(self, interaction: discord.Interaction, button: discord.ui.Button[Any]):
        await interaction.response.send_modal(KillPointsModal(self.event_id, self))
    

    @discord.ui.button(
        label="Crea evento",
        style=discord.ButtonStyle.green,
        row=4
    )
    async def create_event(self, interaction: discord.Interaction, button: discord.ui.Button[Any]):
        view = discord.ui.View()
        select: discord.ui.ChannelSelect[Any] = discord.ui.ChannelSelect(
            channel_types=[discord.ChannelType.text],
            placeholder="Seleziona canale registrazione...",
            min_values=1,
            max_values=1,
            row=0
        )
        async def select_callback(interaction: discord.Interaction):
            if interaction.guild is None:
                return
            await interaction.response.defer(ephemeral=True)
            c_id = select.values[0].id
            channel = interaction.guild.get_channel(c_id)
            if not isinstance(channel, discord.TextChannel):
                await interaction.followup.send(
                    "Devi selezionare un canale testuale!",
                    ephemeral=True
                )
                return
            await channel.send(view=RegistraTeamView(self.event_id))
            await set_event_status(self.event_id, "ready")
            await interaction.followup.send(f"Evento creato con successo!", ephemeral=True)
        select.callback = select_callback
        view.add_item(select)
        embed = discord.Embed(
            title="Seleziona canale registrazione",
            color=discord.Color.blue(),
            description="Seleziona il canale dove verrà mandato il messaggio per permettere ai team di registrarsi"
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class CreaEventoView2(discord.ui.View):
    def __init__(self, event_id: int):
        super().__init__(timeout=None)
        self.event_id = event_id

    @discord.ui.select(
        placeholder="Scarta la partita peggiore?",
        options=[
            discord.SelectOption(
                label="OFF",
                description="Tutte le partite saranno conteggiate",
                value="0",
                emoji="❌"
            ),
            discord.SelectOption(
                label="ON",
                description="La peggiore partita di ogni squadra verrà scartata",
                value="1",
                emoji="✅"    
            ),
        ]
    )
    async def set_drop_worst_match_select(self, interaction: discord.Interaction, select: discord.ui.Select[Any]):
        if interaction.guild is None:
            return
        await set_drop_worst_match(self.event_id, bool(select.values[0]))
        event = await get_event_info(self.event_id, interaction.guild.id)
        if event is None:
            await interaction.response.send_message("C'è stato un errore!", ephemeral=True)
            return
        placement_settings = await get_placement_settings(self.event_id)
        teams = await get_teams_by_event(self.event_id)
        embed = build_event_embed(event, interaction.guild, placement_settings, teams)
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.select(
        cls=discord.ui.ChannelSelect,
        channel_types=[discord.ChannelType.category],
        placeholder="Seleziona la categoria dei ticket dei team",
        min_values=1,
        max_values=1,
        row=1
    )
    async def set_category_channel_select(self, interaction: discord.Interaction, select: discord.ui.ChannelSelect[Any]):
        if interaction.guild is None:
            return
        await set_category_channel_id(self.event_id, select.values[0].id)
        event = await get_event_info(self.event_id, interaction.guild.id)
        if event is None:
            await interaction.response.send_message("C'è stato un errore!", ephemeral=True)
            return
        placement_settings = await get_placement_settings(self.event_id)
        teams = await get_teams_by_event(self.event_id)
        embed = build_event_embed(event, interaction.guild, placement_settings, teams)
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.select(
        placeholder="Sistema di piazzamento",
        options=[
            discord.SelectOption(
                label="Punti",
                description="Verranno aggiunti ai punti delle kill i punti del posizionamento",
                emoji="📊",
                value="points"
            ),
            discord.SelectOption(
                label="Moltiplicatori",
                description="Verranno moltiplicati i punti delle kill in base al posizionamento",
                emoji="✖️",
                value="multipliers"
            )
        ],
        min_values=1,
        max_values=1
    )
    async def set_placement_system(self, interaction: discord.Interaction, select: discord.ui.Select[Any]):
        if interaction.guild is None:
            return
        selected = select.values[0]
        await set_placement_system(self.event_id, selected)
        event = await get_event_info(self.event_id, interaction.guild.id)
        if event is None:
            await interaction.response.send_message("C'è stato un errore!", ephemeral=True)
            return
        placement_settings = await get_placement_settings(self.event_id)
        teams = await get_teams_by_event(self.event_id)
        embed = build_event_embed(event, interaction.guild, placement_settings, teams)
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(
        label="⬅️",
        style=discord.ButtonStyle.blurple,
        row=3
    )
    async def previous_page(self, interaction: discord.Interaction, button: discord.ui.Button[Any]):
        if interaction.guild is None:
            return
        event = await get_event_info(self.event_id, interaction.guild.id)
        if event is None:
            await interaction.response.send_message("C'è stato un errore!", ephemeral=True)
            return
        placement_settings = await get_placement_settings(self.event_id)
        teams = await get_teams_by_event(self.event_id)
        embed = build_event_embed(event, interaction.guild, placement_settings, teams)
        await interaction.response.edit_message(
            embed=embed,
            view=CreaEventoView1(self.event_id)
        )

    @discord.ui.button(
        label="Modifica punti",
        style=discord.ButtonStyle.secondary,
        row=3
    )
    async def edit_placement_points(self, interaction: discord.Interaction, button: discord.ui.Button[Any]):
        await interaction.response.send_modal(KillPointsModal(self.event_id, self))

    @discord.ui.button(
        label="Crea evento",
        style=discord.ButtonStyle.green,
        row=4
    )
    async def create_event(self, interaction: discord.Interaction, button: discord.ui.Button[Any]):
        category_channel_id = await get_category_channel_id(self.event_id)
        if category_channel_id is None:
            await interaction.response.send_message("Non hai ancora impostato una categoria per i ticket dei team!", ephemeral=True)
            return
        embed = build_event_channels_embed()
        await interaction.response.send_message(
            embed=embed,
            view=EventChannelsView(self.event_id),
            ephemeral=True
        )