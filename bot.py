import discord
from discord import app_commands
from discord.ext import commands
import aiohttp
import asyncio
from typing import Optional, List, Dict
from difflib import SequenceMatcher
import os

# Try to import requests as fallback
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

API_BASE = "https://api.atlasacademy.io"

class FGOBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.default(), help_command=None)
        self.session: Optional[aiohttp.ClientSession] = None
        self.servants: List[Dict] = []
        self.ces: List[Dict] = []
        self.data_loaded = False
        self.load_error = None
        
    async def setup_hook(self):
        # Create session with very long timeout
        timeout = aiohttp.ClientTimeout(total=120, connect=60)
        self.session = aiohttp.ClientSession(timeout=timeout)
        
        # Load data immediately and wait for it
        print("Loading data...")
        await self._load_data()
        
        if not self.data_loaded:
            print(f"WARNING: Data not loaded: {self.load_error}")
        
        await self.tree.sync()
        print("Bot ready!")
        
    async def _load_data(self):
        """Load data with multiple retries"""
        max_attempts = 5
        
        for attempt in range(1, max_attempts + 1):
            try:
                print(f"Data load attempt {attempt}/{max_attempts}...")
                
                # Try aiohttp first
                if self.session:
                    try:
                        async with self.session.get(f"{API_BASE}/basic/NA/servant", timeout=90) as resp:
                            if resp.status == 200:
                                self.servants = await resp.json()
                                print(f"✅ Loaded {len(self.servants)} servants via aiohttp")
                    except Exception as e:
                        print(f"  aiohttp servants failed: {e}")
                        # Try requests fallback
                        if HAS_REQUESTS:
                            try:
                                resp = requests.get(f"{API_BASE}/basic/NA/servant", timeout=60)
                                if resp.status_code == 200:
                                    self.servants = resp.json()
                                    print(f"✅ Loaded {len(self.servants)} servants via requests")
                            except Exception as e2:
                                print(f"  requests fallback failed: {e2}")
                
                # Load CEs
                if self.servants:  # Only try CEs if servants worked
                    try:
                        async with self.session.get(f"{API_BASE}/basic/NA/craft-essence", timeout=90) as resp:
                            if resp.status == 200:
                                self.ces = await resp.json()
                                print(f"✅ Loaded {len(self.ces)} CEs via aiohttp")
                    except Exception as e:
                        print(f"  aiohttp CEs failed: {e}")
                        if HAS_REQUESTS:
                            try:
                                resp = requests.get(f"{API_BASE}/basic/NA/craft-essence", timeout=60)
                                if resp.status_code == 200:
                                    self.ces = resp.json()
                                    print(f"✅ Loaded {len(self.ces)} CEs via requests")
                            except Exception as e2:
                                print(f"  requests CE fallback failed: {e2}")
                
                if self.servants:
                    self.data_loaded = True
                    print("✅ Data loading complete!")
                    return
                    
            except Exception as e:
                self.load_error = str(e)
                print(f"Attempt {attempt} error: {e}")
            
            # Wait before retry
            if attempt < max_attempts:
                wait_time = attempt * 3
                print(f"Waiting {wait_time}s before retry...")
                await asyncio.sleep(wait_time)
        
        print("❌ All data load attempts failed")
    
    async def close(self):
        if self.session:
            await self.session.close()
        await super().close()

bot = FGOBot()

def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

