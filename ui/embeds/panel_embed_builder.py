import discord


def build_panel_embed(guild: discord.Guild):
    embed = discord.Embed(
        title="Pannello gestione server",
        color=discord.Color.blue(),
        description=f"""
            Questo è il pannello gestione eventi del tuo server {guild.name}.
        """
    )
    return embed