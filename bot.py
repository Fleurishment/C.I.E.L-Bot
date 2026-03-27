import discord
from discord import app_commands
from discord.ext import commands
import aiohttp
import asyncio
from typing import Optional, Dict, List
import json
import re
from difflib import SequenceMatcher

# API Base URLs
BASE_URL = "https://api.atlasacademy.io"
BASIC_URL = f"{BASE_URL}/basic"
NICE_URL = f"{BASE_URL}/nice"

class FGOBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix="!",
            intents=discord.Intents.default(),
            help_command=None
        )
        self.session: Optional[aiohttp.ClientSession] = None
        self.servant_cache: List[Dict] = []
        self.ce_cache: List[Dict] = []
        self.cache_loaded = False
        
    async def setup_hook(self):
        self.session = aiohttp.ClientSession()
        # Start cache loading in background - don't block bot startup
        asyncio.create_task(self.load_cache())
        await self.tree.sync()
        
    async def load_cache(self, retries=3):
        """Load data with retries"""
        for attempt in range(retries):
            try:
                print(f"Loading cache (attempt {attempt + 1})...")
                
                # Load servants
                async with self.session.get(f"{BASIC_URL}/NA/servant", timeout=30) as resp:
                    if resp.status == 200:
                        self.servant_cache = await resp.json()
                        print(f"✅ Loaded {len(self.servant_cache)} servants")
                
                # Load CEs  
                async with self.session.get(f"{BASIC_URL}/NA/craft-essence", timeout=30) as resp:
                    if resp.status == 200:
                        self.ce_cache = await resp.json()
                        print(f"✅ Loaded {len(self.ce_cache)} CEs")
                
                self.cache_loaded = True
                return True
                
            except Exception as e:
                print(f"❌ Cache load failed: {e}")
                await asyncio.sleep(2)
        
        print("⚠️ Running without cache - will use direct API calls")
        return False
        
    async def close(self):
        if self.session:
            await self.session.close()
        await super().close()

bot = FGOBot()

def similarity(a: str, b: str) -> float:
    """Calculate string similarity"""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

async def api_search_servant(query: str, region: str = "NA"):
    """Fallback: Search directly from API if cache empty"""
    query_clean = query.strip().lower()
    
    # Try ID first
    if query_clean.isdigit():
        try:
            async with bot.session.get(f"{NICE_URL}/{region}/servant/{query_clean}", timeout=15) as resp:
                if resp.status == 200:
                    return await resp.json()
        except:
            pass
    
    # Get list from API
    try:
        async with bot.session.get(f"{BASIC_URL}/{region}/servant", timeout=15) as resp:
            if resp.status != 200:
                return None
            
            servants = await resp.json()
            
            # Exact match
            for s in servants:
                if s["name"].lower() == query_clean:
                    # Get full data
                    async with bot.session.get(f"{NICE_URL}/{region}/servant/{s['id']}", timeout=15) as resp2:
                        if resp2.status == 200:
                            return await resp2.json()
            
            # Starts with
            for s in servants:
                if s["name"].lower().startswith(query_clean):
                    async with bot.session.get(f"{NICE_URL}/{region}/servant/{s['id']}", timeout=15) as resp2:
                        if resp2.status == 200:
                            return await resp2.json()
            
            # Contains
            for s in servants:
                if query_clean in s["name"].lower():
                    async with bot.session.get(f"{NICE_URL}/{region}/servant/{s['id']}", timeout=15) as resp2:
                        if resp2.status == 200:
                            return await resp2.json()
    except Exception as e:
        print(f"API search error: {e}")
    
    return None

async def cache_search_servant(query: str, region: str = "NA"):
    """Search using cache"""
    if not bot.cache_loaded or not bot.servant_cache:
        return None
    
    query_clean = query.strip().lower()
    
    # ID match
    if query_clean.isdigit():
        sid = int(query_clean)
        for s in bot.servant_cache:
            if s["id"] == sid:
                return s
        return None
    
    # Exact match
    for s in bot.servant_cache:
        if s["name"].lower() == query_clean:
            return s
    
    # Starts with
    for s in bot.servant_cache:
        if s["name"].lower().startswith(query_clean):
            return s
    
    # Contains
    for s in bot.servant_cache:
        if query_clean in s["name"].lower():
            return s
    
    # Word match
    for s in bot.servant_cache:
        words = s["name"].lower().split()
        if any(query_clean == w or w.startswith(query_clean) for w in words):
            return s
    
    # Fuzzy
    best_match = None
    best_score = 0
    for s in bot.servant_cache:
        score = similarity(query, s["name"])
        if score > best_score and score > 0.4:
            best_score = score
            best_match = s
    
    return best_match

