import discord
from discord import app_commands
from discord.ext import commands
import aiohttp

class RayshiftCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="rayshift", description="🔍 Get Rayshift.io support list link")
    @app_commands.describe(
        friend_code="Your 9-digit FGO friend code",
        region="Game region"
    )
    @app_commands.choices(region=[
        app_commands.Choice(name="Japan", value="jp"),
        app_commands.Choice(name="North America", value="na")
    ])
    async def rayshift(
        self, 
        interaction: discord.Interaction, 
        friend_code: str,
        region: app_commands.Choice[str] = "jp"
    ):
        """Generate a Rayshift.io profile link"""
        
        # Validate friend code
        cleaned_code = friend_code.replace("-", "").replace(" ", "")
        
        if not cleaned_code.isdigit() or len(cleaned_code) != 9:
            await interaction.response.send_message(
                "❌ Friend code must be exactly 9 digits!\n"
                "Examples: `801625519` or `801-625-519`",
                ephemeral=True
            )
            return
        
        region_code = region.value if isinstance(region, app_commands.Choice) else region
        url = f"https://rayshift.io/{region_code}/{cleaned_code}"
        
        embed = discord.Embed(
            title=f"🔍 Rayshift Profile",
            description=f"**Friend Code:** `{cleaned_code}`\n**Region:** {region_code.upper()}",
            url=url,
            color=0x3498db
        )
        
        embed.add_field(
            name="What is Rayshift?",
            value="Rayshift.io lets you view FGO support lists online without opening the game. "
                  "Click the title above or the button below to view the profile!",
            inline=False
        )
        
        embed.add_field(
            name="First Time?",
            value="If this profile hasn't been viewed before, Rayshift will search the game server. "
                  "This may take 30-60 seconds to load.",
            inline=False
        )
        
        # Add example of what you'll see
        embed.add_field(
            name="You'll See:",
            value="• All 3 support decks\n• Servants + their CEs\n• Skill levels\n• NP levels\n• Last login time",
            inline=False
        )
        
        embed.set_footer(text="Rayshift.io - FGO Support Viewer")
        
        # Create view with link button
        view = discord.ui.View()
        view.add_item(discord.ui.Button(
            label="🔗 Open Rayshift Profile",
            style=discord.ButtonStyle.link,
            url=url
        ))
        
        await interaction.response.send_message(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(RayshiftCog(bot))
