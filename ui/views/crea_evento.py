import discord

from services.event_service import *
from ui.embeds.event_builders import build_event_embed
from ui.modals.placement_modal import KillPointsModal

class CreaEventoView(discord.ui.View):
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
    async def set_matches_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        await set_matches_number(self.event_id, int(select.values[0]))
        event = await get_event_info(self.event_id, interaction.guild_id)
        placement_points = await get_placement_points(self.event_id)
        teams = await get_teams_by_event(self.event_id)
        embed = build_event_embed(event, placement_points, teams)
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.select(
        placeholder="Numero giocatori per team",
        options=[
                discord.SelectOption(label=str(i), value=str(i))
                for i in range(3, 5)
            ]
    )
    async def set_players_per_team_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        await set_players_per_team(self.event_id, int(select.values[0]))
        event = await get_event_info(self.event_id, interaction.guild_id)
        placement_points = await get_placement_points(self.event_id)
        teams = await get_teams_by_event(self.event_id)
        embed = build_event_embed(event, placement_points, teams)
        await interaction.response.edit_message(embed=embed, view=self)
    
    @discord.ui.select(
        placeholder="Lobby Mode",
        options=[
            discord.SelectOption(
                label="Casuale",
                description="Le lobby saranno create casualmente",
                value="random",
                emoji="❌"
            ),
            discord.SelectOption(
                label="KD",
                description="Le lobby verranno create in base al rapporto K/D, ma non saranno bilanciate",
                value="kd",
                emoji="✅"    
            ),
            discord.SelectOption(
                label="KD Bilanciato",
                description="Le lobby verranno create in base al rapporto K/D, ma saranno bilanciate",
                value="kd_balanced",
                emoji="✅"    
            )
        ]
    )
    async def set_kd_mode_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        await set_lobby_mode(self.event_id, select.values[0])
        event = await get_event_info(self.event_id, interaction.guild_id)
        placement_points = await get_placement_points(self.event_id)
        teams = await get_teams_by_event(self.event_id)
        embed = build_event_embed(event, placement_points, teams)
        await interaction.response.edit_message(embed=embed, view=self)
    
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
    async def set_drop_worst_match_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        await set_drop_worst_match(self.event_id, int(select.values[0]))
        event = await get_event_info(self.event_id, interaction.guild_id)
        placement_points = await get_placement_points(self.event_id)
        teams = await get_teams_by_event(self.event_id)
        embed = build_event_embed(event, placement_points, teams)
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(
        label="Modifica punti",
        style=discord.ButtonStyle.secondary
    )
    async def edit_placement_points(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(KillPointsModal(self.event_id, self))
    

    @discord.ui.button(
        label="Crea evento",
        style=discord.ButtonStyle.green,
        row=4
    )
    async def create_event(self, interaction: discord.Interaction, button: discord.ui.Button):
        await set_event_status(self.event_id, "ready")
        await interaction.response.send_message("Evento creato!", ephemeral=True)