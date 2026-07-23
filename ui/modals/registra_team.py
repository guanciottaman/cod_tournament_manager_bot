import discord

import re
from typing import Any

from services.team_service import *
from ui.embeds.lobby_builders import build_info_lobby_embed
from services.lobby_service import get_lobbies
from services.event_service import get_event_info, assign_user_lobby_role, get_category_channel_id
from services.team_service import set_team_channel_id
from services.server_service import get_admin_role_id

async def create_team_channel(
    event_id: int,
    interaction: discord.Interaction,
    team_id: int,
    team_name: str
) -> discord.TextChannel | None:
    if interaction.guild is None:
        return
    category_id = await get_category_channel_id(event_id)
    if category_id is None:
        return
    category = interaction.guild.get_channel(category_id)
    if not isinstance(category, discord.CategoryChannel):
        return
    admin_role_id = await get_admin_role_id(interaction.guild.id)
    if admin_role_id is None:
        return
    admin_role = interaction.guild.get_role(admin_role_id)
    if admin_role is None:
        return
    overwrites = {
        interaction.guild.default_role: discord.PermissionOverwrite(
            view_channel=False
        ),
        interaction.guild.me: discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            manage_messages=True,
            embed_links=True,
            attach_files=True,
        ),
        admin_role: discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
        ),
        interaction.user: discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
        ),
    }

    channel = await category.create_text_channel(
        name=team_name,
        overwrites=overwrites # type: ignore
    )
    await set_team_channel_id(event_id, team_id, channel.id)
    embed = discord.Embed(
        title=f"Canale team {team_name}",
        color=discord.Color.blue(),
        description="In questo canale potrai caricare i tuoi risultati.\nPer farlo, carica semplicemente le 2 foto richieste e dopo potrai inserire i risultati"
    )
    await channel.send(embed=embed)
    return channel

async def notify_admins(interaction: discord.Interaction, team_name: str, members: list[tuple[str, float | None]]):
    embed = discord.Embed(
        title="Nuovo team registrato",
        color=discord.Color.blue()
    )
    emb_description = f"Nome team: **{team_name}**\nMembri:\n"
    for i, (member_name, member_kd) in enumerate(members):
        emb_description += f"{i+1}. {member_name}{f' {member_kd} K/D' if member_kd is not None else ''}\n"
    embed.description = emb_description
    failed = 0

    guild = interaction.guild
    if guild is None:
        return

    admin_role_id = await get_admin_role_id(guild.id)
    if admin_role_id is None:
        await interaction.followup.send("Ruolo admin non configurato!", ephemeral=True)
        return
    admin_role = guild.get_role(admin_role_id)
    if admin_role is None:
        return
    if interaction.client.user is None:
        return
    admins: set[int] = set(m.id for m in admin_role.members if m.id != interaction.client.user.id) if admin_role else set()

    for user_id in admins:
        member = guild.get_member(user_id)
        if member is None:
            failed += 1
            continue

        try:
            await member.send(embed=embed)
        except (discord.Forbidden, discord.HTTPException):
            failed += 1

    await interaction.followup.send("Gli admin sono stati notificati.", ephemeral=True)
    

