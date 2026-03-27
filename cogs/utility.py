import discord
from discord import app_commands
from discord.ext import commands
import time

class UtilityCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.start_time = time.time()
    
    @app_commands.command(name="ping", description="Check bot latency")
    async def ping(self, interaction: discord.Interaction):
        latency = round(self.bot.latency * 1000)
        embed = discord.Embed(
            title="🏓 Pong!",
            description=f"Latency: `{latency}ms`",
            color=0x00ff00 if latency < 200 else 0xff0000
        )
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="help", description="Show all available commands")
    async def help_command(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="📚 FGO Bot Commands",
            description="Your Chaldea Assistant",
            color=0x3498db
        )
        
        # Atlas API Commands
        embed.add_field(
            name="🔍 Servant Lookup (Atlas API)",
            value=(
                "`/servant <name>` - Full servant details (stats, skills, NP)\n"
                "`/artwork <name>` - Servant artwork and ascensions"
            ),
            inline=False
        )
        
        # Web Scraping Commands
        embed.add_field(
            name="🌐 Wiki Scraping",
            value=(
                "`/lore <name>` - Servant lore from Fandom Wiki\n"
                "`/rating <name>` - GamePress tier ratings and analysis\n"
                "`/events` - Current and upcoming events\n"
                "`/tierlist` - GamePress tier list overview\n"
                "`/farm <material>` - Material farming locations"
            ),
            inline=False
        )
        
        # Utility
        embed.add_field(
            name="⚙️ Utility",
            value=(
                "`/ping` - Check bot status\n"
                "`/help` - Show this message"
            ),
            inline=False
        )
        
        embed.set_footer(text="Data sources: Atlas Academy API, Fandom Wiki, GamePress")
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(UtilityCog(bot))
