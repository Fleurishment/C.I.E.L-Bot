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
        self.servant_list = []  # Cache for all servants
        self.ce_list = []       # Cache for all CEs
        
    async def setup_hook(self):
        self.session = aiohttp.ClientSession()
        await self.load_data()
        await self.tree.sync()
        
    async def close(self):
        if self.session:
            await self.session.close()
        await super().close()
        
    async def load_data(self):
        """Pre-load all servant and CE data for fast searching"""
        print("Loading servant data...")
        try:
            async with self.session.get(f"{BASIC_URL}/NA/servant") as resp:
                if resp.status == 200:
                    self.servant_list = await resp.json()
                    print(f"Loaded {len(self.servant_list)} servants")
                    
            async with self.session.get(f"{BASIC_URL}/NA/craft-essence") as resp:
                if resp.status == 200:
                    self.ce_list = await resp.json()
                    print(f"Loaded {len(self.ce_list)} CEs")
        except Exception as e:
            print(f"Error loading data: {e}")

bot = FGOBot()

def similarity(a: str, b: str) -> float:
    """Calculate string similarity (0-1)"""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    print(f'Bot is in {len(bot.guilds)} guilds')

def find_servant(query: str, region: str = "NA"):
    """Find servant using multiple strategies - SYNCHRONOUS using cached data"""
    query = query.strip()
    query_lower = query.lower()
    
    if not bot.servant_list:
        return None, "Cache not loaded"
    
    # Strategy 1: Exact ID match
    if query.isdigit():
        servant_id = int(query)
        for s in bot.servant_list:
            if s["id"] == servant_id:
                return s, None
        return None, f"No servant with ID {query}"
    
    # Strategy 2: Exact name match (case insensitive)
    for s in bot.servant_list:
        if s["name"].lower() == query_lower:
            return s, None
    
    # Strategy 3: Starts with (case insensitive)
    matches = [s for s in bot.servant_list if s["name"].lower().startswith(query_lower)]
    if matches:
        # Return first match (usually the main one)
        return matches[0], None
    
    # Strategy 4: Contains (case insensitive)
    matches = [s for s in bot.servant_list if query_lower in s["name"].lower()]
    if matches:
        return matches[0], None
    
    # Strategy 5: Word boundary match (e.g., "Gil" matches "Gilgamesh" but not "Giles")
    matches = []
    for s in bot.servant_list:
        words = re.findall(r'\b\w+\b', s["name"].lower())
        if any(query_lower == word or word.startswith(query_lower) for word in words):
            matches.append(s)
    if matches:
        return matches[0], None
    
    # Strategy 6: Fuzzy match (for typos like "Altria" vs "Artoria")
    best_match = None
    best_score = 0
    for s in bot.servant_list:
        score = similarity(query, s["name"])
        if score > best_score and score > 0.5:  # Lower threshold
            best_score = score
            best_match = s
    
    if best_match:
        return best_match, None
    
    # Strategy 7: Check for common alternatives (Altria -> Artoria)
    alternatives = {
        "altria": "artoria",
        "artoria": "altria", 
        "cil": "ciel",
        "saber": "artoria",
        "lancer": "",
        "archer": ""
    }
    
    if query_lower in alternatives:
        alt_query = alternatives[query_lower]
        if alt_query:
            for s in bot.servant_list:
                if alt_query in s["name"].lower():
                    return s, None
    
    suggestions = [s["name"] for s in bot.servant_list if similarity(query, s["name"]) > 0.3][:3]
    error_msg = f"Suggestions: {', '.join(suggestions)}" if suggestions else "Try using the servant ID number"
    return None, error_msg

