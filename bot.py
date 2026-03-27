import discord
from discord import app_commands
from discord.ext import commands
import aiohttp
import asyncio
from typing import Optional, Dict, List
from difflib import SequenceMatcher

BASE_URL = "https://api.atlasacademy.io"
NICE_URL = f"{BASE_URL}/nice"
BASIC_URL = f"{BASE_URL}/basic"

class FGOBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.default(), help_command=None)
        self.session = None
        self.servants = []  # Basic data cache
        self.ces = []       # Basic CE cache
        self.ready = False
        
    async def setup_hook(self):
        self.session = aiohttp.ClientSession()
        asyncio.create_task(self.load_data())
        await self.tree.sync()
        
    async def load_data(self):
        """Load data with multiple retries"""
        for attempt in range(5):
            try:
                print(f"Loading data (attempt {attempt+1})...")
                
                # Load servants
                async with self.session.get(f"{BASIC_URL}/NA/servant", timeout=60) as resp:
                    if resp.status == 200:
                        self.servants = await resp.json()
                        print(f"✅ Loaded {len(self.servants)} servants")
                
                # Load CEs
                async with self.session.get(f"{BASIC_URL}/NA/craft-essence", timeout=60) as resp:
                    if resp.status == 200:
                        self.ces = await resp.json()
                        print(f"✅ Loaded {len(self.ces)} CEs")
                
                if self.servants and self.ces:
                    self.ready = True
                    print("✅ Bot is ready!")
                    return
                    
            except Exception as e:
                print(f"❌ Attempt {attempt+1} failed: {e}")
                await asyncio.sleep(5)
        
        print("⚠️ Warning: Could not load cache, will use API fallback")
        
    async def close(self):
        if self.session:
            await self.session.close()
        await super().close()

bot = FGOBot()

def similarity(a, b):
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

async def get_nice_servant(servant_id, region="NA"):
    """Try to get nice data, return None if fails"""
    try:
        async with bot.session.get(f"{NICE_URL}/{region}/servant/{servant_id}", timeout=10) as resp:
            if resp.status == 200:
                return await resp.json()
    except:
        pass
    return None

async def get_nice_ce(ce_id, region="NA"):
    try:
        async with bot.session.get(f"{NICE_URL}/{region}/craft-essence/{ce_id}", timeout=10) as resp:
            if resp.status == 200:
                return await resp.json()
    except:
        pass
    return None

def search_in_list(data_list, query):
    """Search for item in list by ID or name"""
    query = query.strip().lower()
    
    if not data_list:
        return None
    
    # ID search
    if query.isdigit():
        qid = int(query)
        for item in data_list:
            if item.get("id") == qid:
                return item
    
    # Exact match
    for item in data_list:
        if item.get("name", "").lower() == query:
            return item
    
    # Starts with
    for item in data_list:
        if item.get("name", "").lower().startswith(query):
            return item
    
    # Contains
    for item in data_list:
        if query in item.get("name", "").lower():
            return item
    
    # Word boundary
    for item in data_list:
        words = item.get("name", "").lower().split()
        for word in words:
            if word.startswith(query):
                return item
    
    # Fuzzy match (last resort)
    best = None
    best_score = 0
    for item in data_list:
        score = similarity(query, item.get("name", ""))
        if score > best_score and score > 0.5:
            best_score = score
            best = item
    
    return best

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    print(f"Cache: {len(bot.servants)} servants, {len(bot.ces)} CEs")