async def find_servant(query: str, region: str = "NA"):
    """Universal servant finder - tries cache then API"""
    # Try cache first
    if bot.cache_loaded:
        result = await cache_search_servant(query, region)
        if result:
            # Get full data
            try:
                async with bot.session.get(f"{NICE_URL}/{region}/servant/{result['id']}", timeout=15) as resp:
                    if resp.status == 200:
                        return await resp.json()
            except:
                pass
    
    # Fallback to API search
    return await api_search_servant(query, region)

async def find_ce(query: str, region: str = "NA"):
    """Find CE by name or ID"""
    query_clean = query.strip().lower()
    
    # Use cache if available
    if bot.cache_loaded and bot.ce_cache:
        # ID
        if query_clean.isdigit():
            cid = int(query_clean)
            for c in bot.ce_cache:
                if c["id"] == cid:
                    async with bot.session.get(f"{NICE_URL}/{region}/craft-essence/{cid}", timeout=15) as resp:
                        if resp.status == 200:
                            return await resp.json()
        
        # Name search
        for c in bot.ce_cache:
            if c["name"].lower() == query_clean:
                async with bot.session.get(f"{NICE_URL}/{region}/craft-essence/{c['id']}", timeout=15) as resp:
                    if resp.status == 200:
                        return await resp.json()
        
        for c in bot.ce_cache:
            if c["name"].lower().startswith(query_clean):
                async with bot.session.get(f"{NICE_URL}/{region}/craft-essence/{c['id']}", timeout=15) as resp:
                    if resp.status == 200:
                        return await resp.json()
        
        for c in bot.ce_cache:
            if query_clean in c["name"].lower():
                async with bot.session.get(f"{NICE_URL}/{region}/craft-essence/{c['id']}", timeout=15) as resp:
                    if resp.status == 200:
                        return await resp.json()
    
    # Direct API fallback
    if query_clean.isdigit():
        try:
            async with bot.session.get(f"{NICE_URL}/{region}/craft-essence/{query_clean}", timeout=15) as resp:
                if resp.status == 200:
                    return await resp.json()
        except:
            pass
    
    return None

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    print(f'Cache status: {"Loaded" if bot.cache_loaded else "Not loaded (using API fallback)"}')

