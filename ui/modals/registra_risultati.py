import discord

from typing import Any, Callable, Awaitable

from services.team_service import insert_results, edit_results, get_team_player_ids

class RegistraRisultatiModal(discord.ui.Modal, title="Registra i risultati"):
    placement_input: discord.ui.TextInput[Any] = discord.ui.TextInput(
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
            refresh_callback: Callable[[], Awaitable[None]] | None = None
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
        self.refresh_callback = refresh_callback
        self.inputs: list[discord.ui.TextInput[Any]] = []
        for name in self.players_names:
            inp: discord.ui.TextInput[Any] = discord.ui.TextInput(
                    label=f"Kills {name}",
                    placeholder=f"Inserisci le kill di {name}",
                    min_length=1,
                    max_length=2
                )
            self.add_item(inp)
            self.inputs.append(inp)

    async def on_submit(self, interaction: discord.Interaction):
        if interaction.guild is None:
            return
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
            edit_button: discord.ui.Button[Any] = discord.ui.Button(
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
            if self.refresh_callback is not None:
                await self.refresh_callback()
            await interaction.followup.send(
                embed=embed,
                ephemeral=True
            )