import discord
from discord.ext import commands
from discord import app_commands

from ui.selects.event_select import build_event_selector
from ui.modals.registra_risultati import RegistraRisultatiModal
from ui.modals.registra_team import RegistraTeamModal
from services.team_service import *
from services.event_service import *
from services.server_service import *


class Teams(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        super().__init__()
        self.bot = bot
    
    @app_commands.command(name="registra_team", description="Registra il tuo team a un evento")
    async def registra_team(self, interaction: discord.Interaction):
        view = discord.ui.View()
        events = await get_events_for_guild(interaction.guild_id, ["ready"])
        event_selector = build_event_selector(events)
        if not event_selector:
            await interaction.response.send_message("Non ci sono eventi configurati per il tuo server!", ephemeral=True)
            return
        async def event_selector_callback(interaction: discord.Interaction):
            event_id = int(event_selector.values[0])
            event = await get_event_info(event_id, interaction.guild_id)
            players_per_team = event.players_per_team
            is_kd_mode = True if event.lobby_mode in ("kd", "kd_balanced") else False
            await interaction.response.send_modal(
                RegistraTeamModal(event_id=event_id, members_number=players_per_team, is_kd_mode=is_kd_mode)
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
            event = await get_event_info(event_id, interaction.guild_id)
            lobby_mode = event.lobby_mode
            is_kd_mode = True if lobby_mode in ("kd", "kd_balanced") else False
            team_id = await get_team_id(event_id, interaction.user.id)
            if team_id is None:
                await interaction.response.send_message(
                    "Non hai registrato nessun team per questo evento!\nUsa /registra_team per farlo.",
                    ephemeral=True
                )
                return
            players_per_team = await get_players_per_team(event_id)
            await interaction.response.send_modal(
                RegistraTeamModal(
                    event_id=event_id,
                    members_number=players_per_team,
                    is_kd_mode=is_kd_mode,
                    edit_mode=True,
                    team_id=team_id
                )
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
        events = await get_events_for_guild(interaction.guild_id, ["running"])
        if not events:
            await interaction.response.send_message("Non ci sono eventi in corso per il tuo server!", ephemeral=True)
            return
        event_selector = build_event_selector(events)
        if event_selector is None:
            await interaction.response.send_message("Non ci sono eventi configurati per il tuo server!", ephemeral=True)
            return
        async def event_selector_callback(interaction: discord.Interaction):
            event_id = int(event_selector.values[0])
            team_id = await get_team_id(event_id, interaction.user.id)
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
            inserted = await get_inserted_matches(event_id, team_id)

            available_matches = [
                i for i in range(1, matches_number+1)
                if i not in inserted
            ]
            if not available_matches:
                await interaction.response.send_message(
                    "Hai già inserito tutti i match.",
                    ephemeral=True
                )
                return
            view = discord.ui.View()
            match_selector = discord.ui.Select(
                placeholder="Seleziona il match...",
                min_values=1,
                max_values=1,
                options=[
                    discord.SelectOption(label=str(i), value=str(i))
                    for i in available_matches
                ]
            )
            async def match_selector_callback(interaction: discord.Interaction):
                match_selected = int(match_selector.values[0])
                print(match_selected)
                players_names = await get_players_names(team_id)
                print(players_names)
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