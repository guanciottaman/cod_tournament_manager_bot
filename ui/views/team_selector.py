import discord

from models.team import Team
from services.team_service import *
from services.event_service import *
from services.lobby_service import get_lobbies, switch_team_lobby
from ui.modals.penalize_team import PenalizzaTeam

class TeamsSelectorView(discord.ui.View):
    def __init__(
            self,
            teams: list[Team],
            event_id: int,
            mode: str = "info",
            page: int = 0,
            interaction: discord.Interaction | None = None
        ):
        super().__init__(timeout=180)
        self.teams = teams
        self.event_id = event_id
        self.mode = mode
        self.page = page
        self.interaction = interaction
        self.add_item(self.build_select())

    def get_leader_name(self, interaction: discord.Interaction, leader_id: int) -> str:
        member = interaction.guild.get_member(leader_id)
        if member is None:
            return "Unknown"
        return member.display_name

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
                    description=f"Capoteam: {self.get_leader_name(self.interaction, t.leader_discord_id)}"
                )
                for t in page_teams
            ],
            row=0,
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
            

            embed = discord.Embed(
                title=team.name,
                color=discord.Color.blue()
            )
            leader_discord_id = team.leader_discord_id
            capoteam = interaction.guild.get_member(leader_discord_id) if leader_discord_id > 10e16 else None

            emb_description = f"**Evento:** {event.name}\n**Leader:** {capoteam.mention if capoteam is not None else leader_discord_id}\nK/D {team.kd:.2f}\n\n**Membri:**\n"

            if team_members:
                for i, m in enumerate(team_members):
                    emb_description += f"{i+1}. {m[0]}\n"
            else:
                emb_description += "*Nessun membro*"
            embed.description = emb_description
            if self.mode == "info":
                await interaction.response.send_message(embed=embed, ephemeral=True)
            elif self.mode == "switch":
                view = discord.ui.View()
                sposta_team_btn = discord.ui.Button(label="Sposta team", style=discord.ButtonStyle.blurple)
                async def switch_team_callback(interaction: discord.Interaction):
                    embed = discord.Embed(
                        title="Sposta team", 
                        color=discord.Color.blurple(),
                        description=f"Scegli la lobby in cui spostare il team **{team.name}**"
                    )
                    lobbies = await get_lobbies(self.event_id)
                    view = discord.ui.View()
                    lobby_selector = discord.ui.Select(
                        placeholder="Lobby in cui spostare il team...",
                        options=[
                            discord.SelectOption(
                                label=lobby.name, value=str(lobby.lobby_id)
                            ) for lobby in lobbies
                        ],
                        min_values=1,
                        max_values=1
                    )
                    async def lobby_selector_callback(interaction: discord.Interaction):
                        lobby = next(
                            (l for l in lobbies if l.lobby_id == int(lobby_selector.values[0])),
                            None
                        )
                        if lobby is None:
                            await interaction.response.send_message("La lobby non esiste!", ephemeral=True)
                            return
                        if team.lobby == lobby.lobby_id:
                            await interaction.response.send_message(
                                "Il team è già in questa lobby.",
                                ephemeral=True
                            )
                            return
                        await switch_team_lobby(team.team_id, lobby.lobby_id)
                        await interaction.response.send_message(
                            f"Il team {team.name} è stato spostato nella lobby {lobby.name}",
                            ephemeral=True
                        )
                    lobby_selector.callback = lobby_selector_callback
                    view.add_item(lobby_selector)
                    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
                sposta_team_btn.callback = switch_team_callback
                view.add_item(sposta_team_btn)
                await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            elif self.mode == "penalize":
                await interaction.response.send_modal(PenalizzaTeam(self.event_id, team.team_id))
            elif self.mode == "delete":
                await delete_team(team_id, event.status)
                await interaction.response.send_message("Team eliminato con successo!", ephemeral=True)
        select.callback = callback
        return select

    @discord.ui.button(label="⬅️", style=discord.ButtonStyle.secondary, row=1)
    async def prev_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.page > 0:
            self.page -= 1

        self.clear_items()
        self.add_item(self.build_select())
        self.add_item(self.prev_page)
        self.add_item(self.next_page)

        await interaction.response.edit_message(view=self)

    @discord.ui.button(label="➡️", style=discord.ButtonStyle.secondary, row=1)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if (self.page + 1) * 25 < len(self.teams):
            self.page += 1

        self.clear_items()
        self.add_item(self.build_select())
        self.add_item(self.prev_page)
        self.add_item(self.next_page)

        await interaction.response.edit_message(view=self)