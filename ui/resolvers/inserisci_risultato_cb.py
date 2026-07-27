import discord

from typing import Any

from models.event import Event
from services.team_service import get_team_id, get_inserted_matches, get_players_names
from ui.modals.registra_risultati import RegistraRisultatiModal

async def inserisci_risultato_message(
    message: discord.Message,
    event: Event,
    prove: tuple[str, str]
):
    event_id = event.event_id
    team_id = await get_team_id(event_id, message.author.id)
    if not team_id:
        await message.reply(
            "Non hai registrato nessun team per questo evento!\nUsa /registra_team per farlo.",
        )
        return
    embed = discord.Embed(
        title="Inserisci risultato",
        description=f"**ATTENZIONE**\nIL RISULTATO NON È STATO ANCORA REGISTRATO, controlla le foto che hai caricato e, in caso di errore, rifai il comando, altrimenti clicca il bottone qui sotto per inserire i risultati\n",
        color=discord.Colour.blurple()
    )
    second_embed = discord.Embed(color=discord.Color.blurple())
    view = discord.ui.View()
    insert_result_btn: discord.ui.Button[Any] = discord.ui.Button(label="INSERISCI RISULTATO", style=discord.ButtonStyle.green)
    async def insert_result_callback(interaction: discord.Interaction):
        embed = discord.Embed(
            title="Match",
            description="Scegli il match per cui stai riportando i risultati",
            color=discord.Colour.blurple()
        )
        matches_number = event.matches_number
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
        match_selector: discord.ui.Select[Any] = discord.ui.Select(
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
            players_names = await get_players_names(team_id)
            await interaction.response.send_modal(
                RegistraRisultatiModal(event_id, team_id, players_names, match_selected, prove)
            )
        match_selector.callback = match_selector_callback
        view.add_item(match_selector)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    insert_result_btn.callback = insert_result_callback
    view.add_item(insert_result_btn)
    await message.channel.send(embeds=[embed, second_embed], view=view)

async def inserisci_risultato_callback(
    interaction: discord.Interaction,
    event: Event,
    prove: tuple[str, str]
):
    event_id = event.event_id
    team_id = await get_team_id(event_id, interaction.user.id)
    if not team_id:
        await interaction.response.send_message(
            "Non hai registrato nessun team per questo evento!\nUsa /registra_team per farlo.",
            ephemeral=True
        )
        return
    await interaction.response.defer(ephemeral=True)
    embed = discord.Embed(
        title="Inserisci risultato",
        description=f"**ATTENZIONE**\nIL RISULTATO NON È STATO ANCORA REGISTRATO, controlla le foto che hai caricato e, in caso di errore, rifai il comando, altrimenti clicca il bottone qui sotto per inserire i risultati\n",
        color=discord.Colour.blurple()
    )
    embed.set_image(url=prove[0])
    second_embed = discord.Embed(color=discord.Color.blurple())
    second_embed.set_image(url=prove[1])
    view = discord.ui.View()
    insert_result_btn: discord.ui.Button[Any] = discord.ui.Button(label="INSERISCI RISULTATO", style=discord.ButtonStyle.green)
    async def insert_result_callback(interaction: discord.Interaction):
        embed = discord.Embed(
            title="Match",
            description="Scegli il match per cui stai riportando i risultati",
            color=discord.Colour.blurple()
        )
        matches_number = event.matches_number
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
        match_selector: discord.ui.Select[Any] = discord.ui.Select(
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
            players_names = await get_players_names(team_id)
            await interaction.response.send_modal(
                RegistraRisultatiModal(event_id, team_id, players_names, match_selected, prove)
            )
        match_selector.callback = match_selector_callback
        view.add_item(match_selector)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    insert_result_btn.callback = insert_result_callback
    view.add_item(insert_result_btn)
    await interaction.followup.send(embeds=[embed, second_embed], view=view, ephemeral=True)