async def search_servant(query: str, region: str = "NA"):
    """Search with live API fallback"""
    query = query.strip()
    query_lower = query.lower()
    
    # Use cached data if available
    servants = bot.servants if bot.servants else []
    
    # If no cache, try to fetch live
    if not servants:
        print("No cache, fetching live...")
        try:
            async with bot.session.get(f"{API_BASE}/basic/{region}/servant", timeout=60) as resp:
                if resp.status == 200:
                    servants = await resp.json()
                    print(f"Live fetch: {len(servants)} servants")
        except Exception as e:
            print(f"Live fetch failed: {e}")
            # Try requests
            if HAS_REQUESTS:
                try:
                    resp = requests.get(f"{API_BASE}/basic/{region}/servant", timeout=30)
                    if resp.status_code == 200:
                        servants = resp.json()
                except Exception as e2:
                    print(f"Requests fallback failed: {e2}")
    
    if not servants:
        return None, "No data available"
    
    # Try collectionNo (user-facing ID)
    if query.isdigit():
        coll_no = int(query)
        for s in servants:
            if s.get("collectionNo") == coll_no:
                # Get nice data
                try:
                    async with bot.session.get(f"{API_BASE}/nice/{region}/servant/{s['id']}", timeout=30) as resp:
                        if resp.status == 200:
                            return await resp.json(), None
                except:
                    pass
                return s, None  # Return basic if nice fails
        
        # Try internal ID
        internal_id = int(query)
        for s in servants:
            if s.get("id") == internal_id:
                try:
                    async with bot.session.get(f"{API_BASE}/nice/{region}/servant/{internal_id}", timeout=30) as resp:
                        if resp.status == 200:
                            return await resp.json(), None
                except:
                    pass
                return s, None
    
    # Name searches
    # Exact
    for s in servants:
        if s.get("name", "").lower() == query_lower:
            try:
                async with bot.session.get(f"{API_BASE}/nice/{region}/servant/{s['id']}", timeout=30) as resp:
                    if resp.status == 200:
                        return await resp.json(), None
            except:
                pass
            return s, None
    
    # Starts with
    for s in servants:
        if s.get("name", "").lower().startswith(query_lower):
            try:
                async with bot.session.get(f"{API_BASE}/nice/{region}/servant/{s['id']}", timeout=30) as resp:
                    if resp.status == 200:
                        return await resp.json(), None
            except:
                pass
            return s, None
    
    # Contains
    for s in servants:
        if query_lower in s.get("name", "").lower():
            try:
                async with bot.session.get(f"{API_BASE}/nice/{region}/servant/{s['id']}", timeout=30) as resp:
                    if resp.status == 200:
                        return await resp.json(), None
            except:
                pass
            return s, None
    
    # Fuzzy
    best = None
    best_score = 0
    for s in servants:
        score = similarity(query, s.get("name", ""))
        if score > best_score and score > 0.5:
            best_score = score
            best = s
    
    if best:
        try:
            async with bot.session.get(f"{API_BASE}/nice/{region}/servant/{best['id']}", timeout=30) as resp:
                if resp.status == 200:
                    return await resp.json(), None
        except:
            pass
        return best, None
    
    return None, "Not found"

async def search_ce(query: str, region: str = "NA"):
    """Search CE"""
    query = query.strip()
    query_lower = query.lower()
    
    ces = bot.ces if bot.ces else []
    
    # Fetch if no cache
    if not ces:
        try:
            async with bot.session.get(f"{API_BASE}/basic/{region}/craft-essence", timeout=60) as resp:
                if resp.status == 200:
                    ces = await resp.json()
        except:
            if HAS_REQUESTS:
                try:
                    resp = requests.get(f"{API_BASE}/basic/{region}/craft-essence", timeout=30)
                    if resp.status_code == 200:
                        ces = resp.json()
                except:
                    pass
    
    if not ces:
        return None
    
    # ID search (collectionNo or internal)
    if query.isdigit():
        num = int(query)
        for c in ces:
            if c.get("collectionNo") == num or c.get("id") == num:
                try:
                    async with bot.session.get(f"{API_BASE}/nice/{region}/craft-essence/{c['id']}", timeout=30) as resp:
                        if resp.status == 200:
                            return await resp.json()
                except:
                    pass
                return c
    
    # Name searches
    for c in ces:
        if c.get("name", "").lower() == query_lower:
            try:
                async with bot.session.get(f"{API_BASE}/nice/{region}/craft-essence/{c['id']}", timeout=30) as resp:
                    if resp.status == 200:
                        return await resp.json()
            except:
                pass
            return c
    
    for c in ces:
        if c.get("name", "").lower().startswith(query_lower):
            try:
                async with bot.session.get(f"{API_BASE}/nice/{region}/craft-essence/{c['id']}", timeout=30) as resp:
                    if resp.status == 200:
                        return await resp.json()
            except:
                pass
            return c
    
    for c in ces:
        if query_lower in c.get("name", "").lower():
            try:
                async with bot.session.get(f"{API_BASE}/nice/{region}/craft-essence/{c['id']}", timeout=30) as resp:
                    if resp.status == 200:
                        return await resp.json()
            except:
                pass
            return c
    
    return None

@bot.event
async def on_ready():
    status = f"✅ Cache: {len(bot.servants)} servants, {len(bot.ces)} CEs" if bot.data_loaded else f"⚠️ No cache: {bot.load_error}"
    print(f"Bot ready! {status}")

