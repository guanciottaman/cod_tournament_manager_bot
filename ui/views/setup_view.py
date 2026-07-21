import discord

from models.server_config import ServerConfig
from services.server_service import *
from ui.embeds.event_builders import build_server_config_embed
from config.permissions import RANKING_CHANNEL_PERMS, READ_HISTORY_PERMS


class SetupViewPage1(discord.ui.View):
    def __init__(self, guild_id: int, config: ServerConfig | None = None, edit_mode: bool = False):
        super().__init__(timeout=None)
        self.config = ServerConfig(guild_id) if config is None else config
        self.edit_mode = edit_mode

    @discord.ui.select(
        cls=discord.ui.ChannelSelect,
        channel_types=[discord.ChannelType.text],
        placeholder="Seleziona il canale per il pannello di gestione",
        min_values=1,
        max_values=1,
        row=0
    )
    async def select_panel_channel(self, interaction: discord.Interaction, select: discord.ui.ChannelSelect):
        if interaction.guild is None:
            await interaction.response.send_message("Non puoi usarmi dai DM", ephemeral=True)
            return
        selected = select.values[0]
        self.config.panel_channel_id = selected.id
        panel_channel = interaction.guild.get_channel(self.config.panel_channel_id)
        if panel_channel is None:
            await interaction.response.send_message("Canale non trovato!", ephemeral=True)
            return
        missing = await check_channel_permissions(panel_channel, interaction.guild, RANKING_CHANNEL_PERMS)
        if missing:
            embed = discord.Embed(
                title="Permessi mancanti",
                color=discord.Color.red(),
                description=(
                    f"Mancano i seguenti permessi per il canale {panel_channel.mention}:\n"
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
                interaction.guild,
                self.config
            )
        )

    @discord.ui.select(
        cls=discord.ui.ChannelSelect,
        channel_types=[discord.ChannelType.text],
        placeholder="Seleziona il canale per le classifiche",
        min_values=1,
        max_values=1,
        row=1
    )
    async def select_ranking_channel(self, interaction: discord.Interaction, select: discord.ui.ChannelSelect):
        if interaction.guild is None:
            await interaction.response.send_message("Non puoi usarmi dai DM", ephemeral=True)
            return
        selected = select.values[0]
        self.config.ranking_channel_id = selected.id
        ranking_channel = interaction.guild.get_channel(self.config.ranking_channel_id)
        if ranking_channel is None:
            await interaction.response.send_message("Canale non trovato!", ephemeral=True)
            return
        missing = await check_channel_permissions(ranking_channel, interaction.guild, RANKING_CHANNEL_PERMS)
        if missing:
            embed = discord.Embed(
                title="Permessi mancanti",
                color=discord.Color.red(),
                description=(
                    f"Mancano i seguenti permessi per il canale {ranking_channel.mention}:\n"
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
                interaction.guild,
                self.config
            )
        )

    
    @discord.ui.select(
        cls=discord.ui.RoleSelect,
        placeholder="Seleziona il ruolo che potrà gestire eventi",
        min_values=1,
        max_values=1,
        row=2
    )
    async def select_admin_role(self, interaction: discord.Interaction, select: discord.ui.RoleSelect):
        if interaction.guild is None:
            await interaction.response.send_message("Non puoi usarmi dai DM", ephemeral=True)
            return
        selected = select.values[0]
        self.config.admin_role_id = selected.id
        admin_role = interaction.guild.get_role(selected.id)
        if admin_role is None:
            await interaction.response.send_message("Questo ruolo non esiste!", ephemeral=True)
            return
        await interaction.response.edit_message(
            embed=build_server_config_embed(
                interaction.guild,
                self.config
            )
        )
    
    @discord.ui.button(
        label="➡️",
        style=discord.ButtonStyle.blurple,
        row=3
    )
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.guild is None:
            return
        await interaction.response.edit_message(
            embed=build_server_config_embed(
                interaction.guild,
                self.config
            ),
            view=SetupViewPage2(self.config)
        )

    @discord.ui.button(
        label="Conferma",
        style=discord.ButtonStyle.green,
        row=4
    )
    async def confirm_setup(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.guild is None:
            return
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
                self.config.panel_channel_id,
                self.config.ranking_channel_id,
                self.config.admin_role_id,
                self.config.live_ranking_channel_id,
                self.config.lobbies_channel_id
            ]):
                await interaction.response.send_message("Tutte le opzioni devono essere inserite!", ephemeral=True)
                return
            if interaction.guild_id is None:
                await interaction.response.send_message("Non puoi usarmi dai DM", ephemeral=True)
                return
            success = await create_server_config(
                interaction.guild_id,
                self.config
            )

            if not success:
                await interaction.response.send_message(
                    "Il tuo server è già registrato!",
                    ephemeral=True
                )
                return
        else:
            if self.edit_mode and not any([
                self.config.panel_channel_id,
                self.config.ranking_channel_id,
                self.config.admin_role_id,
                self.config.live_ranking_channel_id,
                self.config.lobbies_channel_id
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
                self.config
            )
        await interaction.response.send_message(
            f"Il tuo server è stato {'registrato' if not self.edit_mode else 'modificato'} con successo!",
            ephemeral=True
        )


class SetupViewPage2(discord.ui.View):
    def __init__(self, config: ServerConfig, edit_mode: bool = False):
        super().__init__(timeout=None)
        self.config = config
        self.edit_mode = edit_mode
    
    @discord.ui.select(
        cls=discord.ui.ChannelSelect,
        channel_types=[discord.ChannelType.text],
        placeholder="Seleziona il canale per le classifiche live",
        min_values=1,
        max_values=1,
        row=0
    )
    async def select_live_ranking_channel(self, interaction: discord.Interaction, select: discord.ui.ChannelSelect):
        if interaction.guild is None:
            await interaction.response.send_message("Non puoi usarmi dai DM", ephemeral=True)
            return
        selected = select.values[0]
        self.config.live_ranking_channel_id = selected.id
        live_ranking_channel = interaction.guild.get_channel(selected.id)
        if live_ranking_channel is None:
            await interaction.response.send_message("Canale non trovato!", ephemeral=True)
            return
        missing = await check_channel_permissions(
            live_ranking_channel,
            interaction.guild,
            RANKING_CHANNEL_PERMS | READ_HISTORY_PERMS
        )
        if missing:
            embed = discord.Embed(
                title="Permessi mancanti",
                color=discord.Color.red(),
                description=(
                    f"Mancano i seguenti permessi per il canale {live_ranking_channel.mention}:\n"
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
                interaction.guild,
                self.config
            )
        )
    
    @discord.ui.select(
        cls=discord.ui.ChannelSelect,
        channel_types=[discord.ChannelType.text],
        placeholder="Seleziona il canale dove mandare le lobby",
        min_values=1,
        max_values=1,
        row=1
    )
    async def select_lobbies_channel(self, interaction: discord.Interaction, select: discord.ui.ChannelSelect):
        if interaction.guild is None:
            await interaction.response.send_message("Non puoi usarmi dai DM", ephemeral=True)
            return
        selected = select.values[0]
        self.config.lobbies_channel_id = selected.id
        lobbies_channel = interaction.guild.get_channel(selected.id)
        if lobbies_channel is None:
            await interaction.response.send_message("Canale non trovato!", ephemeral=True)
            return
        missing = await check_channel_permissions(lobbies_channel, interaction.guild, RANKING_CHANNEL_PERMS)
        if missing:
            embed = discord.Embed(
                title="Permessi mancanti",
                color=discord.Color.red(),
                description=(
                    f"Mancano i seguenti permessi per il canale {lobbies_channel.mention}:\n"
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
                interaction.guild,
                self.config
            )
        )

    @discord.ui.button(
        label="⬅️",
        style=discord.ButtonStyle.blurple,
        row=2
    )
    async def previous_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.guild is None:
            return
        await interaction.response.edit_message(
            embed=build_server_config_embed(
                interaction.guild,
                self.config
            ),
            view=SetupViewPage1(interaction.guild.id, self.config)
        )

    @discord.ui.button(
        label="Conferma",
        style=discord.ButtonStyle.green,
        row=3
    )
    async def confirm_setup(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.guild is None:
            return
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
                self.config.panel_channel_id,
                self.config.ranking_channel_id,
                self.config.admin_role_id,
                self.config.live_ranking_channel_id,
                self.config.lobbies_channel_id
            ]):
                await interaction.response.send_message("Tutte le opzioni devono essere inserite!", ephemeral=True)
                return
            if interaction.guild_id is None:
                await interaction.response.send_message("Non puoi usarmi dai DM", ephemeral=True)
                return
            success = await create_server_config(
                interaction.guild_id,
                self.config
            )

            if not success:
                await interaction.response.send_message(
                    "Il tuo server è già registrato!",
                    ephemeral=True
                )
                return
        else:
            if self.edit_mode and not any([
                self.config.panel_channel_id,
                self.config.ranking_channel_id,
                self.config.admin_role_id,
                self.config.live_ranking_channel_id,
                self.config.lobbies_channel_id
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
                self.config
            )
        await interaction.response.send_message(
            f"Il tuo server è stato {'registrato' if not self.edit_mode else 'modificato'} con successo!",
            ephemeral=True
        )

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