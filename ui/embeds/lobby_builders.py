import discord

from services.lobby_service import get_lobbies_names
from models.lobby import Lobby

DEFAULT_PLACEMENT_POINTS = {
    "1": 15,
    "2": 12,
    "3": 10,
    "4": 8,
    "5": 6
}

async def build_config_lobbies_embed(event_id: int, lobbies_number: int, teams_count: int):
    names = await get_lobbies_names(event_id)

    if names:
        names_list = names
    else:
        names_list = [
            f"{i+1}"
            for i in range(lobbies_number)
        ]

    embed = discord.Embed(
        title="Configura le lobby",
        color=discord.Color.blurple()
    )
    emb_description = f"Configura le lobby prima di avviare.\nI giocatori verranno inseriti automaticamente secondo le impostazioni da te selezionate\nTeam attualmente iscritti: {teams_count}\n\n"
    lobby_text = "\n".join(
        f"{i+1}. LOBBY {name}" for i, name in enumerate(names_list)
    )

    emb_description += (
        f"**Numero lobby:** {lobbies_number}\n\n"
        f"**Nomi lobby:**\n{lobby_text}"
    )
    embed.description = emb_description

    return embed


async def build_event_start_summary(lobbies: list[Lobby]) -> discord.Embed:
    embed = discord.Embed(
        title="Evento configurato",
        color=discord.Color.green()
    )

    embed.add_field(
        name="Numero lobby",
        value=str(len(lobbies)),
        inline=True
    )

    description_lines: list[str] = []

    for i, lobby in enumerate(lobbies, start=1):
        description_lines.append(
            f"**{i}. LOBBY {lobby.name}** → {len(lobby.teams)} team"
        )

    embed.add_field(
        name="Distribuzione team",
        value="\n".join(description_lines),
        inline=False
    )

    return embed

def build_info_lobby_embed(event_name: str, lobbies: list[Lobby], show_kd: bool = True) -> discord.Embed:
    embed = discord.Embed(
        title=event_name,
        color=discord.Color.red()
    )
    emb_description = f"Numero lobby: {len(lobbies)}\n\n"
    for lobby in lobbies:
        emb_description += f"**LOBBY {lobby.name} ({len(lobby.teams)} team)**\n\n**Slot | Team**\n"
        for i, team in enumerate(lobby.teams):
            emb_description += f"{i}. {team.name}"
            if show_kd:
                emb_description += f" (K/D {team.kd:.2f})"
            emb_description += "\n"
        emb_description += "\n"
    embed.description = emb_description
    return embed