@bot.tree.command(name="servant", description="Search for a Servant by name or ID")
@app_commands.describe(
    query="Servant name or ID (examples: Gilgamesh, artoria, mash, 12)",
    region="Game region"
)
@app_commands.choices(region=[
    app_commands.Choice(name="North America", value="NA"),
    app_commands.Choice(name="Japan", value="JP")
])
async def servant_command(interaction: discord.Interaction, query: str, region: str = "NA"):
    await interaction.response.defer()
    
    servant = await find_servant(query, region)
    
    if not servant:
        await interaction.followup.send(
            f"❌ Could not find servant: **{query}**\n"
            f"💡 Try: `Gilgamesh`, `Artoria`, `mash`, `12` (ID)\n"
            f"📡 Cache status: {'✅ Ready' if bot.cache_loaded else '⏳ Loading (using API)'}"
        )
        return
    
    embed = discord.Embed(
        title=f"⭐ {servant['name']}",
        description=f"{servant.get('className', 'Unknown Class')} | ID: {servant['id']}",
        color=discord.Color.blue()
    )
    
    # Image
    if "extraAssets" in servant and "charaGraph" in servant["extraAssets"]:
        chara = servant["extraAssets"]["charaGraph"]
        if "ascension" in chara and chara["ascension"]:
            img_url = list(chara["ascension"].values())[0]
            embed.set_thumbnail(url=img_url)
    
    rarity = "⭐" * servant.get("rarity", 1)
    embed.add_field(name="Rarity", value=rarity, inline=True)
    embed.add_field(name="Cost", value=servant.get("cost", "N/A"), inline=True)
    
    if "atkMax" in servant:
        embed.add_field(name="Max ATK", value=f"{servant['atkMax']:,}", inline=True)
    if "hpMax" in servant:
        embed.add_field(name="Max HP", value=f"{servant['hpMax']:,}", inline=True)
    
    if "cards" in servant:
        card_emojis = {"buster": "🔴", "arts": "🔵", "quick": "🟢"}
        cards = " ".join([card_emojis.get(c, c.upper()) for c in servant["cards"]])
        embed.add_field(name="Cards", value=cards, inline=True)
    
    # Skills summary
    if "skills" in servant:
        skill_text = ""
        for i in range(1, 4):
            sk = next((s for s in servant["skills"] if s.get("num") == i), None)
            if sk:
                skill_text += f"**{i}.** {sk.get('name', 'N/A')}\n"
        if skill_text:
            embed.add_field(name="Skills", value=skill_text, inline=False)
    
    # NP
    if "noblePhantasms" in servant and servant["noblePhantasms"]:
        np = servant["noblePhantasms"][0]
        embed.add_field(
            name=f"NP [{np.get('card', '').upper()}]", 
            value=np.get("name", "Unknown"), 
            inline=False
        )
    
    embed.add_field(name="🎨 Artwork", value="Use `/art` for all ascension arts!", inline=False)
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="skills", description="Show all 3 skills with full details")
@app_commands.describe(
    servant_name="Servant name (not case-sensitive)",
    region="Game region"
)
@app_commands.choices(region=[
    app_commands.Choice(name="North America", value="NA"),
    app_commands.Choice(name="Japan", value="JP")
])
async def skills_command(interaction: discord.Interaction, servant_name: str, region: str = "NA"):
    await interaction.response.defer()
    
    servant = await find_servant(servant_name, region)
    if not servant:
        await interaction.followup.send(f"❌ Servant not found: **{servant_name}**")
        return
    
    # Header
    header = discord.Embed(
        title=f"🎯 {servant['name']} - All Skills",
        color=discord.Color.red()
    )
    if "extraAssets" in servant and "faces" in servant["extraAssets"]:
        faces = servant["extraAssets"]["faces"]
        if faces:
            header.set_thumbnail(url=list(faces.values())[0])
    await interaction.followup.send(embed=header)
    
    # Each skill
    for i in range(1, 4):
        skill = next((s for s in servant.get("skills", []) if s.get("num") == i), None)
        if not skill:
            continue
            
        embed = discord.Embed(
            title=f"Skill {i}: {skill.get('name', 'Unknown')}",
            color=discord.Color.dark_red()
        )
        
        if "icon" in skill:
            embed.set_thumbnail(url=skill["icon"])
        
        if "coolDown" in skill:
            cd = skill["coolDown"]
            embed.add_field(name="Cooldown", value=f"{cd[0]} → {cd[-1]} turns", inline=True)
        
        if "functions" in skill:
            effects = []
            for func in skill["functions"]:
                popup = func.get("popupText", "")
                if popup:
                    effects.append(f"• {popup}")
            if effects:
                embed.add_field(name="Effects", value="\n".join(effects[:8]), inline=False)
        
        await interaction.channel.send(embed=embed)
        await asyncio.sleep(0.3)

@bot.tree.command(name="skill", description="View specific skill (1-3) or all skills")
@app_commands.describe(
    servant_name="Servant name",
    skill_num="Skill number (1, 2, or 3). Leave empty to see all",
    region="Game region"
)
@app_commands.choices(region=[
    app_commands.Choice(name="North America", value="NA"),
    app_commands.Choice(name="Japan", value="JP")
])
async def skill_command(
    interaction: discord.Interaction, 
    servant_name: str, 
    skill_num: Optional[int] = None,
    region: str = "NA"
):
    await interaction.response.defer()
    
    servant = await find_servant(servant_name, region)
    if not servant:
        await interaction.followup.send(f"❌ Servant not found: **{servant_name}**")
        return
    
    if skill_num is None:
        # Show all skills compact
        embed = discord.Embed(
            title=f"🎯 {servant['name']} - Skills",
            color=discord.Color.red()
        )
        for i in range(1, 4):
            sk = next((s for s in servant.get("skills", []) if s.get("num") == i), None)
            if sk:
                cd = sk.get('coolDown', [0, 0])
                val = f"**{sk.get('name', 'N/A')}**\nCD: {cd[0]}→{cd[-1]}"
                embed.add_field(name=f"Skill {i}", value=val, inline=False)
        await interaction.followup.send(embed=embed)
    else:
        if skill_num not in [1, 2, 3]:
            await interaction.followup.send("❌ Use 1, 2, or 3!", ephemeral=True)
            return
        
        sk = next((s for s in servant.get("skills", []) if s.get("num") == skill_num), None)
        if not sk:
            await interaction.followup.send(f"❌ Skill {skill_num} not found!")
            return
        
        embed = discord.Embed(
            title=f"🎯 {sk.get('name', 'Unknown')}",
            description=f"{servant['name']} - Skill {skill_num}",
            color=discord.Color.red()
        )
        if "icon" in sk:
            embed.set_thumbnail(url=sk["icon"])
        if "coolDown" in sk:
            cd = sk["coolDown"]
            embed.add_field(name="Cooldown", value=f"{cd[0]}→{cd[-1]}", inline=True)
        if "functions" in sk:
            eff = [f"• {f.get('popupText', '')}" for f in sk["functions"] if f.get("popupText")]
            if eff:
                embed.add_field(name="Effects", value="\n".join(eff[:8]), inline=False)
        await interaction.followup.send(embed=embed)