@bot.tree.command(name="servant", description="Search servant by name or ID")
@app_commands.describe(query="Name or ID (e.g., Gilgamesh, artoria, 12)", region="NA or JP")
@app_commands.choices(region=[
    app_commands.Choice(name="North America", value="NA"),
    app_commands.Choice(name="Japan", value="JP")
])
async def servant_cmd(interaction: discord.Interaction, query: str, region: str = "NA"):
    await interaction.response.defer()
    
    # Search in cache
    basic = None
    if bot.servants:
        basic = search_in_list(bot.servants, query)
    
    # If not in cache, try API directly
    if not basic:
        try:
            async with bot.session.get(f"{BASIC_URL}/{region}/servant", timeout=30) as resp:
                if resp.status == 200:
                    servants = await resp.json()
                    basic = search_in_list(servants, query)
        except Exception as e:
            print(f"API search error: {e}")
    
    if not basic:
        await interaction.followup.send(f"❌ Not found: **{query}**\n💡 Try: `Gilgamesh`, `12`, `mash`")
        return
    
    # Try to get nice data (full details)
    nice = await get_nice_servant(basic["id"], region)
    data = nice if nice else basic  # Use nice if available, else basic
    
    # Create embed
    name = data.get("name", "Unknown")
    s_class = data.get("className", "Unknown")
    sid = data.get("id", "N/A")
    
    embed = discord.Embed(title=f"⭐ {name}", description=f"{s_class} | ID: {sid}", color=discord.Color.blue())
    
    # Image - try nice first, then basic
    img_url = None
    if "extraAssets" in data and "charaGraph" in data["extraAssets"]:
        asc = data["extraAssets"]["charaGraph"].get("ascension", {})
        if asc:
            img_url = list(asc.values())[0]
    elif "face" in data:
        img_url = data["face"]
    
    if img_url:
        embed.set_thumbnail(url=img_url)
    
    # Stats
    rarity = data.get("rarity", 1)
    embed.add_field(name="Rarity", value="⭐" * rarity, inline=True)
    embed.add_field(name="Cost", value=data.get("cost", "N/A"), inline=True)
    
    if "atkMax" in data:
        embed.add_field(name="Max ATK", value=f"{data['atkMax']:,}", inline=True)
    if "hpMax" in data:
        embed.add_field(name="Max HP", value=f"{data['hpMax']:,}", inline=True)
    
    # Cards
    if "cards" in data:
        emojis = {"buster": "🔴", "arts": "🔵", "quick": "🟢"}
        cards = " ".join([emojis.get(c, c.upper()) for c in data["cards"]])
        embed.add_field(name="Command Cards", value=cards, inline=False)
    
    # Skills - only show if we have nice data
    if "skills" in data and data["skills"]:
        skills_text = ""
        for i in range(1, 4):
            sk = next((s for s in data["skills"] if s.get("num") == i), None)
            if sk:
                skills_text += f"**{i}.** {sk.get('name', 'N/A')}\n"
        if skills_text:
            embed.add_field(name="Skills", value=skills_text, inline=False)
    
    # NP
    if "noblePhantasms" in data and data["noblePhantasms"]:
        np = data["noblePhantasms"][0]
        np_name = np.get("name", "Unknown")
        np_card = np.get("card", "").upper()
        embed.add_field(name=f"NP [{np_card}]", value=np_name, inline=False)
    
    # Indicate if using basic data
    if not nice:
        embed.set_footer(text="⚠️ Showing basic data (detailed data unavailable)")
    else:
        embed.add_field(name="🎨 Artwork", value="Use `/art` for all ascension arts!", inline=False)
    
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="ce", description="Search Craft Essence")
@app_commands.describe(query="Name or ID", region="NA or JP")
@app_commands.choices(region=[
    app_commands.Choice(name="North America", value="NA"),
    app_commands.Choice(name="Japan", value="JP")
])
async def ce_cmd(interaction: discord.Interaction, query: str, region: str = "NA"):
    await interaction.response.defer()
    
    # Search cache
    basic = None
    if bot.ces:
        basic = search_in_list(bot.ces, query)
    
    # API fallback
    if not basic:
        try:
            async with bot.session.get(f"{BASIC_URL}/{region}/craft-essence", timeout=30) as resp:
                if resp.status == 200:
                    ces = await resp.json()
                    basic = search_in_list(ces, query)
        except Exception as e:
            print(f"CE API error: {e}")
    
    if not basic:
        await interaction.followup.send(f"❌ CE not found: **{query}**")
        return
    
    # Get nice data
    nice = await get_nice_ce(basic["id"], region)
    data = nice if nice else basic
    
    embed = discord.Embed(
        title=f"🎴 {data.get('name', 'Unknown')}",
        description=f"ID: {data.get('id')} | Cost: {data.get('cost', 'N/A')}",
        color=discord.Color.gold()
    )
    
    # Image
    img_url = None
    if "extraAssets" in data and "equip" in data["extraAssets"]:
        equip = data["extraAssets"]["equip"]
        if equip:
            img_url = list(equip.values())[0]
    elif "face" in data:
        img_url = data["face"]
    
    if img_url:
        embed.set_thumbnail(url=img_url)
    
    rarity = data.get("rarity", 1)
    embed.add_field(name="Rarity", value="⭐" * rarity, inline=True)
    
    if "atkMax" in data:
        embed.add_field(name="Max ATK", value=f"{data['atkMax']:,}", inline=True)
    if "hpMax" in data:
        embed.add_field(name="Max HP", value=f"{data['hpMax']:,}", inline=True)
    
    # Effects
    if "skills" in data and data["skills"]:
        effects = []
        for skill in data["skills"]:
            for func in skill.get("functions", []):
                eff = func.get("popupText", "")
                if eff:
                    effects.append(eff)
        if effects:
            embed.add_field(name="Effects", value="\n".join(effects[:5]), inline=False)
    
    if not nice:
        embed.set_footer(text="⚠️ Basic data only")
    
    await interaction.followup.send(embed=embed)

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
    await interaction.response.defer()
    
    # Get data
    if type == "servant":
        basic = search_in_list(bot.servants, query) if bot.servants else None
        if not basic:
            await interaction.followup.send("❌ Servant not found")
            return
        data = await get_nice_servant(basic["id"], region)
        if not data:
            data = basic
    else:
        basic = search_in_list(bot.ces, query) if bot.ces else None
        if not basic:
            await interaction.followup.send("❌ CE not found")
            return
        data = await get_nice_ce(basic["id"], region)
        if not data:
            data = basic
    
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
    
    # Send
    name = data.get("name", "Unknown")
    color = discord.Color.blue() if type == "servant" else discord.Color.gold()
    
    # First with list
    embed = discord.Embed(title=f"🎨 {name} - Gallery", color=color)
    embed.add_field(name="Available", value="\n".join([f"• {k}" for k in list(images.keys())[:8]]))
    first_url = list(images.values())[0]
    embed.set_image(url=first_url)
    await interaction.followup.send(embed=embed)
    
    # Rest
    items = list(images.items())[1:]
    for i in range(0, len(items), 4):
        batch = items[i:i+4]
        embeds = [discord.Embed(title=n, color=color).set_image(url=u) for n, u in batch]
        if embeds:
            await interaction.channel.send(embeds=embeds)
            await asyncio.sleep(0.5)

