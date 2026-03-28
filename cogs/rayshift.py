import discord
from discord import app_commands
from discord.ext import commands
import aiohttp
from bs4 import BeautifulSoup
import re

class RayshiftCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.base_url = "https://rayshift.io"
    
    @app_commands.command(name="rayshift", description="🔍 Lookup FGO support list on Rayshift.io")
    @app_commands.describe(
        friend_code="Your 9-digit FGO friend code",
        region="Game region (JP or NA)"
    )
    @app_commands.choices(region=[
        app_commands.Choice(name="Japan", value="jp"),
        app_commands.Choice(name="North America", value="na")
    ])
    async def rayshift_lookup(
        self, 
        interaction: discord.Interaction, 
        friend_code: str,
        region: app_commands.Choice[str] = "jp"
    ):
        """Scrape and display a player's support list from Rayshift.io"""
        await interaction.response.defer()
        
        region_code = region.value if isinstance(region, app_commands.Choice) else region
        
        # Clean and validate friend code
        cleaned_code = friend_code.replace("-", "").replace(" ", "")
        if not cleaned_code.isdigit() or len(cleaned_code) != 9:
            await interaction.followup.send(
                "❌ Invalid friend code! Must be exactly 9 digits.\n"
                "Example: `801625519` or `801-625-519`",
                ephemeral=True
            )
            return
        
        profile_url = f"{self.base_url}/{region_code}/{cleaned_code}"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        }
        
        try:
            async with aiohttp.ClientSession(headers=headers) as session:
                async with session.get(profile_url, timeout=20) as resp:
                    if resp.status == 404:
                        await interaction.followup.send(
                            f"❌ Profile not found!\n"
                            f"The friend code `{cleaned_code}` doesn't exist or hasn't been indexed yet.\n"
                            f"Visit {profile_url} first to initialize it.",
                            ephemeral=True
                        )
                        return
                    
                    if resp.status != 200:
                        await interaction.followup.send(
                            f"❌ Rayshift returned error {resp.status}. Try again later.",
                            ephemeral=True
                        )
                        return
                    
                    html = await resp.text()
            
            # Parse with BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            
            # Extract player name
            player_name = "Unknown Master"
            title = soup.find('title')
            if title:
                # Title format: "Rayshift - Player Name"
                title_text = title.get_text().replace("Rayshift - ", "").strip()
                if title_text and title_text != "Rayshift":
                    player_name = title_text
            
            # Alternative: look for h1 or profile name
            h1 = soup.find('h1')
            if h1:
                player_name = h1.get_text().strip()
            
            # Find support decks
            decks = []
            
            # Rayshift uses specific class names for decks
            deck_containers = soup.find_all('div', class_=re.compile(r'deck|support|party', re.I))
            
            # If not found by class, try sections or divs with servant images
            if not deck_containers:
                # Look for containers with multiple servant images
                all_images = soup.find_all('img', src=re.compile(r'rayshift|fgo|servant', re.I))
                # Group images that are close together (same parent)
                deck_parents = {}
                for img in all_images:
                    parent = img.find_parent(['div', 'section'])
                    if parent:
                        parent_id = id(parent)
                        if parent_id not in deck_parents:
                            deck_parents[parent_id] = {'parent': parent, 'images': []}
                        deck_parents[parent_id]['images'].append(img)
                
                # Parents with 3-6 images are likely decks
                for item in deck_parents.values():
                    if 3 <= len(item['images']) <= 6:
                        deck_containers.append(item['parent'])
            
            # Parse each deck
            for deck_idx, deck in enumerate(deck_containers[:3], 1):
                servants = []
                
                # Find servant entries
                servant_entries = deck.find_all(['div', 'a'], class_=re.compile(r'servant|card|unit', re.I))
                
                if not servant_entries:
                    # Try finding by images with alt text containing servant names
                    images = deck.find_all('img')
                    for img in images:
                        alt = img.get('alt', '')
                        src = img.get('src', '')
                        
                        # Skip CE images (usually have "ce" or "craft" in URL)
                        if 'craft' in src.lower() or 'ce-' in src.lower():
                            continue
                            
                        # Extract servant name from alt or title
                        name = alt or img.get('title', '')
                        if name and len(name) > 2:
                            servants.append(name)
                else:
                    for entry in servant_entries:
                        # Get servant name
                        name_elem = entry.find(['span', 'div'], class_=re.compile(r'name|title', re.I))
                        name = name_elem.get_text().strip() if name_elem else entry.get_text().strip()
                        
                        # Get CE if present
                        ce_elem = entry.find(['span', 'div'], class_=re.compile(r'ce|essence|craft', re.I))
                        ce_name = ce_elem.get_text().strip() if ce_elem else None
                        
                        if name:
                            display = f"{name}" + (f" ({ce_name})" if ce_name else "")
                            servants.append(display)
                
                if servants:
                    decks.append({
                        'number': deck_idx,
                        'servants': servants[:6]  # Max 6 per deck
                    })
            
            # Create embed
            embed = discord.Embed(
                title=f"🔍 {player_name}'s Support List",
                url=profile_url,
                description=f"Friend Code: `{cleaned_code}` | Region: {region_code.upper()}",
                color=0x3498db
            )
            
            # Add decks to embed
            if decks:
                for deck in decks:
                    deck_names = "\n".join([f"• {name}" for name in deck['servants']])
                    
                    # Determine deck type based on common FGO patterns
                    deck_type = f"Deck {deck['number']}"
                    if deck['number'] == 1:
                        deck_type = "Deck 1 (All Classes)"
                    elif deck['number'] == 2:
                        deck_type = "Deck 2 (Cavalry/Extra)"
                    elif deck['number'] == 3:
                        deck_type = "Deck 3 (Extra/Specific)"
                    
                    embed.add_field(
                        name=deck_type,
                        value=deck_names or "Empty",
                        inline=False
                    )
            else:
                # Couldn't parse decks - provide link instead
                embed.add_field(
                    name="Support Data",
                    value="⚠️ Couldn't parse support list automatically.\n"
                          f"[Click here to view on Rayshift]({profile_url})",
                    inline=False
                )
            
            # Try to find last updated time
            updated_elem = soup.find(string=re.compile(r'updated|last seen|login', re.I))
            if updated_elem:
                parent = updated_elem.find_parent(['div', 'span', 'p'])
                if parent:
                    embed.set_footer(text=parent.get_text().strip())
                else:
                    embed.set_footer(text="Data from Rayshift.io")
            else:
                embed.set_footer(text="Data from Rayshift.io")
            
            # Add refresh button
            view = RayshiftView(self, cleaned_code, region_code)
            
            await interaction.followup.send(embed=embed, view=view)
            
        except aiohttp.ClientError as e:
            await interaction.followup.send(
                f"❌ Connection error: Couldn't reach Rayshift.io\n"
                f"The site may be down or blocking requests.",
                ephemeral=True
            )
        except Exception as e:
            print(f"Rayshift error: {e}")
            await interaction.followup.send(
                f"⚠️ Error parsing data. [View profile directly]({profile_url})",
                ephemeral=True
            )

class RayshiftView(discord.ui.View):
    def __init__(self, cog, friend_code, region):
        super().__init__(timeout=180)
        self.cog = cog
        self.friend_code = friend_code
        self.region = region
        self.url = f"https://rayshift.io/{region}/{friend_code}"
    
    @discord.ui.button(label="🔄 Refresh", style=discord.ButtonStyle.primary)
    async def refresh_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Refresh the rayshift data"""
        await interaction.response.defer()
        
        # Re-run the lookup
        # Create a fake interaction to reuse the command logic
        class FakeInteraction:
            def __init__(self, original):
                self.user = original.user
                self.guild = original.guild
                self.channel = original.channel
                self._defer = False
            
            async def response(self):
                return self
            
            async def defer(self):
                self._defer = True
            
            async def followup_send(self, **kwargs):
                await interaction.edit_original_response(**kwargs)
        
        # Call the command again
        await self.cog.rayshift_lookup.callback(
            self.cog,
            interaction,
            self.friend_code,
            app_commands.Choice(name=self.region.upper(), value=self.region)
        )
        
        await interaction.followup.send("✅ Refreshed!", ephemeral=True)

async def setup(bot):
    await bot.add_cog(RayshiftCog(bot))
