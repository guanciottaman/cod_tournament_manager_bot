import discord

from typing import Any

from ui.embeds.event_builders import build_event_channels_embed, build_event_embed, LOBBY_MODES
from ui.views.registra_team_view import RegistraTeamView
from ui.views.event_panel_view import EventPanelView
from services.event_service import get_event_info, set_event_status, get_placement_settings, get_teams_by_event
from services.server_service import check_channel_permissions
from config.permissions import BASE_SEND_PERMS

class EventChannelsView(discord.ui.View):
    def __init__(self, event_id: int, timeout: int | None = None):
        super().__init__(timeout=timeout)
        self.event_id = event_id
        self.manage_event_channel: discord.TextChannel | None = None
        self.register_team_channel: discord.TextChannel | None = None

    @discord.ui.select(
        cls=discord.ui.ChannelSelect,
        channel_types=[discord.ChannelType.text],
        placeholder="Seleziona canale registrazione...",
        min_values=1,
        max_values=1,
        row=0
    )
    async def team_register_callback(self, interaction: discord.Interaction, select: discord.ui.ChannelSelect[Any]):
        if interaction.guild is None:
            return
        c_id = select.values[0].id
        channel = interaction.guild.get_channel(c_id)
        if not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message("Canale non trovato!", ephemeral=True)
            return
        missing = await check_channel_permissions(channel, interaction.guild, BASE_SEND_PERMS)
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
        self.register_team_channel = channel
        await interaction.response.edit_message(
            embed=build_event_channels_embed(
                self.register_team_channel, self.manage_event_channel
            )
        )

    @discord.ui.select(
        cls=discord.ui.ChannelSelect,
        channel_types=[discord.ChannelType.text],
        placeholder="Seleziona canale pannello evento...",
        min_values=1,
        max_values=1,
        row=1
    )
    async def event_panel_select(self, interaction: discord.Interaction, select: discord.ui.ChannelSelect[Any]):
        if interaction.guild is None:
            return
        c_id = select.values[0].id
        channel = interaction.guild.get_channel(c_id)
        if not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message("Canale non trovato!", ephemeral=True)
            return
        missing = await check_channel_permissions(channel, interaction.guild, BASE_SEND_PERMS)
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
        self.manage_event_channel = channel
        await interaction.response.edit_message(
            embed=build_event_channels_embed(
                self.register_team_channel, self.manage_event_channel
            )
        )


    @discord.ui.button(
        label="Conferma",
        style=discord.ButtonStyle.green,
        row=2
    )
    async def confirm_button(self, interaction: discord.Interaction, button: discord.ui.Button[Any]):
        if interaction.guild is None:
            return
        await interaction.response.defer(ephemeral=True)
        event = await get_event_info(self.event_id, interaction.guild.id)
        if event is None:
            await interaction.followup.send("C'è stato un errore!", ephemeral=True)
            return
        team_register_embed = discord.Embed(
            title=event.name,
            color=discord.Color.blue(),
            description=f"""
                **Giocatori per team:** {event.players_per_team}
                **Match:** {event.matches_number}
                **Modalità:** {LOBBY_MODES[event.lobby_mode]}
                **Scarta partita peggiore:** {'ON' if event.drop_worst_match else 'OFF'}

                Usa i bottoni qui sotto per registrare il tuo team, modificarlo o eliminarlo.
            """
        )
        if not isinstance(self.register_team_channel, discord.TextChannel):
            return
        await self.register_team_channel.send(
            embed=team_register_embed,
            view=RegistraTeamView(self.event_id)
        )
        placement_settings = await get_placement_settings(self.event_id)
        teams = await get_teams_by_event(self.event_id)
        event_panel_embed = build_event_embed(event, interaction.guild, placement_settings, teams)
        if not isinstance(self.manage_event_channel, discord.TextChannel):
            return
        await self.manage_event_channel.send(
            embed=event_panel_embed,
            view=EventPanelView(self.event_id)
        )
        await set_event_status(self.event_id, "ready")
        await interaction.followup.send(f"Evento creato con successo!", ephemeral=True)