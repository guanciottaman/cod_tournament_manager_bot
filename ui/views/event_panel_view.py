import discord

from typing import Any

from services.event_service import get_event_info, get_placement_points, get_teams_by_event
from services.lobby_service import get_lobbies
from services.server_service import get_ranking_channel_id, get_lobbies_channel_id
from ui.embeds.event_builders import build_event_embed
from ui.embeds.lobby_builders import build_info_lobby_embed
from ui.views.elimina_evento import EliminaEventoView
from ui.views.team_selector import TeamsSelectorView
from ui.resolvers.termina_evento_cb import termina_evento_callback
from ui.resolvers.lobby_config_cb import start_lobby_config
from ui.resolvers.start_event_cb import start_event_callback
from ui.resolvers.set_lobbies_codes_cb import set_lobby_codes_callback
from ui.resolvers.info_lobby_cb import info_lobbies_callback
from ui.resolvers.controlla_risultati_cb import controlla_risultati_callback

class ConfigLobby(discord.ui.Button[Any]):
    def __init__(self, event_id: int):
        super().__init__(
            label="Configura lobby",
            emoji="⚙️",
            style=discord.ButtonStyle.blurple,
            row=0,
            custom_id=f"event_panel:config_lobby:{event_id}"
        )
        self.event_id = event_id

    async def callback(self, interaction: discord.Interaction):
        if interaction.guild is None:
            return
        event = await get_event_info(self.event_id, interaction.guild.id)
        if event is None:
            return
        if event.status != "ready":
            await interaction.response.send_message("Non puoi configurare le lobby in questa fase dell'evento!", ephemeral=True)
            return
        await start_lobby_config(interaction, event)

class AvviaEvento(discord.ui.Button[Any]):
    def __init__(self, event_id: int):
        super().__init__(
            label="Avvia evento",
            emoji="▶️",
            style=discord.ButtonStyle.green,
            row=0,
            custom_id=f"event_panel:avvia_evento:{event_id}"
        )
        self.event_id = event_id

    async def callback(self, interaction: discord.Interaction):
        if interaction.guild is None:
            return
        event = await get_event_info(self.event_id, interaction.guild.id)
        if event is None:
            return
        if event.status != "setup":
            await interaction.response.send_message("Non puoi avviare l'evento in questa fase!", ephemeral=True)
            return
        await start_event_callback(interaction, event)


class ControllaRisultati(discord.ui.Button[Any]):
    def __init__(self, event_id: int):
        super().__init__(
            label="Controlla risultati",
            emoji="☑️",
            style=discord.ButtonStyle.blurple,
            row=0,
            custom_id=f"event_panel:controlla_risultati:{event_id}"
        )
        self.event_id = event_id

    async def callback(self, interaction: discord.Interaction):
        if interaction.guild is None:
            return
        event = await get_event_info(self.event_id, interaction.guild.id)
        if event is None:
            await interaction.response.send_message("Evento non trovato!", ephemeral=True)
            return
        await controlla_risultati_callback(interaction, event)

class RicaricaButton(discord.ui.Button[Any]):
    def __init__(self, event_id: int):
        super().__init__(
            label="Ricarica",
            emoji="🔄",
            style=discord.ButtonStyle.grey,
            row=0,
            custom_id=f"event_panel:ricarica:{event_id}"
        )
        self.event_id = event_id

    async def callback(self, interaction: discord.Interaction):
        if interaction.guild is None:
            return
        event = await get_event_info(self.event_id, interaction.guild.id)
        if event is None:
            await interaction.response.send_message("Evento non trovato!", ephemeral=True)
            return
        placement_points = await get_placement_points(self.event_id)
        teams = await get_teams_by_event(self.event_id)
        await interaction.response.edit_message(
            embed=build_event_embed(
                event, interaction.guild, placement_points, teams
            ),
            view=EventPanelView(self.event_id)
        )

class ImpostaCanaliLobby(discord.ui.Button[Any]):
    def __init__(self, event_id: int):
        super().__init__(
            label="Imposta canali lobby",
            emoji="🗒️",
            style=discord.ButtonStyle.blurple,
            row=1,
            custom_id=f"event_panel:imposta_canali_lobby:{event_id}"
        )
        self.event_id = event_id

    async def callback(self, interaction: discord.Interaction):
        if interaction.guild is None:
            return
        event = await get_event_info(self.event_id, interaction.guild.id)
        if event is None:
            return
        await set_lobby_codes_callback(interaction, event)

