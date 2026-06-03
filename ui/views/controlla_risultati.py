import discord

from ui.embeds.event_builders import build_results_embed
from ui.modals.registra_risultati import RegistraRisultatiModal
from models.team import TeamScore
from services.team_service import set_result_status, get_players_names, get_leader_discord_id

class ControllaRisultatiView(discord.ui.View):
    def __init__(
            self,
            event_id: int, 
            team_scores: list[TeamScore],
            page: int = 0
        ):
        super().__init__(timeout=None)
        self.event_id = event_id
        self.team_scores = team_scores
        self.page = page
        self.sync_buttons()
    
    def sync_buttons(self):
        if not self.team_scores:
            return

        current = self.team_scores[self.page]

        accept = reject = edit = True

        if current.status in ("accepted", "rejected"):
            accept = False
            reject = False
            edit = True

        for item in self.children:
            if isinstance(item, discord.ui.Button):
                if item.label == "Accetta":
                    item.disabled = not accept
                elif item.label == "Rifiuta":
                    item.disabled = not reject
                elif item.label == "Modifica":
                    item.disabled = not edit

    async def refresh(self, interaction: discord.Interaction):
        if not self.team_scores:
            await interaction.edit_original_response(
                content="Nessun risultato rimasto",
                view=None,
                embeds=[]
            )
            return
        embeds = build_results_embed(
            self.page,
            len(self.team_scores),
            self.team_scores[self.page].team_name,
            self.team_scores[self.page]
        )
        self.sync_buttons()
        await interaction.edit_original_response(embeds=embeds, view=self)
    
    async def prev_page_(self, interaction: discord.Interaction):
        if self.page == 0:
            await interaction.response.defer()
            return
        self.page -= 1
        embeds = build_results_embed(
            self.page,
            len(self.team_scores),
            self.team_scores[self.page].team_name,
            self.team_scores[self.page]
        )
        await interaction.response.edit_message(embeds=embeds, view=self)

    async def next_page_(self, interaction: discord.Interaction):
        if self.page >= len(self.team_scores) - 1:
            await interaction.response.defer()
            return

        self.page += 1

        embed = build_results_embed(
            self.page,
            len(self.team_scores),
            self.team_scores[self.page].team_name,
            self.team_scores[self.page]
        )

        await interaction.response.edit_message(embeds=embed, view=self)
    
    async def _handle(self, interaction: discord.Interaction, status: str):
        await set_result_status(self.team_scores[self.page].team_score_id, status)
        self.team_scores.pop(self.page)

        if not self.team_scores:
            await interaction.response.edit_message(
                content="Nessun risultato rimasto",
                view=None,
                embeds=[]
            )
            return

        self.page = min(self.page, len(self.team_scores) - 1)
        await self.refresh(interaction)

    @discord.ui.button(
        style=discord.ButtonStyle.green,
        label="Accetta",
        emoji="✅",
        row=0
    )
    async def accept_result(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        await self._handle(interaction, "accepted")
    
    @discord.ui.button(
        style=discord.ButtonStyle.red,
        label="Rifiuta",
        emoji="❌",
        row=0
    )
    async def reject_result(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        leader_id = await get_leader_discord_id(self.team_scores[self.page].team_id)
        if leader_id is None:
            await interaction.followup.send(
                "Non è stato possibile mandare il DM perché non è stato trovato l'id dell'utente",
                ephemeral=True
            )
        leader = interaction.guild.get_member(leader_id) if leader_id > 10e16 else None
        if leader is not None:
            embed = discord.Embed(
                title="Risultato rifiutato",
                color=discord.Color.red(),
                description=f"Il risultato del match {self.team_scores[self.page].match_number} è stato rifiutato.\nReinseriscilo o contatta gli amministratori per ricevere spiegazioni."
            )
            await leader.send(embed=embed)
        await self._handle(interaction, "rejected")
            
    @discord.ui.button(
        style=discord.ButtonStyle.blurple,
        label="Modifica",
        emoji="✏️",
        row=0
    )
    async def edit_result(self, interaction: discord.Interaction, button: discord.ui.Button):
        team_score = self.team_scores[self.page]
        team_names = await get_players_names(team_score.team_id)
        await interaction.response.send_modal(
            RegistraRisultatiModal(
                self.event_id,
                team_score.team_id,
                team_names,
                team_score.match_number,
                team_score.screenshots,
                mode="edit",
                player_score_id=team_score.team_score_id,
                parent_view=self,
                interaction=interaction
            )
        )
    
    @discord.ui.button(
        label="⬅️",
        style=discord.ButtonStyle.secondary,
        row=1
    )
    async def prev_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.prev_page_(interaction)

    @discord.ui.button(
        label="➡️", 
        style=discord.ButtonStyle.secondary,
        row=1
    )
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.next_page_(interaction)