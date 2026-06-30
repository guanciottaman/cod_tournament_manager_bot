import discord

from services.team_service import insert_results, edit_results, get_team_player_ids, get_leader_discord_id

class RegistraRisultatiModal(discord.ui.Modal, title="Registra i risultati"):
    placement_input = discord.ui.TextInput(
        label="Piazzamento",
        placeholder="Inserisci il piazzamento del tuo team in questo match...",
        min_length=1,
        max_length=2
    )
    def __init__(
            self,
            event_id: int,
            team_id: int,
            players_names: list[str],
            match_selected: int,
            prove: list[str],
            mode: str = "insert",
            admin_mode: bool = False,
            team_score_id: int = 0,
            parent_view: discord.ui.View | None = None,
            interaction: discord.Interaction | None = None
        ):
        super().__init__()
        self.event_id = event_id
        self.team_id = team_id
        self.players_names = players_names
        self.match_selected = match_selected
        self.prove = prove
        self.mode = mode
        self.admin_mode = admin_mode
        self.team_score_id = team_score_id
        if parent_view is not None:
            self.parent_view = parent_view
        if interaction is not None:
            self.interaction = interaction
        self.inputs: list[discord.ui.TextInput] = []
        for name in self.players_names:
            inp = discord.ui.TextInput(
                    label=f"Kills {name}",
                    placeholder=f"Inserisci le kill di {name}",
                    min_length=1,
                    max_length=2
                )
            self.add_item(inp)
            self.inputs.append(inp)

    async def on_submit(self, interaction: discord.Interaction):
        placement = self.placement_input.value
        if not placement.isdigit():
            await interaction.response.send_message("Tutti gli input devono essere numerici!", ephemeral=True)
            return
        placement = int(placement)
        player_ids = await get_team_player_ids(self.team_id)
        players_kills: list[tuple[int, str, int]] = []
        for i, inp in enumerate(self.inputs):
            value = inp.value
            if not value.isnumeric():
                await interaction.response.send_message("Tutti gli input devono essere numerici!", ephemeral=True)
                return
            player_id = player_ids[i]
            player_name = self.players_names[i]
            kills = int(value)

            players_kills.append((player_id, player_name, kills))
        await interaction.response.defer(ephemeral=True)
        if self.mode != "edit":
            team_score_id = await insert_results(
                self.event_id,
                self.team_id,
                placement,
                self.match_selected,
                players_kills,
                self.prove
            )
            if team_score_id is None:
                await interaction.followup.send("C'è stato un problema. Riprova.", ephemeral=True)
                return
            embed = discord.Embed(
                title="Risultato inserito",
                color=discord.Color.blue(),
            )
            emb_description = f"Hai inserito i risultati del match **{self.match_selected}**:\n**Piazzamento:** {placement}\n**Kill membri:**\n"
            for k in players_kills:
                emb_description += f"{k[1]}: {k[2]} kill\n"
            embed.description = emb_description
            view = discord.ui.View()
            edit_button = discord.ui.Button(
                label="Modifica",
                style=discord.ButtonStyle.blurple
            )
            async def edit_result(interaction: discord.Interaction):
                await interaction.response.send_modal(RegistraRisultatiModal(
                    self.event_id,
                    self.team_id,
                    self.players_names,
                    self.match_selected,
                    self.prove,
                    "edit",
                    False,
                    team_score_id,
                ))
            edit_button.callback = edit_result
            view.add_item(edit_button)
            await interaction.followup.send(
                embed=embed,
                view=view,
                ephemeral=True
            )
        else:
            await edit_results(
                self.event_id,
                self.team_id,
                self.team_score_id,
                placement,
                players_kills
            )
            embed = discord.Embed(
                title="Risultato modificato",
                color=discord.Color.gold(),
            )
            emb_description = f"Hai modificato i risultati del match **{self.match_selected}**:\n**Piazzamento:** {placement}\n**Kill membri:**\n"
            for k in players_kills:
                emb_description += f"{k[1]}: {k[2]} kill\n"
            embed.description = emb_description
            if self.admin_mode:
                self.parent_view.team_scores.pop(self.parent_view.page)
                self.parent_view.page = min(
                    self.parent_view.page,
                    len(self.parent_view.team_scores) - 1
                )
                if self.parent_view.page < 0:
                    self.parent_view.page = 0
                
                await self.parent_view.refresh(self.interaction)
                await interaction.followup.send(
                    embed=embed,
                    ephemeral=True
                )
                leader_id = await get_leader_discord_id(self.team_id)
                if leader_id is None:
                    await interaction.followup.send(
                        "Non è stato possibile mandare il DM perché non è stato trovato l'id dell'utente",
                        ephemeral=True
                    )
                    return
                leader = interaction.guild.get_member(leader_id) if leader_id > 10e16 else None
                if leader is not None:
                    await leader.send(
                        embed=embed
                    )
            else:
                await interaction.followup.send(
                    embed=embed,
                    ephemeral=True
                )