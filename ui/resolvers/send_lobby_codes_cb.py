import discord

from services.event_service import get_leader_ids
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

        failed = 0
        user_ids = set(leader_ids)

        for user_id in user_ids:
            if user_id == interaction.client.user.id:
                continue

            member = guild.get_member(user_id)

            if member is None:
                try:
                    member = await guild.fetch_member(user_id)
                except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                    failed += 1
                    continue

            try:
                await member.send(embed=embed)
            except (discord.Forbidden, discord.HTTPException):
                failed += 1

        if failed:
            await interaction.followup.send(
                f"Lobby inviate, ma {failed} utenti non hanno ricevuto il DM",
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