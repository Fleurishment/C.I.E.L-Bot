import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import Button, View
import aiohttp
import re
import random
import datetime
from utils.atlas_api import AtlasAPI

class ServantView(View):
    def __init__(self, servant_data, assets, region):
        super().__init__(timeout=180)
        self.servant = servant_data
        self.assets = assets
        self.region = region
        self.current_page = 0
        
    def get_pages(self):
        """Generate embed pages for the servant"""
        pages = []
        
        # Page 1: Basic Info & Stats
        embed = discord.Embed(
            title=f"{self.servant['name']} [{self.servant['rarity']}★]",
            description=f"**Class:** {self.servant['className']} | **ID:** {self.servant['id']}",
            color=self.get_rarity_color()
        )
        
        if self.servant.get('faces') and len(self.servant['faces']) > 0:
            embed.set_thumbnail(url=self.servant['faces'][0])
        
        stats = self.servant.get('atkGrowth', [])
        hp_stats = self.servant.get('hpGrowth', [])
        
        embed.add_field(name="Cost", value=self.servant.get('cost', 'N/A'), inline=True)
        embed.add_field(name="ATK (Max)", value=stats[-1] if stats else 'N/A', inline=True)
        embed.add_field(name="HP (Max)", value=hp_stats[-1] if hp_stats else 'N/A', inline=True)
        embed.add_field(name="Growth Curve", value=self.servant.get('growthCurve', 'N/A'), inline=True)
        embed.add_field(name="Star Absorption", value=self.servant.get('starAbsorb', 'N/A'), inline=True)
        embed.add_field(name="Star Generation", value=f"{self.servant.get('starGen', 'N/A')}%", inline=True)
        
        np_gain = self.servant.get('npGain', {})
        if np_gain:
            embed.add_field(
                name="NP Gain", 
                value=f"Attack: {np_gain.get('attack', 'N/A')}%\nDefense: {np_gain.get('defense', 'N/A')}%",
                inline=False
            )
        
        traits = [t['name'] for t in self.servant.get('traits', [])][:5]
        if traits:
            embed.add_field(name="Traits", value=", ".join(traits), inline=False)
        
        embed.set_footer(text=f"Page 1/4 • Region: {self.region}")
        pages.append(embed)
        
        # Page 2: Active Skills
        skills_embed = discord.Embed(
            title=f"{self.servant['name']} - Skills",
            color=self.get_rarity_color()
        )
        
        for i, skill in enumerate(self.servant.get('skills', []), 1):
            skill_name = skill.get('name', 'Unknown')
            skill_rank = skill.get('rank', '-')
            cooldown = skill.get('coolDown', [0, 0])
            
            detail = skill.get('detail', 'No description available')
            detail = re.sub(r'\[.*?\]', '', detail)
            detail = detail.replace('&lt;', '<').replace('&gt;', '>')
            detail = detail[:200] + "..." if len(detail) > 200 else detail
            
            skills_embed.add_field(
                name=f"Skill {i}: {skill_name} {skill_rank}",
                value=f"**Cooldown:** {cooldown[0]}-{cooldown[-1]} turns\n{detail}",
                inline=False
            )
        
        skills_embed.set_footer(text=f"Page 2/4 • Region: {self.region}")
        pages.append(skills_embed)
        
        # Page 3: Noble Phantasm
        np_embed = discord.Embed(
            title=f"{self.servant['name']} - Noble Phantasm",
            color=self.get_rarity_color()
        )
        
        np_data = self.servant.get('noblePhantasms', [{}])[0]
        if np_data:
            np_name = np_data.get('name', 'Unknown')
            np_rank = np_data.get('rank', '-')
            np_type = np_data.get('card', 'Unknown')
            
            np_embed.add_field(name="Name", value=f"{np_name} {np_rank}", inline=True)
            np_embed.add_field(name="Card Type", value=np_type, inline=True)
            
            np_detail = np_data.get('detail', 'No description available')
            np_detail = re.sub(r'\[.*?\]', '', np_detail)
            np_detail = np_detail.replace('&lt;', '<').replace('&gt;', '>')
            np_detail = np_detail[:300] + "..." if len(np_detail) > 300 else np_detail
            
            np_embed.add_field(name="Description", value=np_detail, inline=False)
            
            np_functions = np_data.get('functions', [])
            if np_functions:
                effects = []
                for func in np_functions:
                    svals = func.get('svals', [])
                    if svals:
                        effect_text = func.get('popupText', func.get('funcType', 'Effect'))
                        if effect_text and effect_text not in ['addState', 'damage']:
                            effects.append(f"• {effect_text}")
                if effects:
                    np_embed.add_field(name="Effects", value="\n".join(effects[:3]) or "See description", inline=False)
        
        np_embed.set_footer(text=f"Page 3/4 • Region: {self.region}")
        pages.append(np_embed)
        
        # Page 4: Passives & Artwork
        passive_embed = discord.Embed(
            title=f"{self.servant['name']} - Passives & Materials",
            color=self.get_rarity_color()
        )
        
        passives = self.servant.get('classPassive', [])
        if passives:
            for passive in passives:
                p_name = passive.get('name', 'Unknown')
                p_detail = passive.get('detail', 'No description')
                p_detail = re.sub(r'\[.*?\]', '', p_detail)
                passive_embed.add_field(
                    name=f"Passive: {p_name}",
                    value=p_detail[:100] + "..." if len(p_detail) > 100 else p_detail,
                    inline=False
                )
        
        ascension = self.servant.get('ascensionMaterials', {})
        if ascension:
            mats_text = []
            for key, value in list(ascension.items())[:2]:
                items = value.get('items', [])
                item_names = [item.get('name', 'Unknown') for item in items[:3]]
                qp = value.get('qp', 0)
                mats_text.append(f"Ascension {key}: {', '.join(item_names)} ({qp:,} QP)")
            
            if mats_text:
                passive_embed.add_field(name="Ascension Materials", value="\n".join(mats_text), inline=False)
        
        chara_graph = self.assets.get('charaGraph', {})
        if chara_graph:
            asc_images = chara_graph.get('ascension', {})
            if asc_images and len(asc_images) > 0:
                first_key = sorted(asc_images.keys())[0]
                first_art = asc_images[first_key]
                if first_art and first_art.startswith('http'):
                    passive_embed.set_image(url=first_art)
        
        passive_embed.set_footer(text=f"Page 4/4 • Region: {self.region} • Use buttons to navigate")
        pages.append(passive_embed)
        
        return pages
    
    def get_rarity_color(self):
        rarity_colors = {5: 0xffd700, 4: 0xc0c0c0, 3: 0xcd7f32, 2: 0x8b4513, 1: 0x696969, 0: 0x2f4f4f}
        return rarity_colors.get(self.servant.get('rarity', 3), 0x3498db)
    
    @discord.ui.button(label="◀ Previous", style=discord.ButtonStyle.grey)
    async def previous_button(self, interaction: discord.Interaction, button: Button):
        if self.current_page > 0:
            self.current_page -= 1
            pages = self.get_pages()
            await interaction.response.edit_message(embed=pages[self.current_page], view=self)
        else:
            await interaction.response.defer()
    
    @discord.ui.button(label="Next ▶", style=discord.ButtonStyle.grey)
    async def next_button(self, interaction: discord.Interaction, button: Button):
        if self.current_page < 3:
            self.current_page += 1
            pages = self.get_pages()
            await interaction.response.edit_message(embed=pages[self.current_page], view=self)
        else:
            await interaction.response.defer()

class ServantCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.api = None
    
    async def cog_load(self):
        self.api = AtlasAPI(self.bot.session)
    
    @app_commands.command(name="servant", description="Search for FGO servant information")
    @app_commands.describe(name="Servant name to search for", region="Game region (NA or JP)")
    @app_commands.choices(region=[
        app_commands.Choice(name="North America", value="NA"),
        app_commands.Choice(name="Japan", value="JP")
    ])
    async def servant_search(self, interaction: discord.Interaction, name: str, region: app_commands.Choice[str] = "NA"):
        await interaction.response.defer()
        
        region_code = region.value if isinstance(region, app_commands.Choice) else region
        
        try:
            results = await self.api.search_servant(name, region_code)
            
            if not results:
                await interaction.followup.send(f"❌ No servants found matching '{name}' in {region_code} region.")
                return
            
            if len(results) == 1:
                await self.display_servant(interaction, results[0]['id'], region_code)
            else:
                await self.show_selection(interaction, results, region_code, "servant")
        except Exception as e:
            await interaction.followup.send(f"❌ Error: {str(e)}")
    
    async def show_selection(self, interaction, results, region, command_type):
        """Generic selection dropdown"""
        embed = discord.Embed(
            title="Multiple Servants Found",
            description=f"Select a servant from the dropdown:",
            color=0x3498db
        )
        
        for i, servant in enumerate(results[:5], 1):
            rarity = "★" * servant.get('rarity', 0)
            class_name = servant.get('className', 'Unknown')
            embed.add_field(name=f"{i}. {servant['name']}", value=f"{class_name} {rarity}", inline=False)
        
        options = []
        for servant in results[:5]:
            rarity = "★" * servant.get('rarity', 0)
            options.append(discord.SelectOption(
                label=f"{servant['name'][:25]}",
                description=f"{servant.get('className', 'Unknown')} {rarity}",
                value=str(servant['id'])
            ))
        
        select = discord.ui.Select(placeholder="Choose a servant...", options=options, min_values=1, max_values=1)
        
        async def select_callback(interaction: discord.Interaction):
            await interaction.response.defer()
            try:
                servant_id = int(select.values[0])
                if command_type == "servant":
                    await self.display_servant(interaction, servant_id, region)
                elif command_type == "artwork":
                    await self.display_artwork(interaction, servant_id, region)
            except Exception as e:
                await interaction.followup.send(f"Error: {e}", ephemeral=True)
        
        select.callback = select_callback
        
        view = discord.ui.View(timeout=120)
        view.add_item(select)
        
        await interaction.followup.send(embed=embed, view=view)
    
    async def display_servant(self, interaction: discord.Interaction, servant_id: int, region: str):
        """Fetch and display detailed servant information"""
        if not interaction.response.is_done():
            await interaction.response.defer()
        
        try:
            servant_data = await self.api.get_servant_details(servant_id, region)
            
            if not servant_data:
                await interaction.followup.send("❌ Failed to fetch servant details.")
                return
            
            assets = await self.api.get_servant_assets(servant_id, region)
            
            view = ServantView(servant_data, assets, region)
            pages = view.get_pages()
            
            await interaction.followup.send(embed=pages[0], view=view)
        except Exception as e:
            await interaction.followup.send(f"❌ Error displaying servant: {str(e)}")
    
    @app_commands.command(name="artwork", description="Display servant artwork/ascensions")
    @app_commands.describe(servant_name="Name of the servant", ascension="Ascension level (1-4, or 0 for all)", region="Game region")
    @app_commands.choices(region=[
        app_commands.Choice(name="North America", value="NA"),
        app_commands.Choice(name="Japan", value="JP")
    ])
    async def artwork(self, interaction: discord.Interaction, servant_name: str, ascension: int = 4, region: app_commands.Choice[str] = "NA"):
        await interaction.response.defer()
        
        region_code = region.value if isinstance(region, app_commands.Choice) else region
        
        try:
            results = await self.api.search_servant(servant_name, region_code)
            
            if not results:
                await interaction.followup.send(f"❌ No servant found matching '{servant_name}'")
                return
            
            if len(results) == 1:
                await self.display_artwork_by_id(interaction, results[0]['id'], region_code, ascension, results[0]['name'])
            else:
                await self.show_selection(interaction, results, region_code, "artwork")
        except Exception as e:
            await interaction.followup.send(f"❌ Error: {str(e)}")
    
    async def display_artwork(self, interaction: discord.Interaction, servant_id: int, region: str):
        """Display artwork with default ascension 4"""
        try:
            servant_data = await self.api.get_servant_details(servant_id, region)
            name = servant_data.get('name', 'Unknown') if servant_data else 'Unknown'
        except:
            name = 'Unknown'
        
        await self.display_artwork_by_id(interaction, servant_id, region, 4, name)
    
    async def display_artwork_by_id(self, interaction: discord.Interaction, servant_id: int, region: str, ascension: int, servant_name: str = None):
        """Display artwork for specific servant ID"""
        if not interaction.response.is_done():
            await interaction.response.defer()
        
        try:
            if not servant_name:
                servant_data = await self.api.get_servant_details(servant_id, region)
                servant_name = servant_data.get('name', 'Unknown') if servant_data else 'Unknown'
            
            assets = await self.api.get_servant_assets(servant_id, region)
            
            if not assets:
                await interaction.followup.send("❌ No assets found for this servant.")
                return
            
            chara_graph = assets.get('charaGraph', {})
            
            if not chara_graph:
                await interaction.followup.send("❌ No artwork found for this servant.")
                return
            
            embed = discord.Embed(title=f"{servant_name} - Artwork", color=0xffd700)
            
            asc_images = chara_graph.get('ascension', {})
            costume_images = chara_graph.get('costume', {})
            
            if ascension == 0:
                if asc_images:
                    desc_lines = []
                    for key in sorted(asc_images.keys()):
                        url = asc_images[key]
                        if url and isinstance(url, str) and url.startswith('http'):
                            desc_lines.append(f"**Ascension {key}:** [View]({url})")
                    
                    if desc_lines:
                        embed.description = "\n".join(desc_lines[:4])
                    else:
                        embed.description = "No valid artwork URLs found."
                
                if costume_images:
                    costume_lines = []
                    for key, url in list(costume_images.items())[:3]:
                        if url and isinstance(url, str) and url.startswith('http'):
                            costume_lines.append(f"**Costume {key}:** [View]({url})")
                    if costume_lines:
                        embed.add_field(name="Costumes", value="\n".join(costume_lines), inline=False)
                
                await interaction.followup.send(embed=embed)
            else:
                key = str(ascension)
                url = None
                
                if key in asc_images:
                    url = asc_images[key]
                elif asc_images:
                    highest = max(asc_images.keys(), key=lambda x: int(x) if str(x).isdigit() else 0)
                    url = asc_images[highest]
                    embed.description = f"Ascension Level {highest} (requested {ascension} not available)"
                
                if not url or not isinstance(url, str) or not url.startswith('http'):
                    await interaction.followup.send("❌ Invalid artwork URL.")
                    return
                
                embed.set_image(url=url)
                if not embed.description:
                    embed.description = f"Ascension Level {key if key in asc_images else highest}"
                
                await interaction.followup.send(embed=embed)
                
        except Exception as e:
            await interaction.followup.send(f"❌ Error fetching artwork: {str(e)}")
    
    @app_commands.command(name="randomart", description="🎲 Get a random servant artwork")