@bot.tree.command(name="skills", description="Show all 3 skills")
@app_commands.describe(servant_name="Servant name", region="NA or JP")
@app_commands.choices(region=[
    app_commands.Choice(name="NA", value="NA"),
    app_commands.Choice(name="JP", value="JP")
])
async def skills_cmd(interaction: discord.Interaction, servant_name: str, region: str = "NA"):
    await interaction.response.defer()
    
    basic = search_in_list(bot.servants, servant_name) if bot.servants else None
    if not basic:
        await interaction.followup.send(f"❌ Not found: {servant_name}")
        return
    
    data = await get_nice_servant(basic["id"], region)
    if not data or not data.get("skills"):
        await interaction.followup.send("❌ Skill data unavailable")
        return
    
    # Header
    header = discord.Embed(title=f"🎯 {data['name']} - Skills", color=discord.Color.red())
    await interaction.followup.send(embed=header)
    
    # Each skill
    for i in range(1, 4):
        skill = next((s for s in data["skills"] if s.get("num") == i), None)
        if not skill:
            continue
        
        embed = discord.Embed(title=f"Skill {i}: {skill.get('name', 'Unknown')}", color=discord.Color.dark_red())
        if "icon" in skill:
            embed.set_thumbnail(url=skill["icon"])
        
        if "coolDown" in skill:
            cd = skill["coolDown"]
            embed.add_field(name="Cooldown", value=f"{cd[0]} → {cd[-1]} turns", inline=True)
        
        if "functions" in skill:
            effects = [f"• {f.get('popupText', '')}" for f in skill["functions"] if f.get("popupText")]
            if effects:
                embed.add_field(name="Effects", value="\n".join(effects[:6]), inline=False)
        
        await interaction.channel.send(embed=embed)
        await asyncio.sleep(0.3)

@bot.tree.command(name="help", description="Show all commands")
async def help_cmd(interaction: discord.Interaction):
    embed = discord.Embed(
        title="C.I.E.L - Help",
        description="Case-insensitive search for FGO data",
        color=discord.Color.green()
    )
    
    embed.add_field(
        name="Commands",
        value=(
            "`/servant <name/id>` - Find servant (e.g., `gilgamesh`, `12`)\n"
            "`/ce <name/id>` - Find Craft Essence\n"
            "`/skills <name>` - All 3 skills detailed\n"
            "`/art <name> type:servant/ce` - All artwork\n"
            "`/help` - This message"
        ),
        inline=False
    )
    
    embed.add_field(
        name="Search Tips",
        value=(
            "• Not case-sensitive: `gil` = `GIL` = `Gil`\n"
            "• Partial names work: `artoria` finds Artoria Pendragon\n"
            "• Use ID numbers for exact matches\n"
            "• Add `region:JP` for Japanese server data"
        ),
        inline=False
    )
    
    status = "✅ Ready" if bot.ready else "⏳ Loading..."
    embed.set_footer(text=f"Cache Status: {status}")
    
    await interaction.response.send_message(embed=embed)

import os
TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise ValueError("No DISCORD_TOKEN found!")
bot.run(TOKEN)
