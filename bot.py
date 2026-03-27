import discord
from discord import app_commands
from discord.ext import commands
import aiohttp
import asyncio
from typing import Optional, List, Dict
from difflib import SequenceMatcher

API_BASE = "https://api.atlasacademy.io"

class FGOBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.default(), help_command=None)
        self.session: Optional[aiohttp.ClientSession] = None
        # Persistent cache that survives between commands
        self.servant_cache: List[Dict] = []
        self.ce_cache: List[Dict] = []
        self.cache_loaded = False
        
    async def setup_hook(self):
        self.session = aiohttp.ClientSession()
        # Try to load cache in background but don't wait for it
        asyncio.create_task(self._load_cache())
        await self.tree.sync()
        
    async def _load_cache(self):
        """Background cache loading"""
        try:
            print("Loading servant data...")
            async with self.session.get(f"{API_BASE}/basic/NA/servant", timeout=60) as resp:
                if resp.status == 200:
                    self.servant_cache = await resp.json()
                    print(f"✅ Cached {len(self.servant_cache)} servants")
            
            print("Loading CE data...")        
            async with self.session.get(f"{API_BASE}/basic/NA/craft-essence", timeout=60) as resp:
                if resp.status == 200:
                    self.ce_cache = await resp.json()
                    print(f"✅ Cached {len(self.ce_cache)} CEs")
            
            self.cache_loaded = True
        except Exception as e:
            print(f"⚠️ Cache load failed: {e}")
            print("Bot will use API fallback mode")
    
    async def close(self):
        if self.session:
            await self.session.close()
        await super().close()

bot = FGOBot()

def similarity(a: str, b: str) -> float:
    """Fuzzy string matching"""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

async def fetch_servant_list(region: str = "NA") -> List[Dict]:
    """Fetch servant list from API"""
    try:
        async with bot.session.get(f"{API_BASE}/basic/{region}/servant", timeout=20) as resp:
            if resp.status == 200:
                return await resp.json()
    except Exception as e:
        print(f"Error fetching servant list: {e}")
    return []

async def fetch_ce_list(region: str = "NA") -> List[Dict]:
    """Fetch CE list from API"""
    try:
        async with bot.session.get(f"{API_BASE}/basic/{region}/craft-essence", timeout=20) as resp:
            if resp.status == 200:
                return await resp.json()
    except Exception as e:
        print(f"Error fetching CE list: {e}")
    return []

async def fetch_nice_servant(servant_id: int, region: str = "NA") -> Optional[Dict]:
    """Fetch detailed servant data"""
    try:
        async with bot.session.get(f"{API_BASE}/nice/{region}/servant/{servant_id}", timeout=15) as resp:
            if resp.status == 200:
                return await resp.json()
    except Exception as e:
        print(f"Error fetching nice servant {servant_id}: {e}")
    return None

async def fetch_nice_ce(ce_id: int, region: str = "NA") -> Optional[Dict]:
    """Fetch detailed CE data"""
    try:
        async with bot.session.get(f"{API_BASE}/nice/{region}/craft-essence/{ce_id}", timeout=15) as resp:
            if resp.status == 200:
                return await resp.json()
    except Exception as e:
        print(f"Error fetching nice CE {ce_id}: {e}")
    return None

async def find_servant(query: str, region: str = "NA") -> Optional[Dict]:
    """
    Find servant by ID or name.
    Returns nice data if available, otherwise basic data.
    """
    query = query.strip()
    query_lower = query.lower()
    
    # Get data source (cache or API)
    servants = bot.servant_cache if bot.cache_loaded else await fetch_servant_list(region)
    
    if not servants:
        print("ERROR: No servant data available")
        return None
    
    # Try ID first (exact match)
    if query.isdigit():
        servant_id = int(query)
        # Check if we have this in cache with full data already
        for s in servants:
            if s.get("id") == servant_id:
                # Try to get nice data, but return basic if nice fails
                nice_data = await fetch_nice_servant(servant_id, region)
                return nice_data if nice_data else s
    
    # Name searches
    # 1. Exact match (case insensitive)
    for s in servants:
        if s.get("name", "").lower() == query_lower:
            nice_data = await fetch_nice_servant(s.get("id"), region)
            return nice_data if nice_data else s
    
    # 2. Starts with
    for s in servants:
        if s.get("name", "").lower().startswith(query_lower):
            nice_data = await fetch_nice_servant(s.get("id"), region)
            return nice_data if nice_data else s
    
    # 3. Contains
    for s in servants:
        if query_lower in s.get("name", "").lower():
            nice_data = await fetch_nice_servant(s.get("id"), region)
            return nice_data if nice_data else s
    
    # 4. Word match
    for s in servants:
        words = s.get("name", "").lower().replace("-", " ").replace("(", " ").replace(")", " ").split()
        if any(query_lower == word or word.startswith(query_lower) for word in words):
            nice_data = await fetch_nice_servant(s.get("id"), region)
            return nice_data if nice_data else s
    
    # 5. Fuzzy match
    best_match = None
    best_score = 0.0
    for s in servants:
        score = similarity(query, s.get("name", ""))
        if score > best_score and score > 0.6:  # 60% similarity threshold
            best_score = score
            best_match = s
    
    if best_match:
        nice_data = await fetch_nice_servant(best_match.get("id"), region)
        return nice_data if nice_data else best_match
    
    return None