class InviaLobby(discord.ui.Button[Any]):
    def __init__(self, event_id: int):
        super().__init__(
            label="Invia lobby",
            emoji="📨",
            style=discord.ButtonStyle.blurple,
            row=1,
            custom_id=f"event_panel:invia_lobby:{event_id}"
        )
        self.event_id = event_id

    async def callback(self, interaction: discord.Interaction):
        if interaction.guild is None:
            return
        await interaction.response.defer(ephemeral=True)
        lobbies = await get_lobbies(self.event_id)
        event = await get_event_info(self.event_id, interaction.guild.id)
        if event is None:
            return
        embed = build_info_lobby_embed(event.name, lobbies, show_kd=False)

        guild = interaction.guild

        lobbies_channel_id = await get_lobbies_channel_id(guild.id)
        if lobbies_channel_id is None:
            await interaction.followup.send("Non hai impostato un canale dove mandare le lobby!", ephemeral=True)
            return
        lobbies_channel = guild.get_channel(lobbies_channel_id)
        if not isinstance(lobbies_channel, discord.TextChannel):
            await interaction.followup.send(
                "Devi selezionare un canale testuale nella config!",
                ephemeral=True
            )
            return
        await lobbies_channel.send(embed=embed)
        await interaction.followup.send(f"Lobby mandate nel canale {lobbies_channel.mention}", ephemeral=True)

class InfoLobby(discord.ui.Button[Any]):
    def __init__(self, event_id: int):
        super().__init__(
            label="Info lobby",
            emoji="ℹ️",
            style=discord.ButtonStyle.blurple,
            row=1,
            custom_id=f"event_panel:info_lobby:{event_id}"
        )
        self.event_id = event_id

    async def callback(self, interaction: discord.Interaction):
        if interaction.guild is None:
            return
        event = await get_event_info(self.event_id, interaction.guild.id)
        if event is None:
            return
        await info_lobbies_callback(interaction, event)

class InfoTeam(discord.ui.Button[Any]):
    def __init__(self, event_id: int):
        super().__init__(
            label="Info team",
            emoji="ℹ️",
            style=discord.ButtonStyle.blurple,
            row=2,
            custom_id=f"event_panel:info_team:{event_id}"
        )
        self.event_id = event_id

    async def callback(self, interaction: discord.Interaction):
        if interaction.guild is None:
            return
        event = await get_event_info(self.event_id, interaction.guild.id)
        if event is None:
            await interaction.response.send_message("Evento non trovato!", ephemeral=True)
            return
        teams = await get_teams_by_event(self.event_id)
        embed = discord.Embed(
            title="Info team",
            color=discord.Color.blue(),
            description="Scegli il team su cui vuoi informazioni"
        )
        await interaction.response.send_message(
            embed=embed,
            view=TeamsSelectorView(
                teams,
                event,
                "info",
                use_lobbies=True,
                lobbies=await get_lobbies(self.event_id),
                interaction=interaction
            ),
            ephemeral=True
        )

class SpostaTeam(discord.ui.Button[Any]):
    def __init__(self, event_id: int):
        super().__init__(
            label="Sposta team",
            emoji="⤵️",
            style=discord.ButtonStyle.blurple,
            row=2,
            custom_id=f"event_panel:sposta_team:{event_id}"
        )
        self.event_id = event_id

    async def callback(self, interaction: discord.Interaction):
        if interaction.guild is None:
            return
        event = await get_event_info(self.event_id, interaction.guild.id)
        if event is None:
            await interaction.response.send_message("Evento non trovato!", ephemeral=True)
            return
        if event.status != "setup":
            await interaction.response.send_message("Non puoi spostare team in questa fase dell'evento!", ephemeral=True)
            return
        teams = await get_teams_by_event(self.event_id)
        embed = discord.Embed(
            title="Sposta team",
            color=discord.Color.blue(),
            description="Scegli il team da spostare"
        )
        await interaction.response.send_message(
            embed=embed,
            view=TeamsSelectorView(
                teams,
                event,
                "switch",
                use_lobbies=True,
                lobbies=await get_lobbies(self.event_id),
                interaction=interaction
            ),
            ephemeral=True
        )

class ModificaTeam(discord.ui.Button[Any]):
    def __init__(self, event_id: int):
        super().__init__(
            label="Modifica team",
            emoji="✏️",
            style=discord.ButtonStyle.grey,
            row=2,
            custom_id=f"event_panel:modifica_team:{event_id}"
        )
        self.event_id = event_id

    async def callback(self, interaction: discord.Interaction):
        if interaction.guild is None:
            return
        event = await get_event_info(self.event_id, interaction.guild.id)
        if event is None:
            await interaction.response.send_message("Evento non trovato!", ephemeral=True)
            return
        teams = await get_teams_by_event(self.event_id)
        embed = discord.Embed(
            title="Modifica team",
            color=discord.Color.gold(),
            description="Scegli il team da modificare"
        )
        await interaction.response.send_message(
            embed=embed,
            view=TeamsSelectorView(
                teams,
                event,
                "edit",
                use_lobbies=True,
                lobbies=await get_lobbies(self.event_id),
                interaction=interaction
            ),
            ephemeral=True
        )

