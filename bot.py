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
        self.servants: List[Dict] = []  # Basic data cache
        self.ces: List[Dict] = []
        
    async def setup_hook(self):
        # Create session with longer timeout
        timeout = aiohttp.ClientTimeout(total=60, connect=30)
        self.session = aiohttp.ClientSession(timeout=timeout)
        
        # Load data in background
        asyncio.create_task(self._load_data())
        await self.tree.sync()
        
    async def _load_data(self):
        """Load data with retries"""
        for attempt in range(3):
            try:
                print(f"Loading data (attempt {attempt+1}/3)...")
                
                # Servants
                async with self.session.get(f"{API_BASE}/basic/NA/servant") as resp:
                    if resp.status == 200:
                        self.servants = await resp.json()
                        print(f"✅ Loaded {len(self.servants)} servants")
                
                # CEs
                async with self.session.get(f"{API_BASE}/basic/NA/craft-essence") as resp:
                    if resp.status == 200:
                        self.ces = await resp.json()
                        print(f"✅ Loaded {len(self.ces)} CEs")
                
                if self.servants:
                    print("✅ Data ready!")
                    return
                    
            except Exception as e:
                print(f"❌ Attempt {attempt+1} failed: {e}")
                await asyncio.sleep(3)
        
        print("⚠️ Will use API fallback mode")
    
    async def close(self):
        if self.session:
            await self.session.close()
        await super().close()

bot = FGOBot()

def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

async def ensure_servants():
    """Make sure we have servant data"""
    if bot.servants:
        return bot.servants
    
    # Fetch if not cached
    try:
        async with bot.session.get(f"{API_BASE}/basic/NA/servant") as resp:
            if resp.status == 200:
                bot.servants = await resp.json()
                return bot.servants
    except Exception as e:
        print(f"Error fetching servants: {e}")
    return []

async def ensure_ces():
    """Make sure we have CE data"""
    if bot.ces:
        return bot.ces
    
    try:
        async with bot.session.get(f"{API_BASE}/basic/NA/craft-essence") as resp:
            if resp.status == 200:
                bot.ces = await resp.json()
                return bot.ces
    except Exception as e:
        print(f"Error fetching CEs: {e}")
    return []

async def search_servant(query: str, region: str = "NA"):
    """
    Search servant by collectionNo (user ID) or name.
    Returns nice data or None.
    """
    query = query.strip()
    query_lower = query.lower()
    
    # Get servant list
    servants = await ensure_servants()
    if not servants:
        print("ERROR: No servant data available")
        return None
    
    print(f"Searching for: '{query}' in {len(servants)} servants")
    
    # Try collectionNo first (what users type as ID)
    if query.isdigit():
        collection_no = int(query)
        for s in servants:
            if s.get("collectionNo") == collection_no:
                print(f"Found by collectionNo: {s['name']} (internal ID: {s['id']})")
                # Get nice data
                try:
                    async with bot.session.get(f"{API_BASE}/nice/{region}/servant/{s['id']}") as resp:
                        if resp.status == 200:
                            return await resp.json()
                except Exception as e:
                    print(f"Error fetching nice data: {e}")
                # Return basic if nice fails
                return s
    
    # Try internal ID (just in case)
    if query.isdigit():
        internal_id = int(query)
        for s in servants:
            if s.get("id") == internal_id:
                print(f"Found by internal ID: {s['name']}")
                try:
                    async with bot.session.get(f"{API_BASE}/nice/{region}/servant/{internal_id}") as resp:
                        if resp.status == 200:
                            return await resp.json()
                except:
                    pass
                return s
    
    # Name search - Exact match
    for s in servants:
        if s.get("name", "").lower() == query_lower:
            print(f"Found exact match: {s['name']}")
            try:
                async with bot.session.get(f"{API_BASE}/nice/{region}/servant/{s['id']}") as resp:
                    if resp.status == 200:
                        return await resp.json()
            except:
                pass
            return s
    
    # Starts with
    for s in servants:
        if s.get("name", "").lower().startswith(query_lower):
            print(f"Found starts-with: {s['name']}")
            try:
                async with bot.session.get(f"{API_BASE}/nice/{region}/servant/{s['id']}") as resp:
                    if resp.status == 200:
                        return await resp.json()
            except:
                pass
            return s
    
    # Contains
    for s in servants:
        if query_lower in s.get("name", "").lower():
            print(f"Found contains: {s['name']}")
            try:
                async with bot.session.get(f"{API_BASE}/nice/{region}/servant/{s['id']}") as resp:
                    if resp.status == 200:
                        return await resp.json()
            except:
                pass
            return s
    
    # Fuzzy match
    best = None
    best_score = 0
    for s in servants:
        score = similarity(query, s.get("name", ""))
        if score > best_score and score > 0.5:
            best_score = score
            best = s
    
    if best:
        print(f"Found fuzzy match ({best_score:.2f}): {best['name']}")
        try:
            async with bot.session.get(f"{API_BASE}/nice/{region}/servant/{best['id']}") as resp:
                if resp.status == 200:
                    return await resp.json()
        except:
            pass
        return best
    
    print(f"No match found for: {query}")
    return None

