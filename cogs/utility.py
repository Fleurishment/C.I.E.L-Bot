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
            title="C.I.E.L Commands",
            description="Your Chaldea Assistant - All commands use official Atlas Academy API",
            color=0x3498db
        )
        
        # Servant Lookup Commands
        embed.add_field(
            name="🔍 Servant Lookup",
            value=(
                "`/servant <name>` - Full servant details with stats, skills, NP\n"
                "`/artwork <name> [ascension]` - View servant artwork (1-4)\n"
                "`/search <name>` - Quick search multiple results\n"
                "`/ce <name>` - Search Craft Essences"
            ),
            inline=False
        )
        
        # Fun Tools
        embed.add_field(
            name="🎮 Fun & Tools",
            value=(
                "`/gacha [quartz] [banner]` - Gacha roll simulator\n"
                "`/sqcalc [target_np] [quartz] [tickets]` - Calculate SQ needed\n"
                "`/daily` - Show today's training grounds rotation"
            ),
            inline=False
        )
        
        # Utility
        embed.add_field(
            name="⚙️ Utility",
            value=(
                "`/ping` - Check bot status & latency\n"
                "`/help` - Show this message"
            ),
            inline=False
        )
        
        # Tips
        embed.add_field(
            name="💡 Tips",
            value=(
                "• Servant commands support both NA and JP regions\n"
                "• For `/artwork`, use `ascension: 0` to see all ascensions as links\n"
                "• The gacha simulator uses realistic 1% SSR rates with pity system\n"
                "• All data is fetched live from Atlas Academy API"
            ),
            inline=False
        )
        
        embed.set_footer(text="Made by krlnel | Data provided by Atlas Academy API")
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(UtilityCog(bot))