@bot.tree.command(name="ce", description="Search for Craft Essence")
@app_commands.describe(
    query="CE name or ID (not case-sensitive)",
    region="Game region"
)
@app_commands.choices(region=[
    app_commands.Choice(name="North America", value="NA"),
    app_commands.Choice(name="Japan", value="JP")
])
async def ce_command(interaction: discord.Interaction, query: str, region: str = "NA"):
    await interaction.response.defer()
    
    ce = await find_ce(query, region)
    if not ce:
        await interaction.followup.send(f"❌ CE not found: **{query}**")
        return
    
    embed = discord.Embed(
        title=f"🎴 {ce['name']}",
        description=f"ID: {ce['id']} | Cost: {ce.get('cost', 'N/A')}",
        color=discord.Color.gold()
    )
    
    if "extraAssets" in ce and "equip" in ce["extraAssets"]:
        equip = ce["extraAssets"]["equip"]
        if equip:
            embed.set_thumbnail(url=list(equip.values())[0])
    
    rarity = "⭐" * ce.get("rarity", 1)
    embed.add_field(name="Rarity", value=rarity, inline=True)
    
    if "atkMax" in ce:
        embed.add_field(name="Max ATK", value=f"{ce['atkMax']:,}", inline=True)
    if "hpMax" in ce:
        embed.add_field(name="Max HP", value=f"{ce['hpMax']:,}", inline=True)
    
    if "skills" in ce and ce["skills"]:
        effects = []
        for skill in ce["skills"]:
            for func in skill.get("functions", []):
                eff = func.get("popupText", "")
                if eff:
                    effects.append(eff)
        if effects:
            embed.add_field(name="Effects", value="\n".join(effects[:5]), inline=False)
    
    embed.add_field(name="🎨 Artwork", value="Use `/art` to see all art!", inline=False)
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="art", description="Display all artwork")
@app_commands.describe(
    query="Name or ID",
    type="Type",
    region="Game region"
)
@app_commands.choices(type=[
    app_commands.Choice(name="Servant", value="servant"),
    app_commands.Choice(name="Craft Essence", value="ce")
], region=[
    app_commands.Choice(name="North America", value="NA"),
    app_commands.Choice(name="Japan", value="JP")
])
async def art_command(interaction: discord.Interaction, query: str, type: str = "servant", region: str = "NA"):
    await interaction.response.defer()
    
    data = None
    if type == "servant":
        data = await find_servant(query, region)
    else:
        data = await find_ce(query, region)
    
    if not data:
        await interaction.followup.send(f"❌ Not found: **{query}**")
        return
    
    arts = {}
    if type == "servant":
        if "extraAssets" in data and "charaGraph" in data["extraAssets"]:
            asc = data["extraAssets"]["charaGraph"].get("ascension", {})
            for k, v in asc.items():
                arts[f"Ascension {k}"] = v
            cos = data["extraAssets"]["charaGraph"].get("costume", {})
            for k, v in cos.items():
                arts[f"Costume {k}"] = v
    else:
        if "extraAssets" in data and "equip" in data["extraAssets"]:
            for k, v in data["extraAssets"]["equip"].items():
                arts[f"Art {k}"] = v
    
    if not arts:
        await interaction.followup.send("❌ No artwork found.")
        return
    
    # First embed with list
    embed = discord.Embed(
        title=f"🎨 {data['name']} - Gallery",
        color=discord.Color.purple()
    )
    embed.add_field(name="Available", value="\n".join([f"• {k}" for k in list(arts.keys())[:10]]))
    first_url = list(arts.values())[0]
    embed.set_image(url=first_url)
    await interaction.followup.send(embed=embed)
    
    # Send rest in batches
    items = list(arts.items())[1:]
    for i in range(0, len(items), 4):
        batch = items[i:i+4]
        embeds = [discord.Embed(title=name, color=discord.Color.purple()).set_image(url=url) for name, url in batch]
        if embeds:
            await interaction.channel.send(embeds=embeds)
            await asyncio.sleep(0.5)

