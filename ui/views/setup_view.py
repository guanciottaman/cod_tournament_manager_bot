import discord

from services.server_service import *
from ui.embeds.event_builders import build_server_config_embed
from config.permissions import RANKING_CHANNEL_PERMS, READ_HISTORY_PERMS


class SetupView(discord.ui.View):
    def __init__(self, edit_mode: bool = False):
        super().__init__(timeout=None)
        self.ranking_channel: discord.TextChannel | None = None
        self.admin_role: discord.Role | None = None
        self.live_ranking_channel: discord.TextChannel | None = None
        self.lobbies_channel: discord.TextChannel | None = None
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
        selected = select.values[0]
        self.ranking_channel = interaction.guild.get_channel(selected.id)
        if self.ranking_channel is None:
            await interaction.response.send_message("Canale non trovato!", ephemeral=True)
            return
        if interaction.guild is None:
            await interaction.response.send_message("Non puoi usarmi dai DM", ephemeral=True)
            return
        missing = await check_channel_permissions(self.ranking_channel, interaction.guild, RANKING_CHANNEL_PERMS)
        if missing:
            embed = discord.Embed(
                title="Permessi mancanti",
                color=discord.Color.red(),
                description=(
                    f"Mancano i seguenti permessi per il canale {self.ranking_channel.mention}:\n"
                    + "\n".join(f"- {perm}" for perm in missing)
                )
            )

            await interaction.response.send_message(
                embed=embed,
                ephemeral=True
            )
            return
        await interaction.response.edit_message(
            embed=build_server_config_embed(
                interaction.guild.name,
                self.ranking_channel,
                self.admin_role,
                self.live_ranking_channel,
                self.lobbies_channel
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
        selected = select.values[0]
        self.admin_role = interaction.guild.get_role(selected.id)
        if interaction.guild is None:
            await interaction.response.send_message("Non puoi usarmi dai DM", ephemeral=True)
            return
        await interaction.response.edit_message(
            embed=build_server_config_embed(
                interaction.guild.name,
                self.ranking_channel,
                self.admin_role,
                self.live_ranking_channel,
                self.lobbies_channel
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
        selected = select.values[0]
        self.live_ranking_channel = interaction.guild.get_channel(selected.id)
        if self.live_ranking_channel is None:
            await interaction.response.send_message("Canale non trovato!", ephemeral=True)
            return
        if interaction.guild is None:
            await interaction.response.send_message("Non puoi usarmi dai DM", ephemeral=True)
            return
        missing = await check_channel_permissions(
            self.live_ranking_channel,
            interaction.guild,
            RANKING_CHANNEL_PERMS | READ_HISTORY_PERMS
        )
        if missing:
            embed = discord.Embed(
                title="Permessi mancanti",
                color=discord.Color.red(),
                description=(
                    f"Mancano i seguenti permessi per il canale {self.ranking_channel.mention}:\n"
                    + "\n".join(f"- {perm}" for perm in missing)
                )
            )

            await interaction.response.send_message(
                embed=embed,
                ephemeral=True
            )
            return
        await interaction.response.edit_message(
            embed=build_server_config_embed(
                interaction.guild.name,
                self.ranking_channel,
                self.admin_role,
                self.live_ranking_channel,
                self.lobbies_channel
            )
        )
    
    @discord.ui.select(
        cls=discord.ui.ChannelSelect,
        channel_types=[discord.ChannelType.text],
        placeholder="Seleziona il canale dove mandare le lobby",
        min_values=1,
        max_values=1,
        row=3
    )
    async def select_lobbies_channel(self, interaction: discord.Interaction, select: discord.ui.ChannelSelect):
        selected = select.values[0]
        self.lobbies_channel = interaction.guild.get_channel(selected.id)
        if self.lobbies_channel is None:
            await interaction.response.send_message("Canale non trovato!", ephemeral=True)
            return
        if interaction.guild is None:
            await interaction.response.send_message("Non puoi usarmi dai DM", ephemeral=True)
            return
        missing = await check_channel_permissions(self.lobbies_channel, interaction.guild, RANKING_CHANNEL_PERMS)
        if missing:
            embed = discord.Embed(
                title="Permessi mancanti",
                color=discord.Color.red(),
                description=(
                    f"Mancano i seguenti permessi per il canale {self.ranking_channel.mention}:\n"
                    + "\n".join(f"- {perm}" for perm in missing)
                )
            )

            await interaction.response.send_message(
                embed=embed,
                ephemeral=True
            )
            return
        await interaction.response.edit_message(
            embed=build_server_config_embed(
                interaction.guild.name,
                self.ranking_channel,
                self.admin_role,
                self.live_ranking_channel,
                self.lobbies_channel
            )
        )

    @discord.ui.button(
        label="Conferma",
        style=discord.ButtonStyle.green,
        row=4
    )
    async def confirm_setup(self, interaction: discord.Interaction, button: discord.ui.Button):
        missing = await check_bot_permissions(interaction.guild)
        if missing:
            embed = discord.Embed(
                title="Permessi mancanti",
                color=discord.Color.red()
            )
            emb_description = "Al bot mancano i seguenti permessi:\n"
            for m in missing:
                emb_description += f"- {m}\n"
            embed.description = emb_description
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        if not self.edit_mode:
            if not all([
                self.ranking_channel,
                self.admin_role,
                self.live_ranking_channel,
                self.lobbies_channel
            ]):
                await interaction.response.send_message("Tutte le opzioni devono essere inserite!", ephemeral=True)
                return
            if interaction.guild_id is None:
                await interaction.response.send_message("Non puoi usarmi dai DM", ephemeral=True)
                return
            success = await create_server_config(
                interaction.guild_id,
                self.ranking_channel.id,
                self.admin_role.id,
                self.live_ranking_channel.id,
                self.lobbies_channel.id
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
                self.live_ranking_channel,
                self.lobbies_channel
            ]):
                await interaction.response.send_message(
                    "Non hai modificato nessun valore.",
                    ephemeral=True
                )
                return
            if interaction.guild_id is None:
                await interaction.response.send_message("Non puoi usarmi dai DM", ephemeral=True)
                return
            await edit_server_config(
                interaction.guild_id,
                ranking_channel_id=self.ranking_channel.id if self.ranking_channel else None,
                admin_role_id=self.admin_role.id if self.admin_role else None,
                live_ranking_channel_id=self.live_ranking_channel.id if self.live_ranking_channel else None,
                lobbies_channel_id=self.lobbies_channel.id if self.lobbies_channel else None
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
        if interaction.guild_id is None:
            await interaction.response.send_message("Non puoi usarmi dai DM", ephemeral=True)
            return
        await delete_server_config(interaction.guild_id)
        await interaction.response.edit_message(
            content="Server rimosso dal sistema con successo.",
            view=None
        )