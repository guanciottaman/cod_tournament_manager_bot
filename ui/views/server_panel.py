import discord

from typing import Any

from services.server_service import get_server_config, check_server_registered
from ui.embeds.event_builders import build_server_config_embed
from ui.modals.nome_evento import NomeEventoModal
from ui.views.setup_view import SetupViewPage1, DeleteServerView


class ServerPanelView(discord.ui.View):
    def __init__(self, timeout: int | None = None):
        super().__init__(timeout=timeout)

    
    @discord.ui.button(
        label="Crea evento",
        style=discord.ButtonStyle.green,
        row=0,
        custom_id="server_panel:create_event"
    )
    async def create_event(self, interaction: discord.Interaction, button: discord.ui.Button[Any]):
        await interaction.response.send_modal(NomeEventoModal())


    @discord.ui.button(
        label="Modifica configurazione",
        emoji="✏️",
        style=discord.ButtonStyle.grey,
        row=1,
        custom_id="server_panel:edit_config"
    )
    async def edit_server_config(self, interaction: discord.Interaction, button: discord.ui.Button[Any]):
        if interaction.guild is None:
            return
        config = await get_server_config(interaction.guild.id)
        if config is None:
            await interaction.response.send_message("Il server non è stato configurato correttamente!", ephemeral=True)
            return
        await interaction.response.send_message(
            embed=build_server_config_embed(interaction.guild, config),
            view=SetupViewPage1(interaction.guild.id, config, True),
            ephemeral=True
        )

    @discord.ui.button(
        label="Elimina configurazione",
        emoji="🗑️",
        style=discord.ButtonStyle.red,
        row=1,
        custom_id="server_panel:delete_config"
    )
    async def delete_server_config(self, interaction: discord.Interaction, button: discord.ui.Button[Any]):
        if interaction.guild is None:
            return
        exists = await check_server_registered(interaction.guild.id)
        if not exists:
            await interaction.response.send_message("Il tuo server non è registrato!", ephemeral=True)
            return
        await interaction.response.send_message(view=DeleteServerView(), ephemeral=True)