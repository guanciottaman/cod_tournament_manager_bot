import discord

from ui.modals.nome_evento import NomeEventoModal


class ServerPanelView(discord.ui.View):
    def __init__(self, timeout: int | None = None):
        super().__init__(timeout=None)
    
    @discord.ui.button(
        label="Crea evento",
        style=discord.ButtonStyle.green,
        custom_id="1"
    )
    async def create_event(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(NomeEventoModal())