class RegistraTeamModal(discord.ui.Modal, title="Registra il tuo team"):
    nome_team: discord.ui.TextInput[Any] = discord.ui.TextInput(
        label="Nome team + (CLAN)",
        placeholder="Inserisci il nome del tuo team...",
        min_length=3,
        max_length=50
    )
    capoteam: discord.ui.TextInput[Any] = discord.ui.TextInput(
        label="Nome capoteam",
        placeholder="Inserisci il tuo username di CoD (compreso il numero)...",
        min_length=3,
        max_length=40
    )
    def __init__(
            self,
            event_id: int,
            members_number: int,
            is_kd_mode: bool,
            status: str,
            edit_mode: bool = False,
            team_id: int | None=None,
            players_names: list[str] | None = None,
            kds: list[float] | None = None,
            is_admin: bool = False,
            team_name: str | None = None
        ):
        super().__init__()
        self.event_id = event_id
        self.members_number = members_number
        self.is_kd_mode = is_kd_mode
        self.status = status
        self.edit_mode = edit_mode
        self.is_admin = is_admin
        if edit_mode and team_id is not None and players_names is not None:
            self.team_id = team_id
            self.title = "Modifica il tuo team"
            if not is_admin:
                self.remove_item(self.nome_team)
            elif is_admin and team_name is not None:
                self.nome_team.default = team_name
            self.player_names = players_names
            self.capoteam.default = self.player_names[0]
            if kds is not None:
                self.kds = kds
        other_players = players_names[1:] if players_names else []

        self.inputs: list[discord.ui.TextInput[Any]] = []


        if edit_mode and players_names:
            self.player_names = players_names
            self.capoteam.default = self.player_names[0]

            other_players = players_names[1:]

            for i, name in enumerate(other_players):
                inp: discord.ui.TextInput[Any] = discord.ui.TextInput(
                    label=f"Giocatore {i+2}",
                    placeholder=f"Inserisci l'username...",
                    default=name,
                    min_length=3,
                    max_length=40
                )
                self.add_item(inp)
                self.inputs.append(inp)

        else:
            other_players = []
            for i in range(members_number - 1):
                inp = discord.ui.TextInput(
                    label=f"Giocatore {i+2}",
                    placeholder="Inserisci username...",
                    min_length=3,
                    max_length=40
                )
                self.add_item(inp)
                self.inputs.append(inp)
            
    def normalize_team_name(self, name: str) -> str:
        name = name.strip()
        name = re.sub(r"\s*\(", " (", name)
        name = re.sub(r"\s+", " ", name)
        return name

    async def on_submit(self, interaction: discord.Interaction):
        if interaction.guild is None:
            return
        if not self.edit_mode or self.is_admin:
            nome_team = self.normalize_team_name(self.nome_team.value)

            match = re.match(r"^(.+?)\s*\(([^)]+)\)\s*$", nome_team)
            if not match:
                await interaction.response.send_message(
                    "# ATTENZIONE\nIl team non è stato creato. Il nome team deve essere nel formato '<Nome team> (<CLAN>)' e CLAN può avere massimo 5 caratteri.",
                    ephemeral=True
                )
                return

            team_name_clean = match.group(1).strip()
            team_name_clean = team_name_clean[0].upper() + team_name_clean[1:]
            if not team_name_clean:
                await interaction.response.send_message("Nome team non valido", ephemeral=True)
                return
            clan_tag = match.group(2).strip().upper()
            nome_team = f"{team_name_clean} ({clan_tag})"

            if len(clan_tag) > 5:
                await interaction.response.send_message(
                    "Il tag clan non può essere più lungo di 5 caratteri.",
                    ephemeral=True
                )
                return
            
            if not clan_tag.isalnum():
                await interaction.response.send_message(
                    "Il tag clan può contenere solo lettere e numeri.",
                    ephemeral=True
                )
                return

        else:
            nome_team = ""
        names = [self.capoteam.value]
        for inp in self.inputs:
            names.append(inp.value)

        if self.is_kd_mode:
            if self.edit_mode:
                view = discord.ui.View()
                yes_btn: discord.ui.Button[Any] = discord.ui.Button(style=discord.ButtonStyle.green, label="Si")
                async def yes_callback(interaction: discord.Interaction):
                    await interaction.response.send_modal(
                        TeamKDModal(
                            self.event_id,
                            names,
                            self.status,
                            team_name=self.nome_team.value,
                            edit_mode=self.edit_mode,
                            team_id=self.team_id,
                            kds=self.kds
                        )
                    )
                yes_btn.callback = yes_callback
                view.add_item(yes_btn)
                no_btn: discord.ui.Button[Any] = discord.ui.Button(style=discord.ButtonStyle.red, label="No")
                async def no_callback(interaction: discord.Interaction):
                    await edit_teams(self.team_id, names, nome_team if nome_team else None)
                    await interaction.response.send_message(
                        "Hai modificato il tuo team con successo!",
                        ephemeral=True
                    )
                    return
                no_btn.callback = no_callback
                view.add_item(no_btn)
                await interaction.response.send_message(
                    "# ATTENZIONE\nQuesto evento richiede di inserire i valori K/D del proprio team, vuoi modificare anche quelli?\nSe premi no, solo i nomi dei membri saranno modificati.\nSE NON PREMI ALCUN BOTTONE IL TEAM NON VERRÀ MODIFICATO.",
                    view=view,
                    ephemeral=True
                )
            else:
                view = discord.ui.View()
                btn: discord.ui.Button[Any] = discord.ui.Button(style=discord.ButtonStyle.green, label="INSERISCI K/D")
                async def btn_callback(interaction: discord.Interaction):
                    await interaction.response.send_modal(
                        TeamKDModal(self.event_id, names, self.status, nome_team, False)
                    )
                btn.callback = btn_callback
                view.add_item(btn)
                await interaction.response.send_message(
                    "# ATTENZIONE:\nIl tuo team non è stato ancora registrato.\n Hai inserito le info del team, l'evento richiede i rapporti K/D dei tuoi membri. Clicca il bottone qui sotto", 
                    view=view,
                    ephemeral=True
                )
        else:
            if self.edit_mode:
                await edit_teams(self.team_id, names, team_name=nome_team if nome_team else None)
                await interaction.response.send_message("Hai modificato il tuo team con successo!", ephemeral=True)
                return
            try:
                if self.status == "setup":
                    team_tuple = await assign_free_slot(
                        self.event_id,
                        nome_team,
                        interaction.user.id,
                        names
                    )
                    if team_tuple is None:
                        await interaction.response.send_message("C'è stato un problema!", ephemeral=True)
                        return
                    self.team_id, lobby_id, _ = team_tuple
                    await assign_user_lobby_role(self.event_id, lobby_id, interaction.user.id, interaction.guild)
                else:
                    await insert_teams(self.event_id, nome_team, interaction.user.id, names)
                
                channel = await create_team_channel(self.event_id, interaction, self.team_id, nome_team)
                if channel is None:
                    raise RuntimeError("Errore nella creazione del canale")
            except ValueError:
                await interaction.response.send_message("Hai già iscritto un team a questo evento!", ephemeral=True)
                return
            await interaction.response.send_message(
                f"Hai registrato il tuo team correttamente!\nCreato il canale {channel.mention}",
                ephemeral=True
            )
            await notify_admins(interaction, nome_team, [(n, None) for n in names])


