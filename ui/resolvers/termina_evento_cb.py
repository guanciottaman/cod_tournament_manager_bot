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

def build_ranking_embed(title: str, rows: list[dict[str, Any]], is_mvp: bool = False):
    embed = discord.Embed(
        title=title,
        color=discord.Color.blurple()
    )

    rank = ""
    names = ""
    values = ""

    for i, row in enumerate(rows):
        rank += f"{MEDALS.get(i + 1, f'{i+1}°')}\n"

        if is_mvp:
            names += f"{clean_player_name(row.get('player', 'Unknown'))}\n"
            values += f"{row.get('kills', 0)} kill\n"
        else:
            names += f"{row['name']}\n"
            values += f"{row['score']} punti\n"

    embed.add_field(
        name="RANK",
        value=rank or "-",
        inline=True
    )
    embed.add_field(
        name="TEAM" if not is_mvp else "PLAYER",
        value=names or "-",
        inline=True
    )
    embed.add_field(
        name="PUNTEGGIO" if not is_mvp else "KILL",
        value=values or "-",
        inline=True
    )

    return embed

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
    embeds: list[discord.Embed] = [
        build_ranking_embed(
            f"CLASSIFICA GENERALE {event.name}",
            teams_ranking_global
        )
    ]
    embeds.append(
        build_ranking_embed(
            f"MVP GENERALE {event.name}",
            mvp_ranking_global,
            is_mvp=True
        )
    )
    for lobby in lobbies:
        lobby_ranking = await compute_team_ranking(
            event_id,
            "lobby",
            lobby_id=lobby.lobby_id
        )

        embeds.append(
            build_ranking_embed(
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
            build_ranking_embed(
                f"MVP LOBBY {lobby.name}",
                mvp_lobby_ranking,
                is_mvp=True
            )
        )
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