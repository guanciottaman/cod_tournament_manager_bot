import discord

from services.event_service import get_leader_ids, get_lobby_codes_channel
from models.event import Event
from models.lobby import Lobby

async def send_lobby_codes_callback(
    interaction: discord.Interaction, 
    event: Event, 
    lobbies: list[Lobby], 
    code: str
):
    event_id = event.event_id
    view = discord.ui.View()
    select = discord.ui.Select(
        placeholder="Scegli la lobby a cui mandare il codice",
        options=[
            discord.SelectOption(
                label=lobby.name,
                description=f"Il codice {code} verrà mandato ai capoteam della lobby {lobby.name}",
                value=str(lobby.lobby_id)
            )
            for lobby in lobbies
        ],
        min_values=1,
        max_values=1
    )
    async def select_callback(interaction: discord.Interaction):
        lobby_id = int(select.values[0])
        await interaction.response.defer(ephemeral=True)
        leader_ids = await get_leader_ids(event_id, lobby_id=lobby_id)
        if not leader_ids:
            await interaction.followup.send("C'è stato un problema con i capoteam!", ephemeral=True)
            return

        embed = discord.Embed(
            title="Codice partita",
            color=discord.Color.blue(),
            description=f"Usa il seguente codice per entrare in partita:\nCodice: **{code}**"
        )
        if interaction.guild is None:
            return

        guild = interaction.guild
        lobby_codes_channel_id = await get_lobby_codes_channel(event_id, lobby_id)
        if lobby_codes_channel_id is None:
            await interaction.followup.send("Non è stato impostato un canale per questa lobby!", ephemeral=True)
            return
        lobby_codes_channel = guild.get_channel(lobby_codes_channel_id)
        if lobby_codes_channel is None:
            await interaction.followup.send("Il canale non esiste!", ephemeral=True)
            return
        view = discord.ui.View()
        yes_btn = discord.ui.Button(
            style=discord.ButtonStyle.green,
            label="Conferma"
        )
        cancel_btn = discord.ui.Button(
            style=discord.ButtonStyle.gray,
            label="Annulla"
        )
        async def yes_callback(interaction: discord.Interaction):
            try:
                await lobby_codes_channel.send(embed=embed)
                await interaction.response.send_message(f"Codice mandato in {lobby_codes_channel.mention}", ephemeral=True)
            except discord.Forbidden:
                await interaction.response.send_message("Mancano i permessi per il canale!", ephemeral=True)
        yes_btn.callback = yes_callback
        view.add_item(yes_btn)
        async def cancel_callback(interaction: discord.Interaction):
            await interaction.response.send_message("Hai annullato l'invio del codice.", ephemeral=True)
        cancel_btn.callback = cancel_callback
        view.add_item(cancel_btn)
        await interaction.followup.send(
            f"Stai per mandare il codice **{code}** nel canale {lobby_codes_channel.mention}",
            view=view,
            ephemeral=True
        )
        
    select.callback = select_callback
    view.add_item(select)
    embed = discord.Embed(
        title="Manda codice lobby",
        color=discord.Color.blue(),
        description="Scegli la lobby a cui mandare il codice"
    )
    await interaction.response.send_message(
        embed=embed, view=view, ephemeral=True
    )