class PenalizzaTeam(discord.ui.Button[Any]):
    def __init__(self, event_id: int):
        super().__init__(
            label="Penalizza team",
            emoji="➖",
            style=discord.ButtonStyle.red,
            row=2,
            custom_id=f"event_panel:penalizza_team:{event_id}"
        )
        self.event_id = event_id

    async def callback(self, interaction: discord.Interaction):
        if interaction.guild is None:
            return
        event_id = self.event_id
        event = await get_event_info(self.event_id, interaction.guild.id)
        if event is None:
            return
        teams = await get_teams_by_event(event_id)
        embed = discord.Embed(
            title="Penalizza team",
            color=discord.Color.red(),
            description="Seleziona il team che vuoi penalizzare"
        )
        await interaction.response.send_message(
            embed=embed,
            view=TeamsSelectorView(
                teams,
                event,
                "penalize",
                use_lobbies=event.status in ("setup", "running"),
                lobbies=None if event.status not in ("setup", "running") else await get_lobbies(event_id),
                interaction=interaction
            ),
            ephemeral=True
        )

class EliminaTeam(discord.ui.Button[Any]):
    def __init__(self, event_id: int):
        super().__init__(
            label="Elimina team",
            emoji="🔨",
            style=discord.ButtonStyle.red,
            row=2,
            custom_id=f"event_panel:elimina_team:{event_id}"
        )
        self.event_id = event_id

    async def callback(self, interaction: discord.Interaction):
        if interaction.guild is None:
            return
        event = await get_event_info(self.event_id, interaction.guild.id)
        if event is None:
            await interaction.response.send_message("Evento non trovato!", ephemeral=True)
            return
        teams = await get_teams_by_event(self.event_id)
        embed = discord.Embed(
            title="Elimina team",
            color=discord.Color.red(),
            description="Scegli il team da eliminare"
        )
        await interaction.response.send_message(
            embed=embed,
            view=TeamsSelectorView(
                teams,
                event,
                "delete",
                use_lobbies=True,
                lobbies=await get_lobbies(self.event_id),
                interaction=interaction
            ),
            ephemeral=True
        )

class EliminaButton(discord.ui.Button[Any]):
    def __init__(self, event_id: int):
        super().__init__(
            label="Elimina evento",
            emoji="🗑️",
            style=discord.ButtonStyle.red,
            row=3,
            custom_id=f"event_panel:elimina:{event_id}"
        )
        self.event_id = event_id

    async def callback(self, interaction: discord.Interaction):
        if interaction.guild is None:
            return
        event = await get_event_info(self.event_id, interaction.guild.id)
        if event is None:
            await interaction.response.send_message("C'è stato un errore!", ephemeral=True)
            return
        embed = discord.Embed(
            title="Elimina evento",
            color=discord.Color.red(),
            description=f"Stai per eliminare l'evento **{event.name}**. Sei sicuro?"
        )
        await interaction.response.send_message(
            embed=embed,
            view=EliminaEventoView(self.event_id),
            ephemeral=True
        )

class TerminaButton(discord.ui.Button[Any]):
    def __init__(self, event_id: int):
        super().__init__(
            label="Termina evento",
            emoji="🛑",
            style=discord.ButtonStyle.red,
            row=3,
            custom_id=f"event_panel:termina:{event_id}"
        )
        self.event_id = event_id

    async def callback(self, interaction: discord.Interaction):
        if interaction.guild is None:
            return
        event = await get_event_info(self.event_id, interaction.guild.id)
        if event is None:
            await interaction.response.send_message("Evento non trovato!", ephemeral=True)
            return
        if event.status != "running":
            await interaction.response.send_message("Non puoi terminare l'evento in questa fase!", ephemeral=True)
            return
        ranking_channel_id = await get_ranking_channel_id(interaction.guild.id)
        if ranking_channel_id is None:
            await interaction.response.send_message("Server non configurato correttamente!", ephemeral=True)
            return
        ranking_channel = interaction.guild.get_channel(ranking_channel_id)
        if not isinstance(ranking_channel, discord.TextChannel):
            await interaction.response.send_message("Canale classifiche non trovato!", ephemeral=True)
            return
        await termina_evento_callback(interaction, event, ranking_channel, True)

class EventPanelView(discord.ui.View):
    def __init__(self, event_id: int):
        super().__init__(timeout=None)

        self.add_item(ConfigLobby(event_id))
        self.add_item(AvviaEvento(event_id))
        self.add_item(ControllaRisultati(event_id))
        self.add_item(RicaricaButton(event_id))

        self.add_item(ImpostaCanaliLobby(event_id))
        self.add_item(InviaLobby(event_id))
        self.add_item(InfoLobby(event_id))

        self.add_item(InfoTeam(event_id))
        self.add_item(SpostaTeam(event_id))
        self.add_item(ModificaTeam(event_id))
        self.add_item(PenalizzaTeam(event_id))
        self.add_item(EliminaTeam(event_id))

        self.add_item(TerminaButton(event_id))
        self.add_item(EliminaButton(event_id))