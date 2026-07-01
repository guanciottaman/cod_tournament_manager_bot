import discord

from models.event import Event
from services.lobby_service import get_lobbies
from services.event_service import delete_event
from services.ranking_service import *
from services.image_service import build_leaderboard_image, build_mvp_image
from services.live_ranking_service import stop_live

async def termina_evento_callback(interaction: discord.Interaction, event: Event, ranking_channel: discord.TextChannel, delete_event_flag: bool = True):
    await interaction.response.defer(thinking=True, ephemeral=True)
    event_id = event.event_id

    teams_ranking_global = await compute_team_ranking(event_id, "global")
    if not teams_ranking_global:
        await interaction.followup.send("Nessun risultato è stato accettato!", ephemeral=True)
        return
    lobbies = await get_lobbies(event_id)
    files: list[discord.File] = []
    mvp_ranking_global = await compute_mvp_ranking(event_id)
    files.append(
        discord.File(
            await build_leaderboard_image(teams_ranking_global), filename="teams_ranking_global.png"
        )
    )
    files.append(
        discord.File(
            build_mvp_image(mvp_ranking_global), filename="mvp_ranking_global.png"
        )
    )
    embed = discord.Embed(
        title="Evento terminato" if delete_event_flag else "Classifiche evento",
        color=discord.Color.blurple(),
    )
    if delete_event_flag:
        emb_description = f"Hai terminato l'evento **{event.name}**.\nEcco le classifiche finali globali:\n\n**Claassifica team:**\n"
    else:
        emb_description = f"Ecco le classifiche dell'evento **{event.name}**:\n\n**Claassifica team:**\n"
    for i, r in enumerate(teams_ranking_global):
        team_id = r["team_id"]
        team_name = r["name"]
        team_score = r["score"]
        emb_description += f"{i+1}. {team_name} | ID {team_id} | {team_score} punti\n"
    emb_description += "\n**MVPs:**\n"
    for i, p in enumerate(mvp_ranking_global):
        player_name = clean_player_name(p.get("player", "Unknown"))
        player_kills = p.get("kills")
        emb_description += f"{i+1}. {player_name} | {player_kills} kill\n"
    emb_description += "\n**Classifiche Lobby**\n"
    for i, lobby in enumerate(lobbies):
        emb_description += f"\n**Lobby {lobby.name}**\n*Classifica team:*\n"
        lobby_ranking = await compute_team_ranking(event_id, "lobby", lobby_id=lobby.lobby_id)
        lobby_image = await build_leaderboard_image(lobby_ranking, lobby_name=lobby.name)
        files.append(
            discord.File(
                lobby_image, filename=f"lobby{i+1}.png"
            )
        )
        for j, r in enumerate(lobby_ranking):
            team_id = r["team_id"]
            team_name = r["name"]
            team_score = r["score"]
            emb_description += f"{j+1}. {team_name}| ID {team_id} | {team_score} punti\n"
        mvp_lobby_ranking = await compute_mvp_ranking(event_id, "lobby", lobby_id=lobby.lobby_id)
        mvp_lobby_image = build_mvp_image(mvp_lobby_ranking, lobby_name=lobby.name)
        files.append(
            discord.File(
                mvp_lobby_image, filename=f"lobby_mvp{i+1}.png"
            )
        )
        emb_description += "\n*MVP:*\n"
        for j, r in enumerate(mvp_lobby_ranking):
            player_name = r["player"]
            player_kills = r["kills"]
            emb_description += f"{j+1}. {player_name} | {player_kills} kill\n"
    embed.description = emb_description
    try:
        await ranking_channel.send(
            embed=embed,
            files=files
        )
    except (discord.Forbidden, discord.HTTPException):
        await interaction.followup.send(
            "Il bot non ha i permessi per vedere o scrivere nel canale!"
        )
        return
    
    await stop_live(event_id)
    await interaction.followup.send(f"La classifica è stata mandata su {ranking_channel.mention}")
    if delete_event_flag:
        await delete_event(interaction.guild_id, event_id)