async def search_ce(query: str, region: str = "NA"):
    """Search CE by collectionNo or name"""
    query = query.strip()
    query_lower = query.lower()
    
    ces = await ensure_ces()
    if not ces:
        return None
    
    # Try collectionNo first
    if query.isdigit():
        collection_no = int(query)
        for c in ces:
            if c.get("collectionNo") == collection_no:
                try:
                    async with bot.session.get(f"{API_BASE}/nice/{region}/craft-essence/{c['id']}") as resp:
                        if resp.status == 200:
                            return await resp.json()
                except:
                    pass
                return c
        
        # Try internal ID
        internal_id = int(query)
        for c in ces:
            if c.get("id") == internal_id:
                try:
                    async with bot.session.get(f"{API_BASE}/nice/{region}/craft-essence/{internal_id}") as resp:
                        if resp.status == 200:
                            return await resp.json()
                except:
                    pass
                return c
    
    # Name searches
    for c in ces:
        if c.get("name", "").lower() == query_lower:
            try:
                async with bot.session.get(f"{API_BASE}/nice/{region}/craft-essence/{c['id']}") as resp:
                    if resp.status == 200:
                        return await resp.json()
            except:
                pass
            return c
    
    for c in ces:
        if c.get("name", "").lower().startswith(query_lower):
            try:
                async with bot.session.get(f"{API_BASE}/nice/{region}/craft-essence/{c['id']}") as resp:
                    if resp.status == 200:
                        return await resp.json()
            except:
                pass
            return c
    
    for c in ces:
        if query_lower in c.get("name", "").lower():
            try:
                async with bot.session.get(f"{API_BASE}/nice/{region}/craft-essence/{c['id']}") as resp:
                    if resp.status == 200:
                        return await resp.json()
            except:
                pass
            return c
    
    # Fuzzy
    best = None
    best_score = 0
    for c in ces:
        score = similarity(query, c.get("name", ""))
        if score > best_score and score > 0.5:
            best_score = score
            best = c
    
    if best:
        try:
            async with bot.session.get(f"{API_BASE}/nice/{region}/craft-essence/{best['id']}") as resp:
                if resp.status == 200:
                    return await resp.json()
        except:
            pass
        return best
    
    return None

@bot.event
async def on_ready():
    print(f"✅ Bot ready as {bot.user}")
    print(f"Data cached: {len(bot.servants)} servants, {len(bot.ces)} CEs")

