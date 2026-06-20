import discord
import aiohttp
from io import BytesIO
from services.team_service import insert_results, edit_results, get_team_player_ids, get_leader_discord_id, set_result_status

async def download_file(url: str):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                return None

            data = await resp.read()
            return BytesIO(data)

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
            await insert_results(
                self.event_id,
                self.team_id,
                placement,
                self.match_selected,
                players_kills,
                self.prove
            )
            files = []

            for i, url in enumerate(self.prove):
                buffer = await download_file(url)
                if buffer is None:
                    continue

                files.append(discord.File(buffer, filename=f"prova_{i+1}.png"))
            await interaction.followup.send(
                f"Il risultato del match {self.match_selected} è stato registrato!",
                ephemeral=True,
                files=files
            )
        else:
            await edit_results(
                self.event_id,
                self.team_id,
                self.team_score_id,
                placement,
                players_kills
            )
            self.parent_view.team_scores.pop(self.parent_view.page)
            self.parent_view.page = min(
                self.parent_view.page,
                len(self.parent_view.team_scores) - 1
            )
            if self.parent_view.page < 0:
                self.parent_view.page = 0
            
            await self.parent_view.refresh(self.interaction)
            await interaction.followup.send(
                f"Il risultato del match {self.match_selected} è stato modificato!",
                ephemeral=True
            )
            leader_id = await get_leader_discord_id(self.team_id)
            if leader_id is None:
                await interaction.followup.send(
                    "Non è stato possibile mandare il DM perché non è stato trovato l'id dell'utente",
                    ephemeral=True
                )
            leader = interaction.guild.get_member(leader_id) if leader_id > 10e16 else None
            if leader is not None:
                embed = discord.Embed(
                    title="Risultato modificato",
                    color=discord.Color.dark_gold()
                )
                emb_description = f"Il risultato del match {self.match_selected} è stato modificato come seguente.\nPiazzamento: **{placement}°** posto\n"
                for _, player_name, kills in players_kills:
                    emb_description += f"- {player_name} {kills} kill\n"
                embed.description = emb_description
                await leader.send(
                    embed=embed
                )