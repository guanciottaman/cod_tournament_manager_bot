import random
import discord
from discord import app_commands
from discord.ext import commands

from db.db import *
from services.team_service import (insert_teams, update_team_kd, get_teams,
    insert_results, get_inserted_match_numbers, set_result_status, get_players_names)
from services.event_service import get_events_for_guild, get_event_info
from services.server_service import get_admin_role_id
from models.team import Team


TEAM_NAMES = [
    "Alpha", "Bravo", "Delta", "Omega", "Titan", "Shadow",
    "Storm", "Viper", "Ghost", "Nova", "Blaze", "Phantom"
]

FIRST_NAMES = [
    "Alex", "Marco", "Luca", "Sara", "John", "Mike",
    "Leo", "Nico", "Kai", "Zane", "Ryo", "Eren"
]

LAST_NAMES = [
    "Storm", "Blade", "Fox", "Wolf", "Night", "Zero",
    "Prime", "Nova", "Ghost", "X"
]

IMAGE_POOL = [
    "https://cdn.discordapp.com/attachments/1496915639170891847/1511440911282864259/1776018259429.png?ex=6a20768a&is=6a1f250a&hm=d9fce02d1ad92a70e33d078ee323da062e211c808433865dc33643b54a7993c8&",
    "https://cdn.discordapp.com/attachments/1496915639170891847/1511440911807156304/appunti.png?ex=6a20768a&is=6a1f250a&hm=a756c98e8c2869ca302212ad5f5186e172c8b14b5c64f27964c927c77b499a6a&"
]


def generate_team_name():
    return f"{random.choice(TEAM_NAMES)}#{random.randint(1000, 9999)}"


def generate_player_name():
    return f"{random.choice(FIRST_NAMES)}{random.choice(LAST_NAMES)}#{random.randint(1000, 9999)}"


def generate_players(amount: int):
    return [
        generate_player_name()
        for _ in range(amount)
    ]

def generate_kd():
    """
    Simula KD realistico:
    - molti player medi
    - pochi forti
    - pochi scarsi
    """

    base = random.gauss(1.2, 0.6)

    if base < 0.1:
        base = 0.1
    if base > 3.5:
        base = 3.5

    return round(base, 2)

async def generate_match_results(
    teams: list[Team],
) -> list[dict]:
    match = []

    shuffled = teams[:]
    random.shuffle(shuffled)

    team_ids = tuple(t.team_id for t in shuffled)

    if not team_ids:
        return []

    placeholders = ",".join(["?"] * len(team_ids))

    rows = await fetch_all(f"""
        SELECT team_id, member_id, member_name
        FROM team_members
        WHERE team_id IN ({placeholders})
    """, team_ids)

    # dizionario da team_id -> (player_id, name)
    players_map: dict[int, list[tuple[int, str]]] = {}

    for team_id, member_id, member_name in rows:
        players_map.setdefault(team_id, []).append((member_id, member_name))

    temp = []

    for t in shuffled:
        players = players_map.get(t.team_id, [])

        if not players:
            continue

        players_kills: list[tuple[int, str, int]] = []
        total_kills = 0

        for player_id, player_name in players:
            k = max(0, int(random.gauss(3, 2)))

            players_kills.append((player_id, player_name, k))
            total_kills += k

        temp.append((t, total_kills, players_kills))

    temp.sort(key=lambda x: x[1], reverse=True)

    for placement, (team, _, players) in enumerate(temp, start=1):
        match.append({
            "team_id": team.team_id,
            "team_name": team.name,
            "placement": placement,
            "players": players
        })

    return match

class DebugCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    async def check_admin_role(self, interaction: discord.Interaction):
        admin_role_id = await get_admin_role_id(interaction.guild_id)
        if not admin_role_id:
            return False

        admin_role = interaction.guild.get_role(admin_role_id)
        if admin_role is None:
            return False
        return admin_role in interaction.user.roles

    @app_commands.command(name="gen_teams", description="Genera team random per un evento")
    @app_commands.describe(
        event_id="ID evento",
        amount="Numero team da generare"
    )
    async def gen_teams(
        self,
        interaction: discord.Interaction,
        event_id: int,
        amount: int
    ):
        if not await self.check_admin_role(interaction):
            await interaction.response.send_message("Non hai il ruolo necessario per configurare le lobby di un evento!", ephemeral=True)
            return
        if amount <= 0 or amount > 100:
            await interaction.response.send_message(
                "Numero team non valido (1–100)",
                ephemeral=True
            )
            return
        event = await get_event_info(event_id, interaction.guild_id)
        if event is None:
            await interaction.response.send_message(f"L'evento con id {event_id} non esiste!", ephemeral=True)
            return
        if event.status != "ready":
            await interaction.response.send_message("Puoi generare team solo prima di configurare le lobby", ephemeral=True)
            return
        team_count = event.players_per_team
        await interaction.response.defer(thinking=True, ephemeral=True)
        created_teams: list[str] = []
        for i in range(amount):
            team_name = generate_team_name()
            players = generate_players(team_count)
            leader_id: int = 10_000_000 + i
            kds = [generate_kd() for _ in range(team_count)]

            team_id, _ = await insert_teams(event_id, team_name, leader_id, players)
            kd = await update_team_kd(team_id, kds)

            created_teams.append(
                f"{team_name} | KD: {kd:.2f} | {len(players)} players"
            )
        embed = discord.Embed(
            title="Team generati",
            description="\n".join(f"- {t}" for t in created_teams),
            color=discord.Color.green()
        )

        await interaction.followup.send(embed=embed, ephemeral=True)
    
    @app_commands.command(
        name="gen_risultati",
        description="Genera risultati fittizi per un evento"
    )
    @app_commands.describe(event_id="Evento per cui generare i risultati")
    async def gen_risultati(
        self,
        interaction: discord.Interaction,
        event_id: int
    ):
        if not await self.check_admin_role(interaction):
            await interaction.response.send_message("Non hai il ruolo necessario per configurare le lobby di un evento!", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)

        event = await get_event_info(event_id, interaction.guild_id)
        if not event:
            await interaction.followup.send("Evento non valido", ephemeral=True)
            return

        teams = await get_teams(event_id)
        if not teams:
            await interaction.followup.send("Nessun team trovato", ephemeral=True)
            return

        existing_matches = await get_inserted_match_numbers(event_id)

        matches_number = getattr(event, "matches_number", None)
        if not matches_number:
            matches_number = max(1, len(teams) // 10)

        inserted = 0

        for match_number in range(1, matches_number + 1):

            if match_number in existing_matches:
                continue

            match_results = await generate_match_results(
                teams
            )

            for r in match_results:
                await insert_results(
                    event_id=event_id,
                    team_id=r["team_id"],
                    placement=r["placement"],
                    match=match_number,
                    players=r["players"],
                    prove=IMAGE_POOL
                )

            inserted += 1

        await interaction.followup.send(
            f"Generati {inserted} match per evento {event_id}",
            ephemeral=True
        )

    @app_commands.command(
        name="accept_all_results",
        description="Accetta automaticamente tutti i risultati in attesa"
    )
    @app_commands.describe(event_id="Evento per cui accettare i risultati")
    async def accept_all_results(
        self,
        interaction: discord.Interaction,
        event_id: int
    ):
        if not await self.check_admin_role(interaction):
            await interaction.response.send_message("Non hai il ruolo necessario per configurare le lobby di un evento!", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)

        results = await fetch_all("""
            SELECT id
            FROM team_scores
            WHERE event_id = ?
            AND status = 'pending'
        """, (event_id,))

        if not results:
            await interaction.followup.send("Nessun risultato da accettare.")
            return

        for (team_score_id,) in results:
            await set_result_status(team_score_id, "accepted")

        await interaction.followup.send(
            f"Accettati {len(results)} risultati per l'evento {event_id}."
        )

    @app_commands.command(
        name="get_event_ids",
        description="Mostra gli ID degli eventi"
    )
    async def get_event_ids(
        self,
        interaction: discord.Interaction
    ):
        if not await self.check_admin_role(interaction):
            await interaction.response.send_message("Non hai il ruolo necessario per ottenere gli id di un evento!", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        try:
            if interaction.guild_id is None:
                await interaction.followup.send(
                    "Usa questo comando in un server.",
                    ephemeral=True
                )
                return
            
            events = await get_events_for_guild(
                interaction.guild_id,
                ["ready", "setup", "running"]
            )

            if not events:
                await interaction.followup.send(
                    "Nessun evento trovato.",
                    ephemeral=True
                )
                return

            lines = [
                f"ID: `{e.event_id}` | {e.name} | {e.status}"
                for e in events
            ]

            embed = discord.Embed(
                title="Eventi",
                description="\n".join(lines),
                color=discord.Color.blurple()
            )

            await interaction.followup.send(
                embed=embed,
                ephemeral=True
            )

        except Exception as e:
            print(e)

            await interaction.followup.send(
                f"Errore: {e}",
                ephemeral=True
            )



async def setup(bot: commands.Bot):
    await bot.add_cog(DebugCommands(bot))