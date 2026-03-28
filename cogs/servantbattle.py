import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View, Button, Select
import aiohttp
import random
import asyncio
import datetime

class BattleView(View):
    def __init__(self, battle_data, player1, message, player2=None, is_pvp=False):
        super().__init__(timeout=300)
        self.battle = battle_data
        self.player1 = player1
        self.player2 = player2
        self.is_pvp = is_pvp
        self.turn = 0
        self.current_player = 0  # 0 = player1, 1 = player2
        self.message = message  # Store message reference for editing
        self.processing = False  # Prevent double clicks
        
    def get_battle_embed(self):
        p1 = self.battle['p1']
        p2 = self.battle['p2']
        
        embed = discord.Embed(
            title="⚔️ Servant Battle",
            color=0x9b59b6,
            timestamp=datetime.datetime.now()
        )
        
        # Clamp HP at 0 for display
        p1_hp = max(0, p1['hp'])
        p2_hp = max(0, p2['hp'])
        
        # HP Bars
        p1_hp_pct = (p1_hp / p1['max_hp']) * 100 if p1['max_hp'] > 0 else 0
        p2_hp_pct = (p2_hp / p2['max_hp']) * 100 if p2['max_hp'] > 0 else 0
        
        p1_bar = "█" * int(p1_hp_pct / 10) + "░" * (10 - int(p1_hp_pct / 10))
        p2_bar = "█" * int(p2_hp_pct / 10) + "░" * (10 - int(p2_hp_pct / 10))
        
        p1_name = p1['servant']['name']
        p2_name = p2['servant']['name']
        
        field1 = f"{p1_bar}\n**{p1_hp}/{p1['max_hp']} HP**"
        field2 = f"{p2_bar}\n**{p2_hp}/{p2['max_hp']} HP**"
        
        embed.add_field(name=f"🧑‍🎤 {self.player1.display_name}\n{p1_name}", value=field1, inline=True)
        embed.add_field(name="VS", value="⚔️", inline=True)
        
        p2_display = self.player2.display_name if self.is_pvp else "🤖 Bot"
        embed.add_field(name=f"🧑‍🎤 {p2_display}\n{p2_name}", value=field2, inline=True)
        
        # Battle Log (last 5 actions to fit better)
        if self.battle.get('log'):
            recent_logs = self.battle['log'][-5:]
            embed.add_field(name="📜 Battle Log", value="\n".join(recent_logs), inline=False)
        
        # Turn indicator
        current = self.player1.display_name if self.current_player == 0 else (self.player2.display_name if self.is_pvp else "Bot")
        embed.set_footer(text=f"Turn {self.turn + 1} | Current: {current}")
        
        # Show current player's servant as main image, opponent as thumbnail
        if self.current_player == 0:
            if p1.get('art_url'):
                embed.set_image(url=p1['art_url'])
            if p2.get('art_url'):
                embed.set_thumbnail(url=p2['art_url'])
        else:
            if p2.get('art_url'):
                embed.set_image(url=p2['art_url'])
            if p1.get('art_url'):
                embed.set_thumbnail(url=p1['art_url'])
        
        return embed
    
    def check_winner(self):
        p1 = self.battle['p1']
        p2 = self.battle['p2']
        
        if p1['hp'] <= 0:
            return 2  # Player 2 wins
        if p2['hp'] <= 0:
            return 1  # Player 1 wins
        return 0  # No winner yet
    
    async def end_battle(self, winner):
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
            loser = p2 if winner == 2 else p1
            embed.add_field(
                name="Result",
                value=f"**{loser['servant']['name']}**: Ahh master it seems we lost this one...",
                inline=False
            )
        
        await self.message.edit(embed=embed, view=self)
        self.stop()
    
    async def process_turn(self, action):
        if self.processing:
            return
        self.processing = True
        
        p1 = self.battle['p1']
        p2 = self.battle['p2']
        
        attacker = p1 if self.current_player == 0 else p2
        defender = p2 if self.current_player == 0 else p1
        
        # Get NP name if available
        np_data = attacker['servant'].get('noblePhantasms', [{}])[0]
        np_name = np_data.get('name', 'Special Attack') if np_data else 'Special Attack'
        
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
        
        # Update display
        await self.message.edit(embed=self.get_battle_embed(), view=self)
        
        # Check winner
        winner = self.check_winner()
        if winner != 0:
            await self.end_battle(winner)
            self.processing = False
            return
        
        # Switch turns
        self.current_player = 1 - self.current_player
        self.turn += 1
        
        # Update display for turn switch
        await self.message.edit(embed=self.get_battle_embed(), view=self)
        
        # If bot's turn
        if not self.is_pvp and self.current_player == 1:
            await self.bot_turn()
        
        self.processing = False
    
    async def bot_turn(self):
        await asyncio.sleep(2)  # Delay for realism
        
        # Bot AI: 50% attack, 25% defend, 25% special
        roll = random.random()
        if roll < 0.5:
            action = "attack"
        elif roll < 0.75:
            action = "defend"
        else:
            action = "special"
        
        p1 = self.battle['p1']
        p2 = self.battle['p2']
        
        attacker = p2  # Bot
        defender = p1
        
        np_data = attacker['servant'].get('noblePhantasms', [{}])[0]
        np_name = np_data.get('name', 'Special Attack') if np_data else 'Special Attack'
        
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
        
        # Update display
        await self.message.edit(embed=self.get_battle_embed(), view=self)
        
        # Check winner
        winner = self.check_winner()
        if winner != 0:
            await self.end_battle(winner)
            return
        
        # Switch back to player
        self.current_player = 0
        self.turn += 1
        
        await self.message.edit(embed=self.get_battle_embed(), view=self)
    
    @discord.ui.button(label="⚔️ Attack", style=discord.ButtonStyle.red, custom_id="attack")
    async def attack_btn(self, interaction: discord.Interaction, button: Button):
        if not await self.check_user(interaction):
            return
        await interaction.response.defer()
        await self.process_turn("attack")
    
    @discord.ui.button(label="🛡️ Defend", style=discord.ButtonStyle.blurple, custom_id="defend")
    async def defend_btn(self, interaction: discord.Interaction, button: Button):
        if not await self.check_user(interaction):
            return
        await interaction.response.defer()
        await self.process_turn("defend")
    
    @discord.ui.button(label="✨ Special", style=discord.ButtonStyle.green, custom_id="special")
    async def special_btn(self, interaction: discord.Interaction, button: Button):
        if not await self.check_user(interaction):
            return
        await interaction.response.defer()
        await self.process_turn("special")
    
    async def check_user(self, interaction):
        if interaction.user.id != self.player1.id and (self.is_pvp and interaction.user.id != self.player2.id):
            await interaction.response.send_message("Not your battle!", ephemeral=True)
            return False
        
        if self.is_pvp:
            expected = self.player1.id if self.current_player == 0 else self.player2.id
            if interaction.user.id != expected:
                await interaction.response.send_message("Not your turn!", ephemeral=True)
                return False
        elif self.current_player != 0:
            await interaction.response.send_message("Wait for the bot!", ephemeral=True)
            return False
        
        return True

class ServantBattleCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    async def search_servant(self, name, region="NA"):
        """Search for servants using Atlas API"""
        base_url = "https://api.atlasacademy.io"
        url = f"{base_url}/basic/{region}/servant/search"
        params = {"name": name, "lang": "en"}
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=10) as resp:
                if resp.status == 200:
                    return await resp.json()
                return []
    
    async def get_servant_details(self, servant_id, region="NA"):
        """Get detailed servant info"""
        base_url = "https://api.atlasacademy.io"
        url = f"{base_url}/nice/{region}/svt/{servant_id}"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as resp:
                if resp.status == 200:
                    return await resp.json()
                return None
    
    @app_commands.command(name="servantbattle", description="⚔️ Battle against the bot or another player!")
    @app_commands.describe(opponent="User to battle (leave empty to fight bot)")
    async def servantbattle(self, interaction: discord.Interaction, opponent: discord.Member = None):
        """Start a servant battle"""
        # Check if user is already in a battle
        if interaction.user.id in getattr(self.bot, 'active_battles', {}):
            await interaction.response.send_message("❌ You already have an active battle! Finish it first.", ephemeral=True)
            return
        
        is_pvp = opponent is not None and opponent.id != interaction.user.id and not opponent.bot
        
        if is_pvp:
            if opponent.id in getattr(self.bot, 'active_battles', {}):
                await interaction.response.send_message("❌ Opponent is already in a battle!", ephemeral=True)
                return
            
            await interaction.response.send_message(
                f"⚔️ {opponent.mention}, {interaction.user.mention} challenges you to a Servant Battle!\n"
                f"{opponent.display_name}, type `accept` to accept the challenge!", 
                ephemeral=False
            )
            
            def check(m):
                return m.author.id == opponent.id and m.channel.id == interaction.channel_id and m.content.lower() == "accept"
            
            try:
                await self.bot.wait_for('message', timeout=30.0, check=check)
            except asyncio.TimeoutError:
                await interaction.followup.send("⏰ Challenge expired!")
                return
        
        await interaction.response.defer(ephemeral=False)
        
        # Initialize active battles tracking
        if not hasattr(self.bot, 'active_battles'):
            self.bot.active_battles = {}
        
        # Mark both users as in battle
        self.bot.active_battles[interaction.user.id] = True
        if is_pvp:
            self.bot.active_battles[opponent.id] = True
        
        try:
            await self.setup_player(interaction, interaction.user, is_pvp, opponent)
        except Exception as e:
            del self.bot.active_battles[interaction.user.id]
            if is_pvp:
                del self.bot.active_battles[opponent.id]
            await interaction.followup.send(f"❌ Error starting battle: {str(e)}")
    
    async def setup_player(self, interaction: discord.Interaction, player: discord.Member, is_pvp: bool, opponent: discord.Member = None):
        """Setup player servant selection"""
        await interaction.followup.send(f"{player.mention}, type a servant name to search:", ephemeral=False)
        
        def check(m):
            return m.author.id == player.id and m.channel.id == interaction.channel_id
        
        try:
            msg = await self.bot.wait_for('message', timeout=60.0, check=check)
            search_name = msg.content
            
            results = await self.search_servant(search_name)
            
            if not results:
                await interaction.followup.send(f"❌ No servants found for '{search_name}'. Try again with `/servantbattle`", ephemeral=False)
                # Clean up
                if hasattr(self.bot, 'active_battles') and player.id in self.bot.active_battles:
                    del self.bot.active_battles[player.id]
                return
            
            # Show selection dropdown
            await self.show_servant_selection(interaction, results, player, is_pvp, opponent)
            
        except asyncio.TimeoutError:
            await interaction.followup.send("⏰ Battle setup timed out!", ephemeral=False)
            if hasattr(self.bot, 'active_battles') and player.id in self.bot.active_battles:
                del self.bot.active_battles[player.id]
    
    async def show_servant_selection(self, interaction: discord.Interaction, results, player, is_pvp, opponent):
        """Show servant selection dropdown"""
        embed = discord.Embed(title="Choose your Servant", color=0x3498db)
        
        for i, servant in enumerate(results[:5], 1):
            rarity = "★" * servant.get('rarity', 0)
            embed.add_field(name=f"{i}. {servant['name']}", value=f"{servant.get('className', 'Unknown')} {rarity}", inline=False)
        
        options = []
        for servant in results[:5]:
            options.append(discord.SelectOption(
                label=servant['name'][:25],
                description=f"{servant.get('className', 'Unknown')} {'★' * servant.get('rarity', 0)}",
                value=str(servant['id'])
            ))
        
        select = Select(placeholder="Select your servant...", options=options)
        
        async def select_callback(inter):
            await inter.response.defer()
            servant_id = int(select.values[0])
            await self.select_artwork(interaction, servant_id, player, is_pvp, opponent)
        
        select.callback = select_callback
        
        view = View(timeout=120)
        view.add_item(select)
        
        await interaction.followup.send(embed=embed, view=view, ephemeral=False)
    
    async def select_artwork(self, interaction: discord.Interaction, servant_id, player, is_pvp, opponent):
        """Let player choose ascension art"""
        try:
            servant_data = await self.get_servant_details(servant_id)
            
            if not servant_data:
                await interaction.followup.send("❌ Failed to load servant data!", ephemeral=False)
                return
            
            # Get artwork options
            assets = servant_data.get('extraAssets', {})
            chara_graph = assets.get('charaGraph', {})
            asc_images = chara_graph.get('ascension', {})
            
            if not asc_images:
                await interaction.followup.send("❌ No artwork found!", ephemeral=False)
                return
            
            # Create artwork selection
            embed = discord.Embed(
                title=f"Select Ascension Art for {servant_data['name']}",
                color=0xffd700
            )
            
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
            
            select = Select(placeholder="Choose artwork...", options=options)
            
            async def art_callback(inter):
                await inter.response.defer()
                asc_key = select.values[0]
                art_url = asc_images.get(asc_key, asc_images.get('1'))
                
                player_data = {
                    'servant': servant_data,
                    'hp': 100,
                    'max_hp': 100,
                    'art_url': art_url,
                    'defending': False
                }
                
                # Check if this is player 1 (initiator)
                if player.id == interaction.user.id:
                    battle_data = {'p1': player_data, 'p2': None, 'log': []}
                    
                    if is_pvp and opponent:
                        await interaction.followup.send(f"✅ {player.display_name} is ready! Waiting for {opponent.display_name}...", ephemeral=False)
                        await self.setup_opponent(interaction, battle_data, player, opponent)
                    else:
                        await self.setup_bot_opponent(interaction, battle_data, player)
            
            select.callback = art_callback
            
            view = View(timeout=120)
            view.add_item(select)
            
            await interaction.followup.send(embed=embed, view=view, ephemeral=False)
            
        except Exception as e:
            await interaction.followup.send(f"❌ Error: {str(e)}", ephemeral=False)
    
    async def setup_opponent(self, interaction, battle_data, player1, player2):
        """Setup for PvP opponent"""
        await interaction.followup.send(f"{player2.mention}, type a servant name to search:", ephemeral=False)
        
        def check(m):
            return m.author.id == player2.id and m.channel.id == interaction.channel_id
        
        try:
            msg = await self.bot.wait_for('message', timeout=60.0, check=check)
            search_name = msg.content
            
            results = await self.search_servant(search_name)
            
            if not results:
                await interaction.followup.send(f"❌ No servants found. Battle cancelled.", ephemeral=False)
                self.cleanup_battle(player1.id, player2.id)
                return
            
            # Show selection for opponent
            await self.show_opponent_selection(interaction, results, battle_data, player1, player2)
            
        except asyncio.TimeoutError:
            await interaction.followup.send("⏰ Opponent took too long! Battle cancelled.", ephemeral=False)
            self.cleanup_battle(player1.id, player2.id)
    
    async def show_opponent_selection(self, interaction, results, battle_data, player1, player2):
        """Show servant selection for opponent"""
        embed = discord.Embed(title=f"{player2.display_name} - Choose your Servant", color=0xe74c3c)
        
        for i, servant in enumerate(results[:5], 1):
            rarity = "★" * servant.get('rarity', 0)
            embed.add_field(name=f"{i}. {servant['name']}", value=f"{servant.get('className', 'Unknown')} {rarity}", inline=False)
        
        options = []
        for servant in results[:5]:
            options.append(discord.SelectOption(
                label=servant['name'][:25],
                description=f"{servant.get('className', 'Unknown')} {'★' * servant.get('rarity', 0)}",
                value=str(servant['id'])
            ))
        
        select = Select(placeholder="Select your servant...", options=options)
        
        async def select_callback(inter):
            await inter.response.defer()
            servant_id = int(select.values[0])
            await self.select_opponent_artwork(interaction, servant_id, battle_data, player1, player2)
        
        select.callback = select_callback
        
        view = View(timeout=120)
        view.add_item(select)
        
        await interaction.followup.send(embed=embed, view=view, ephemeral=False)
    
    async def select_opponent_artwork(self, interaction, servant_id, battle_data, player1, player2):
        """Select artwork for opponent"""
        try:
            servant_data = await self.get_servant_details(servant_id)
            assets = servant_data.get('extraAssets', {})
            chara_graph = assets.get('charaGraph', {})
            asc_images = chara_graph.get('ascension', {})
            
            options = []
            for key in sorted(asc_images.keys())[:4]:
                url = asc_images[key]
                if url and url.startswith('http'):
                    options.append(discord.SelectOption(label=f"Ascension {key}", value=key))
            
            if not options:
                options = [discord.SelectOption(label="Default", value="1")]
            
            select = Select(placeholder="Choose artwork...", options=options)
            
            async def art_callback(inter):
                await inter.response.defer()
                asc_key = select.values[0]
                art_url = asc_images.get(asc_key, asc_images.get('1'))
                
                battle_data['p2'] = {
                    'servant': servant_data,
                    'hp': 100,
                    'max_hp': 100,
                    'art_url': art_url,
                    'defending': False
                }
                
                await self.start_battle(interaction, battle_data, player1, player2, True)
            
            select.callback = art_callback
            
            view = View(timeout=120)
            view.add_item(select)
            
            embed = discord.Embed(title=f"Select Ascension Art for {servant_data['name']}", color=0xffd700)
            await interaction.followup.send(embed=embed, view=view, ephemeral=False)
            
        except Exception as e:
            await interaction.followup.send(f"❌ Error: {str(e)}", ephemeral=False)
            self.cleanup_battle(player1.id, player2.id)
    
    async def setup_bot_opponent(self, interaction, battle_data, player):
        """Setup bot opponent"""
        # Get random servant for bot
        search_terms = ["Artoria", "Gilgamesh", "Ishtar", "Kama", "Mash", "Okita", "Jeanne", "Altera", "Scathach"]
        term = random.choice(search_terms)
        results = await self.search_servant(term)
        
        if results:
            bot_servant = random.choice(results[:5])
            bot_data = await self.get_servant_details(bot_servant['id'])
            
            if bot_data:
                assets = bot_data.get('extraAssets', {})
                chara_graph = assets.get('charaGraph', {})
                asc_images = chara_graph.get('ascension', {})
                bot_art = asc_images.get('1') if asc_images else None
                
                battle_data['p2'] = {
                    'servant': bot_data,
                    'hp': 100,
                    'max_hp': 100,
                    'art_url': bot_art,
                    'defending': False
                }
                
                await self.start_battle(interaction, battle_data, player, None, False)
            else:
                await interaction.followup.send("❌ Failed to setup opponent!", ephemeral=False)
                self.cleanup_battle(player.id)
        else:
            await interaction.followup.send("❌ Failed to setup opponent!", ephemeral=False)
            self.cleanup_battle(player.id)
    
    async def start_battle(self, interaction, battle_data, player1, player2, is_pvp):
        """Start the actual battle"""
        # Send initial message
        temp_view = View()
        temp_msg = await interaction.followup.send("⚔️ Battle Starting...", view=temp_view, ephemeral=False)
        
        # Create proper battle view with message reference
        view = BattleView(battle_data, player1, temp_msg, player2, is_pvp)
        embed = view.get_battle_embed()
        
        # Edit the message with the actual battle
        await temp_msg.edit(embed=embed, view=view)
    
    def cleanup_battle(self, p1_id, p2_id=None):
        """Remove users from active battles"""
        if hasattr(self.bot, 'active_battles'):
            if p1_id in self.bot.active_battles:
                del self.bot.active_battles[p1_id]
            if p2_id and p2_id in self.bot.active_battles:
                del self.bot.active_battles[p2_id]

async def setup(bot):
    await bot.add_cog(ServantBattleCog(bot))
