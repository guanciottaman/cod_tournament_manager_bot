import discord

from typing import Any

from ui.embeds.event_builders import build_results_embed
from ui.modals.registra_risultati import RegistraRisultatiModal
from models.team import TeamScore
from services.event_service import get_leader_ids, get_team_from_leader, get_duplicate_team_score
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
        self.leader_page = 0
        self.leaders_per_page = 25
        self.leaders: list[discord.Member] = []
        self.leader_view = None
        self.go_to_duplicate_btn: discord.ui.Button[Any] = discord.ui.Button(
            label="Vai al duplicato",
            style=discord.ButtonStyle.grey
        )
        self.go_to_duplicate_btn.callback = self.go_to_duplicate
        self.add_item(self.go_to_duplicate_btn)
    
    async def go_to_duplicate(self, interaction: discord.Interaction):
        duplicate_id = await get_duplicate_team_score(self.team_scores[self.page].team_score_id)

        if duplicate_id is None:
            await interaction.response.defer()
            return

        team_score = next(
            (ts for ts in self.team_scores if ts.team_score_id == duplicate_id),
            None
        )

        if team_score is None:
            await interaction.response.defer()
            return
        await interaction.response.defer()

        self.page = self.team_scores.index(team_score)
        await self.refresh(interaction)
    
    def get_leader_page(self):
        start = self.leader_page * self.leaders_per_page
        end = start + self.leaders_per_page
        return self.leaders[start:end]

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
    
    def build_leader_select(self) -> discord.ui.Select[Any] | None:
        page_leaders = self.get_leader_page()
        if not page_leaders:
            return None

        options = [
            discord.SelectOption(
                label=l.display_name[:100],
                value=str(l.id)
            )
            for l in page_leaders
        ]

        select = discord.ui.Select[Any](
            placeholder="Seleziona capoteam...",
            min_values=1,
            max_values=1,
            options=options
        )

        return select

    async def show_leader_page(self, interaction: discord.Interaction, edit: bool = True):
        embed = discord.Embed(
            title=f"Filtra capoteam (pagina {self.leader_page + 1})",
            color=discord.Color.blue()
        )

        self.leader_view = discord.ui.View()

        select: discord.ui.Select[Any] | None = self.build_leader_select()
        if select is None:
            if edit:
                await interaction.response.edit_message(content="Non ci sono leader reali disponibili")
            else:
                await interaction.response.send_message(content="Non ci sono leader reali disponibili", ephemeral=True)
            return

        async def callback(interaction: discord.Interaction):
            selected = int(select.values[0])
            team = await get_team_from_leader(self.event_id, selected)
            scores = await get_event_results(self.event_id, self.status, team)

            self.team_scores = scores
            self.page = 0
            self.sync_buttons()
            await interaction.response.defer()

            await self.refresh(interaction)

        select.callback = callback

        prev_btn: discord.ui.Button[Any] = discord.ui.Button(label="⬅️")
        next_btn: discord.ui.Button[Any] = discord.ui.Button(label="➡️")

        async def prev_callback(interaction: discord.Interaction):
            if self.leader_page > 0:
                self.leader_page -= 1
                await self.show_leader_page(interaction)
            else:
                await interaction.response.defer()
        async def next_callback(interaction: discord.Interaction):
            max_page = (len(self.leaders) - 1) // self.leaders_per_page
            if self.leader_page < max_page:
                self.leader_page += 1
                await self.show_leader_page(interaction)
            else:
                await interaction.response.defer()
        prev_btn.callback = prev_callback
        next_btn.callback = next_callback
        self.leader_view.add_item(select)
        self.leader_view.add_item(prev_btn)
        self.leader_view.add_item(next_btn)
        if edit:
            await interaction.response.edit_message(
                embed=embed,
                view=self.leader_view
            )
        else:
            await interaction.response.send_message(
                embed=embed,
                view=self.leader_view,
                ephemeral=True
            )

    async def refresh(self, interaction: discord.Interaction):
        if not self.team_scores:
            await interaction.edit_original_response(
                content="Nessun risultato rimasto",
                view=None,
                embeds=[]
            )
            return
        warnings: list[str] = []
        duplicate_placement_id = await get_duplicate_team_score(self.team_scores[self.page].team_score_id)
        if duplicate_placement_id is not None:
            warnings.append("QUESTO PIAZZAMENTO È DUPLICATO!")
            team_score = next(
                (ts for ts in self.team_scores if ts.team_score_id == duplicate_placement_id),
                None
            )
            if team_score is not None:
                self.go_to_duplicate_btn.disabled = False
        else:
            self.go_to_duplicate_btn.disabled = True
        embeds = build_results_embed(
            self.page,
            len(self.team_scores),
            self.team_scores[self.page].team_name,
            self.team_scores[self.page],
            warnings
        )
        if embeds is None:
            await interaction.edit_original_response(
                content="Errore generazione embed",
                view=self
            )
            return
        self.sync_buttons()
        await interaction.edit_original_response(embeds=embeds, view=self)
    
    async def prev_page_(self, interaction: discord.Interaction):
        if self.page == 0:
            await interaction.response.defer()
            return
        self.page -= 1
        warnings: list[str] = []
        duplicate_team_score_id = await get_duplicate_team_score(self.team_scores[self.page].team_score_id)
        if duplicate_team_score_id is not None:
            warnings.append("QUESTO PIAZZAMENTO È DUPLICATO!")
            self.go_to_duplicate_btn.disabled = False
        else:
            self.go_to_duplicate_btn.disabled = True

        embeds = build_results_embed(
            self.page,
            len(self.team_scores),
            self.team_scores[self.page].team_name,
            self.team_scores[self.page],
            warnings
        )
        if embeds is None:
            await interaction.response.edit_message(
                content="Errore generazione embed",
                view=self
            )
            return
        await interaction.response.edit_message(embeds=embeds, view=self)

    async def next_page_(self, interaction: discord.Interaction):
        if self.page >= len(self.team_scores) - 1:
            await interaction.response.defer()
            return

        self.page += 1
        warnings: list[str] = []
        duplicate_team_score_id = await get_duplicate_team_score(self.team_scores[self.page].team_score_id)
        if duplicate_team_score_id is not None:
            warnings.append("QUESTO PIAZZAMENTO È DUPLICATO!")
            self.go_to_duplicate_btn.disabled = False
        else:
            self.go_to_duplicate_btn.disabled = True

        embeds = build_results_embed(
            self.page,
            len(self.team_scores),
            self.team_scores[self.page].team_name,
            self.team_scores[self.page],
            warnings
        )
        if embeds is None:
            await interaction.response.edit_message(
                content="Errore generazione embed",
                view=self
            )
            return

        await interaction.response.edit_message(embeds=embeds, view=self)
    
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
    async def accept_result(self, interaction: discord.Interaction, button: discord.ui.Button[Any]):
        await interaction.response.defer()
        await self._handle(interaction, "accepted")

    @discord.ui.button(
        style=discord.ButtonStyle.blurple,
        label="Modifica",
        emoji="✏️",
        row=0
    )
    async def edit_result(self, interaction: discord.Interaction, button: discord.ui.Button[Any]):
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
                refresh_callback=lambda: self.refresh(interaction)
            )
        )

    @discord.ui.button(
        style=discord.ButtonStyle.red,
        label="Rifiuta",
        emoji="❌",
        row=0
    )
    async def reject_result(self, interaction: discord.Interaction, button: discord.ui.Button[Any]):
        if interaction.guild is None:
            return
        await interaction.response.defer()
        leader_id = await get_leader_discord_id(self.team_scores[self.page].team_id)
        if leader_id is None:
            await interaction.followup.send(
                "Non è stato possibile mandare il DM perché non è stato trovato l'id dell'utente",
                ephemeral=True
            )
            return
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
    async def prev_page(self, interaction: discord.Interaction, button: discord.ui.Button[Any]):
        await self.prev_page_(interaction)

    @discord.ui.button(
        label="➡️", 
        style=discord.ButtonStyle.secondary,
        row=1
    )
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button[Any]):
        await self.next_page_(interaction)
    
    @discord.ui.button(
        label="Filtra per capoteam",
        style=discord.ButtonStyle.blurple,
        row=2
    )
    async def filter_by_leader(self, interaction: discord.Interaction, button: discord.ui.Button[Any]):
        if interaction.guild is None:
            return
        leader_ids = await get_leader_ids(self.event_id)

        leaders: list[discord.Member] = []
        for l in leader_ids:
            member = interaction.guild.get_member(l)
            if member:
                leaders.append(member)

        self.leaders = leaders
        self.leader_page = 0
        await self.show_leader_page(interaction, edit=False)

    @discord.ui.button(
        label="Resetta filtro",
        style=discord.ButtonStyle.red,
        row=2
    )
    async def reset_filter(self, interaction: discord.Interaction, button: discord.ui.Button[Any]):
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
        duplicate_team_score_id = await get_duplicate_team_score(self.team_scores[self.page].team_score_id)
        if duplicate_team_score_id is not None:
            warnings.append("QUESTO PIAZZAMENTO È DUPLICATO!")
            self.go_to_duplicate_btn.disabled = False
        else:
            self.go_to_duplicate_btn.disabled = True

        embeds = build_results_embed(
            0,
            len(scores),
            self.team_scores[0].team_name,
            self.team_scores[0],
            warnings
        )
        if embeds is None:
            return

        await interaction.response.edit_message(
            embeds=embeds,
            view=self
        )