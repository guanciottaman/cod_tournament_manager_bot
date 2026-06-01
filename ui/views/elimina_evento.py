import discord

from services.event_service import delete_event

class EliminaEventoView(discord.ui.View):
    def __init__(self, event_id: int):
        super().__init__(timeout=None)
        self.event_id = event_id
    
    @discord.ui.button(
        label="Annulla",
        style=discord.ButtonStyle.secondary
    )
    async def cancel_delete_event(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Eliminazione evento annullata.", ephemeral=True)

    @discord.ui.button(
            label="🗑️Conferma eliminazione",
            style=discord.ButtonStyle.danger
    )
    async def delete_event_confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        await delete_event(interaction.guild_id, self.event_id)
        await interaction.response.send_message("Evento eliminato con successo!", ephemeral=True)