@bot.tree.command(name="np", description="Noble Phantasm details")
@app_commands.describe(
    servant_name="Servant name (not case-sensitive)",
    region="Game region"
)
@app_commands.choices(region=[
    app_commands.Choice(name="North America", value="NA"),
    app_commands.Choice(name="Japan", value="JP")
])
async def np_command(interaction: discord.Interaction, servant_name: str, region: str = "NA"):
    await interaction.response.defer()
    
    servant = await find_servant(servant_name, region)
    if not servant or not servant.get("noblePhantasms"):
        await interaction.followup.send("❌ NP not found!")
        return
    
    np = servant["noblePhantasms"][0]
    embed = discord.Embed(
        title=f"⚔️ {np.get('name', 'Unknown')}",
        description=f"Rank: {np.get('rank', '?')} | Card: {np.get('card', '').upper()}",
        color=discord.Color.purple()
    )
    
    if "functions" in np:
        effects = [f.get("popupText", "") for f in np["functions"] if f.get("popupText")]
        if effects:
            embed.add_field(name="Effects", value="\n".join(effects[:8]), inline=False)
    
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="reload", description="Reload the data cache (admin only)")
async def reload_command(interaction: discord.Interaction):
    """Force reload cache"""
    await interaction.response.defer(ephemeral=True)
    await interaction.followup.send("🔄 Reloading cache...")
    success = await bot.load_cache()
    if success:
        await interaction.followup.send("✅ Cache reloaded!", ephemeral=True)
    else:
        await interaction.followup.send("❌ Failed to reload cache", ephemeral=True)

@bot.tree.command(name="help", description="Show all available commands")
async def help_command(interaction: discord.Interaction):
    """Display help information"""
    embed = discord.Embed(
        title="C.I.E.L - Help",
        description="Search Fate/Grand Order data from Atlas Academy API",
        color=discord.Color.green()
    )
    
    embed.add_field(
        name="🔍 Servant Commands",
        value=(
            "`/servant <name/id>` - Search servant info\n"
            "`/skills <name>` - Show all 3 skills with details\n"
            "`/skill <name> [1-3]` - Specific skill or overview\n"
            "`/np <name>` - Noble Phantasm details\n"
            "`/art <name> type:Servant` - All artwork"
        ),
        inline=False
    )
    
    embed.add_field(
        name="🎴 Craft Essence Commands",
        value=(
            "`/ce <name/id>` - Search CE info\n"
            "`/art <name> type:CE` - CE artwork"
        ),
        inline=False
    )
    
    embed.add_field(
        name="💡 Search Tips",
        value=(
            "• **Not case-sensitive**: `gilgamesh` = `GILGAMESH`\n"
            "• **Partial names work**: `gil` finds Gilgamesh\n"
            "• **Use IDs**: `1` finds Mash Kyrielight\n"
            "• **No spaces needed**: `artoria` finds Artoria Pendragon"
        ),
        inline=False
    )
    
    embed.add_field(
        name="🌍 Regions",
        value="Add `region:JP` for Japanese server data (defaults to NA)",
        inline=False
    )
    
    embed.add_field(
        name="⚙️ System",
        value=f"Cache status: {'✅ Loaded' if bot.cache_loaded else '⏳ Loading'}\nUse `/reload` to refresh cache",
        inline=False
    )
    
    await interaction.response.send_message(embed=embed)

import os
TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise ValueError("No DISCORD_TOKEN found! Set it as an environment variable.")
bot.run(TOKEN)