@app_commands.describe(region="Game region")
@app_commands.choices(region=[
    app_commands.Choice(name="North America", value="NA"),
    app_commands.Choice(name="Japan", value="JP")
])
async def random_artwork(self, interaction: discord.Interaction, region: app_commands.Choice[str] = "NA"):
    """Get random servant artwork from ascension 1-4 or costumes"""
    await interaction.response.defer()
    
    region_code = region.value if isinstance(region, app_commands.Choice) else region
    
    try:
        # First, search for a common term to get a list of valid servant IDs
        # Using "a" gets many servants
        search_results = await self.api.search_servant("a", region_code)
        
        if not search_results or len(search_results) == 0:
            await interaction.followup.send("❌ Could not fetch servant list.")
            return
        
        # Shuffle and pick random servants from valid results
        valid_servants = [s for s in search_results if s.get('id')]
        random.shuffle(valid_servants)
        
        # Try up to 10 random servants
        for servant_info in valid_servants[:10]:
            try:
                servant_id = servant_info['id']
                servant_name = servant_info.get('name', 'Unknown')
                
                # Get assets directly - skip getting full details to save time
                assets = await self.api.get_servant_assets(servant_id, region_code)
                
                if not assets:
                    continue
                
                chara_graph = assets.get('charaGraph', {})
                if not chara_graph:
                    continue
                
                # Collect all artwork
                all_artwork = []
                
                # Ascension artwork
                asc_images = chara_graph.get('ascension', {})
                for key, url in asc_images.items():
                    if url and isinstance(url, str) and url.startswith('http'):
                        all_artwork.append({
                            'url': url,
                            'type': 'Ascension',
                            'number': key
                        })
                
                # Costume artwork
                costume_images = chara_graph.get('costume', {})
                for key, url in costume_images.items():
                    if url and isinstance(url, str) and url.startswith('http'):
                        all_artwork.append({
                            'url': url,
                            'type': 'Costume',
                            'number': key
                        })
                
                if not all_artwork:
                    continue
                
                # Success! Pick random artwork
                selected = random.choice(all_artwork)
                
                # Get full details only if we found artwork
                servant_data = await self.api.get_servant_details(servant_id, region_code)
                if servant_data:
                    servant_name = servant_data.get('name', servant_name)
                    servant_class = servant_data.get('className', 'Unknown')
                    rarity = servant_data.get('rarity', 0)
                else:
                    servant_class = servant_info.get('className', 'Unknown')
                    rarity = servant_info.get('rarity', 0)
                
                # Create embed
                embed = discord.Embed(
                    title=f"🎲 Random Artwork",
                    description=f"**{servant_name}**",
                    color=0xff69b4
                )
                embed.set_image(url=selected['url'])
                
                # Info fields
                embed.add_field(name="Class", value=servant_class, inline=True)
                embed.add_field(name="Rarity", value="★" * rarity, inline=True)
                embed.add_field(name="Region", value=region_code, inline=True)
                embed.add_field(
                    name="Artwork", 
                    value=f"{selected['type']} {selected['number']}", 
                    inline=True
                )
                embed.add_field(name="Servant ID", value=servant_id, inline=True)
                
                # Add link to view all artwork
                embed.set_footer(text=f"Use /artwork {servant_name} to see all artwork")
                
                await interaction.followup.send(embed=embed)
                return  # Success!
                
            except Exception as e:
                print(f"Error with servant {servant_info.get('id')}: {e}")
                continue
        
        # If we get here, no artwork was found after trying all
        await interaction.followup.send("❌ Couldn't find any artwork after trying multiple servants. The API might be slow - try again!")
        
    except Exception as e:
        print(f"Randomart error: {e}")
        await interaction.followup.send(f"❌ Error: {str(e)}")
    
    @app_commands.command(name="search", description="Search servants by name (API only)")
    @app_commands.describe(name="Servant name")
    async def search(self, interaction: discord.Interaction, name: str):
        """Quick search without scraping"""
        await interaction.response.defer()
        
        try:
            results = await self.api.search_servant(name, "NA")
            if not results:
                await interaction.followup.send(f"No results for '{name}'")
                return
            
            embed = discord.Embed(title="Search Results", color=0x00ff00)
            for s in results[:5]:
                stars = "★" * s.get('rarity', 0)
                embed.add_field(
                    name=s['name'],
                    value=f"{s.get('className', '?')} | {stars} | ID: {s['id']}",
                    inline=False
                )
            
            await interaction.followup.send(embed=embed)
        except Exception as e:
            await interaction.followup.send(f"❌ Error: {str(e)}")
    
    @app_commands.command(name="ce", description="Search for Craft Essences")
    @app_commands.describe(name="CE name to search for", region="Game region")
    @app_commands.choices(region=[
        app_commands.Choice(name="North America", value="NA"),
        app_commands.Choice(name="Japan", value="JP")
    ])
    async def ce_search(self, interaction: discord.Interaction, name: str, region: app_commands.Choice[str] = "NA"):
        """Search for Craft Essences"""
        await interaction.response.defer()
        
        region_code = region.value if isinstance(region, app_commands.Choice) else region
        url = f"https://api.atlasacademy.io/nice/{region_code}/equip/search?name={name}"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status != 200:
                        await interaction.followup.send("❌ No CEs found.")
                        return
                    ces = await resp.json()
            
            if not ces:
                await interaction.followup.send(f"No CEs found matching '{name}'")
                return
            
            embed = discord.Embed(title="Craft Essence Results", color=0xff69b4)
            
            for ce in ces[:5]:
                stars = "★" * ce.get('rarity', 0)
                hp = ce.get('hpGrowth', [0])[-1] if ce.get('hpGrowth') else 0
                atk = ce.get('atkGrowth', [0])[-1] if ce.get('atkGrowth') else 0
                
                skills = ce.get('skills', [])
                effect = "No effect"
                if skills:
                    effect = skills[0].get('detail', 'Unknown')
                    effect = re.sub(r'\[.*?\]', '', effect)[:100] + "..."
                
                embed.add_field(
                    name=f"{ce['name']} {stars}",
                    value=f"ATK: {atk} | HP: {hp}\n{effect}",
                    inline=False
                )
            
            await interaction.followup.send(embed=embed)
        except Exception as e:
            await interaction.followup.send(f"❌ Error: {str(e)}")
    
    @app_commands.command(name="gacha", description="🎲 Roll the gacha!")
    @app_commands.describe(quartz="Amount of Saint Quartz to spend (3 per roll)", banner="Choose your banner type")
    @app_commands.choices(banner=[
        app_commands.Choice(name="Story Banner", value="story"),
        app_commands.Choice(name="Rate-Up SSR", value="rateup_ssr"),
        app_commands.Choice(name="Rate-Up SR", value="rateup_sr")
    ])
    async def gacha(self, interaction: discord.Interaction, quartz: int = 30, banner: app_commands.Choice[str] = "story"):
        """Fun gacha simulator"""
        await interaction.response.defer()
        
        rates = {
            "story": {"SSR": 0.01, "SR": 0.03},
            "rateup_ssr": {"SSR": 0.008, "SR": 0.03},
            "rateup_sr": {"SSR": 0.01, "SR": 0.024}
        }
        
        banner_type = banner.value if isinstance(banner, app_commands.Choice) else banner
        current_rates = rates.get(banner_type, rates["story"])
        
        rolls = min(quartz // 3, 100)
        if rolls <= 0:
            await interaction.followup.send("❌ You need at least 3 Saint Quartz for 1 roll!")
            return
        
        results = {"SSR": 0, "SR": 0, "R": 0, "CE_SSR": 0, "CE_SR": 0, "CE_R": 0}
        notable_rolls = []
        
        featured_ssr = ["Space Ishtar", "Gilgamesh", "Kama", "Morgan", "Oberon", "Artoria Caster"]
        featured_sr = ["Ishtar", "Ereshkigal", "Gawain", "Lancelot", "Nitocris", "Heracles"]
        
        for _ in range(rolls):
            roll = random.random()
            
            if roll < current_rates["SSR"]:
                servant = random.choice(featured_ssr) if (banner_type == "rateup_ssr" and random.random() < 0.7) else "Random SSR"
                results["SSR"] += 1
                notable_rolls.append(f"⭐⭐⭐⭐⭐ **{servant}**")
            elif roll < current_rates["SSR"] + current_rates["SR"]:
                servant = random.choice(featured_sr) if (banner_type == "rateup_sr" and random.random() < 0.7) else "Random SR"
                results["SR"] += 1
                notable_rolls.append(f"⭐⭐⭐⭐ {servant}")
            elif roll < current_rates["SSR"] + current_rates["SR"] + 0.40:
                results["R"] += 1
            else:
                ce_roll = random.random()
                if ce_roll < 0.04:
                    results["CE_SSR"] += 1
                elif ce_roll < 0.12:
                    results["CE_SR"] += 1
                else:
                    results["CE_R"] += 1
        
        embed = discord.Embed(
            title=f"🎲 Gacha Results ({rolls} rolls)",
            description=f"Banner: {banner_type.replace('_', ' ').title()}",
            color=0xffd700 if results["SSR"] > 0 else 0x3498db
        )
        
        embed.add_field(name="⭐⭐⭐⭐⭐ SSR", value=results["SSR"], inline=True)
        embed.add_field(name="⭐⭐⭐⭐ SR", value=results["SR"], inline=True)
        embed.add_field(name="⭐⭐⭐ R", value=results["R"], inline=True)
        embed.add_field(name="🎴 CEs", value=f"SSR: {results['CE_SSR']}, SR: {results['CE_SR']}, R: {results['CE_R']}", inline=False)
        
        if notable_rolls:
            recent = "\n".join(notable_rolls[-5:])
            embed.add_field(name="Notable Rolls", value=recent, inline=False)
        
        if results["SSR"] == 0 and rolls >= 30:
            embed.set_footer(text="😢 No SSRs? The gacha is cruel... (330 rolls for guaranteed)")
        elif results["SSR"] >= 2:
            embed.set_footer(text="🎉 Jackpot! Excellent rolls!")
        else:
            embed.set_footer(text=f"SQ Used: {rolls * 3} | Good luck on your next rolls!")
        
        await interaction.followup.send(embed=embed)
    
    @app_commands.command(name="sqcalc", description="📊 Calculate Saint Quartz needed")
    @app_commands.describe(target_np="Target NP level (1-5)", current_quartz="How many SQ you have", summon_tickets="How many tickets you have")
    async def sqcalc(self, interaction: discord.Interaction, target_np: int = 1, current_quartz: int = 0, summon_tickets: int = 0):
        """Calculate Saint Quartz needed for NP targets"""
        
        avg_rolls_per_ssr = 143
        np_requirements = {1: 1, 2: 2, 3: 3, 4: 5, 5: 8}
        
        copies_needed = np_requirements.get(target_np, 1)
        expected_rolls = copies_needed * avg_rolls_per_ssr
        sq_needed = (expected_rolls * 3) - current_quartz - (summon_tickets * 3)
        rolls_possible = (current_quartz // 3) + summon_tickets
        
        embed = discord.Embed(title="📊 Saint Quartz Calculator", color=0x9b59b6)
        embed.add_field(name="Target", value=f"NP{target_np} ({copies_needed} copies)", inline=True)
        embed.add_field(name="Expected Rolls", value=f"~{expected_rolls}", inline=True)
        embed.add_field(name="Your Resources", value=f"{current_quartz} SQ + {summon_tickets} tickets = {rolls_possible} rolls", inline=True)
        
        if sq_needed > 0:
            days = sq_needed // 3
            embed.add_field(name="You Need", value=f"**{sq_needed}** more SQ (~{days} days of login)", inline=False)
            embed.color = 0xe74c3c
        else:
            embed.add_field(name="Status", value="✅ You have enough! Good luck!", inline=False)
            embed.color = 0x2ecc71
        
        embed.set_footer(text="Based on 1% SSR rate. Luck varies!")
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="daily", description="📅 Show today's daily quests")
    async def daily(self, interaction: discord.Interaction):
        """Show training grounds rotation"""
        days = ["Archer/Assassin", "Lancer/Rider", "Saber/Caster", "Berserker/All", "Archer/Assassin", "Lancer/Rider", "Saber/Caster"]
        today = days[datetime.datetime.now().weekday()]
        
        embed = discord.Embed(
            title="📅 Today's Training Grounds",
            description=f"**{today}**",
            color=0x1abc9c
        )
        
        embed.add_field(name="Ember Gathering", value="40 AP (Gold), 30 AP (Silver)", inline=False)
        embed.add_field(name="QP Vault", value="40 AP (Super), 30 AP (Extreme)", inline=False)
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="weakness", description="⚔️ Show class advantages")
    @app_commands.describe(class_name="Class to check")
    @app_commands.choices(class_name=[
        app_commands.Choice(name="Saber", value="Saber"),
        app_commands.Choice(name="Archer", value="Archer"),
        app_commands.Choice(name="Lancer", value="Lancer"),
        app_commands.Choice(name="Rider", value="Rider"),
        app_commands.Choice(name="Caster", value="Caster"),
        app_commands.Choice(name="Assassin", value="Assassin"),
        app_commands.Choice(name="Berserker", value="Berserker"),
        app_commands.Choice(name="Ruler", value="Ruler"),
        app_commands.Choice(name="Avenger", value="Avenger"),
        app_commands.Choice(name="Alter Ego", value="AlterEgo"),
        app_commands.Choice(name="Moon Cancer", value="MoonCancer"),
        app_commands.Choice(name="Foreigner", value="Foreigner"),
        app_commands.Choice(name="Pretender", value="Pretender")
    ])
    async def weakness(self, interaction: discord.Interaction, class_name: app_commands.Choice[str]):
        """Class advantage chart"""
        name = class_name.value
        
        advantages = {
            "Saber": {"strong": "Lancer", "weak": "Archer", "damage": "0.5x to Archer, 2x to Lancer"},
            "Archer": {"strong": "Saber", "weak": "Lancer", "damage": "0.5x to Lancer, 2x to Saber"},
            "Lancer": {"strong": "Archer", "weak": "Saber", "damage": "0.5x to Saber, 2x to Archer"},
            "Rider": {"strong": "Caster", "weak": "Assassin", "damage": "0.5x to Assassin, 2x to Caster"},
            "Caster": {"strong": "Assassin", "weak": "Rider", "damage": "0.5x to Rider, 2x to Assassin"},
            "Assassin": {"strong": "Rider", "weak": "Caster", "damage": "0.5x to Caster, 2x to Rider"},
            "Berserker": {"strong": "All (except Foreigner)", "weak": "All (2x damage taken)", "damage": "1.5x to all, takes 2x from all"},
            "Ruler": {"strong": "Avenger, Moon Cancer, Berserker", "weak": "Avenger", "damage": "Takes half from most classes"},
            "Avenger": {"strong": "Ruler, Berserker", "weak": "Ruler, Foreigner", "damage": "2x to Ruler"},
            "AlterEgo": {"strong": "Cavalry classes", "weak": "Knight classes", "damage": "1.5x to Rider/Caster/Assassin"},
            "MoonCancer": {"strong": "Avenger, Berserker", "weak": "Ruler, Foreigner", "damage": "2x to Avenger"},
            "Foreigner": {"strong": "Berserker, Foreigner", "weak": "Alter Ego", "damage": "2x to Berserker"},
            "Pretender": {"strong": "Assassin, Caster, Rider", "weak": "Berserker, Foreigner", "damage": "2x to Assassin/Caster/Rider"}
        }
        
        data = advantages.get(name, {"strong": "Unknown", "weak": "Unknown", "damage": "No data"})
        
        embed = discord.Embed(
            title=f"⚔️ {name} Class Advantage",
            color=0xe74c3c
        )
        embed.add_field(name="Strong Against", value=data["strong"], inline=True)
        embed.add_field(name="Weak Against", value=data["weak"], inline=True)
        embed.add_field(name="Damage Modifiers", value=data["damage"], inline=False)
        
        if name in ["Saber", "Archer", "Lancer"]:
            embed.add_field(name="Class Triangle", value="Saber > Lancer > Archer > Saber", inline=False)
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="banner", description="🎰 Check current/upcoming banners")
    async def banner(self, interaction: discord.Interaction):
        """Show current and upcoming rate-up banners"""
        banners = [
            {"name": "New Year 2026", "servant": "Koyanskaya of Light", "class": "Assassin", "start": "Jan 1", "end": "Jan 15"},
            {"name": "Valentine 2026", "servant": "Nero Claudius (Bride)", "class": "Saber", "start": "Feb 8", "end": "Feb 22"},
            {"name": "White Day 2026", "servant": "Arthur Pendragon (Prototype)", "class": "Saber", "start": "Mar 8", "end": "Mar 22"}
        ]
        
        embed = discord.Embed(
            title="🎰 Upcoming Banners (NA)",
            description="Rate-up banners for 2026",
            color=0xff69b4
        )
        
        for b in banners:
            embed.add_field(
                name=f"{b['name']}",
                value=f"⭐⭐⭐⭐⭐ {b['servant']} ({b['class']})\n📅 {b['start']} - {b['end']}",
                inline=False
            )
        
        embed.set_footer(text="Dates are estimates based on JP schedule")
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="exp", description="📈 Calculate EXP cards needed")
    @app_commands.describe(current_level="Current level", target_level="Target level", rarity="Servant rarity")
    async def exp_calc(self, interaction: discord.Interaction, current_level: int, target_level: int, rarity: int = 5):
        """Calculate EXP cards needed for leveling"""
        if current_level >= target_level or target_level > 120:
            await interaction.response.send_message("❌ Invalid levels! (Max 120)", ephemeral=True)
            return
        
        exp_per_gold = 32400
        levels_needed = target_level - current_level
        avg_exp_per_level = 100000 if target_level <= 100 else 200000
        total_exp = levels_needed * avg_exp_per_level
        gold_cards = (total_exp // exp_per_gold) + 1
        qp_cost = total_exp * 10
        
        embed = discord.Embed(
            title="📈 EXP Calculator",
            description=f"Level {current_level} → {target_level} ({rarity}★ servant)",
            color=0x9b59b6
        )
        embed.add_field(name="4★ EXP Cards Needed", value=f"~**{gold_cards}** cards", inline=True)
        embed.add_field(name="Approximate QP Cost", value=f"{qp_cost:,}", inline=True)
        embed.add_field(name="Tips", value="Run Ember Gathering daily quests!\n40 AP quest drops ~5-7 gold cards.", inline=False)
        
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(ServantCog(bot))
