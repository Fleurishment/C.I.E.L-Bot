import discord
from discord import app_commands
from discord.ext import commands
import aiohttp
from typing import Optional, Dict, List

class RayshiftCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.base_url = "https://rayshift.io"
    
    @app_commands.command(name="rayshift", description="üîç Lookup FGO support list on Rayshift.io")
    @app_commands.describe(
        friend_code="Your FGO friend code (9 digits)",
        region="Game region (JP or NA)",
        refresh="Force refresh the data"
    )
    @app_commands.choices(region=[
        app_commands.Choice(name="Japan", value="jp"),
        app_commands.Choice(name="North America", value="na")
    ])
    async def rayshift_lookup(
        self, 
        interaction: discord.Interaction, 
        friend_code: str,
        region: app_commands.Choice[str] = "jp",
        refresh: bool = False
    ):
        """Lookup a player's support list on Rayshift.io"""
        await interaction.response.defer()
        
        region_code = region.value if isinstance(region, app_commands.Choice) else region
        
        # Validate friend code (should be 9 digits)
        if not friend_code.isdigit() or len(friend_code) != 9:
            await interaction.followup.send(
                "‚ùŒ Invalid friend code! It should be exactly 9 digits.\n"
                "Example: `/rayshift 801625519 region:JP`",
                ephemeral=True
            )
            return
        
        profile_url = f"{self.base_url}/{region_code}/{friend_code}"
        
        try:
            # Fetch the rayshift page
            async with aiohttp.ClientSession() as session:
                async with session.get(profile_url, timeout=15) as resp:
                    if resp.status == 404:
                        await interaction.followup.send(
                            f"‚ùŒ Profile not found!\n"
                            f"The friend code `{friend_code}` doesn't exist or hasn't been looked up before.\n"
                            f"Visit {profile_url} to initialize the lookup.",
                            ephemeral=True
                        )
                        return
                    
                    if resp.status != 200:
                        await interaction.followup.send(
                            "‚ùŒ Rayshift.io is currently unavailable. Try again later.",
                            ephemeral=True
                        )
                        return
                    
                    html = await resp.text()
            
            # Parse the HTML to extract support data
            # Note: This is basic parsing - you may need to adjust based on actual HTML structure
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            
            # Try to find player name
            player_name = "Unknown Master"
            name_elem = soup.find('h1') or soup.find('title')
            if name_elem:
                player_name = name_elem.get_text().strip().replace("Rayshift - ", "")
            
            # Create embed with profile link
            embed = discord.Embed(
                title=f"ü” Rayshift Profile: {player_name}",
                url=profile_url,
                description=f"Friend Code: `{friend_code}` | Region: {region_code.upper()}",
                color=0x3498db
            )
            
            # Add support decks info (basic extraction)
            # Rayshift typically shows support decks in sections
            decks = soup.find_all('div', {'class': 'deck'}) or soup.find_all('section')
            
            if decks:
                for i, deck in enumerate(decks[:3], 1):  # Max 3 decks
                    servants = deck.find_all('img')
                    servant_names = []
                    
                    for img in servants[:6]:  # Max 6 servants per deck
                        alt = img.get('alt', '')
                        if alt and 'servant' in alt.lower():
                            servant_names.append(alt)
                    
                    if servant_names:
                        embed.add_field(
                            name=f"Support Deck {i}",
                            value="\n".join([f"‚Ä¢ {name}" for name in servant_names[:6]]) or "No servants found",
                            inline=False
                        )
            else:
                # If we can't parse decks, just link to the profile
                embed.add_field(
                    name="Support List",
                    value=f"[Click here to view full support list]({profile_url})",
                    inline=False
                )
            
            # Add last updated info if available
            update_elem = soup.find('span', string=lambda x: x and 'updated' in x.lower())
            if update_elem:
                embed.set_footer(text=f"Last {update_elem.get_text()}")
            else:
                embed.set_footer(text="Data from Rayshift.io")
            
            # Add refresh button
            view = RayshiftView(self, friend_code, region_code, profile_url)
            
            await interaction.followup.send(embed=embed, view=view)
            
        except Exception as e:
            print(f"Rayshift error: {e}")
            await interaction.followup.send(
                f"‚š Ô¸ Couldn't fetch data from Rayshift.\n"
                f"You can view the profile directly at: {profile_url}",
                ephemeral=True
            )

class RayshiftView(discord.ui.View):
    def __init__(self, cog, friend_code, region, url):
        super().__init__(timeout=180)
        self.cog = cog
        self.friend_code = friend_code
        self.region = region
        self.url = url
    
    @discord.ui.button(label="Ÿ”„ Refresh", style=discord.ButtonStyle.primary)
    async def refresh_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Refresh the rayshift data"""
        await interaction.response.defer()
        
        # Trigger a refresh by visiting the URL with refresh parameter
        try:
            async with aiohttp.ClientSession() as session:
                refresh_url = f"{self.url}?refresh=1"
                async with session.get(refresh_url, timeout=10) as resp:
                    if resp.status == 200:
                        embed = interaction.message.embeds[0]
                        embed.color = 0x2ecc71
                        embed.set_footer(text="Data refreshed just now")
                        await interaction.edit_original_response(embed=embed, view=self)
                    else:
                        await interaction.followup.send(
                            "‚š Ô¸ Refresh failed. Rayshift may be rate limiting.",
                            ephemeral=True
                        )
        except Exception as e:
            await interaction.followup.send(
                "‚š Ô¸ Couldn't refresh data.",
                ephemeral=True
            )
    
    @discord.ui.button(label="Ÿ”— Open in Browser", style=discord.ButtonStyle.link, url="")
    async def open_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """This button is a link button, URL set dynamically"""
        pass  # Link buttons don't need callbacks

async def setup(bot):
    await bot.add_cog(RayshiftCog(bot))