def find_ce(query: str, region: str = "NA"):
    """Find CE using cached data"""
    query = query.strip()
    query_lower = query.lower()
    
    if not bot.ce_list:
        return None, "Cache not loaded"
    
    # Exact ID
    if query.isdigit():
        ce_id = int(query)
        for c in bot.ce_list:
            if c["id"] == ce_id:
                return c, None
    
    # Exact name
    for c in bot.ce_list:
        if c["name"].lower() == query_lower:
            return c, None
    
    # Starts with
    matches = [c for c in bot.ce_list if c["name"].lower().startswith(query_lower)]
    if matches:
        return matches[0], None
    
    # Contains
    matches = [c for c in bot.ce_list if query_lower in c["name"].lower()]
    if matches:
        return matches[0], None
    
    # Fuzzy
    best_match = None
    best_score = 0
    for c in bot.ce_list:
        score = similarity(query, c["name"])
        if score > best_score and score > 0.5:
            best_score = score
            best_match = c
    
    if best_match:
        return best_match, None
        
    return None, "CE not found"

async def get_full_servant_data(basic_data: dict, region: str):
    """Fetch full nice data from basic data"""
    if not basic_data:
        return None
    try:
        async with bot.session.get(f"{NICE_URL}/{region}/servant/{basic_data['id']}") as resp:
            if resp.status == 200:
                return await resp.json()
    except Exception as e:
        print(f"Error fetching servant data: {e}")
    return None

async def get_full_ce_data(basic_data: dict, region: str):
    """Fetch full nice data for CE"""
    if not basic_data:
        return None
    try:
        async with bot.session.get(f"{NICE_URL}/{region}/craft-essence/{basic_data['id']}") as resp:
            if resp.status == 200:
                return await resp.json()
    except Exception as e:
        print(f"Error fetching CE data: {e}")
    return None

@bot.tree.command(name="servant", description="Search for a Servant by name or ID")
@app_commands.describe(
    query="Servant name or ID number (not case-sensitive)",
    region="Game region (NA or JP)"
)
@app_commands.choices(region=[
    app_commands.Choice(name="North America", value="NA"),
    app_commands.Choice(name="Japan", value="JP")
])
async def servant_command(interaction: discord.Interaction, query: str, region: str = "NA"):
    await interaction.response.defer()
    
    # Find in cache
    basic_servant, error = find_servant(query, region)
    
    if not basic_servant:
        await interaction.followup.send(
            f"❌ Could not find servant: **{query}**\n"
            f"💡 {error}\n"
            f"📝 Try: `Gilgamesh`, `Artoria`, `mash`, `1` (ID)"
        )
        return
    
    # Fetch full data
    servant = await get_full_servant_data(basic_servant, region)
    if not servant:
        await interaction.followup.send("❌ Found servant but failed to load details. Try again!")
        return
    
    embed = discord.Embed(
        title=f"⭐ {servant['name']}",
        description=f"{servant.get('className', 'Unknown Class')} | ID: {servant['id']}",
        color=discord.Color.blue()
    )
    
    # Add image
    if "extraAssets" in servant and "charaGraph" in servant["extraAssets"]:
        chara = servant["extraAssets"]["charaGraph"]
        if "ascension" in chara and chara["ascension"]:
            asc = chara["ascension"]
            img_url = asc.get("1") or asc.get("0") or list(asc.values())[0]
            if img_url:
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
        card_str = " ".join([card_emojis.get(c, c.upper()) for c in servant["cards"]])
        embed.add_field(name="Command Cards", value=card_str, inline=False)
    
    # All 3 skills summary
    if "skills" in servant:
        skill_lines = []
        for i in range(1, 4):
            skill = next((s for s in servant["skills"] if s.get("num") == i), None)
            if skill:
                skill_lines.append(f"**{i}.** {skill.get('name', 'Unknown')}")
        if skill_lines:
            embed.add_field(name="Skills", value="\n".join(skill_lines), inline=False)
    
    # NP
    if "noblePhantasms" in servant and servant["noblePhantasms"]:
        np = servant["noblePhantasms"][0]
        np_name = np.get('name', 'Unknown')
        np_card = np.get('card', '').upper()
        embed.add_field(name=f"Noble Phantasm [{np_card}]", value=np_name, inline=False)
    
    embed.add_field(name="🎨 Artwork", value="Use `/art` to see all ascension arts!", inline=False)
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="ce", description="Search for a Craft Essence")
@app_commands.describe(
    query="CE name or ID (not case-sensitive)",
    region="Game region (NA or JP)"
)
@app_commands.choices(region=[
    app_commands.Choice(name="North America", value="NA"),
    app_commands.Choice(name="Japan", value="JP")
])
async def ce_command(interaction: discord.Interaction, query: str, region: str = "NA"):
    await interaction.response.defer()
    
    basic_ce, error = find_ce(query, region)
    
    if not basic_ce:
        await interaction.followup.send(
            f"❌ Could not find CE: **{query}**\n"
            f"💡 Try partial names like `kaleid` or use ID number"
        )
        return
    
    ce = await get_full_ce_data(basic_ce, region)
    if not ce:
        await interaction.followup.send("❌ Found CE but failed to load details.")
        return
    
    embed = discord.Embed(
        title=f"🎴 {ce['name']}",
        description=f"ID: {ce['id']} | Cost: {ce.get('cost', 'N/A')}",
        color=discord.Color.gold()
    )
    
    if "extraAssets" in ce and "equip" in ce["extraAssets"]:
        equip = ce["extraAssets"]["equip"]
        if equip:
            img_url = equip.get("1") or list(equip.values())[0]
            if img_url:
                embed.set_thumbnail(url=img_url)
    
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
                effect = func.get("popupText", "")
                if effect:
                    effects.append(effect)
        if effects:
            embed.add_field(name="Effects", value="\n".join(effects[:5]), inline=False)
    
    embed.add_field(name="🎨 Artwork", value="Use `/art` to see base and MLB art!", inline=False)
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
    
    basic_servant, error = find_servant(servant_name, region)
    if not basic_servant:
        await interaction.followup.send(f"❌ Servant not found: **{servant_name}**\n💡 {error}")
        return
    
    servant = await get_full_servant_data(basic_servant, region)
    if not servant:
        await interaction.followup.send("❌ Failed to load servant data.")
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
    
    # Send each skill
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
                embed.add_field(name="Effects", value="\n".join(effects[:10]), inline=False)
        
        await interaction.channel.send(embed=embed)
        await asyncio.sleep(0.5)

