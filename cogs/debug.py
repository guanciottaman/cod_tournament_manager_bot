import random
import discord
from discord import app_commands
from discord.ext import commands

from db.db import *


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


def generate_players():
    return [
        generate_player_name()
        for _ in range(random.randint(2, 5))
    ]



class DebugCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="gen_teams", description="Genera team random per un evento")
    @commands.has_permissions(ban_members=True)
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

        created_teams = []

        for _ in range(amount):
            team_name = generate_team_name()
            players = generate_players()

            leader_id = random.randint(100000, 999999)

            team_id = await execute(
                """
                INSERT INTO teams (event_id, name, leader_discord_id)
                VALUES (?, ?, ?)
                """,
                (event_id, team_name, leader_id)
            )

            for player in players:
                await execute(
                    """
                    INSERT INTO team_members (team_id, member_name)
                    VALUES (?, ?)
                    """,
                    (team_id, player)
                )

            created_teams.append(f"{team_name} ({len(players)} players)")

        embed = discord.Embed(
            title="Team generati",
            description="\n".join(f"- {t}" for t in created_teams),
            color=discord.Color.green()
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(DebugCommands(bot))