async def find_ce(query: str, region: str = "NA") -> Optional[Dict]:
    """Find CE by ID or name"""
    query = query.strip()
    query_lower = query.lower()
    
    # Get data
    ces = bot.ce_cache if bot.ce_cache else await fetch_ce_list(region)
    
    if not ces:
        return None
    
    # ID match
    if query.isdigit():
        ce_id = int(query)
        for c in ces:
            if c.get("id") == ce_id:
                nice_data = await fetch_nice_ce(ce_id, region)
                return nice_data if nice_data else c
    
    # Exact match
    for c in ces:
        if c.get("name", "").lower() == query_lower:
            nice_data = await fetch_nice_ce(c.get("id"), region)
            return nice_data if nice_data else c
    
    # Starts with
    for c in ces:
        if c.get("name", "").lower().startswith(query_lower):
            nice_data = await fetch_nice_ce(c.get("id"), region)
            return nice_data if nice_data else c
    
    # Contains
    for c in ces:
        if query_lower in c.get("name", "").lower():
            nice_data = await fetch_nice_ce(c.get("id"), region)
            return nice_data if nice_data else c
    
    # Fuzzy
    best_match = None
    best_score = 0.0
    for c in ces:
        score = similarity(query, c.get("name", ""))
        if score > best_score and score > 0.6:
            best_score = score
            best_match = c
    
    if best_match:
        nice_data = await fetch_nice_ce(best_match.get("id"), region)
        return nice_data if nice_data else best_match
    
    return None

@bot.event
async def on_ready():
    print(f"✅ Bot logged in as {bot.user}")
    print(f"Cache status: {'Loaded' if bot.cache_loaded else 'Not loaded (using API)'}")

@bot.tree.command(name="servant", description="Search for a Servant by name or ID")
@app_commands.describe(
    query="Name or ID (e.g., Mash, gilgamesh, 12, 1)",
    region="Game region"
)
@app_commands.choices(region=[
    app_commands.Choice(name="North America", value="NA"),
    app_commands.Choice(name="Japan", value="JP")
])
async def servant_command(interaction: discord.Interaction, query: str, region: str = "NA"):
    await interaction.response.defer(thinking=True)
    
    try:
        servant = await find_servant(query, region)
        
        if not servant:
            await interaction.followup.send(
                f"❌ Could not find servant: **{query}**\n"
                f"💡 Try exact ID like `1`, `12`, `200100`\n"
                f"📝 Or check spelling: `Mash`, `Gilgamesh`, `Artoria`"
            )
            return
        
        # Build embed
        name = servant.get("name", "Unknown")
        s_class = servant.get("className", servant.get("className", "Unknown"))
        sid = servant.get("id", "N/A")
        
        embed = discord.Embed(
            title=f"⭐ {name}",
            description=f"{s_class} | ID: {sid}",
            color=discord.Color.blue()
        )
        
        # Image
        img_url = None
        if "extraAssets" in servant:
            if "charaGraph" in servant["extraAssets"]:
                asc = servant["extraAssets"]["charaGraph"].get("ascension", {})
                if asc:
                    img_url = list(asc.values())[0]
            elif "faces" in servant["extraAssets"]:
                faces = servant["extraAssets"]["faces"]
                if faces:
                    img_url = list(faces.values())[0]
        elif "face" in servant:
            img_url = servant["face"]
        
        if img_url:
            embed.set_thumbnail(url=img_url)
        
        # Stats
        rarity = servant.get("rarity", 1)
        embed.add_field(name="Rarity", value="⭐" * rarity, inline=True)
        embed.add_field(name="Cost", value=servant.get("cost", "N/A"), inline=True)
        
        if "atkMax" in servant:
            embed.add_field(name="Max ATK", value=f"{servant['atkMax']:,}", inline=True)
        if "hpMax" in servant:
            embed.add_field(name="Max HP", value=f"{servant['hpMax']:,}", inline=True)
        
        # Command Cards
        if "cards" in servant:
            emojis = {"buster": "🔴", "arts": "🔵", "quick": "🟢"}
            cards = " ".join([emojis.get(c, c.upper()) for c in servant["cards"]])
            embed.add_field(name="Command Cards", value=cards, inline=True)
        
        # Skills (if available in nice data)
        if "skills" in servant and servant["skills"]:
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
            np_name = np.get("name", "Unknown")
            np_card = np.get("card", "").upper()
            embed.add_field(name=f"Noble Phantasm [{np_card}]", value=np_name, inline=False)
        
        # Note if using basic data
        if "skills" not in servant:
            embed.set_footer(text="⚠️ Basic data only - use ID for full details")
        else:
            embed.add_field(name="🎨 Artwork", value="Use `/art` for all sprites!", inline=False)
        
        await interaction.followup.send(embed=embed)
        
    except Exception as e:
        print(f"Error in servant command: {e}")
        await interaction.followup.send(f"❌ Error: {str(e)}")

