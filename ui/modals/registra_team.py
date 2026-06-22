import discord

import re

from services.team_service import *
from ui.embeds.lobby_builders import build_info_lobby_embed
from services.lobby_service import get_lobbies
from services.event_service import get_event_info

class RegistraTeamModal(discord.ui.Modal, title="Registra il tuo team"):
    nome_team = discord.ui.TextInput(
        label="Nome team + (CLAN)",
        placeholder="Inserisci il nome del tuo team...",
        min_length=3,
        max_length=50
    )
    capoteam = discord.ui.TextInput(
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
            kds: list[float] | None = None
        ):
        super().__init__()
        self.event_id = event_id
        self.members_number = members_number
        self.is_kd_mode = is_kd_mode
        self.status = status
        self.edit_mode = edit_mode
        if edit_mode and team_id is not None and players_names is not None:
            self.team_id = team_id
            self.title = "Modifica il tuo team"
            self.remove_item(self.nome_team)
            self.player_names = players_names
            self.capoteam.default = self.player_names[0]
            if kds is not None:
                self.kds = kds
        other_players = players_names[1:] if players_names else []

        self.inputs: list[discord.ui.TextInput] = []


        if edit_mode and players_names:
            self.player_names = players_names
            self.capoteam.default = self.player_names[0]

            other_players = players_names[1:]

            for i, name in enumerate(other_players):
                inp = discord.ui.TextInput(
                    label=f"Giocatore {i+2}",
                    placeholder=f"Inserisci l'username...",
                    default=name,
                    min_length=3,
                    max_length=40
                )
                self.add_item(inp)
                self.inputs.append(inp)

        else:
            for i in range(members_number - 1):
                inp = discord.ui.TextInput(
                    label=f"Giocatore {i+2}",
                    placeholder="Inserisci username...",
                    min_length=3,
                    max_length=40
                )
                self.add_item(inp)
                self.inputs.append(inp)
            
    async def on_submit(self, interaction: discord.Interaction):
        if not re.match(r"^.+\s\([^)]+\)$", self.nome_team.value) and not self.edit_mode:
            await interaction.response.send_message(
                "Il nome del team deve essere nel formato: Nome Team (CLAN)",
                ephemeral=True
            )
            return
        names = [self.capoteam.value]
        for inp in self.inputs:
            names.append(inp.value)

        if self.is_kd_mode:
            if self.edit_mode:
                view = discord.ui.View()
                yes_btn = discord.ui.Button(style=discord.ButtonStyle.green, label="Si")
                async def yes_callback(interaction: discord.Interaction):
                    await interaction.response.send_modal(
                        TeamKDModal(
                            self.event_id, names,
                            self.status,
                            edit_mode=self.edit_mode,
                            team_id=self.team_id,
                            kds=self.kds
                        )
                    )
                yes_btn.callback = yes_callback
                view.add_item(yes_btn)
                no_btn = discord.ui.Button(style=discord.ButtonStyle.red, label="No")
                async def no_callback(interaction: discord.Interaction):
                    await edit_teams(self.team_id, names)
                    await interaction.response.send_message(
                        "Hai modificato il tuo team con successo!",
                        ephemeral=True
                    )
                    return
                no_btn.callback = no_callback
                view.add_item(no_btn)
                await interaction.response.send_message(
                    "# ATTENZIONE\nQuesto evento richiede di inserire i valori K/D del proprio team, vuoi modificare anche quelli?\nSe premi no, solo i nomi dei membri saranno modificati.",
                    view=view,
                    ephemeral=True
                )
            else:
                view = discord.ui.View()
                btn = discord.ui.Button(style=discord.ButtonStyle.green, label="INSERISCI K/D")
                async def btn_callback(interaction: discord.Interaction):
                    await interaction.response.send_modal(
                        TeamKDModal(self.event_id, names, self.status, self.nome_team.value, False)
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
                await edit_teams(self.team_id, names)
                await interaction.response.send_message("Hai modificato il tuo team con successo!", ephemeral=True)
                return
            try:
                if self.status == "setup":
                    team_tuple = await assign_free_slot(
                        self.event_id,
                        self.nome_team.value,
                        interaction.user.id,
                        names
                    )
                    if team_tuple is None:
                        await interaction.response.send_message("C'è stato un problema!", ephemeral=True)
                        return
                    lobbies = await get_lobbies(self.event_id)
                    event = await get_event_info(self.event_id, interaction.guild_id)
                    if event is None:
                        return
                    embed = build_info_lobby_embed(event.name, lobbies, show_kd=False)
                    await interaction.user.send(embed=embed)
                else:
                    await insert_teams(self.event_id, self.nome_team.value, interaction.user.id, names)
            except ValueError:
                await interaction.response.send_message("Hai già iscritto un team a questo evento!", ephemeral=True)
                return
            await interaction.response.send_message("Hai registrato il tuo team correttamente!", ephemeral=True)


class TeamKDModal(discord.ui.Modal, title="Inserisci KD team"):
    def __init__(
            self,
            event_id: int,
            players_list: list[str],
            status: str,
            team_name: str | None = None,
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

        self.inputs: list[discord.ui.TextInput] = []

        for i, p in enumerate(self.players):
            inp = discord.ui.TextInput(
                label=f"KD {p}",
                placeholder="Inserisci KD",
                default=None if kds is None else str(self.kds[i]),
                min_length=1,
                max_length=5
            )
            self.inputs.append(inp)
            self.add_item(inp)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            kd_values = [float(inp.value) for inp in self.inputs]
        except ValueError:
            await interaction.response.send_message(
                "KD non valido. Controlla di aver usato il punto e non la virgola",
                ephemeral=True
            )
            return
        if self.edit_mode:
            member_ids = await edit_teams(self.team_id, self.players)

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
                team_id, member_ids = team_tuple
                players_kd_dict = dict(zip(member_ids, kd_values))

                await update_team_kd(team_id, players_kd_dict)
                lobbies = await get_lobbies(self.event_id)
                event = await get_event_info(self.event_id, interaction.guild_id)
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