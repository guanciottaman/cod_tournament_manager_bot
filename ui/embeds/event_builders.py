import discord

from typing import Any

from services.event_service import *
from models.team import TeamScore

DEFAULT_PLACEMENT_POINTS = {
    "1": 15,
    "2": 12,
    "3": 10,
    "4": 8,
    "5": 6
}


def build_event_embed(
    event: Event,
    placement_points: list[tuple[int, int]],
    teams: list[Team],
    embed_title: str="Configurazione evento"
) -> discord.Embed:
    embed = discord.Embed(
        title=embed_title,
        color=discord.Color.blurple()
    )
    lobby_modes = {
        "random": "Casuale",
        "random_max": "Casuale (massimo 16 team/lobby)",
        "kd": "KD",
        "kd_balanced": "KD bilanciato"
    }

    embed.description = (
        f"# {event.name}\n"
        f"**Stato:** {event.status}\n"
        f"**Match:** {event.matches_number}\n"
        f"**Giocatori per team:** {event.players_per_team}\n"
        f"**Lobby Mode:** {lobby_modes[event.lobby_mode]}\n"
        f"**Scarta partita peggiore:** {'ON' if event.drop_worst_match else 'OFF'}\n\n"
        f"**Punti piazzamento:**\n"
    )

    if placement_points:
        for position, points in placement_points:
            embed.description += f"{position}° posto: *{points} punti*\n"
    else:
        for position, points in DEFAULT_PLACEMENT_POINTS.items():
            embed.description += f"{position}° posto: *{points} punti*\n"

    embed.description += "\n**Team**\n"

    if teams:
        for i, team in enumerate(teams):
            embed.description += f"{i+1}. {team.name}\n"
    else:
        embed.description += "*Nessun team iscritto*\n"

    return embed

def build_results_embed(
    page: int,
    pages_number: int,
    team_name: str,
    team_score: TeamScore
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
        return None
    player_scores = team_score.player_scores
    for score in player_scores:
        emb_description += f"**{score.member_name}:** {score.kills} kill\n"
    embed.description = emb_description
    if len(team_score.screenshots) != 2:
        return None
    embed.set_image(url=team_score.screenshots[0])
    embed2 = discord.Embed(color=embed.color)
    embed2.set_image(url=team_score.screenshots[1])
    embed2.set_footer(text=f"Pagina: {page+1}/{pages_number}")

    embeds = [embed, embed2]
    return embeds

def build_live_ranking_embed(event_name: str, lobby_name: str, team_ranking: list[dict[str, Any]]) -> discord.Embed:
    embed = discord.Embed(
        title="Classifiche evento",
        color=discord.Color.blurple(),
    )
    emb_description = f"Ecco la classifiche dell'evento **{event_name}** per la tua lobby {lobby_name}:\n\n**Claassifica team:**\n"
    for i, team in enumerate(team_ranking, start=1):
        name = team["name"]
        score = team["score"]
        kills = team.get("kills", 0)

        emb_description += f"**{i}. {name}** | {score} pts | {kills} kill\n"
    embed.description = emb_description
    return embed