@bot.tree.command(name="skill", description="View specific skill or all skills (compact)")
@app_commands.describe(
    servant_name="Servant name",
    skill_num="Skill number (1, 2, or 3) - leave empty for all",
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
    
    basic_servant, error = find_servant(servant_name, region)
    if not basic_servant:
        await interaction.followup.send(f"❌ Servant not found: **{servant_name}**")
        return
    
    servant = await get_full_servant_data(basic_servant, region)
    if not servant:
        await interaction.followup.send("❌ Failed to load data.")
        return
    
    if skill_num is None:
        # Compact view of all skills
        embed = discord.Embed(
            title=f"🎯 {servant['name']} - Skills Overview",
            color=discord.Color.red()
        )
        
        for i in range(1, 4):
            skill = next((s for s in servant.get("skills", []) if s.get("num") == i), None)
            if skill:
                name = skill.get('name', 'Unknown')
                cd = skill.get('coolDown', [0, 0])
                effects = [f.get("popupText", "") for f in skill.get("functions", []) if f.get("popupText")]
                value = f"**{name}**\nCooldown: {cd[0]}→{cd[-1]}"
                if effects:
                    value += f"\n*{effects[0][:50]}...*"
                embed.add_field(name=f"Skill {i}", value=value, inline=False)
        
        await interaction.followup.send(embed=embed)
    else:
        if skill_num not in [1, 2, 3]:
            await interaction.followup.send("❌ Skill number must be 1, 2, or 3!", ephemeral=True)
            return
        
        skills = [s for s in servant.get("skills", []) if s.get("num") == skill_num]
        if not skills:
            await interaction.followup.send(f"❌ Skill {skill_num} not found!")
            return
        
        skill = skills[0]
        embed = discord.Embed(
            title=f"🎯 {skill.get('name', 'Unknown')}",
            description=f"{servant['name']} - Skill {skill_num}",
            color=discord.Color.red()
        )
        
        if "icon" in skill:
            embed.set_thumbnail(url=skill["icon"])
        if "coolDown" in skill:
            cd = skill["coolDown"]
            embed.add_field(name="Cooldown", value=f"{cd[0]}→{cd[-1]} turns", inline=True)
        if "functions" in skill:
            effects = [f"• {f.get('popupText', '')}" for f in skill["functions"] if f.get("popupText")]
            if effects:
                embed.add_field(name="Effects", value="\n".join(effects[:10]), inline=False)
        
        await interaction.followup.send(embed=embed)

@bot.tree.command(name="art", description="Display all artwork for Servant or CE")
@app_commands.describe(
    query="Name or ID",
    type="Servant or CE",
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
    is_servant = type == "servant"
    
    if is_servant:
        basic, error = find_servant(query, region)
        if not basic:
            await interaction.followup.send(f"❌ Servant not found: **{query}**")
            return
        data = await get_full_servant_data(basic, region)
    else:
        basic, error = find_ce(query, region)
        if not basic:
            await interaction.followup.send(f"❌ CE not found: **{query}**")
            return
        data = await get_full_ce_data(basic, region)
    
    if not data:
        await interaction.followup.send("❌ Failed to load artwork data.")
        return
    
    arts = {}
    if is_servant:
        if "extraAssets" in data:
            extra = data["extraAssets"]
            if "charaGraph" in extra and "ascension" in extra["charaGraph"]:
                for key, url in extra["charaGraph"]["ascension"].items():
                    arts[f"Ascension {key}"] = url
            if "charaGraph" in extra and "costume" in extra["charaGraph"]:
                for key, url in extra["charaGraph"]["costume"].items():
                    arts[f"Costume {key}"] = url
        title = f"🎨 {data['name']} - Gallery"
        color = discord.Color.blue()
    else:
        if "extraAssets" in data and "equip" in data["extraAssets"]:
            for key, url in data["extraAssets"]["equip"].items():
                arts[f"Art {key}"] = url
        title = f"🎴 {data['name']} - Gallery"
        color = discord.Color.gold()
    
    if not arts:
        await interaction.followup.send("❌ No artwork found.")
        return
    
    # Send first image with list
    embed = discord.Embed(title=title, color=color)
    art_list = list(arts.items())
    embed.set_image(url=art_list[0][1])
    embed.add_field(name="Available", value="\n".join([f"• {k}" for k, v in art_list[:10]]))
    await interaction.followup.send(embed=embed)
    
    # Send remaining images
    for i in range(1, len(art_list), 4):
        batch = art_list[i:i+4]
        embeds = [discord.Embed(title=name, color=color).set_image(url=url) for name, url in batch]
        if embeds:
            await interaction.channel.send(embeds=embeds)
            await asyncio.sleep(0.5)

@bot.tree.command(name="np", description="Noble Phantasm details")
@app_commands.describe(servant_name="Servant name", region="Game region")
@app_commands.choices(region=[
    app_commands.Choice(name="North America", value="NA"),
    app_commands.Choice(name="Japan", value="JP")
])
async def np_command(interaction: discord.Interaction, servant_name: str, region: str = "NA"):
    await interaction.response.defer()
    
    basic, error = find_servant(servant_name, region)
    if not basic:
        await interaction.followup.send(f"❌ Servant not found: **{servant_name}**")
        return
    
    servant = await get_full_servant_data(basic, region)
    if not servant or not servant.get("noblePhantasms"):
        await interaction.followup.send("❌ No NP found!")
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

@bot.tree.command(name="help", description="Show commands")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="C.I.E.L",
        description="Commands are NOT case-sensitive! `gilgamesh` = `GILGAMESH` = `Gil`",
        color=discord.Color.green()
    )
    commands = [
        ("`/servant <name/id>`", "Search servant (try: gil, artoria, 12)"),
        ("`/ce <name/id>`", "Search CE"),
        ("`/skills <servant>`", "All 3 skills with details"),
        ("`/skill <servant> [1-3]`", "Specific skill or compact view"),
        ("`/art <name> [type]`", "All artwork"),
        ("`/np <servant>`", "Noble Phantasm"),
    ]
    for name, value in commands:
        embed.add_field(name=name, value=value, inline=False)
    await interaction.response.send_message(embed=embed)

import os
TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise ValueError("No DISCORD_TOKEN environment variable found!")
bot.run(TOKEN)
