import discord
from discord import app_commands
from discord.ext import commands
import aiohttp
import json

class RayshiftCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.api_base = "https://api.rayshift.io"  # Attempted API endpoint
    
    @app_commands.command(name="rayshift", description="🔍 Fetch and display FGO support list")
    @app_commands.describe(
        friend_code="Your 9-digit FGO friend code",
        region="Game region",
        force_refresh="Force refresh from game server"
    )
    @app_commands.choices(region=[
        app_commands.Choice(name="Japan", value="jp"),
        app_commands.Choice(name="North America", value="na")
    ])
    async def rayshift(
        self, 
        interaction: discord.Interaction, 
        friend_code: str,
        region: app_commands.Choice[str] = "jp",
        force_refresh: bool = False
    ):
        """Fetch support list from Rayshift and display in Discord"""
        await interaction.response.defer()
        
        # Clean and validate
        cleaned_code = friend_code.replace("-", "").replace(" ", "")
        if not cleaned_code.isdigit() or len(cleaned_code) != 9:
            await interaction.followup.send("❌ Friend code must be 9 digits!", ephemeral=True)
            return
        
        region_code = region.value if isinstance(region, app_commands.Choice) else region
        
        try:
            # Try to fetch from Rayshift's API
            # Note: This endpoint may not work - Rayshift API is private
            url = f"https://rayshift.io/api/v1/profile/{region_code}/{cleaned_code}"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json',
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=15) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        await self.display_support_list(interaction, data, cleaned_code, region_code)
                        return
                    elif resp.status == 404:
                        # Profile not cached, need to initialize
                        await self.trigger_initial_lookup(interaction, cleaned_code, region_code)
                        return
                    else:
                        raise Exception(f"API returned {resp.status}")
                        
        except Exception as e:
            print(f"Rayshift API error: {e}")
            # Fallback: Tell user to visit website first
            await self.send_fallback_embed(interaction, cleaned_code, region_code)
    
    async def display_support_list(self, interaction, data, friend_code, region):
        """Display the support list from API data"""
        try:
            user_name = data.get('name', 'Unknown Master')
            decks = data.get('decks', [])
            
            embed = discord.Embed(
                title=f"🔍 {user_name}'s Support List",
                description=f"Friend Code: `{friend_code}` | Region: {region.upper()}",
                color=0x3498db
            )
            
            # Display up to 3 decks
            for i, deck in enumerate(decks[:3], 1):
                servants = deck.get('servants', [])
                deck_text = []
                
                for servant in servants[:6]:  # Max 6 slots
                    svt_name = servant.get('name', 'Unknown')
                    svt_class = servant.get('className', '?')
                    level = servant.get('level', '?')
                    np_level = servant.get('npLevel', 1)
                    
                    # Get CE info if equipped
                    ce = servant.get('craftEssence', {})
                    ce_name = ce.get('name', 'No CE')
                    ce_level = ce.get('level', '')
                    
                    # Build entry
                    stars = "⭐" * np_level
                    entry = f"**{svt_name}** ({svt_class}) Lv.{level} NP{stars}"
                    if ce_name != 'No CE':
                        entry += f"\n└ {ce_name} Lv.{ce_level}"
                    
                    deck_text.append(entry)
                
                if deck_text:
                    embed.add_field(
                        name=f"Support Deck {i}",
                        value="\n\n".join(deck_text),
                        inline=False
                    )
            
            # Add last updated
            last_updated = data.get('lastUpdated', 'Unknown')
            embed.set_footer(text=f"Last Updated: {last_updated} | Data from Rayshift.io")
            
            # Add refresh button
            view = RayshiftRefreshView(self, friend_code, region)
            await interaction.followup.send(embed=embed, view=view)
            
        except Exception as e:
            print(f"Display error: {e}")
            await self.send_fallback_embed(interaction, friend_code, region)
    
    async def trigger_initial_lookup(self, interaction, friend_code, region):
        """Trigger first-time lookup"""
        profile_url = f"https://rayshift.io/{region}/{friend_code}"
        
        embed = discord.Embed(
            title="⏳ Profile Not Cached",
            description=f"Friend Code: `{friend_code}`",
            color=0xf1c40f
        )
        
        embed.add_field(
            name="First Time Setup Required",
            value=f"This profile hasn't been looked up before.\n\n"
                  f"Rayshift needs to search the game server, which takes ~30-60 seconds.\n\n"
                  f"**[Click here to initialize →]({profile_url})**\n\n"
                  f"After the page loads, run this command again!",
            inline=False
        )
        
        await interaction.followup.send(embed=embed)
    
    async def send_fallback_embed(self, interaction, friend_code, region):
        """Send fallback when API fails"""
        profile_url = f"https://rayshift.io/{region}/{friend_code}"
        
        embed = discord.Embed(
            title="⚠️ Couldn't Fetch Support List",
            description=f"Friend Code: `{friend_code}` | Region: {region.upper()}",
            color=0xe74c3c
        )
        
        embed.add_field(
            name="Why?",
            value="Rayshift.io uses Cloudflare protection that blocks automated requests from cloud servers.\n\n"
                  "This is a common issue with Discord bots hosted on Railway/Heroku/AWS.",
            inline=False
        )
        
        embed.add_field(
            name="Solution",
            value=f"**[View profile directly on Rayshift →]({profile_url})**\n\n"
                  "The website works fine - only automated fetching is blocked.",
            inline=False
        )
        
        view = discord.ui.View()
        view.add_item(discord.ui.Button(
            label="🔗 Open Rayshift",
            style=discord.ButtonStyle.link,
            url=profile_url
        ))
        
        await interaction.followup.send(embed=embed, view=view)

class RayshiftRefreshView(discord.ui.View):
    def __init__(self, cog, friend_code, region):
        super().__init__(timeout=60)
        self.cog = cog
        self.friend_code = friend_code
        self.region = region
    
    @discord.ui.button(label="🔄 Refresh", style=discord.ButtonStyle.primary)
    async def refresh(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        # Re-run the command
        await self.cog.rayshift.callback(
            self.cog, 
            interaction, 
            self.friend_code, 
            app_commands.Choice(name=self.region.upper(), value=self.region)
        )

async def setup(bot):
    await bot.add_cog(RayshiftCog(bot))