@bot.tree.command(name="servant", description="Search servant")
@app_commands.describe(query="Name or collection ID (1=Mash, 12=Artoria)", region="NA/JP")
@app_commands.choices(region=[
    app_commands.Choice(name="North America", value="NA"),
    app_commands.Choice(name="Japan", value="JP")
])
async def servant_cmd(interaction: discord.Interaction, query: str, region: str = "NA"):
    await interaction.response.defer(thinking=True)
    
    result, error = await search_servant(query, region)
    
    if not result:
        cache_status = f"{len(bot.servants)} loaded" if bot.servants else "0 loaded (API issue)"
        await interaction.followup.send(
            f"❌ Not found: **{query}**\n"
            f"💡 Try: `1`, `12`, `mash`, `gilgamesh`\n"
            f"📊 Status: {cache_status}\n"
            f"⚠️ If this persists, the API may be down"
        )
        return
    
    # Build embed
    embed = discord.Embed(
        title=f"⭐ {result.get('name', 'Unknown')}",
        description=f"{result.get('className', 'Unknown')} | Coll. No. {result.get('collectionNo', 'N/A')}",
        color=discord.Color.blue()
    )
    
    # Image
    img = None
    if "extraAssets" in result:
        if "charaGraph" in result["extraAssets"]:
            asc = result["extraAssets"]["charaGraph"].get("ascension", {})
            if asc:
                img = list(asc.values())[0]
        elif "faces" in result["extraAssets"]:
            faces = result["extraAssets"]["faces"]
            if faces:
                img = list(faces.values())[0]
    elif "face" in result:
        img = result["face"]
    
    if img:
        embed.set_thumbnail(url=img)
    
    # Stats
    rarity = result.get("rarity", 1)
    embed.add_field(name="Rarity", value="⭐" * rarity, inline=True)
    embed.add_field(name="Cost", value=result.get("cost", "N/A"), inline=True)
    
    if "atkMax" in result:
        embed.add_field(name="Max ATK", value=f"{result['atkMax']:,}", inline=True)
    if "hpMax" in result:
        embed.add_field(name="Max HP", value=f"{result['hpMax']:,}", inline=True)
    
    # Cards
    if "cards" in result:
        emojis = {"buster": "🔴", "arts": "🔵", "quick": "🟢"}
        cards = " ".join([emojis.get(c, c.upper()) for c in result["cards"]])
        embed.add_field(name="Cards", value=cards, inline=True)
    
    # Skills
    if "skills" in result and result["skills"]:
        skills_text = ""
        for i in range(1, 4):
            sk = next((s for s in result["skills"] if s.get("num") == i), None)
            if sk:
                skills_text += f"**{i}.** {sk.get('name', 'N/A')}\n"
        if skills_text:
            embed.add_field(name="Skills", value=skills_text, inline=False)
    
    # NP
    if "noblePhantasms" in result and result["noblePhantasms"]:
        np = result["noblePhantasms"][0]
        embed.add_field(name=f"NP [{np.get('card', '').upper()}]", value=np.get("name", "Unknown"), inline=False)
    
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="ce", description="Search Craft Essence")
@app_commands.describe(query="Name or ID", region="NA/JP")
@app_commands.choices(region=[
    app_commands.Choice(name="NA", value="NA"),
    app_commands.Choice(name="JP", value="JP")
])
async def ce_cmd(interaction: discord.Interaction, query: str, region: str = "NA"):
    await interaction.response.defer(thinking=True)
    
    result = await search_ce(query, region)
    
    if not result:
        await interaction.followup.send(f"❌ CE not found: **{query}**")
        return
    
    embed = discord.Embed(
        title=f"🎴 {result.get('name', 'Unknown')}",
        description=f"Collection No. {result.get('collectionNo', result.get('id'))}",
        color=discord.Color.gold()
    )
    
    img = None
    if "extraAssets" in result and "equip" in result["extraAssets"]:
        equip = result["extraAssets"]["equip"]
        if equip:
            img = list(equip.values())[0]
    elif "face" in result:
        img = result["face"]
    
    if img:
        embed.set_thumbnail(url=img)
    
    rarity = result.get("rarity", 1)
    embed.add_field(name="Rarity", value="⭐" * rarity, inline=True)
    
    if "atkMax" in result:
        embed.add_field(name="Max ATK", value=f"{result['atkMax']:,}", inline=True)
    if "hpMax" in result:
        embed.add_field(name="Max HP", value=f"{result['hpMax']:,}", inline=True)
    
    if "skills" in result and result["skills"]:
        effects = []
        for skill in result["skills"]:
            for func in skill.get("functions", []):
                eff = func.get("popupText", "")
                if eff:
                    effects.append(eff)
        if effects:
            embed.add_field(name="Effects", value="\n".join(effects[:5]), inline=False)
    
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="skills", description="Show all 3 skills")
@app_commands.describe(servant_name="Name or ID", region="NA/JP")
@app_commands.choices(region=[
    app_commands.Choice(name="NA", value="NA"),
    app_commands.Choice(name="JP", value="JP")
])
async def skills_cmd(interaction: discord.Interaction, servant_name: str, region: str = "NA"):
    await interaction.response.defer(thinking=True)
    
    result, _ = await search_servant(servant_name, region)
    
    if not result:
        await interaction.followup.send(f"❌ Not found: {servant_name}")
        return
    
    if "skills" not in result or not result["skills"]:
        await interaction.followup.send("❌ No skill data")
        return
    
    header = discord.Embed(title=f"🎯 {result['name']} - Skills", color=discord.Color.red())
    await interaction.followup.send(embed=header)
    
    for i in range(1, 4):
        skill = next((s for s in result["skills"] if s.get("num") == i), None)
        if not skill:
            continue
        
        embed = discord.Embed(title=f"Skill {i}: {skill.get('name', 'Unknown')}", color=discord.Color.dark_red())
        
        if "icon" in skill:
            embed.set_thumbnail(url=skill["icon"])
        
        if "coolDown" in skill:
            cd = skill["coolDown"]
            embed.add_field(name="Cooldown", value=f"{cd[0]} → {cd[-1]}", inline=True)
        
        if "functions" in skill:
            effects = [f"• {f.get('popupText', '')}" for f in skill["functions"] if f.get("popupText")]
            if effects:
                embed.add_field(name="Effects", value="\n".join(effects[:6]), inline=False)
        
        await interaction.channel.send(embed=embed)
        await asyncio.sleep(0.3)

