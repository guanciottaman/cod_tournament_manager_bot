import discord

from services.server_service import *


class SetupView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.ranking_channel: discord.TextChannel | None = None
        self.admin_role: discord.Role | None = None

    @discord.ui.select(
        cls=discord.ui.ChannelSelect,
        channel_types=[discord.ChannelType.text],
        placeholder="Seleziona il canale per le classifiche",
        min_values=1,
        max_values=1,
        row=0
    )
    async def select_ranking_channel(self, interaction: discord.Interaction, select: discord.ui.ChannelSelect):
        self.ranking_channel = select.values[0]
        await interaction.response.defer()

    
    @discord.ui.select(
        cls=discord.ui.RoleSelect,
        placeholder="Seleziona il ruolo che potrà dare penalità o gestire eventi",
        min_values=1,
        max_values=1,
        row=1
    )
    async def select_admin_role(self, interaction: discord.Interaction, select: discord.ui.RoleSelect):
        self.admin_role = select.values[0]
        await interaction.response.defer()

    @discord.ui.button(
        label="Conferma",
        style=discord.ButtonStyle.green,
        row=2
    )
    async def confirm_setup(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not all([
            self.ranking_channel,
            self.admin_role
        ]):
            await interaction.response.send_message("Tutte le opzioni devono essere inserite!", ephemeral=True)
            return
        
        success = await create_server_config(
            interaction.guild_id,
            self.ranking_channel.id,
            self.admin_role.id
        )

        if not success:
            await interaction.response.send_message(
                "Il tuo server è già registrato!",
                ephemeral=True
            )
            return
        await interaction.response.send_message("Il tuo server è stato registrato con successo!", ephemeral=True)


class DeleteServerView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=30)

    @discord.ui.button(
        label="❌ Annulla",
        style=discord.ButtonStyle.gray
    )
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(
            content="Operazione annullata.",
            view=None
        )

    @discord.ui.button(
        label="🗑 Conferma eliminazione",
        style=discord.ButtonStyle.danger
    )
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        await delete_server_config(interaction.guild_id)
        await interaction.response.edit_message(
            content="Server rimosso dal sistema con successo.",
            view=None
        )