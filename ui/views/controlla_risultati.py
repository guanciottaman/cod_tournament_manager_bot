import discord

from ui.embeds.event_builders import build_results_embed
from ui.modals.registra_risultati import RegistraRisultatiModal
from models.team import TeamScore
from services.event_service import get_leader_ids, get_team_from_leader, has_duplicate_placement
from services.team_service import set_result_status, get_players_names, get_leader_discord_id, get_event_results

class ControllaRisultatiView(discord.ui.View):
    def __init__(
            self,
            event_id: int, 
            team_scores: list[TeamScore],
            status: str,
            page: int = 0
        ):
        super().__init__(timeout=None)
        self.event_id = event_id
        self.team_scores = team_scores
        self.status = status
        self.page = page
        self.sync_buttons()
    
    def sync_buttons(self):
        if not self.team_scores:
            return

        current = self.team_scores[self.page]

        accept = reject = edit = True

        if current.status == "accepted":
            accept = False
            reject = True
            edit = True
        elif current.status == "rejected":
            accept = True
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
        warnings: list[str] = []
        if await has_duplicate_placement(self.team_scores[self.page].team_score_id):
            warnings.append("Questo piazzamento è duplicato!")
        embeds = build_results_embed(
            self.page,
            len(self.team_scores),
            self.team_scores[self.page].team_name,
            self.team_scores[self.page],
            warnings
        )
        self.sync_buttons()
        await interaction.edit_original_response(embeds=embeds, view=self)
    
    async def prev_page_(self, interaction: discord.Interaction):
        if self.page == 0:
            await interaction.response.defer()
            return
        self.page -= 1
        warnings: list[str] = []
        if await has_duplicate_placement(self.team_scores[self.page].team_score_id):
            warnings.append("Questo piazzamento è duplicato!")
        embeds = build_results_embed(
            self.page,
            len(self.team_scores),
            self.team_scores[self.page].team_name,
            self.team_scores[self.page],
            warnings
        )
        await interaction.response.edit_message(embeds=embeds, view=self)

    async def next_page_(self, interaction: discord.Interaction):
        if self.page >= len(self.team_scores) - 1:
            await interaction.response.defer()
            return

        self.page += 1
        warnings: list[str] = []
        if await has_duplicate_placement(self.team_scores[self.page].team_score_id):
            warnings.append("Questo piazzamento è duplicato!")
        embed = build_results_embed(
            self.page,
            len(self.team_scores),
            self.team_scores[self.page].team_name,
            self.team_scores[self.page],
            warnings
        )

        await interaction.response.edit_message(embeds=embed, view=self)
    
    async def _handle(self, interaction: discord.Interaction, status: str):
        rows = await set_result_status(self.team_scores[self.page].team_score_id, status, self.team_scores[self.page].status)
        if rows == 0:
            await interaction.response.send_message(
                "Questo risultato è già stato modificato da qualcun altro.",
                ephemeral=True
            )
            await self.refresh(interaction)
            return
        self.team_scores.pop(self.page)

        if not self.team_scores:
            await interaction.edit_original_response(
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
        style=discord.ButtonStyle.blurple,
        label="Modifica",
        emoji="✏️",
        row=0
    )
    async def edit_result(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.team_scores:
            await interaction.response.send_message(
                "Nessun risultato disponibile.",
                ephemeral=True
            )
            return
        if self.page >= len(self.team_scores):
            self.page = max(0, len(self.team_scores) - 1)
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
                team_score_id=team_score.team_score_id,
                parent_view=self,
                interaction=interaction
            )
        )

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
                description=f"Il risultato del match {self.team_scores[self.page].match_number} è stato rifiutato.\nContatta gli amministratori per ricevere spiegazioni."
            )
            await leader.send(embed=embed)
        await self._handle(interaction, "rejected")
            
    
    
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
    
    @discord.ui.button(
        label="Filtra per capoteam",
        style=discord.ButtonStyle.blurple,
        row=2
    )
    async def filter_by_leader(self, interaction: discord.Interaction, button: discord.ui.Button):
        leader_ids = await get_leader_ids(self.event_id)
        if not leader_ids:
            await interaction.response.send_message("Non ci sono capoteam in questo evento!", ephemeral=True)
            return
        leaders: list[discord.Member] = []
        for l in leader_ids:
            member = interaction.guild.get_member(l)
            if member is None:
                continue
            leaders.append(member)
        embed = discord.Embed(
            title="Filtra per capoteam",
            color=discord.Color.blue(),
            description="Seleziona il capoteam di cui vuoi controllare i risultati"
        )
        
        view = discord.ui.View()
        member_select = discord.ui.Select(
            placeholder="Seleziona il capoteam...",
            min_values=1,
            max_values=1,
            options=[
                discord.SelectOption(
                    label=l.name,
                    value=str(l.id)
                ) for l in leaders
            ]
        )
        async def member_select_callback(interaction: discord.Interaction):
            team = await get_team_from_leader(self.event_id, int(member_select.values[0]))
            if team is None:
                await interaction.response.send_message(f"Il team del capoteam selezionato non esiste", ephemeral=True)
                return
            scores = await get_event_results(self.event_id, self.status, team)
            if not scores:
                await interaction.response.send_message(
                    "Nessun risultato per questo team",
                    ephemeral=True
                )
                return
            self.team_scores = scores
            self.page = 0
            self.sync_buttons()
            warnings: list[str] = []
            if await has_duplicate_placement(self.team_scores[self.page].team_score_id):
                warnings.append("Questo piazzamento è duplicato!")
            embeds = build_results_embed(0, len(self.team_scores), team.name, self.team_scores[0], warnings)
            await interaction.response.edit_message(
                embeds=embeds,
                view=self
            )
        member_select.callback = member_select_callback
        view.add_item(member_select)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @discord.ui.button(
        label="Resetta filtro",
        style=discord.ButtonStyle.red,
        row=2
    )
    async def reset_filter(self, interaction: discord.Interaction, button: discord.ui.Button):
        scores = await get_event_results(self.event_id, self.status)
        if not scores:
            await interaction.response.send_message(
                "Nessun risultato trovato",
                ephemeral=True
            )
            return
        self.team_scores = scores
        self.page = 0
        self.sync_buttons()
        warnings: list[str] = []
        if await has_duplicate_placement(self.team_scores[self.page].team_score_id):
            warnings.append("Questo piazzamento è duplicato!")
        embeds = build_results_embed(
            0,
            len(scores),
            self.team_scores[0].team_name,
            self.team_scores[0],
            warnings
        )

        await interaction.response.edit_message(
            embeds=embeds,
            view=self
        )