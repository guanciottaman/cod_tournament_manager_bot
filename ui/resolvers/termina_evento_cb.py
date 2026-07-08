import discord

from typing import Any

from models.event import Event
from services.lobby_service import get_lobbies
from services.event_service import delete_event, delete_lobbies_roles
from services.ranking_service import *
from services.live_ranking_service import stop_live

MEDALS: dict[int, str] = {
    1: "🏆",
    2: "🥈",
    3: "🥉"
}

async def termina_evento_callback(
    interaction: discord.Interaction,
    event: Event,
    ranking_channel: discord.TextChannel,
    delete_event_flag: bool = True
):
    await interaction.response.defer(thinking=True, ephemeral=True)
    event_id = event.event_id

    teams_ranking_global: list[dict[str, Any]] = await compute_team_ranking(event_id, "global")
    if not teams_ranking_global:
        await interaction.followup.send("Nessun risultato è stato accettato!", ephemeral=True)
        return
    lobbies = await get_lobbies(event_id)
    mvp_ranking_global: list[dict[str, Any]] = await compute_mvp_ranking(event_id)
    embeds: list[discord.Embed] = []
    general_embed = discord.Embed(
        title=f"CLASSIFICA GENERALE {event.name}",
        color=discord.Color.blurple(),
    )
    emb_description = "**RANK | TEAM | PUNTEGGIO**\n"
    for i, r in enumerate(teams_ranking_global):
        team_name = r["name"]
        team_score = r["score"]
        emb_description += f"{f'{i+1}°' if i+1>3 else MEDALS[i+1]} {team_name} | {team_score} punti\n"
    general_embed.description = emb_description
    embeds.append(general_embed)
    mvp_general_embed = discord.Embed(
        title=f"MVP GENERALE {event.name}",
        color=discord.Color.blurple(),
    )
    mvp_general_emb_description = "**RANK | PLAYER | KILL**\n"
    for i, p in enumerate(mvp_ranking_global):
        player_name = clean_player_name(p.get("player", "Unknown"))
        player_kills = p.get("kills")
        mvp_general_emb_description += f"{i+1 if i+1>3 else MEDALS[i+1]}. {player_name} | {player_kills} kill\n"
    mvp_general_embed.description = mvp_general_emb_description
    embeds.append(mvp_general_embed)
    for i, lobby in enumerate(lobbies):
        lobby_team_embed = discord.Embed(
            title=f"CLASSIFICA LOBBY {lobby.name}",
            color=discord.Color.blurple(),
        )
        lobby_team_emb_description = "**RANK | TEAM | PUNTEGGIO**\n"
        lobby_ranking: list[dict[str, Any]] = await compute_team_ranking(event_id, "lobby", lobby_id=lobby.lobby_id)
        for j, r in enumerate(lobby_ranking):
            team_name = r["name"]
            team_score = r["score"]
            lobby_team_emb_description += f"{f'{j+1}°' if j+1>3 else MEDALS[j+1]} {team_name} | {team_score} punti\n"
        lobby_team_embed.description = lobby_team_emb_description
        embeds.append(lobby_team_embed)
        mvp_lobby_embed = discord.Embed(
            title=f"MVP LOBBY {event.name}",
            color=discord.Color.blurple(),
        )
        mvp_lobby_emb_description = "**RANK | PLAYER | KILL**\n"
        mvp_lobby_ranking: list[dict[str, Any]] = await compute_mvp_ranking(event_id, "lobby", lobby_id=lobby.lobby_id)
        emb_description += "\n*MVP:*\n"
        for j, r in enumerate(mvp_lobby_ranking):
            player_name = r["player"]
            player_kills = r["kills"]
            mvp_lobby_emb_description += f"{f'{j+1}°' if j+1>3 else MEDALS[j+1]} {player_name} | {player_kills} kill\n"
        mvp_lobby_embed.description = mvp_lobby_emb_description
        embeds.append(mvp_lobby_embed)
    try:
        await ranking_channel.send(embeds=embeds)
    except (discord.Forbidden, discord.HTTPException):
        await interaction.followup.send(
            "Il bot non ha i permessi per vedere o scrivere nel canale!"
        )
        return
    await interaction.followup.send(f"La classifica è stata mandata su {ranking_channel.mention}")
    if delete_event_flag:
        await stop_live(event_id)
        await delete_lobbies_roles(event_id, interaction.guild)
        await delete_event(interaction.guild_id, event_id)