@bot.tree.command(name="servant", description="Search servant by name or collection ID")
@app_commands.describe(query="Name or ID (e.g., 1, Mash, 12, Gilgamesh)", region="NA or JP")
@app_commands.choices(region=[
    app_commands.Choice(name="North America", value="NA"),
    app_commands.Choice(name="Japan", value="JP")
])
async def servant_cmd(interaction: discord.Interaction, query: str, region: str = "NA"):
    await interaction.response.defer(thinking=True)
    
    try:
        result = await search_servant(query, region)
        
        if not result:
            await interaction.followup.send(
                f"❌ Not found: **{query}**\n"
                f"💡 Try: `1` (Mash), `12` (Artoria), `gilgamesh`, `mash`\n"
                f"📊 Cache: {len(bot.servants)} servants loaded"
            )
            return
        
        # Build embed
        embed = discord.Embed(
            title=f"⭐ {result.get('name', 'Unknown')}",
            description=f"{result.get('className', 'Unknown Class')} | Collection No. {result.get('collectionNo', 'N/A')}",
            color=discord.Color.blue()
        )
        
        # Image
        img = None
        if "extraAssets" in result:
            if "charaGraph" in result["extraAssets"] and result["extraAssets"]["charaGraph"]:
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
            embed.add_field(name="Command Cards", value=cards, inline=True)
        
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
            embed.add_field(
                name=f"NP [{np.get('card', '').upper()}]",
                value=np.get("name", "Unknown"),
                inline=False
            )
        
        # Traits
        if "traits" in result and result["traits"]:
            traits = ", ".join([t.get("name", "") for t in result["traits"][:3]])
            embed.set_footer(text=f"Traits: {traits}")
        
        await interaction.followup.send(embed=embed)
        
    except Exception as e:
        print(f"Error: {e}")
        await interaction.followup.send(f"❌ Error: {str(e)}")

@bot.tree.command(name="ce", description="Search Craft Essence")
@app_commands.describe(query="Name or ID", region="NA or JP")
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
    
    # Image
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
    
    # Effects
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
@app_commands.describe(servant_name="Name or ID", region="NA or JP")
@app_commands.choices(region=[
    app_commands.Choice(name="NA", value="NA"),
    app_commands.Choice(name="JP", value="JP")
])
async def skills_cmd(interaction: discord.Interaction, servant_name: str, region: str = "NA"):
    await interaction.response.defer(thinking=True)
    
    servant = await search_servant(servant_name, region)
    
    if not servant:
        await interaction.followup.send(f"❌ Not found: {servant_name}")
        return
    
    if "skills" not in servant or not servant["skills"]:
        await interaction.followup.send("❌ No skill data available")
        return
    
    # Header
    header = discord.Embed(
        title=f"🎯 {servant['name']} - Skills",
        color=discord.Color.red()
    )
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
            embed.add_field(name="Cooldown", value=f"{cd[0]} → {cd[-1]}", inline=True)
        
        if "functions" in skill:
            effects = [f"• {f.get('popupText', '')}" for f in skill["functions"] if f.get("popupText")]
            if effects:
                embed.add_field(name="Effects", value="\n".join(effects[:6]), inline=False)
        
        await interaction.channel.send(embed=embed)
        await asyncio.sleep(0.3)

@bot.tree.command(name="art", description="Show all artwork")
@app_commands.describe(query="Name or ID", type="Type", region="Region")
@app_commands.choices(type=[
    app_commands.Choice(name="Servant", value="servant"),
    app_commands.Choice(name="Craft Essence", value="ce")
], region=[
    app_commands.Choice(name="NA", value="NA"),
    app_commands.Choice(name="JP", value="JP")
])
async def art_cmd(interaction: discord.Interaction, query: str, type: str, region: str = "NA"):
    await interaction.response.defer(thinking=True)
    
    if type == "servant":
        data = await search_servant(query, region)
    else:
        data = await search_ce(query, region)
    
    if not data:
        await interaction.followup.send(f"❌ Not found: {query}")
        return
    
    # Collect images
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
        title="📖 FGO Atlas Bot",
        description="Search FGO game data",
        color=discord.Color.green()
    )
    
    embed.add_field(
        name="Commands",
        value=(
            "`/servant <name/id>` - Find servant\n"
            "`/ce <name/id>` - Find CE\n"
            "`/skills <name>` - All 3 skills\n"
            "`/art <name> type:servant/ce` - Artwork"
        ),
        inline=False
    )
    
    embed.add_field(
        name="Search Tips",
        value=(
            "• Use **collection number**: `1` = Mash, `12` = Artoria\n"
            "• Not case-sensitive: `mash` = `Mash`\n"
            "• Partial names: `gil` finds Gilgamesh"
        ),
        inline=False
    )
    
    await interaction.response.send_message(embed=embed)

import os
TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise ValueError("No DISCORD_TOKEN!")
bot.run(TOKEN)
