import discord

import datetime
import pytz

from services.event_service import *
from models.team import TeamScore
from models.ranking import TeamRankingEntry, MVPRanking
from models.server_config import ServerConfig
from models.placement_settings import PlacementSettings
from config.consts import STATUSES, LOBBY_MODES, DEFAULT_PLACEMENT_MULTIPLIERS, DEFAULT_PLACEMENT_POINTS

def build_event_embed(
    event: Event,
    guild: discord.Guild,
    placement_settings: PlacementSettings,
    teams: list[Team],
    embed_title: str="Configurazione evento"
) -> discord.Embed:
    embed = discord.Embed(
        title=embed_title,
        color=discord.Color.blurple()
    )
    
    category_channel = guild.get_channel(event.teams_category_id) if event.teams_category_id else None

    embed.description = (
        f"# {event.name}\n"
        f"**Stato:** {STATUSES[event.status]}\n"
        f"**Match:** {event.matches_number}\n"
        f"**Giocatori per team:** {event.players_per_team}\n"
        f"**Lobby Mode:** {LOBBY_MODES[event.lobby_mode]}\n"
        f"**Scarta partita peggiore:** {'ON' if event.drop_worst_match else 'OFF'}\n"
        f"**Categoria ticket team:** {category_channel.mention if event.teams_category_id and category_channel is not None else 'Nessuno'}\n"
        f"**Sistema piazzamento:** {'punti' if placement_settings.system == "points" else 'moltiplicatori'}\n\n"
    )

    if placement_settings.system == "points":
        embed.description += "**Punti piazzamento:**\n"
        if placement_settings.points:
            for position, points in placement_settings.points.items():
                embed.description += f"{position}° posto: *{points} punti*\n"
        else:
            for position, points in DEFAULT_PLACEMENT_POINTS.items():
                embed.description += f"{position}° posto: *{points} punti*\n"
    elif placement_settings.system == "multipliers":
        embed.description += "**Moltiplicatori piazzamento:**\n"
        if placement_settings.multipliers:
            for (min_placement, max_placement), multiplier in placement_settings.multipliers.items():
                if min_placement == 1:
                    embed.description += f"1° posto: *{multiplier:g}x*\n"
                else:
                    embed.description += f"{min_placement}°{f'-{max_placement}°' if max_placement is not None else '+'} posto: *{multiplier:g}x*\n"
        else:
            for (min_placement, max_placement), multiplier in DEFAULT_PLACEMENT_MULTIPLIERS.items():
                if min_placement == 1:
                    embed.description += f"1° posto: *{multiplier:g}x*\n"
                else:
                    embed.description += f"{min_placement}°{f'-{max_placement}°' if max_placement is not None else '+'} posto: *{multiplier:g}x*\n"

    embed.description += "\n**Team**\n"

    if teams:
        for i, team in enumerate(teams):
            embed.description += f"{i+1}. {team.name}\n"
    else:
        embed.description += "*Nessun team iscritto*\n"

    return embed

def build_event_channels_embed(
    register_team_channel: discord.TextChannel | None = None,
    event_panel_channel: discord.TextChannel | None = None
) -> discord.Embed:
    embed = discord.Embed(
        title="Seleziona canali evento",
        color=discord.Color.blue(),
        description=f"**Canale registra team:** {register_team_channel.mention if register_team_channel else 'Nessuno'}\n**Canale pannello gestione evento:** {event_panel_channel.mention if event_panel_channel else 'Nessuno'}\n"
    )
    return embed

def build_server_config_embed(
    guild: discord.Guild,
    server_config: ServerConfig
) -> discord.Embed:
    if server_config.panel_channel_id is not None:
        panel_channel = guild.get_channel(server_config.panel_channel_id)
    else:
        panel_channel = None
    if server_config.ranking_channel_id is not None:
        ranking_channel = guild.get_channel(server_config.ranking_channel_id)
    else:
        ranking_channel = None
    if server_config.admin_role_id is not None:
        admin_role = guild.get_role(server_config.admin_role_id)
    else:
        admin_role = None
    if server_config.live_ranking_channel_id is not None:
        live_ranking_channel = guild.get_channel(server_config.live_ranking_channel_id)
    else:
        live_ranking_channel = None
    if server_config.lobbies_channel_id is not None:
        lobbies_channel = guild.get_channel(server_config.lobbies_channel_id)
    else:
        lobbies_channel = None
    embed = discord.Embed(
        title="Config server",
        color=discord.Color.blue()
    )
    description = f"**Server:** {guild.name}\n"
    description += f"**Canale pannello: ** {panel_channel.mention if panel_channel is not None else 'Nessuno'}\n"
    description += f"**Canale classifiche:** {ranking_channel.mention if ranking_channel is not None else 'Nessuno'}\n"
    description += f"**Ruolo admin:** {admin_role.mention if admin_role is not None else 'Nessuno'}\n"
    description += f"**Canale classifiche live:** {live_ranking_channel.mention if live_ranking_channel is not None else 'Nessuno'}\n"
    description += f"**Canale lobby:** {lobbies_channel.mention if lobbies_channel is not None else 'Nessuno'}\n"
    embed.description = description
    return embed

