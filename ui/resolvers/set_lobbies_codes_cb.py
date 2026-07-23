import discord

from typing import Any

from models.lobby import Lobby
from models.event import Event
from services.lobby_service import get_lobbies
from services.event_service import (get_lobby_codes_channels, get_lobby_role,
    set_lobby_codes_channels, lock_channel_for_lobby)
from services.server_service import check_channel_permissions
from config.permissions import LOBBY_CODES_CHANNEL_PERMS

async def set_lobby_codes_callback(interaction: discord.Interaction, event: Event):
    if interaction.guild is None:
        return
    lobbies = await get_lobbies(event.event_id)
    embed = discord.Embed(
        title="Seleziona canali",
        color=discord.Color.blue()
    )
    emb_description = "Seleziona i canali dove mandare i codici lobby.\nCanali attuali:\n"
    current_channels = await get_lobby_codes_channels(event.event_id)
    if current_channels is not None:
        for lobby in lobbies:
            channel_id = current_channels.get(lobby.lobby_id)

            if channel_id:
                channel = interaction.guild.get_channel(channel_id)
                if channel:
                    emb_description += f"LOBBY {lobby.name} | {channel.mention}\n"
    embed.description = emb_description
    channels: dict[int, int] = dict()
    view = discord.ui.View()

    def make_callback(current_lobby: Lobby, select: discord.ui.ChannelSelect[Any]):
        async def select_callback(interaction: discord.Interaction):
            selected_channel = select.values[0]
            if interaction.guild is None:
                return
            channel = interaction.guild.get_channel(selected_channel.id)

            if channel is None:
                await interaction.response.send_message(
                    "Canale non trovato",
                    ephemeral=True
                )
                return

            channels[current_lobby.lobby_id] = channel.id
            
            embed = discord.Embed(
                title="Seleziona canali",
                color=discord.Color.blue()
            )
            emb_description = "Seleziona i canali dove mandare i codici lobby.\nCanali attuali:\n"
            for lobby in lobbies:
                channel_id = channels.get(lobby.lobby_id)

                if channel_id:
                    channel = interaction.guild.get_channel(channel_id)
                    if channel is not None:
                        emb_description += f"LOBBY {lobby.name} | {channel.mention}\n"
            embed.description = emb_description
            await interaction.response.edit_message(
                embed=embed,
                view=view
            )
        return select_callback
    
    for lobby in lobbies:
        select: discord.ui.ChannelSelect[Any] = discord.ui.ChannelSelect(
            placeholder=f"Seleziona il canale per la lobby {lobby.name}",
            channel_types=[discord.ChannelType.text],
            min_values=1,
            max_values=1
        )
        select.callback = make_callback(lobby, select)
        view.add_item(select)
    confirm_btn: discord.ui.Button[Any] = discord.ui.Button(
        style=discord.ButtonStyle.green,
        label="Conferma"
    )
    async def confirm_callback(interaction: discord.Interaction):
        if interaction.guild is None:
            return
        if len(lobbies) != len(channels):
            await interaction.response.send_message("Non hai impostato tutti i canali!", ephemeral=True)
            return
        
        for lobby_id, channel_id in channels.items():
            channel = interaction.guild.get_channel(channel_id)
            if channel is None:
                await interaction.response.send_message("Il canale non esiste!", ephemeral=True)
                return
            
            missing = await check_channel_permissions(
                channel,
                interaction.guild,
                LOBBY_CODES_CHANNEL_PERMS
            )
            if missing:
                embed = discord.Embed(
                    title="Permessi mancanti",
                    color=discord.Color.red(),
                    description=(
                        f"Mancano i seguenti permessi per il canale {channel.mention}:\n"
                        + "\n".join(f"- {perm}" for perm in missing)
                    )
                )

                await interaction.response.send_message(
                    embed=embed,
                    ephemeral=True
                )
                return

        for lobby_id, channel_id in channels.items():
            role_id = await get_lobby_role(event.event_id, lobby_id)

            if role_id is None:
                await interaction.response.send_message("Il ruolo non è registrato!", ephemeral=True)
                return

            channel = interaction.guild.get_channel(channel_id)
            role = interaction.guild.get_role(role_id)

            if not isinstance(channel, discord.TextChannel):
                await interaction.response.send_message("Il canale non esiste!", ephemeral=True)
                return

            if role is None:
                await interaction.response.send_message("Il ruolo non esiste!", ephemeral=True)
                return

            await lock_channel_for_lobby(channel, role)
        await set_lobby_codes_channels(event.event_id, channels)
        await interaction.response.send_message("Hai impostato correttamente i canali!", ephemeral=True)
    confirm_btn.callback = confirm_callback
    view.add_item(confirm_btn)
    await interaction.response.send_message(
        embed=embed,
        view=view,
        ephemeral=True
    )