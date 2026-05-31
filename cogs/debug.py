import random
import discord
from discord import app_commands
from discord.ext import commands

from db.db import *
from services.team_service import insert_teams, update_team_kd
from services.event_service import get_events_for_guild, get_event_info


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


def generate_team_name():
    return f"{random.choice(TEAM_NAMES)}-{random.randint(100, 999)}"


def generate_player_name():
    return f"{random.choice(FIRST_NAMES)}{random.choice(LAST_NAMES)}"


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


class DebugCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="gen_teams", description="Genera team random per un evento")
    @app_commands.checks.has_permissions(ban_members=True)
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
        if amount <= 0 or amount > 100:
            await interaction.response.send_message(
                "Numero team non valido (1–100)",
                ephemeral=True
            )
            return
        event = await get_event_info(event_id, interaction.guild_id)
        if event is None:
            await interaction.response.send_message(f"L'evento con id {event_id} non esiste!", ephemeral=True)
        team_count = event.players_per_team
        await interaction.response.defer(thinking=True, ephemeral=True)
        created_teams: list[str] = []
        for i in range(amount):
            team_name = generate_team_name()
            players = generate_players(team_count)
            leader_id: int = 10_000_000 + i
            kds = [generate_kd() for _ in range(team_count)]

            team_id = await insert_teams(event_id, team_name, leader_id, players)
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
    name="get_event_ids",
    description="Mostra gli ID degli eventi"
    )
    @app_commands.checks.has_permissions(ban_members=True)
    async def get_event_ids(
        self,
        interaction: discord.Interaction
    ):

        try:

            if interaction.guild_id is None:
                await interaction.response.send_message(
                    "Usa questo comando in un server.",
                    ephemeral=True
                )
                return

            events = await get_events_for_guild(
                interaction.guild_id,
                ["ready"]
            )

            if not events:
                await interaction.response.send_message(
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

            await interaction.response.send_message(
                embed=embed,
                ephemeral=True
            )

        except Exception as e:
            print(e)

            await interaction.response.send_message(
                f"Errore: {e}",
                ephemeral=True
            )



async def setup(bot: commands.Bot):
    await bot.add_cog(DebugCommands(bot))