def build_results_embed(
    page: int,
    pages_number: int,
    team_name: str,
    team_score: TeamScore,
    warnings: list[str] | None = None
) -> list[discord.Embed] | None:
    embed = discord.Embed(
        title=f"Risultati evento team {team_name}"
    )
    emb_description = f"**Match** n.{team_score.match_number}\n**Piazzamento:** {team_score.placement}\n**Stato:** {team_score.status}\n\nRisultati giocatori:\n"
    if team_score.status == "pending":
        embed.color = discord.Color.yellow()
    elif team_score.status == "accepted":
        embed.color = discord.Color.green()
    elif team_score.status == "rejected":
        embed.color = discord.Color.red()
    elif team_score.status == "edited":
        embed.color = discord.Color.dark_gold()
    else:
        embed.description = "Stato non valido"
        embed.color = discord.Color.greyple()
        return [embed]

    if len(team_score.screenshots) < 2:
        embed.description = "⚠️ Screenshot mancanti"
        embed.color = discord.Color.orange()
        return [embed]
    player_scores = team_score.player_scores
    for score in player_scores:
        emb_description += f"**{score.member_name}:** {score.kills} kill\n"
    embed.description = emb_description
    warnings = warnings or []
    for warning in warnings:
        embed.add_field(
            name="⚠️ATTENZIONE",
            value=warning
        )
    embed.set_image(url=team_score.screenshots[0])
    embed2 = discord.Embed(color=embed.color)
    embed2.set_image(url=team_score.screenshots[1])
    embed2.set_footer(text=f"Pagina: {page+1}/{pages_number}")

    embeds = [embed, embed2]
    return embeds

def build_live_mvp_ranking_embed(
    event_name: str,
    lobby_name: str,
    mvp_ranking: list[MVPRanking],
    drop_worst_match: bool
) -> discord.Embed:
    embed = discord.Embed(
        title="Classifica Live MVP Evento",
        color=discord.Color.blurple(),
    )
    emb_description = f"Ecco la classifiche degli MVP dell'evento **{event_name}** per la tua **LOBBY {lobby_name}**:\n\n**MVP:**\n"
    for i, player in enumerate(mvp_ranking, start=1):
        name = player.player
        kills = player.kills

        emb_description += f"**{i}. {name}** | {kills} kill\n"
    if drop_worst_match:
        emb_description += "\n*La partita peggiore viene scartata dal secondo match in poi*"
    embed.description = emb_description
    embed.set_footer(text=f"Le classifiche verranno aggiornate ogni 5 secondi | {datetime.datetime.now(pytz.timezone('Europe/Rome')):%H:%M}")
    return embed

def build_live_team_ranking_embed(
    event_name: str,
    lobby_name: str,
    team_ranking: list[TeamRankingEntry],
    inserted_matches: dict[int, int],
    matches_number: int,
    drop_worst_match: bool
) -> discord.Embed:
    embed = discord.Embed(
        title="Classifica Live Evento",
        color=discord.Color.blurple(),
    )
    emb_description = f"Ecco la classifiche dell'evento **{event_name}** per la tua **LOBBY {lobby_name}**:\n\n**Classifica Team:**\n"
    for i, team in enumerate(team_ranking, start=1):
        name = team.name
        score = team.score
        kills = team.kills
        inserted = inserted_matches.get(team.team_id, 0)

        emb_description += f"**{i}. {name}** | {score} pts | {kills} kill ({inserted}/{matches_number} match inseriti)\n"
    if drop_worst_match:
        emb_description += "\n*La partita peggiore viene scartata dal secondo match in poi*"
    embed.description = emb_description
    embed.set_footer(text=f"Le classifiche verranno aggiornate ogni 5 secondi | {datetime.datetime.now(pytz.timezone('Europe/Rome')):%H:%M}")
    return embed