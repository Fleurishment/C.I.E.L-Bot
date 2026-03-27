import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import Button, View
import aiohttp
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
        
        # Cost & Stats
        stats = self.servant.get('atkGrowth', [])
        hp_stats = self.servant.get('hpGrowth', [])
        
        embed.add_field(name="Cost", value=self.servant.get('cost', 'N/A'), inline=True)
        embed.add_field(name="ATK (Max)", value=stats[-1] if stats else 'N/A', inline=True)
        embed.add_field(name="HP (Max)", value=hp_stats[-1] if hp_stats else 'N/A', inline=True)
        
        # Growth Curve
        embed.add_field(name="Growth Curve", value=self.servant.get('growthCurve', 'N/A'), inline=True)
        embed.add_field(name="Star Absorption", value=self.servant.get('starAbsorb', 'N/A'), inline=True)
        embed.add_field(name="Star Generation", value=f"{self.servant.get('starGen', 'N/A')}%", inline=True)
        
        # NP Gain
        np_gain = self.servant.get('npGain', {})
        if np_gain:
            embed.add_field(
                name="NP Gain", 
                value=f"Attack: {np_gain.get('attack', 'N/A')}%\nDefense: {np_gain.get('defense', 'N/A')}%",
                inline=False
            )
        
        # Traits
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
            
            # Get actual skill description
            detail = skill.get('detail', 'No description available')
            # Clean up description - replace [g][o] style tags if present
            import re
            detail = re.sub(r'\[.*?\]', '', detail)  # Remove square bracket tags
            detail = detail.replace('&lt;', '<').replace('&gt;', '>')  # Fix HTML entities
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
            
            # Get NP description
            np_detail = np_data.get('detail', 'No description available')
            np_detail = re.sub(r'\[.*?\]', '', np_detail)
            np_detail = np_detail.replace('&lt;', '<').replace('&gt;', '>')
            np_detail = np_detail[:300] + "..." if len(np_detail) > 300 else np_detail
            
            np_embed.add_field(
                name="Description",
                value=np_detail,
                inline=False
            )
            
            # Overcharge effects if available
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
                    np_embed.add_field(
                        name="Effects",
                        value="\n".join(effects[:3]) or "See description",
                        inline=False
                    )
        
        np_embed.set_footer(text=f"Page 3/4 • Region: {self.region}")
        pages.append(np_embed)
        
        # Page 4: Passives & Ascensions
        passive_embed = discord.Embed(
            title=f"{self.servant['name']} - Passives & Materials",
            color=self.get_rarity_color()
        )
        
        # Passive Skills
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
        
        # Ascension materials
        ascension = self.servant.get('ascensionMaterials', {})
        if ascension:
            mats_text = []
            for key, value in list(ascension.items())[:2]:
                items = value.get('items', [])
                item_names = [item.get('name', 'Unknown') for item in items[:3]]
                qp = value.get('qp', 0)
                mats_text.append(f"Ascension {key}: {', '.join(item_names)} ({qp:,} QP)")
            
            if mats_text:
                passive_embed.add_field(
                    name="Ascension Materials",
                    value="\n".join(mats_text),
                    inline=False
                )
        
        # Artwork preview
        if self.assets.get('charaGraph', {}):
            cards = self.assets['charaGraph']
            if isinstance(cards, dict) and len(cards) > 0:
                # Get first available ascension
                first_key = sorted(cards.keys())[0]
                first_art = cards[first_key]
                passive_embed.set_image(url=first_art)
        
        passive_embed.set_footer(text=f"Page 4/4 • Region: {self.region} • Use buttons to navigate")
        pages.append(passive_embed)
        
        return pages
    
    def get_rarity_color(self):
        rarity_colors = {
            5: 0xffd700,
            4: 0xc0c0c0,
            3: 0xcd7f32,
            2: 0x8b4513,
            1: 0x696969,
            0: 0x2f4f4f
        }
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
        self.session = aiohttp.ClientSession()
        self.api = AtlasAPI(self.session)
    
    async def cog_unload(self):
        await self.session.close()
    
    @app_commands.command(name="servant", description="Search for FGO servant information")
    @app_commands.describe(
        name="Servant name to search for",
        region="Game region (NA or JP)"
    )
    @app_commands.choices(region=[
        app_commands.Choice(name="North America", value="NA"),
        app_commands.Choice(name="Japan", value="JP")
    ])
    async def servant_search(
        self, 
        interaction: discord.Interaction, 
        name: str, 
        region: app_commands.Choice[str] = "NA"
    ):
        await interaction.response.defer()
        
        region_code = region.value if isinstance(region, app_commands.Choice) else region
        
        try:
            results = await self.api.search_servant(name, region_code)
            
            if not results:
                await interaction.followup.send(
                    f"❌ No servants found matching '{name}' in {region_code} region."
                )
                return
            
            if len(results) == 1:
                await self.display_servant(interaction, results[0]['id'], region_code)
            else:
                await self.show_servant_selection(interaction, results, region_code)
        except Exception as e:
            await interaction.followup.send(f"❌ Error: {str(e)}")
    
    async def show_servant_selection(self, interaction, results, region):
        """Show dropdown for multiple servant matches"""
        embed = discord.Embed(
            title="Multiple Servants Found",
            description=f"Select a servant from the dropdown:",
            color=0x3498db
        )
        
        for i, servant in enumerate(results[:5], 1):
            rarity = "★" * servant.get('rarity', 0)
            class_name = servant.get('className', 'Unknown')
            embed.add_field(
                name=f"{i}. {servant['name']}",
                value=f"{class_name} {rarity}",
                inline=False
            )
        
        options = []
        for servant in results[:5]:
            rarity = "★" * servant.get('rarity', 0)
            options.append(discord.SelectOption(
                label=f"{servant['name'][:25]}",
                description=f"{servant.get('className', 'Unknown')} {rarity}",
                value=str(servant['id'])
            ))
        
        select = discord.ui.Select(
            placeholder="Choose a servant...",
            options=options,
            min_values=1,
            max_values=1
        )
        
        async def select_callback(interaction: discord.Interaction):
            await interaction.response.defer()
            try:
                servant_id = int(select.values[0])
                await self.display_servant(interaction, servant_id, region)
            except Exception as e:
                await interaction.followup.send(f"Error loading servant: {e}", ephemeral=True)
        
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
    @app_commands.describe(
        servant_name="Name of the servant",
        ascension="Ascension level (1-4, or 0 for all)",
        region="Game region"
    )
    @app_commands.choices(region=[
        app_commands.Choice(name="North America", value="NA"),
        app_commands.Choice(name="Japan", value="JP")
    ])
    async def artwork(
        self,
        interaction: discord.Interaction,
        servant_name: str,
        ascension: int = 4,
        region: app_commands.Choice[str] = "NA"
    ):
        # Defer immediately to prevent timeout
        await interaction.response.defer()
        
        region_code = region.value if isinstance(region, app_commands.Choice) else region
        
        try:
            results = await self.api.search_servant(servant_name, region_code)
            
            if not results:
                await interaction.followup.send(f"❌ No servant found matching '{servant_name}'")
                return
            
            # Use exact match if available, otherwise first result
            servant = None
            for r in results:
                if servant_name.lower() in r['name'].lower():
                    servant = r
                    break
            if not servant:
                servant = results[0]
            
            servant_id = servant['id']
            assets = await self.api.get_servant_assets(servant_id, region_code)
            chara_graph = assets.get('charaGraph', {})
            
            if not chara_graph:
                await interaction.followup.send("❌ No artwork found for this servant.")
                return
            
            embed = discord.Embed(
                title=f"{servant['name']} - Artwork",
                color=0xffd700
            )
            
            if ascension == 0:
                # Show all ascensions
                for key, url in sorted(chara_graph.items())[:4]:
                    embed.add_field(name=f"Ascension {key}", value=f"[View Image]({url})", inline=True)
                await interaction.followup.send(embed=embed)
            else:
                # Show specific ascension
                key = str(ascension)
                if key in chara_graph:
                    embed.set_image(url=chara_graph[key])
                    embed.description = f"Ascension Level {ascension}"
                else:
                    # Fallback to highest available
                    highest = max(chara_graph.keys(), key=lambda x: int(x) if str(x).isdigit() else 0)
                    embed.set_image(url=chara_graph[highest])
                    embed.description = f"Ascension Level {highest} (requested {ascension} not available)"
                await interaction.followup.send(embed=embed)
                
        except Exception as e:
            await interaction.followup.send(f"❌ Error fetching artwork: {str(e)}")
    
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

async def setup(bot):
    await bot.add_cog(ServantCog(bot))
