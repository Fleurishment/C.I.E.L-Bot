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
            
            # Get skill effects
            functions = skill.get('functions', [])
            effects = []
            for func in functions:
                effect = func.get('popupText', func.get('funcType', 'Unknown effect'))
                effects.append(effect)
            
            effect_text = "\n".join(effects[:3]) if effects else "No description available"
            
            skills_embed.add_field(
                name=f"Skill {i}: {skill_name} {skill_rank}",
                value=f"**Cooldown:** {cooldown[0]}-{cooldown[-1]} turns\n{effect_text}",
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
            
            # NP Effects
            np_functions = np_data.get('functions', [])
            np_effects = []
            for func in np_functions:
                effect = func.get('popupText', func.get('funcType', ''))
                if effect:
                    np_effects.append(f"• {effect}")
            
            if np_effects:
                np_embed.add_field(
                    name="Effects", 
                    value="\n".join(np_effects[:5]) or "No effects listed", 
                    inline=False
                )
            
            # Level values if available
            levels = np_data.get('functions', [])
            if levels and len(levels) > 0:
                svals = levels[0].get('svals', [])
                if svals:
                    np_embed.add_field(
                        name="Level Scaling",
                        value=f"LV1: {svals[0]}\nLV5: {svals[-1] if len(svals) > 4 else svals[0]}",
                        inline=True
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
            passive_text = []
            for passive in passives:
                p_name = passive.get('name', 'Unknown')
                p_skill = passive.get('skill', {})
                p_detail = p_skill.get('detail', 'No description')
                passive_text.append(f"**{p_name}**: {p_detail[:100]}...")
            
            passive_embed.add_field(
                name="Passive Skills",
                value="\n".join(passive_text) or "None",
                inline=False
            )
        
        # Ascension materials (if available in nice data)
        ascension = self.servant.get('ascensionMaterials', {})
        if ascension:
            mats_text = []
            for key, value in list(ascension.items())[:2]:
                items = value.get('items', [])
                item_names = [item.get('name', 'Unknown') for item in items[:3]]
                mats_text.append(f"Ascension {key}: {', '.join(item_names)}")
            
            if mats_text:
                passive_embed.add_field(
                    name="Ascension Materials (Sample)",
                    value="\n".join(mats_text),
                    inline=False
                )
        
        # Artwork preview
        if self.assets.get('charaGraph', {}):
            cards = self.assets['charaGraph']
            if isinstance(cards, dict) and len(cards) > 0:
                first_art = list(cards.values())[0]
                passive_embed.set_image(url=first_art)
        
        passive_embed.set_footer(text=f"Page 4/4 • Region: {self.region} • Use buttons to navigate")
        pages.append(passive_embed)
        
        return pages
    
    def get_rarity_color(self):
        rarity_colors = {
            5: 0xffd700,  # Gold
            4: 0xc0c0c0,  # Silver
            3: 0xcd7f32,  # Bronze
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
        
        # Search for servants
        results = await self.api.search_servant(name, region_code)
        
        if not results:
            await interaction.followup.send(
                f"❌ No servants found matching '{name}' in {region_code} region."
            )
            return
        
        if len(results) == 1:
            # Direct display if only one result
            await self.display_servant(interaction, results[0]['id'], region_code)
        else:
            # Show selection menu if multiple results
            await self.show_servant_selection(interaction, results, region_code)
    
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
        
        # Create select menu
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
            # This is a NEW interaction from the dropdown, so we defer it
            await interaction.response.defer()
            try:
                servant_id = int(select.values[0])
                await self.display_servant(interaction, servant_id, region)
            except Exception as e:
                await interaction.followup.send(f"Error loading servant: {e}", ephemeral=True)
        
        select.callback = select_callback
        
        view = discord.ui.View(timeout=120)  # Increased timeout
        view.add_item(select)
        
        await interaction.followup.send(embed=embed, view=view)
        
        options = []
        for i, servant in enumerate(results[:10], 1):  # Limit to 10
            rarity = "★" * servant.get('rarity', 0)
            class_name = servant.get('className', 'Unknown')
            embed.add_field(
                name=f"{i}. {servant['name']}",
                value=f"{class_name} {rarity}",
                inline=False
            )
            
            options.append(discord.SelectOption(
                label=f"{servant['name'][:25]}",
                description=f"{class_name} {rarity}",
                value=str(servant['id'])
            ))
        
        # Create select menu
        select = discord.ui.Select(
            placeholder="Choose a servant...",
            options=options
        )
        
        async def select_callback(interaction: discord.Interaction):
            servant_id = int(select.values[0])
            await self.display_servant(interaction, servant_id, region)
        
        select.callback = select_callback
        
        view = discord.ui.View()
        view.add_item(select)
        
        await interaction.followup.send(embed=embed, view=view)
    
       async def display_servant(self, interaction: discord.Interaction, servant_id: int, region: str):
        """Fetch and display detailed servant information"""
        # Check if interaction was already responded to
        if not interaction.response.is_done():
            await interaction.response.defer()
        
        servant_data = await self.api.get_servant_details(servant_id, region)
        
        if not servant_data:
            await interaction.followup.send("❌ Failed to fetch servant details.")
            return
        
        # Get assets
        assets = await self.api.get_servant_assets(servant_id, region)
        
        # Create paginated view
        view = ServantView(servant_data, assets, region)
        pages = view.get_pages()
        
        await interaction.followup.send(embed=pages[0], view=view)
    
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
        await interaction.response.defer()
        
        region_code = region.value if isinstance(region, app_commands.Choice) else region
        
        results = await self.api.search_servant(servant_name, region_code)
        if not results:
            await interaction.followup.send(f"❌ No servant found matching '{servant_name}'")
            return
        
        servant_id = results[0]['id']
        assets = await self.api.get_servant_assets(servant_id, region_code)
        chara_graph = assets.get('charaGraph', {})
        
        if not chara_graph:
            await interaction.followup.send("❌ No artwork found for this servant.")
            return
        
        embed = discord.Embed(
            title=f"{results[0]['name']} - Artwork",
            color=0xffd700
        )
        
        # Get specific ascension or max available
        if ascension == 0:
            # Show all
            for key, url in list(chara_graph.items())[:4]:
                embed.add_field(name=f"Ascension {key}", value=f"[View Image]({url})", inline=True)
        else:
            key = str(ascension)
            if key in chara_graph:
                embed.set_image(url=chara_graph[key])
                embed.description = f"Ascension Level {ascension}"
            else:
                # Fallback to highest available
                highest = max(chara_graph.keys(), key=lambda x: int(x) if x.isdigit() else 0)
                embed.set_image(url=chara_graph[highest])
                embed.description = f"Ascension Level {highest} (requested {ascension} not available)"
        
        await interaction.followup.send(embed=embed)

async def setup(bot):
    await bot.add_cog(ServantCog(bot))
