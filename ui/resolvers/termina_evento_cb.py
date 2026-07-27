import discord

from models.event import Event
from services.lobby_service import get_lobbies, get_teams
from services.event_service import delete_event, delete_lobbies_roles, delete_teams_category, delete_lobbies_category
from services.ranking_service import *
from services.live_ranking_service import stop_live

MEDALS: dict[int, str] = {
    1: "🏆",
    2: "🥈",
    3: "🥉"
}

def format_rank(rank_number: int) -> str:
    rank = MEDALS.get(rank_number, f"{rank_number}{'' if len(str(rank_number)) > 1 else ' '}°")
    return f"{rank:<4}" if rank_number <= 3 else f"{rank:<5}"

def build_team_ranking_description(title: str, rows: list[TeamRankingEntry]) -> str:
    description = f"**{title}**\n"

    description += f"**RANK | TEAM | PUNTI | KILL**\n"

    for i, row in enumerate(rows):
        team = row.name
        score = row.score
        kills = row.kills

        description += (
            f"{format_rank(i+1)} **{team}** | {score} pts | {kills} kill\n"
        )
    return description

def build_mvp_ranking_description(title: str, rows: list[MVPRanking]) -> str:
    description = f"**{title}**\n"
    description += f"**RANK | PLAYER | KILL**\n"
    
    for i, row in enumerate(rows):
        player = clean_player_name(row.player)[:25]
        kills = row.kills

        description += (
            f"{format_rank(i+1)} **{player}** | {kills} kill\n"
        )
    return description

def build_team_ranking_embed(title: str, rows: list[TeamRankingEntry]):
    return discord.Embed(
        title=title,
        description=build_team_ranking_description(title, rows),
        color=discord.Color.blurple()
    )

def build_mvp_ranking_embed(title: str, rows: list[MVPRanking]):
    return discord.Embed(
        title=title,
        description=build_mvp_ranking_description(title, rows),
        color=discord.Color.blurple()
    )

async def termina_evento_callback(
    interaction: discord.Interaction,
    event: Event,
    ranking_channel: discord.TextChannel,
    delete_event_flag: bool = True
):
    if interaction.guild is None:
        return
    await interaction.response.defer(thinking=True, ephemeral=True)
    event_id = event.event_id

    teams_ranking_global: list[TeamRankingEntry] = await compute_team_ranking(event_id, "global")
    if not teams_ranking_global:
        await interaction.followup.send("Nessun risultato è stato accettato!", ephemeral=True)
        return
    lobbies = await get_lobbies(event_id)
    mvp_ranking_global: list[MVPRanking] = await compute_mvp_ranking(event_id)
    embeds: list[discord.Embed] = [
        build_team_ranking_embed(
            f"CLASSIFICA GENERALE {event.name}",
            teams_ranking_global
        )
    ]
    embeds.append(
        build_mvp_ranking_embed(
            f"MVP GENERALE {event.name}",
            mvp_ranking_global
        )
    )
    for lobby in lobbies:
        lobby_ranking = await compute_team_ranking(
            event_id,
            "lobby",
            lobby_id=lobby.lobby_id
        )

        embeds.append(
            build_team_ranking_embed(
                f"CLASSIFICA LOBBY {lobby.name}",
                lobby_ranking
            )
        )

        mvp_lobby_ranking = await compute_mvp_ranking(
            event_id,
            "lobby",
            lobby_id=lobby.lobby_id
        )

        embeds.append(
            build_mvp_ranking_embed(
                f"MVP LOBBY {lobby.name}",
                mvp_lobby_ranking
            )
        )
    try:
        await ranking_channel.send(embeds=embeds)
    except (discord.Forbidden, discord.HTTPException):
        await interaction.followup.send(
            "Il bot non ha i permessi per vedere o scrivere nel canale!",
            ephemeral=True
        )
        return
    await interaction.followup.send(f"La classifica è stata mandata su {ranking_channel.mention}", ephemeral=True)
    if delete_event_flag:
        teams = await get_teams(event_id)
        for team in teams:
            channel_id = team.channel_id
            if channel_id is None:
                continue
            channel = interaction.guild.get_channel(channel_id)
            if channel is None:
                continue
            await channel.delete()
        await stop_live(event_id)
        await delete_teams_category(event_id, interaction.guild)
        await delete_lobbies_category(event_id, interaction.guild)
        await delete_lobbies_roles(event_id, interaction.guild)
        await delete_event(interaction.guild.id, event_id)