import discord

from models.team import Team
from services.team_service import *
from services.event_service import *

class TeamsSelectorView(discord.ui.View):
    def __init__(self, teams: list[Team], event_id: int, page: int = 0):
        super().__init__(timeout=180)
        self.teams = teams
        self.event_id = event_id
        self.page = page
        self.add_item(self.build_select())

    def build_select(self):
        start = self.page * 25
        end = start + 25
        page_teams = self.teams[start:end]

        select = discord.ui.Select(
            placeholder=f"Seleziona team (pagina {self.page + 1})",
            options=[
                discord.SelectOption(
                    label=t.name,
                    value=str(t.team_id),
                    description=f"Capoteam: {t.leader_discord_id}"
                )
                for t in page_teams
            ],
            min_values=1,
            max_values=1
        )

        async def callback(interaction: discord.Interaction):
            team_id = int(select.values[0])

            team = await get_team_info(team_id)
            if team is None:
                await interaction.response.send_message("Il team non esiste!", ephemeral=True)
                return
            team_members = await get_team_members(team_id)
            event = await get_event_info(self.event_id, interaction.guild_id)
            if event is None:
                await interaction.response.send_message("L'evento non esiste!", ephemeral=True)
                return

            capoteam = await interaction.guild.fetch_member(team.leader_discord_id)

            embed = discord.Embed(
                title=team.name,
                color=discord.Color.red()
            )

            emb_description = f"**Evento:** {event.name}\n**Leader:** {capoteam.mention}\nK/D{team.kd:.2f}\n\n**Membri:**\n",

            if team_members:
                for i, m in enumerate(team_members):
                    emb_description += f"{i+1}. {m[0]}\n"
            else:
                emb_description += "*Nessun membro*"
            embed.description = emb_description
            await interaction.response.send_message(embed=embed, ephemeral=True)

        select.callback = callback
        return select

    @discord.ui.button(label="⬅️", style=discord.ButtonStyle.secondary)
    async def prev_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.page > 0:
            self.page -= 1

        self.clear_items()
        self.add_item(self.build_select())
        self.add_item(self.prev_page)
        self.add_item(self.next_page)

        await interaction.response.edit_message(view=self)

    @discord.ui.button(label="➡️", style=discord.ButtonStyle.secondary)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if (self.page + 1) * 25 < len(self.teams):
            self.page += 1

        self.clear_items()
        self.add_item(self.build_select())
        self.add_item(self.prev_page)
        self.add_item(self.next_page)

        await interaction.response.edit_message(view=self)