@bot.tree.command(name="art", description="Show artwork")
@app_commands.describe(query="Name or ID", type="Type", region="Region")
@app_commands.choices(type=[
    app_commands.Choice(name="Servant", value="servant"),
    app_commands.Choice(name="CE", value="ce")
], region=[
    app_commands.Choice(name="NA", value="NA"),
    app_commands.Choice(name="JP", value="JP")
])
async def art_cmd(interaction: discord.Interaction, query: str, type: str, region: str = "NA"):
    await interaction.response.defer(thinking=True)
    
    if type == "servant":
        data, _ = await search_servant(query, region)
    else:
        data = await search_ce(query, region)
    
    if not data:
        await interaction.followup.send(f"❌ Not found: {query}")
        return
    
    images = {}
    if type == "servant":
        if "extraAssets" in data and "charaGraph" in data["extraAssets"]:
            for k, v in data["extraAssets"]["charaGraph"].get("ascension", {}).items():
                images[f"Ascension {k}"] = v
            for k, v in data["extraAssets"]["charaGraph"].get("costume", {}).items():
                images[f"Costume {k}"] = v
    else:
        if "extraAssets" in data and "equip" in data["extraAssets"]:
            for k, v in data["extraAssets"]["equip"].items():
                images[f"Art {k}"] = v
    
    if not images:
        await interaction.followup.send("❌ No artwork found")
        return
    
    name = data.get("name", "Unknown")
    color = discord.Color.blue() if type == "servant" else discord.Color.gold()
    
    embed = discord.Embed(title=f"🎨 {name} - Gallery", color=color)
    embed.add_field(name="Available", value="\n".join([f"• {k}" for k in list(images.keys())[:8]]))
    embed.set_image(url=list(images.values())[0])
    await interaction.followup.send(embed=embed)
    
    items = list(images.items())[1:]
    for i in range(0, len(items), 4):
        batch = items[i:i+4]
        embeds = [discord.Embed(title=n, color=color).set_image(url=u) for n, u in batch]
        if embeds:
            await interaction.channel.send(embeds=embeds)
            await asyncio.sleep(0.5)

@bot.tree.command(name="help", description="Show help")
async def help_cmd(interaction: discord.Interaction):
    embed = discord.Embed(
        title="📖t",
        description="Search FGO game data from Atlas Academy",
        color=discord.Color.green()
    )
    
    embed.add_field(
        name="Commands",
        value=(
            "`/servant <name/id>` - Find servant (e.g., `1`, `Mash`, `12`)\n"
            "`/ce <name/id>` - Find Craft Essence\n"
            "`/skills <name>` - Show all 3 skills\n"
            "`/art <name> type:servant/ce` - Show all artwork"
        ),
        inline=False
    )
    
    embed.add_field(
        name="Collection IDs",
        value="`1` = Mash Kyrielight\n`12` = Artoria Pendragon (Saber)\n`200100` = Gilgamesh",
        inline=False
    )
    
    embed.add_field(
        name="Search Tips",
        value="• Not case-sensitive\n• Partial names work\n• Use IDs for exact matches",
        inline=False
    )
    
    cache_status = f"✅ {len(bot.servants)} servants cached" if bot.servants else "⚠️ Using live API"
    embed.set_footer(text=cache_status)
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="reload", description="Force reload data cache")
async def reload_cmd(interaction: discord.Interaction):
    """Admin command to reload cache"""
    await interaction.response.defer(thinking=True)
    
    await interaction.followup.send("🔄 Reloading data...")
    bot.servants = []
    bot.ces = []
    bot.data_loaded = False
    
    await bot._load_data()
    
    if bot.data_loaded:
        await interaction.channel.send(f"✅ Reloaded! {len(bot.servants)} servants, {len(bot.ces)} CEs")
    else:
        await interaction.channel.send(f"❌ Reload failed: {bot.load_error}")

# Run
TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise ValueError("Set DISCORD_TOKEN environment variable!")
bot.run(TOKEN)