@bot.tree.command(name="ce", description="Search for a Craft Essence")
@app_commands.describe(
    query="Name or ID (not case-sensitive)",
    region="Game region"
)
@app_commands.choices(region=[
    app_commands.Choice(name="North America", value="NA"),
    app_commands.Choice(name="Japan", value="JP")
])
async def ce_command(interaction: discord.Interaction, query: str, region: str = "NA"):
    await interaction.response.defer(thinking=True)
    
    try:
        ce = await find_ce(query, region)
        
        if not ce:
            await interaction.followup.send(f"❌ Could not find CE: **{query}**")
            return
        
        embed = discord.Embed(
            title=f"🎴 {ce.get('name', 'Unknown')}",
            description=f"ID: {ce.get('id')} | Cost: {ce.get('cost', 'N/A')}",
            color=discord.Color.gold()
        )
        
        # Image
        img_url = None
        if "extraAssets" in ce and "equip" in ce["extraAssets"]:
            equip = ce["extraAssets"]["equip"]
            if equip:
                img_url = list(equip.values())[0]
        elif "face" in ce:
            img_url = ce["face"]
        
        if img_url:
            embed.set_thumbnail(url=img_url)
        
        rarity = ce.get("rarity", 1)
        embed.add_field(name="Rarity", value="⭐" * rarity, inline=True)
        
        if "atkMax" in ce:
            embed.add_field(name="Max ATK", value=f"{ce['atkMax']:,}", inline=True)
        if "hpMax" in ce:
            embed.add_field(name="Max HP", value=f"{ce['hpMax']:,}", inline=True)
        
        # Effects
        if "skills" in ce and ce["skills"]:
            effects = []
            for skill in ce["skills"]:
                for func in skill.get("functions", []):
                    eff = func.get("popupText", "")
                    if eff:
                        effects.append(eff)
            if effects:
                embed.add_field(name="Effects", value="\n".join(effects[:5]), inline=False)
        
        if "skills" not in ce:
            embed.set_footer(text="⚠️ Basic data only")
        
        await interaction.followup.send(embed=embed)
        
    except Exception as e:
        print(f"Error in CE command: {e}")
        await interaction.followup.send(f"❌ Error: {str(e)}")

@bot.tree.command(name="skills", description="Show all 3 skills with details")
@app_commands.describe(
    servant_name="Servant name or ID",
    region="Game region"
)
@app_commands.choices(region=[
    app_commands.Choice(name="NA", value="NA"),
    app_commands.Choice(name="JP", value="JP")
])
async def skills_command(interaction: discord.Interaction, servant_name: str, region: str = "NA"):
    await interaction.response.defer(thinking=True)
    
    servant = await find_servant(servant_name, region)
    
    if not servant:
        await interaction.followup.send(f"❌ Servant not found: **{servant_name}**")
        return
    
    if "skills" not in servant or not servant["skills"]:
        await interaction.followup.send("❌ Detailed skill data not available. Try using servant ID.")
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
        skill = next((s for s in servant["skills"] if s.get("num") == i), None)
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
            effects = [f"• {f.get('popupText', '')}" for f in skill["functions"] if f.get("popupText")]
            if effects:
                embed.add_field(name="Effects", value="\n".join(effects[:8]), inline=False)
        
        await interaction.channel.send(embed=embed)
        await asyncio.sleep(0.3)