class TeamKDModal(discord.ui.Modal, title="Inserisci KD team"):
    def __init__(
            self,
            event_id: int,
            players_list: list[str],
            status: str,
            team_name: str,
            edit_mode: bool = False,
            team_id: int | None=None,
            kds: list[float] | None = None
        ):
        super().__init__()
        self.event_id = event_id
        self.team_name = team_name
        self.players = players_list
        self.status = status
        self.edit_mode = edit_mode
        if self.edit_mode and team_id is not None and kds is not None:
            self.team_id = team_id
            self.kds = kds

        self.inputs: list[discord.ui.TextInput[Any]] = []

        for i, p in enumerate(self.players):
            inp: discord.ui.TextInput[Any] = discord.ui.TextInput(
                label=f"KD {p}",
                placeholder="Inserisci KD",
                default=None if kds is None else str(self.kds[i]),
                min_length=1,
                max_length=5
            )
            self.inputs.append(inp)
            self.add_item(inp)

    async def on_submit(self, interaction: discord.Interaction):
        if interaction.guild is None:
            return
        try:
            kd_values = [
                float(inp.value.replace(",", "."))
                for inp in self.inputs
            ]
        except ValueError:
            await interaction.response.send_message(
                "KD non valido. Controlla di aver usato il punto e non la virgola",
                ephemeral=True
            )
            return
        if self.edit_mode:
            member_ids = await edit_teams(self.team_id, self.players, self.team_name if self.team_name else None)

            players_kd_dict = dict(zip(member_ids, kd_values))
            await update_team_kd(self.team_id, players_kd_dict)

            await interaction.response.send_message(
                "Hai modificato il tuo team con successo.",
                ephemeral=True
            )
        else:
            if self.status == "setup":
                team_tuple = await assign_free_slot(
                    self.event_id,
                    self.team_name,
                    interaction.user.id,
                    self.players
                )
                if team_tuple is None:
                    await interaction.response.send_message("Nessuno slot disponibile", ephemeral=True)
                    return
                self.team_id, lobby_id, member_ids = team_tuple
                await assign_user_lobby_role(self.event_id, lobby_id, interaction.user.id, interaction.guild)
                players_kd_dict = dict(zip(member_ids, kd_values))

                await update_team_kd(self.team_id, players_kd_dict)
                lobbies = await get_lobbies(self.event_id)
                event = await get_event_info(self.event_id, interaction.guild.id)
                if event is None:
                    return
                embed = build_info_lobby_embed(event.name, lobbies, show_kd=False)
                await interaction.user.send(embed=embed)
            else:
                team_tuple = await insert_teams(self.event_id, self.team_name, interaction.user.id, self.players)
                if team_tuple is None:
                    await interaction.response.send_message("Errore interno team_id", ephemeral=True)
                    return
                team_id, member_ids = team_tuple
                players_kd_dict = dict(zip(member_ids, kd_values))
                await update_team_kd(team_id, players_kd_dict)
            await interaction.response.send_message(
                "Hai iscritto il tuo team all'evento con successo.",
                ephemeral=True
            )
            await notify_admins(interaction, self.team_name, [(n, kd) for n, kd in zip(self.players, kd_values)])