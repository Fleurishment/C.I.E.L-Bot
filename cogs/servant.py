import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import Button, View, Select
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
        
        # Page 4: Passives & Materials
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

class BattleView(View):
    def __init__(self, battle_data, player1, player2=None, is_pvp=False):
        super().__init__(timeout=300)
        self.battle = battle_data
        self.player1 = player1
        self.player2 = player2  # If None, bot controls player2
        self.is_pvp = is_pvp
        self.turn = 0
        self.current_player = 0  # 0 = player1, 1 = player2
        self.message = None
        
    def get_battle_embed(self):
        p1 = self.battle['p1']
        p2 = self.battle['p2']
        
        # Determine colors
        p1_color = 0x3498db
        p2_color = 0xe74c3c
        
        embed = discord.Embed(
            title="⚔️ Master Battle",
            color=0x9b59b6,
            timestamp=datetime.datetime.now()
        )
        
        # HP Bars
        p1_hp_pct = max(0, (p1['hp'] / p1['max_hp']) * 100)
        p2_hp_pct = max(0, (p2['hp'] / p2['max_hp']) * 100)
        
        p1_bar = "█" * int(p1_hp_pct / 10) + "░" * (10 - int(p1_hp_pct / 10))
        p2_bar = "█" * int(p2_hp_pct / 10) + "░" * (10 - int(p2_hp_pct / 10))
        
        p1_name = p1['servant']['name']
        p2_name = p2['servant']['name']
        
        field1 = f"{p1_bar}\n**{p1['hp']}/{p1['max_hp']} HP**"
        field2 = f"{p2_bar}\n**{p2['hp']}/{p2['max_hp']} HP**"
        
        embed.add_field(name=f"🧑‍🎤 {self.player1.display_name}\n{p1_name}", value=field1, inline=True)
        embed.add_field(name="VS", value="⚔️", inline=True)
        
        p2_display = self.player2.display_name if self.is_pvp else "🤖 Bot"
        embed.add_field(name=f"🧑‍🎤 {p2_display}\n{p2_name}", value=field2, inline=True)
        
        # Battle Log (last 3 actions)
        if self.battle.get('log'):
            recent_logs = self.battle['log'][-3:]
            embed.add_field(name="📜 Battle Log", value="\n".join(recent_logs), inline=False)
        
        # Turn indicator
        current = self.player1.display_name if self.current_player == 0 else (self.player2.display_name if self.is_pvp else "Bot")
        embed.set_footer(text=f"Turn {self.turn + 1} | Current: {current}")
        
        return embed
    
    def check_winner(self):
        p1 = self.battle['p1']
        p2 = self.battle['p2']
        
        if p1['hp'] <= 0:
            return 2  # Player 2 wins
        if p2['hp'] <= 0:
            return 1  # Player 1 wins
        return 0  # No winner yet
    
    async def end_battle(self, interaction, winner):
        p1 = self.battle['p1']
        p2 = self.battle['p2']
        
        # Disable all buttons
        for child in self.children:
            child.disabled = True
        
        embed = self.get_battle_embed()
        
        if winner == 1:
            embed.title = "🏆 Victory!"
            embed.color = 0x2ecc71
            embed.add_field(
                name="Result",
                value=f"**{p1['servant']['name']}**: WE WON Master! I promise I will not let anymore danger come your way.",
                inline=False
            )
        else:
            embed.title = "💀 Defeat..."
            embed.color = 0xe74c3c
            loser = p1 if winner == 2 else p2
            embed.add_field(
                name="Result",
                value=f"**{loser['servant']['name']}**: Ahh master it seems we lost this one...",
                inline=False
            )
        
        await interaction.response.edit_message(embed=embed, view=self)
        self.stop()
    
    async def process_action(self, interaction, action):
        p1 = self.battle['p1']
        p2 = self.battle['p2']
        
        attacker = p1 if self.current_player == 0 else p2
        defender = p2 if self.current_player == 0 else p1
        
        # Get NP name if available
        np_name = attacker['servant'].get('noblePhantasms', [{}])[0].get('name', 'Special Attack')
        
        if action == "attack":
            damage = random.randint(10, 20)
            defender['hp'] -= damage
            self.battle['log'].append(f"⚔️ {attacker['servant']['name']} dealt {damage} damage!")
            
        elif action == "defend":
            attacker['defending'] = True
            self.battle['log'].append(f"🛡️ {attacker['servant']['name']} is defending!")
            
        elif action == "special":
            # 70% hit chance, 30-50 damage
            if random.random() < 0.7:
                damage = random.randint(30, 50)
                if defender.get('defending'):
                    damage = damage // 2
                    defender['defending'] = False
                defender['hp'] -= damage
                self.battle['log'].append(f"✨ {attacker['servant']['name']} used **[{np_name}]** to deal {damage} damage!")
            else:
                self.battle['log'].append(f"❌ {attacker['servant']['name']} failed to use skill due to lack of magical energy!")
        
        # Check winner
        winner = self.check_winner()
        if winner != 0:
            await self.end_battle(interaction, winner)
            return
        
        # Switch turns
        self.current_player = 1 - self.current_player
        self.turn += 1
        
        # If bot's turn
        if not self.is_pvp and self.current_player == 1:
            await self.bot_turn(interaction)
        else:
            await interaction.response.edit_message(embed=self.get_battle_embed(), view=self)
    
    async def bot_turn(self, interaction):
        await asyncio.sleep(1.5)
        
        # Bot AI: 50% attack, 25% defend, 25% special
        roll = random.random()
        if roll < 0.5:
            action = "attack"
        elif roll < 0.75:
            action = "defend"
        else:
            action = "special"
        
        # Process bot action (current_player is 1/bot)
        await self.process_bot_action(interaction, action)
    
    async def process_bot_action(self, interaction, action):
        p1 = self.battle['p1']
        p2 = self.battle['p2']
        
        attacker = p2  # Bot
        defender = p1
        
        np_name = attacker['servant'].get('noblePhantasms', [{}])[0].get('name', 'Special Attack')
        
        if action == "attack":
            damage = random.randint(10, 20)
            if defender.get('defending'):
                damage = damage // 2
                defender['defending'] = False
            defender['hp'] -= damage
            self.battle['log'].append(f"⚔️ {attacker['servant']['name']} dealt {damage} damage!")
            
        elif action == "defend":
            attacker['defending'] = True
            self.battle['log'].append(f"🛡️ {attacker['servant']['name']} is defending!")
            
        elif action == "special":
            if random.random() < 0.7:
                damage = random.randint(30, 50)
                if defender.get('defending'):
                    damage = damage // 2
                    defender['defending'] = False
                defender['hp'] -= damage
                self.battle['log'].append(f"✨ {attacker['servant']['name']} used **[{np_name}]** to deal {damage} damage!")
            else:
                self.battle['log'].append(f"❌ {attacker['servant']['name']} failed to use skill due to lack of magical energy!")
        
        # Check winner
        winner = self.check_winner()
        if winner != 0:
            await self.end_battle(interaction, winner)
            return
        
        # Switch back to player
        self.current_player = 0
        self.turn += 1
        
        await interaction.followup.edit_message(interaction.message.id, embed=self.get_battle_embed(), view=self)
    
    @discord.ui.button(label="⚔️ Attack", style=discord.ButtonStyle.red)
    async def attack_btn(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.player1.id and (self.is_pvp and interaction.user.id != self.player2.id):
            await interaction.response.send_message("Not your battle!", ephemeral=True)
            return
        
        if self.is_pvp:
            expected = self.player1.id if self.current_player == 0 else self.player2.id
            if interaction.user.id != expected:
                await interaction.response.send_message("Not your turn!", ephemeral=True)
                return
        
        await self.process_action(interaction, "attack")
    
    @discord.ui.button(label="🛡️ Defend", style=discord.ButtonStyle.blurple)
    async def defend_btn(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.player1.id and (self.is_pvp and interaction.user.id != self.player2.id):
            await interaction.response.send_message("Not your battle!", ephemeral=True)
            return
        
        if self.is_pvp:
            expected = self.player1.id if self.current_player == 0 else self.player2.id
            if interaction.user.id != expected:
                await interaction.response.send_message("Not your turn!", ephemeral=True)
                return
        
        await self.process_action(interaction, "defend")
    
    @discord.ui.button(label="✨ Special", style=discord.ButtonStyle.green)
    async def special_btn(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.player1.id and (self.is_pvp and interaction.user.id != self.player2.id):
            await interaction.response.send_message("Not your battle!", ephemeral=True)
            return
        
        if self.is_pvp:
            expected = self.player1.id if self.current_player == 0 else self.player2.id
            if interaction.user.id != expected:
                await interaction.response.send_message("Not your turn!", ephemeral=True)
                return
        
        await self.process_action(interaction, "special")

class ServantCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.api = None
        self.active_hangman = {}
        self.active_unscramble = {}
    
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
    
    async def show_selection(self, interaction, results, region, command_type, player=None, is_pvp=False, opponent=None):
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
                elif command_type == "masterbattle":
                    await self.select_artwork_for_battle(interaction, servant_id, region, player, is_pvp, opponent)
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
            # Try multiple search terms to get servants
            search_terms = ["Artoria", "Ishtar", "Gilgamesh", "Mash", "Kama", "Morgan", "Oberon", "a"]
            all_servants = []
            
            base_url = "https://api.atlasacademy.io"
            
            # Try each search term until we get results
            for term in search_terms:
                try:
                    url = f"{base_url}/basic/{region_code}/servant/search"
                    params = {"name": term, "lang": "en"}
                    
                    async with aiohttp.ClientSession() as session:
                        async with session.get(url, params=params, timeout=10) as resp:
                            if resp.status == 200:
                                results = await resp.json()
                                if results and len(results) > 0:
                                    all_servants.extend(results)
                except Exception as e:
                    print(f"Search term '{term}' failed: {e}")
                    continue
            
            # Remove duplicates by ID
            seen_ids = set()
            unique_servants = []
            for s in all_servants:
                if s.get('id') and s['id'] not in seen_ids:
                    seen_ids.add(s['id'])
                    unique_servants.append(s)
            
            if len(unique_servants) == 0:
                await interaction.followup.send("❌ Could not fetch any servants from the API. Please try again later.")
                return
            
            # Filter valid servants (collectionNo > 0 means playable)
            valid_servants = [s for s in unique_servants if s.get('collectionNo', 0) > 0]
            
            if len(valid_servants) == 0:
                # If no collectionNo filter works, just use all unique
                valid_servants = unique_servants
            
            # Shuffle for randomness
            random.shuffle(valid_servants)
            
            # Try up to 25 servants
            for servant_info in valid_servants[:25]:
                try:
                    servant_id = servant_info['id']
                    
                    # Get assets
                    assets_url = f"{base_url}/nice/{region_code}/svt/{servant_id}"
                    
                    async with aiohttp.ClientSession() as session:
                        async with session.get(assets_url, timeout=10) as resp:
                            if resp.status != 200:
                                continue
                            
                            data = await resp.json()
                            assets = data.get('extraAssets', {})
                            
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
                            
                            # Get servant info
                            servant_name = servant_info.get('name', 'Unknown')
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
                            
                            embed.set_footer(text=f"Use /artwork {servant_name} to see all artwork")
                            
                            await interaction.followup.send(embed=embed)
                            return  # Success!
                            
                except Exception as e:
                    print(f"Error with servant {servant_info.get('id', 'unknown')}: {e}")
                    continue
            
            # If we get here, no artwork was found
            await interaction.followup.send(f"❌ Couldn't find any artwork after trying {len(valid_servants)} servants. The API might be having issues - try again later!")
            
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
    
    # NEW COMMANDS START HERE
    
    @app_commands.command(name="material", description="🧱 Show material farming locations")
    @app_commands.describe(material_name="Material to search for")
    async def material(self, interaction: discord.Interaction, material_name: str):
        """Hardcoded material farming guide"""
        materials_db = {
            "gem": {"locations": "Training Grounds (daily)", "ap": "40 AP", "best": "Expert/Extreme"},
            "magic gem": {"locations": "Training Grounds (daily)", "ap": "40 AP", "best": "Expert/Extreme"},
            "secret gem": {"locations": "Training Grounds (daily)", "ap": "40 AP", "best": "Extreme"},
            "void dust": {"locations": "Septem, Okeanos, America", "ap": "varies", "best": "Chaldea Gate - Daily"},
            "bone": {"locations": "Fuyuki", "ap": "5 AP", "best": "Unknown Coordinates X-F"},
            "fangs": {"locations": "Okeanos, Babylonia", "ap": "varies", "best": "Chaldea Gate - Cavalry"},
            "fluid": {"locations": "Shinjuku, Salem", "ap": "varies", "best": "Shinjuku - Tower"},
            "lamp": {"locations": "Babylonia", "ap": "varies", "best": "Babylonia - Observatory"},
            "scarab": {"locations": "Camelot", "ap": "varies", "best": "Camelot - Holy City"}
        }
        
        key = material_name.lower()
        found = None
        for k, v in materials_db.items():
            if k in key or key in k:
                found = v
                break
        
        if found:
            embed = discord.Embed(
                title=f"🧱 Farming Guide: {material_name.title()}",
                color=0xd35400
            )
            embed.add_field(name="Best Locations", value=found["locations"], inline=False)
            embed.add_field(name="Recommended AP", value=found["ap"], inline=True)
            embed.add_field(name="Best Node", value=found["best"], inline=True)
        else:
            embed = discord.Embed(
                title="🧱 Material Farming",
                description=f"No specific data for '{material_name}'. Try: Void Dust, Bone, Fangs, Gems, etc.",
                color=0xd35400
            )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="apcalc", description="⏱️ Calculate AP refill time")
    @app_commands.describe(current_ap="Current AP", target_ap="Target AP", max_ap="Your max AP")
    async def apcalc(self, interaction: discord.Interaction, current_ap: int, target_ap: int, max_ap: int = 140):
        """Calculate AP regeneration time"""
        if current_ap >= target_ap:
            await interaction.response.send_message("❌ Current AP is already at or above target!", ephemeral=True)
            return
        
        ap_needed = target_ap - current_ap
        minutes_needed = ap_needed * 5  # 1 AP per 5 minutes
        hours = minutes_needed // 60
        minutes = minutes_needed % 60
        
        ready_time = datetime.datetime.now() + datetime.timedelta(minutes=minutes_needed)
        
        embed = discord.Embed(
            title="⏱️ AP Calculator",
            color=0xe67e22
        )
        embed.add_field(name="AP Needed", value=str(ap_needed), inline=True)
        embed.add_field(name="Time Required", value=f"{hours}h {minutes}m", inline=True)
        embed.add_field(name="Full at", value=ready_time.strftime("%H:%M"), inline=True)
        
        if ap_needed > max_ap:
            apple_time = (ap_needed // max_ap) + (1 if ap_needed % max_ap > 0 else 0)
            embed.add_field(name="💡 Tip", value=f"You'll cap {apple_time} time(s). Use apples!", inline=False)
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="mysticcode", description="🔮 Look up Mystic Code information")
    @app_commands.describe(name="Mystic Code name (e.g., Chaldea, Atlas)")
    async def mysticcode(self, interaction: discord.Interaction, name: str):
        """Search for Mystic Codes"""
        await interaction.response.defer()
        
        try:
            url = f"https://api.atlasacademy.io/nice/NA/mc?lang=en"
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        mcs = await resp.json()
                        matches = [mc for mc in mcs if name.lower() in mc.get('name', '').lower()]
                        
                        if not matches:
                            await interaction.followup.send(f"❌ No Mystic Code found matching '{name}'")
                            return
                        
                        mc = matches[0]
                        embed = discord.Embed(
                            title=f"🔮 {mc['name']}",
                            description=f"ID: {mc['id']}",
                            color=0x9b59b6
                        )
                        
                        for skill in mc.get('skills', [])[:3]:
                            embed.add_field(
                                name=skill.get('name', 'Skill'),
                                value=skill.get('detail', 'No description')[:200] + "...",
                                inline=False
                            )
                        
                        await interaction.followup.send(embed=embed)
                    else:
                        await interaction.followup.send("❌ API Error")
        except Exception as e:
            await interaction.followup.send(f"❌ Error: {str(e)}")
    
    @app_commands.command(name="grailcalc", description="🏆 Calculate Grails needed for levels")
    @app_commands.describe(current_level="Current level", target_level="Target level", rarity="Base rarity (1-5)")
    async def grailcalc(self, interaction: discord.Interaction, current_level: int, target_level: int, rarity: int = 5):
        """Calculate Grail requirements"""
        # Simplified grail costs
        grail_limits = {1: 70, 2: 80, 3: 90, 4: 100, 5: 120}
        max_level = grail_limits.get(rarity, 100)
        
        if target_level > max_level:
            await interaction.response.send_message(f"❌ {rarity}★ servants can only reach level {max_level}!", ephemeral=True)
            return
        
        # Approximate grail costs per 10 levels beyond cap
        grails_needed = 0
        if target_level > 100:
            grails_needed = ((target_level - 100) // 2) + 1
        elif target_level > 90 and rarity < 5:
            grails_needed = ((target_level - 90) // 2) + 1
        elif target_level > 80 and rarity < 4:
            grails_needed = ((target_level - 80) // 2) + 1
        
        qp_cost = (target_level - current_level) * 1000000
        
        embed = discord.Embed(
            title="🏆 Grail Calculator",
            description=f"Level {current_level} → {target_level} ({rarity}★)",
            color=0xf1c40f
        )
        embed.add_field(name="Grails Needed", value=str(grails_needed), inline=True)
        embed.add_field(name="Approx QP Cost", value=f"{qp_cost:,}", inline=True)
        embed.add_field(name="Max Level", value=str(max_level), inline=True)
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="hangman", description="🎮 Play Hangman with FGO servant names")
    async def hangman(self, interaction: discord.Interaction):
        """FGO themed hangman game"""
        await interaction.response.defer()
        
        try:
            # Get random servant
            search_terms = ["Artoria", "Gilgamesh", "Ishtar", "Kama", "Mash", "Okita"]
            term = random.choice(search_terms)
            results = await self.api.search_servant(term, "NA")
            
            if not results:
                await interaction.followup.send("❌ Could not start game. Try again!")
                return
            
            servant = random.choice(results)
            name = servant['name'].upper()
            # Remove spaces for game
            display_name = name
            hidden = ['_' if c.isalpha() else c for c in name]
            
            game_data = {
                'word': name,
                'display': hidden,
                'guesses': [],
                'lives': 6,
                'servant': servant
            }
            
            self.active_hangman[interaction.user.id] = game_data
            
            embed = discord.Embed(
                title="🎮 FGO Hangman",
                description=f"Guess the servant name!\n\n**{' '.join(hidden)}**",
                color=0x3498db
            )
            embed.add_field(name="Lives", value="❤️" * game_data['lives'], inline=True)
            embed.add_field(name="Guesses", value="None", inline=True)
            embed.set_footer(text="Reply with a letter to guess!")
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            await interaction.followup.send(f"❌ Error starting game: {str(e)}")
    
    @app_commands.command(name="unscramble", description="🧩 Unscramble the FGO servant name")
    async def unscramble(self, interaction: discord.Interaction):
        """FGO word scramble"""
        await interaction.response.defer()
        
        try:
            terms = ["Artoria", "Gilgamesh", "Ishtar", "Kama", "Mash", "Okita", "Mordred", "Arthur"]
            term = random.choice(terms)
            results = await self.api.search_servant(term, "NA")
            
            if not results:
                await interaction.followup.send("❌ Game error. Try again!")
                return
            
            servant = random.choice(results)
            name = servant['name']
            # Scramble letters (preserve spaces)
            words = name.split()
            scrambled_words = []
            for word in words:
                if len(word) > 3:
                    middle = list(word[1:-1])
                    random.shuffle(middle)
                    scrambled = word[0] + ''.join(middle) + word[-1]
                else:
                    scrambled = word
                scrambled_words.append(scrambled)
            
            scrambled = ' '.join(scrambled_words)
            
            self.active_unscramble[interaction.user.id] = {
                'answer': name.lower(),
                'servant': servant,
                'time': datetime.datetime.now()
            }
            
            embed = discord.Embed(
                title="🧩 FGO Unscramble",
                description=f"**{scrambled}**\n\nType your answer in chat!",
                color=0xe74c3c
            )
            embed.set_footer(text="You have 30 seconds!")
            
            await interaction.followup.send(embed=embed)
            
            # Wait for answer
            def check(m):
                return m.author.id == interaction.user.id and m.channel.id == interaction.channel_id
            
            try:
                msg = await self.bot.wait_for('message', timeout=30.0, check=check)
                if msg.content.lower() == name.lower():
                    await msg.reply(f"🎉 Correct! It was **{name}**!")
                else:
                    await msg.reply(f"❌ Wrong! It was **{name}**!")
            except asyncio.TimeoutError:
                await interaction.followup.send(f"⏰ Time's up! It was **{name}**!")
                
        except Exception as e:
            await interaction.followup.send(f"❌ Error: {str(e)}")
    
    @app_commands.command(name="masterbattle", description="⚔️ Battle against the bot or another player!")
    @app_commands.describe(opponent="User to battle (leave empty to fight bot)")
    async def masterbattle(self, interaction: discord.Interaction, opponent: discord.Member = None):
        """Start a master battle"""
        await interaction.response.defer()
        
        is_pvp = opponent is not None and opponent.id != interaction.user.id and not opponent.bot
        
        if is_pvp:
            await interaction.followup.send(f"⚔️ {opponent.mention}, {interaction.user.mention} challenges you to a Master Battle!\nReact with ✅ to accept!")
            # In a real implementation, add confirmation logic here
            # For now, proceed with bot setup for both
            await asyncio.sleep(2)
        
        # Search for servants for player 1
        await interaction.followup.send(f"{interaction.user.mention}, searching for your servant... Type a servant name:")
        
        def check(m):
            return m.author.id == interaction.user.id and m.channel.id == interaction.channel_id
        
        try:
            msg = await self.bot.wait_for('message', timeout=60.0, check=check)
            search_name = msg.content
            
            results = await self.api.search_servant(search_name, "NA")
            
            if not results:
                await interaction.followup.send("❌ No servants found!")
                return
            
            # Show selection for P1
            await self.show_selection_for_battle(interaction, results, "NA", interaction.user, is_pvp, opponent)
            
        except asyncio.TimeoutError:
            await interaction.followup.send("⏰ Battle cancelled - timeout!")
    
    async def show_selection_for_battle(self, interaction, results, region, player, is_pvp, opponent):
        """Show servant selection for battle"""
        embed = discord.Embed(title="Choose your Servant", color=0x3498db)
        
        for i, servant in enumerate(results[:5], 1):
            rarity = "★" * servant.get('rarity', 0)
            embed.add_field(name=f"{i}. {servant['name']}", value=f"{servant.get('className')} {rarity}", inline=False)
        
        options = []
        for servant in results[:5]:
            options.append(discord.SelectOption(
                label=servant['name'][:25],
                value=str(servant['id'])
            ))
        
        select = Select(options=options, placeholder="Select your servant...")
        
        async def callback(interaction2):
            servant_id = int(select.values[0])
            await self.select_artwork_for_battle(interaction2, servant_id, region, player, is_pvp, opponent)
        
        select.callback = callback
        view = View(timeout=120)
        view.add_item(select)
        
        await interaction.followup.send(embed=embed, view=view)
    
    async def select_artwork_for_battle(self, interaction, servant_id, region, player, is_pvp, opponent):
        """Let player choose ascension art"""
        try:
            servant_data = await self.api.get_servant_details(servant_id, region)
            assets = await self.api.get_servant_assets(servant_id, region)
            
            chara_graph = assets.get('charaGraph', {})
            asc_images = chara_graph.get('ascension', {})
            
            if not asc_images:
                await interaction.followup.send("❌ No artwork found!")
                return
            
            # Create selection for artwork
            embed = discord.Embed(title=f"Select Ascension Art for {servant_data['name']}", color=0xffd700)
            
            options = []
            for key in sorted(asc_images.keys())[:4]:
                url = asc_images[key]
                if url and url.startswith('http'):
                    options.append(discord.SelectOption(
                        label=f"Ascension {key}",
                        value=key
                    ))
            
            if not options:
                options = [discord.SelectOption(label="Default", value="1")]
            
            select = Select(options=options, placeholder="Choose artwork...")
            
            async def artwork_callback(inter2):
                asc_key = select.values[0]
                art_url = asc_images.get(asc_key, asc_images.get('1'))
                
                # Store player 1 data
                battle_data = {
                    'p1': {
                        'servant': servant_data,
                        'hp': 100,
                        'max_hp': 100,
                        'art_url': art_url,
                        'defending': False
                    },
                    'p2': None,
                    'log': []
                }
                
                if is_pvp and opponent:
                    # In real implementation, wait for opponent to pick
                    # For now, bot picks random
                    pass
                
                # Get bot's random servant
                search_terms = ["Artoria", "Gilgamesh", "Ishtar", "Kama", "Mash", "Okita"]
                term = random.choice(search_terms)
                bot_results = await self.api.search_servant(term, "NA")
                
                if bot_results:
                    bot_servant = random.choice(bot_results[:5])
                    bot_assets = await self.api.get_servant_assets(bot_servant['id'], region)
                    bot_chara = bot_assets.get('charaGraph', {})
                    bot_asc = bot_chara.get('ascension', {})
                    bot_art = bot_asc.get('1') if bot_asc else None
                    
                    battle_data['p2'] = {
                        'servant': bot_servant,
                        'hp': 100,
                        'max_hp': 100,
                        'art_url': bot_art,
                        'defending': False
                    }
                
                # Start battle
                view = BattleView(battle_data, player, opponent, is_pvp)
                embed = view.get_battle_embed()
                
                await interaction.followup.send(embed=embed, view=view)
            
            select.callback = artwork_callback
            view = View(timeout=120)
            view.add_item(select)
            
            await interaction.followup.send(embed=embed, view=view)
            
        except Exception as e:
            await interaction.followup.send(f"❌ Error: {str(e)}")

async def setup(bot):
    await bot.add_cog(ServantCog(bot))
