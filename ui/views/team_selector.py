import discord

from collections import defaultdict

from models.team import Team
from models.event import Event
from models.lobby import Lobby
from services.team_service import *
from services.event_service import *
from services.lobby_service import get_lobbies, switch_team_lobby
from services.server_service import get_admin_role_id
from ui.modals.penalize_team import PenalizzaTeam
from ui.modals.registra_team import RegistraTeamModal
from ui.embeds.lobby_builders import build_info_lobby_embed

class TeamsSelectorView(discord.ui.View):
    def __init__(
            self,
            teams: list[Team],
            event: Event,
            mode: str = "info",
            page: int = 0,
            use_lobbies: bool = False,
            lobbies: list[Lobby] | None = None,
            interaction: discord.Interaction | None = None,
            send_lobbies: bool = False,
        ):
        super().__init__(timeout=180)
        self.teams = teams
        self.event = event
        self.event_id = self.event.event_id
        
        self.mode = mode
        self.page = page
        self.use_lobbies = use_lobbies
        self.interaction = interaction
        self.send_lobbies = send_lobbies
        self.teams_by_lobby = defaultdict(list[Team])

        for t in self.teams:
            if t.lobby is None:
                continue
            self.teams_by_lobby[t.lobby].append(t)
        
        if self.use_lobbies and lobbies is not None:
            self.lobbies = lobbies

            self.lobby_map = {l.lobby_id: l for l in self.lobbies}
            self.lobby_ids = list(self.lobby_map.keys())
            self.lobby_ids.sort()
        self.add_item(self.build_select())

    async def notify_users(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True, ephemeral=True)
        lobbies = await get_lobbies(self.event_id)
        embed = build_info_lobby_embed(self.event.name, lobbies, show_kd=False)
        embed.title = "AGGIORNAMENTO TEAM LOBBY"
        failed = 0

        guild = interaction.guild
        if guild is None:
            return

        admin_role_id = await get_admin_role_id(interaction.guild_id)
        admin_role = guild.get_role(admin_role_id)

        admins = set(m.id for m in admin_role.members if m.id != interaction.client.user.id) if admin_role else set()
        leader_ids = await get_leader_ids(self.event_id)
        leaders = set(leader_ids)

        for user_id in (leaders | admins):
            member = guild.get_member(user_id)
            if member is None:
                failed += 1
                continue

            try:
                await member.send(embed=embed)
            except (discord.Forbidden, discord.HTTPException):
                failed += 1

        if failed:
            await interaction.followup.send(
                f"DM falliti: {failed}",
                ephemeral=True
            )

    def get_leader_name(self, interaction: discord.Interaction, leader_id: int) -> str:
        member = interaction.guild.get_member(leader_id)
        if member is None:
            return "Unknown"
        return member.display_name

    def build_select(self) -> discord.ui.Select:
        if self.use_lobbies:
            lobby = self.lobby_map[self.lobby_ids[self.page]]
            page_teams: list[Team] = self.teams_by_lobby[lobby.lobby_id]
            placeholder = f"{lobby.name} (pagina {self.page + 1}/{len(self.lobbies)})"
        else:
            start = self.page * 25
            end = start + 25
            page_teams = self.teams[start:end]
            placeholder = f"Seleziona team (pagina {self.page + 1})"

        if not page_teams:
            return discord.ui.Select(
                placeholder="Nessun team disponibile",
                options=[discord.SelectOption(label="Vuoto", value="0")],
                disabled=True
            )


        select = discord.ui.Select(
            placeholder=placeholder,
            options=[
                discord.SelectOption(
                    label=t.name,
                    value=str(t.team_id),
                    description=f"Capoteam: {self.get_leader_name(self.interaction, t.leader_discord_id)}"
                )
                for t in page_teams[:25]
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
                kds = await get_team_kds(team_id)
                for i, m in enumerate(team_members):
                    emb_description += f"{i+1}. {m[0]}{f' K/D {kds[i]}' if kds else ''}\n"
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
                            ) for lobby in lobbies if team not in lobby.teams
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
                        confirm_view = discord.ui.View()
                        sposta_team_yes = discord.ui.Button(
                            label="Si",
                            style=discord.ButtonStyle.green
                        )
                        sposta_team_no = discord.ui.Button(
                            label="No",
                            style=discord.ButtonStyle.red
                        )
                        async def yes_callback(interaction: discord.Interaction):
                            await self.notify_users(interaction)
                        sposta_team_yes.callback = yes_callback
                        async def no_callback(interaction: discord.Interaction):
                            await interaction.response.send_message("Non è stato mandato nessun dm.", ephemeral=True)
                        sposta_team_no.callback = no_callback
                        confirm_view.add_item(sposta_team_yes)
                        confirm_view.add_item(sposta_team_no)
                        await interaction.followup.send(
                            "Vuoi mandare un aggiornamento delle lobby ai capoteam e agli admin?",
                            view=confirm_view,
                            ephemeral=True
                        )
                    lobby_selector.callback = lobby_selector_callback
                    view.add_item(lobby_selector)
                    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
                sposta_team_btn.callback = switch_team_callback
                view.add_item(sposta_team_btn)
                await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            elif self.mode == "penalize":
                await interaction.response.send_modal(PenalizzaTeam(self.event_id, team_id))
            elif self.mode == "edit":
                players_names = await get_players_names(team_id)
                await interaction.response.send_modal(
                    RegistraTeamModal(
                        event_id=self.event_id,
                        members_number=self.event.players_per_team,
                        is_kd_mode=True if event.lobby_mode in ("kd", "kd_balanced") else False,
                        status=self.event.status,
                        edit_mode=True,
                        team_id=team_id,
                        players_names=players_names,
                        kds=None if event.lobby_mode not in ("kd", "kd_balanced") else await get_team_kds(team_id),
                        is_admin=True,
                        team_name=team.name
                    ) 
                )
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
        if self.use_lobbies:
            if self.page < len(self.lobby_ids) - 1:
                self.page += 1
        else:
            if (self.page + 1) * 25 < len(self.teams):
                self.page += 1

        self.clear_items()
        self.add_item(self.build_select())
        self.add_item(self.prev_page)
        self.add_item(self.next_page)

        await interaction.response.edit_message(view=self)