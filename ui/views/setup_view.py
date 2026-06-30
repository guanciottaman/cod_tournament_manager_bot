import discord

from services.server_service import *
from ui.embeds.event_builders import build_server_config_embed


class SetupView(discord.ui.View):
    def __init__(self, edit_mode: bool = False):
        super().__init__(timeout=None)
        self.ranking_channel: discord.TextChannel | None = None
        self.admin_role: discord.Role | None = None
        self.live_ranking_channel: discord.TextChannel | None = None
        self.edit_mode = edit_mode

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
        await interaction.response.edit_message(
            embed=build_server_config_embed(
                interaction.guild.name,
                self.ranking_channel,
                self.admin_role,
                self.live_ranking_channel
            )
        )

    
    @discord.ui.select(
        cls=discord.ui.RoleSelect,
        placeholder="Seleziona il ruolo che potrà dare penalità o gestire eventi",
        min_values=1,
        max_values=1,
        row=1
    )
    async def select_admin_role(self, interaction: discord.Interaction, select: discord.ui.RoleSelect):
        self.admin_role = select.values[0]
        await interaction.response.edit_message(
            embed=build_server_config_embed(
                interaction.guild.name,
                self.ranking_channel,
                self.admin_role,
                self.live_ranking_channel
            )
        )

    @discord.ui.select(
        cls=discord.ui.ChannelSelect,
        channel_types=[discord.ChannelType.text],
        placeholder="Seleziona il canale per le classifiche live",
        min_values=1,
        max_values=1,
        row=2
    )
    async def select_live_ranking_channel(self, interaction: discord.Interaction, select: discord.ui.ChannelSelect):
        self.live_ranking_channel = select.values[0]
        await interaction.response.edit_message(
            embed=build_server_config_embed(
                interaction.guild.name,
                self.ranking_channel,
                self.admin_role,
                self.live_ranking_channel
            )
        )

    @discord.ui.button(
        label="Conferma",
        style=discord.ButtonStyle.green,
        row=2
    )
    async def confirm_setup(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.edit_mode:
            if not all([
                self.ranking_channel,
                self.admin_role,
                self.live_ranking_channel
            ]):
                await interaction.response.send_message("Tutte le opzioni devono essere inserite!", ephemeral=True)
                return
            success = await create_server_config(
                interaction.guild_id,
                self.ranking_channel.id,
                self.admin_role.id,
                self.live_ranking_channel.id
            )

            if not success:
                await interaction.response.send_message(
                    "Il tuo server è già registrato!",
                    ephemeral=True
                )
                return
        else:
            if self.edit_mode and not any([
                self.ranking_channel,
                self.admin_role,
                self.live_ranking_channel
            ]):
                await interaction.response.send_message(
                    "Non hai modificato nessun valore.",
                    ephemeral=True
                )
                return
            await edit_server_config(
                interaction.guild_id,
                ranking_channel_id=self.ranking_channel.id if self.ranking_channel else None,
                admin_role_id=self.admin_role.id if self.admin_role else None,
                live_ranking_channel_id=self.live_ranking_channel.id if self.live_ranking_channel else None,
            )
        await interaction.response.send_message(f"Il tuo server è stato {'registrato' if not self.edit_mode else 'modificato'} con successo!", ephemeral=True)


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