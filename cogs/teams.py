import discord
from discord.ext import commands
from discord import app_commands

from cogs.events import build_event_selector
from services.team_service import *
from services.event_service import *
from services.server_service import *


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
            prove: list[str]
        ):
        super().__init__()
        self.event_id = event_id
        self.team_id = team_id
        self.players_names = players_names
        self.match_selected = match_selected
        self.prove = prove
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
        if not placement.isnumeric():
            await interaction.response.send_message("Tutti gli input devono essere numerici!", ephemeral=True)
            return
        players_kills = dict()
        for i, inp in enumerate(self.inputs):
            value = inp.value
            if not value.isnumeric():
                await interaction.response.send_message("Tutti gli input devono essere numerici!", ephemeral=True)
                return
            players_kills[self.players_names[i]] = value
        await insert_results(
            self.event_id,
            self.team_id,
            placement,
            self.match_selected,
            players_kills,
            self.prove
        )
        await interaction.response.send_message(
            f"Il risultato del match {self.match_selected} è stato registrato!",
            ephemeral=True
        )

class RegistraTeamModal(discord.ui.Modal, title="Registra il tuo team"):
    nome_team = discord.ui.TextInput(
        label="Nome team",
        placeholder="Inserisci il nome del tuo team...",
        min_length=3,
        max_length=40
    )
    capoteam = discord.ui.TextInput(
        label="Nome capoteam",
        placeholder="Inserisci il tuo username di CoD (compreso il numero)...",
        min_length=3,
        max_length=40
    )
    def __init__(self, event_id: int, members_number: int, edit_mode: bool = False):
        super().__init__()
        self.event_id = event_id
        self.members_number = members_number
        self.edit_mode: bool = edit_mode

        self.inputs: list[discord.ui.TextInput] = []
        for i in range(self.members_number-1):

            inp = discord.ui.TextInput(
                label=f"Giocatore {i+2}",
                placeholder=f"Inserisci l'username di CoD del giocatore {i+2} (compreso il numero)...",
                min_length=3,
                max_length=40
            )

            self.inputs.append(inp)
            self.add_item(inp)
    
    async def on_submit(self, interaction: discord.Interaction):
        names = [self.capoteam.value]
        for inp in self.inputs:
            names.append(inp.value)
        if self.edit_mode:
            await edit_teams(self.event_id, self.nome_team.value, interaction.user.id, names)
            await interaction.response.send_message("Hai modificato il tuo team con successo!", ephemeral=True)
        else:
            try:
                await insert_teams(self.event_id, self.nome_team.value, interaction.user.id, names)
            except ValueError:
                await interaction.response.send_message("Hai già iscritto un team a questo evento!", ephemeral=True)
                return
            await interaction.response.send_message("Hai iscritto il tuo team all'evento con successo!", ephemeral=True)


class Teams(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        super().__init__()
        self.bot = bot
    
    @app_commands.command(name="registra_team", description="Registra il tuo team a un evento")
    async def registra_team(self, interaction: discord.Interaction):
        view = discord.ui.View()
        events = await get_events_for_guild(interaction.guild_id)
        event_selector = build_event_selector(events)
        if not event_selector:
            await interaction.response.send_message("Non ci sono eventi configurati per il tuo server!", ephemeral=True)
            return
        async def event_selector_callback(interaction: discord.Interaction):
            event_id = int(event_selector.values[0])
            players_per_team = await get_players_per_team(event_id)
            await interaction.response.send_modal(
                RegistraTeamModal(event_id=event_id, members_number=players_per_team)
            )
            
        event_selector.callback = event_selector_callback
        view.add_item(event_selector)
        embed = discord.Embed(
            title="Scegli l'evento a cui iscriverti",
            color=discord.Colour.red(),
            description="Questa è una lista degli eventi attivi.\nScegli l'evento a cui ti sei iscritto durante il ticket."
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @app_commands.command(name="modifica_team", description="Modifica il tuo team")
    async def modifica_team(self, interaction: discord.Interaction):
        view = discord.ui.View()
        events = await get_events_for_guild(interaction.guild_id, ["ready"])
        event_selector = build_event_selector(events)
        if not event_selector:
            await interaction.response.send_message("Non ci sono eventi configurati per il tuo server!", ephemeral=True)
            return
        async def event_selector_callback(interaction: discord.Interaction):
            event_id = int(event_selector.values[0])
            team_exists = await check_team_exists(event_id, interaction.user.id)
            if not team_exists:
                await interaction.response.send_message(
                    "Non hai registrato nessun team per questo evento!\nUsa /registra_team per farlo.",
                    ephemeral=True
                )
                return
            players_per_team = await get_players_per_team(event_id)
            await interaction.response.send_modal(
                RegistraTeamModal(event_id=event_id, members_number=players_per_team, edit_mode=True)
            )

        event_selector.callback = event_selector_callback
        view.add_item(event_selector)
        embed = discord.Embed(
            title="Scegli l'evento a cui ti sei iscritto",
            color=discord.Colour.red(),
            description="Questa è una lista degli eventi attivi.\nScegli l'evento del team che hai iscritto."
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @app_commands.command(name="inserisci_risultato", description="Inserisci i risultati di un match")
    @app_commands.describe(prova1="Prima prova dei risultati", prova2="Seconda prova dei risultati")
    async def inserisci_risultato(
        self,
        interaction: discord.Interaction,
        prova1: discord.Attachment,
        prova2: discord.Attachment
    ):
        view = discord.ui.View()
        events = await get_events_for_guild(interaction.guild_id, ["ready"])
        event_selector = build_event_selector(events)
        if not event_selector:
            await interaction.response.send_message("Non ci sono eventi configurati per il tuo server!", ephemeral=True)
            return
        async def event_selector_callback(interaction: discord.Interaction):
            event_id = int(event_selector.values[0])
            team_id = await check_team_exists(event_id, interaction.user.id)
            if not team_id:
                await interaction.response.send_message(
                    "Non hai registrato nessun team per questo evento!\nUsa /registra_team per farlo.",
                    ephemeral=True
                )
                return
            embed = discord.Embed(
                title="match",
                description="Scegli il match per cui stai riportando i risultati",
                color=discord.Colour.blurple()
            )
            matches_number = await get_matches_number(event_id)
            view = discord.ui.View()
            match_selector = discord.ui.Select(
                placeholder="Seleziona il match...",
                min_values=1,
                max_values=1,
                options=[
                    discord.SelectOption(label=str(i+1), value=str(i+1))
                    for i in range(matches_number)
                ]
            )
            async def match_selector_callback(interaction: discord.Interaction):
                match_selected = match_selector.values[0]
                players_names = await get_players_names(team_id)
                await interaction.response.send_modal(
                    RegistraRisultatiModal(event_id, team_id, players_names, match_selected, [prova1.url, prova2.url])
                )
            match_selector.callback = match_selector_callback
            view.add_item(match_selector)
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        event_selector.callback = event_selector_callback
        view.add_item(event_selector)
        embed = discord.Embed(
            title="Scegli l'evento a cui ti sei iscritto",
            color=discord.Colour.red(),
            description="Questa è una lista degli eventi attivi.\nScegli l'evento del team che hai iscritto."
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Teams(bot))