@bot.tree.command(name="art", description="Display all artwork")
@app_commands.describe(
    query="Name or ID",
    type="Type",
    region="Region"
)
@app_commands.choices(type=[
    app_commands.Choice(name="Servant", value="servant"),
    app_commands.Choice(name="Craft Essence", value="ce")
], region=[
    app_commands.Choice(name="NA", value="NA"),
    app_commands.Choice(name="JP", value="JP")
])
async def art_command(interaction: discord.Interaction, query: str, type: str, region: str = "NA"):
    await interaction.response.defer(thinking=True)
    
    if type == "servant":
        data = await find_servant(query, region)
    else:
        data = await find_ce(query, region)
    
    if not data:
        await interaction.followup.send(f"❌ Not found: **{query}**")
        return
    
    # Collect images
    images = {}
    if type == "servant":
        if "extraAssets" in data and "charaGraph" in data["extraAssets"]:
            for key, url in data["extraAssets"]["charaGraph"].get("ascension", {}).items():
                images[f"Ascension {key}"] = url
            for key, url in data["extraAssets"]["charaGraph"].get("costume", {}).items():
                images[f"Costume {key}"] = url
    else:
        if "extraAssets" in data and "equip" in data["extraAssets"]:
            for key, url in data["extraAssets"]["equip"].items():
                images[f"Art {key}"] = url
    
    if not images:
        await interaction.followup.send("❌ No artwork found")
        return
    
    # Send first with list
    name = data.get("name", "Unknown")
    color = discord.Color.blue() if type == "servant" else discord.Color.gold()
    
    embed = discord.Embed(title=f"🎨 {name} - Gallery", color=color)
    embed.add_field(name="Available", value="\n".join([f"• {k}" for k in list(images.keys())[:8]]))
    embed.set_image(url=list(images.values())[0])
    await interaction.followup.send(embed=embed)
    
    # Send rest
    items = list(images.items())[1:]
    for i in range(0, len(items), 4):
        batch = items[i:i+4]
        embeds = [discord.Embed(title=n, color=color).set_image(url=u) for n, u in batch]
        if embeds:
            await interaction.channel.send(embeds=embeds)
            await asyncio.sleep(0.5)

@bot.tree.command(name="help", description="Show all commands and help info")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Help Guide",
        description="Search Fate/Grand Order game data",
        color=discord.Color.green()
    )
    
    embed.add_field(
        name="🔍 Servant Commands",
        value=(
            "`/servant <name/id>` - Search servant info\n"
            "  • Examples: `1`, `Mash`, `gilgamesh`, `Artoria`\n"
            "`/skills <name>` - All 3 skills detailed\n"
            "`/art <name> type:servant` - All artwork"
        ),
        inline=False
    )
    
    embed.add_field(
        name="🎴 Craft Essence Commands",
        value=(
            "`/ce <name/id>` - Search CE info\n"
            "  • Examples: `Kaleidoscope`, `1`\n"
            "`/art <name> type:ce` - CE artwork"
        ),
        inline=False
    )
    
    embed.add_field(
        name="💡 Search Tips",
        value=(
            "• **Not case-sensitive**: `mash` = `Mash` = `MASH`\n"
            "• **Use IDs for best results**: `/servant 1` (Mash)\n"
            "• **Partial names work**: `gil` finds Gilgamesh\n"
            "• **Region**: Add `region:JP` for Japanese server"
        ),
        inline=False
    )
    
    embed.add_field(
        name="⚡ Quick ID Reference",
        value=(
            "`1` = Mash Kyrielight\n"
            "`12` = Artoria Pendragon (Saber)\n"
            "`200100` = Gilgamesh"
        ),
        inline=False
    )
    
    status = "✅ Ready" if bot.cache_loaded else "⏳ Loading (API mode)"
    embed.set_footer(text=f"Bot Status: {status}")
    
    await interaction.response.send_message(embed=embed)

import os
TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise ValueError("No DISCORD_TOKEN environment variable found! Set it in Railway/Replit secrets.")
bot.run(TOKEN)
