import discord
from discord import app_commands
from discord.ext import commands
import aiohttp
import asyncio
from typing import Optional, Dict, List
import json
import re
from difflib import get_close_matches

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
        
    async def setup_hook(self):
        self.session = aiohttp.ClientSession()
        await self.tree.sync()
        
    async def close(self):
        if self.session:
            await self.session.close()
        await super().close()

bot = FGOBot()

# Cache for autocomplete
servant_cache: List[Dict] = []
ce_cache: List[Dict] = []

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    print(f'Bot is in {len(bot.guilds)} guilds')
    await load_cache()
    print("Cache loaded!")

async def load_cache():
    """Load basic servant and CE data for autocomplete"""
    global servant_cache, ce_cache
    try:
        async with bot.session.get(f"{BASIC_URL}/NA/servant") as resp:
            if resp.status == 200:
                data = await resp.json()
                servant_cache = [
                    {"name": s["name"], "id": s["id"], "className": s.get("className", "Unknown")}
                    for s in data
                ]
        
        async with bot.session.get(f"{BASIC_URL}/NA/craft-essence") as resp:
            if resp.status == 200:
                data = await resp.json()
                ce_cache = [
                    {"name": ce["name"], "id": ce["id"], "rarity": ce.get("rarity", 0)}
                    for ce in data
                ]
    except Exception as e:
        print(f"Cache loading error: {e}")

def normalize_name(name: str) -> str:
    """Normalize name for better matching"""
    # Remove extra spaces, lowercase, remove special punctuation
    name = re.sub(r'\s+', ' ', name.strip().lower())
    name = re.sub(r'[^\w\s]', '', name)  # Remove special chars
    return name

async def search_servant(query: str, region: str = "NA"):
    """Search for servant by name or ID - improved fuzzy matching"""
    query = query.strip()
    
    # Try ID first
    if query.isdigit():
        async with bot.session.get(f"{NICE_URL}/{region}/servant/{query}") as resp:
            if resp.status == 200:
                return await resp.json()
            return None
    
    # Get all servants
    async with bot.session.get(f"{BASIC_URL}/{region}/servant") as resp:
        if resp.status != 200:
            return None
            
        servants = await resp.json()
        query_lower = query.lower()
        query_normalized = normalize_name(query)
        
        # Priority 1: Exact match (case-insensitive)
        for s in servants:
            if s["name"].lower() == query_lower:
                async with bot.session.get(f"{NICE_URL}/{region}/servant/{s['id']}") as resp2:
                    if resp2.status == 200:
                        return await resp2.json()
        
        # Priority 2: Starts with (case-insensitive)
        matches = [s for s in servants if s["name"].lower().startswith(query_lower)]
        if matches:
            servant_id = matches[0]["id"]
            async with bot.session.get(f"{NICE_URL}/{region}/servant/{servant_id}") as resp2:
                if resp2.status == 200:
                    return await resp2.json()
        
        # Priority 3: Contains (case-insensitive)
        matches = [s for s in servants if query_lower in s["name"].lower()]
        if matches:
            servant_id = matches[0]["id"]
            async with bot.session.get(f"{NICE_URL}/{region}/servant/{servant_id}") as resp2:
                if resp2.status == 200:
                    return await resp2.json()
        
        # Priority 4: Fuzzy matching for typos/similar names
        names = [s["name"] for s in servants]
        close_matches = get_close_matches(query, names, n=1, cutoff=0.6)
        if close_matches:
            match_name = close_matches[0]
            servant = next((s for s in servants if s["name"] == match_name), None)
            if servant:
                async with bot.session.get(f"{NICE_URL}/{region}/servant/{servant['id']}") as resp2:
                    if resp2.status == 200:
                        return await resp2.json()
    
    return None

async def search_ce(query: str, region: str = "NA"):
    """Search for craft essence with improved matching"""
    query = query.strip()
    
    if query.isdigit():
        async with bot.session.get(f"{NICE_URL}/{region}/craft-essence/{query}") as resp:
            if resp.status == 200:
                return await resp.json()
            return None
    
    async with bot.session.get(f"{BASIC_URL}/{region}/craft-essence") as resp:
        if resp.status != 200:
            return None
            
        ces = await resp.json()
        query_lower = query.lower()
        
        # Priority 1: Exact match
        for ce in ces:
            if ce["name"].lower() == query_lower:
                async with bot.session.get(f"{NICE_URL}/{region}/craft-essence/{ce['id']}") as resp2:
                    if resp2.status == 200:
                        return await resp2.json()
        
        # Priority 2: Starts with
        matches = [c for c in ces if c["name"].lower().startswith(query_lower)]
        if matches:
            ce_id = matches[0]["id"]
            async with bot.session.get(f"{NICE_URL}/{region}/craft-essence/{ce_id}") as resp2:
                if resp2.status == 200:
                    return await resp2.json()
        
        # Priority 3: Contains
        matches = [c for c in ces if query_lower in c["name"].lower()]
        if matches:
            ce_id = matches[0]["id"]
            async with bot.session.get(f"{NICE_URL}/{region}/craft-essence/{ce_id}") as resp2:
                if resp2.status == 200:
                    return await resp2.json()
        
        # Priority 4: Fuzzy
        names = [c["name"] for c in ces]
        close_matches = get_close_matches(query, names, n=1, cutoff=0.6)
        if close_matches:
            match_name = close_matches[0]
            ce = next((c for c in ces if c["name"] == match_name), None)
            if ce:
                async with bot.session.get(f"{NICE_URL}/{region}/craft-essence/{ce['id']}") as resp2:
                    if resp2.status == 200:
                        return await resp2.json()
    
    return None

def get_servant_arts(data: dict) -> dict:
    """Extract all art URLs from servant data"""
    arts = {}
    if "extraAssets" not in data:
        return arts
    
    extra = data["extraAssets"]
    
    if "charaGraph" in extra and "ascension" in extra["charaGraph"]:
        ascension = extra["charaGraph"]["ascension"]
        for key in ["0", "1", "2", "3", "4"]:
            if key in ascension:
                arts[f"Ascension {key}"] = ascension[key]
    
    if "charaGraph" in extra and "costume" in extra["charaGraph"]:
        costumes = extra["charaGraph"]["costume"]
        for costume_id, url in costumes.items():
            costume_name = f"Costume {costume_id}"
            if "costumeAssets" in data and "items" in data["costumeAssets"]:
                for item in data["costumeAssets"]["items"]:
                    if str(item.get("id")) == costume_id:
                        costume_name = item.get("name", f"Costume {costume_id}")
                        break
            arts[costume_name] = url
    
    if "commands" in extra:
        cmds = extra["commands"]
        if "ascension" in cmds:
            for key, url in cmds["ascension"].items():
                arts[f"Command Card {key}"] = url
    
    if "status" in extra and "ascension" in extra["status"]:
        for key, url in extra["status"]["ascension"].items():
            arts[f"Status {key}"] = url
    
    return arts

def get_ce_arts(data: dict) -> dict:
    """Extract art URLs from CE data"""
    arts = {}
    if "extraAssets" not in data:
        return arts
    
    extra = data["extraAssets"]
    
    if "equip" in extra:
        equip = extra["equip"]
        if "1" in equip:
            arts["Base Art"] = equip["1"]
        if "2" in equip:
            arts["Max Limit Broken"] = equip["2"]
        for key, url in equip.items():
            if key not in ["1", "2"]:
                arts[f"Art {key}"] = url
    
    if "faces" in extra and "equip" in extra["faces"]:
        faces = extra["faces"]["equip"]
        for key, url in faces.items():
            arts[f"Icon {key}"] = url
    
    return arts

@bot.tree.command(name="art", description="Display all artwork and sprites for a Servant or CE")
@app_commands.describe(
    query="Servant or CE name/ID",
    type="Search for Servant or Craft Essence",
    region="Game region (NA or JP)"
)
@app_commands.choices(type=[
    app_commands.Choice(name="Servant", value="servant"),
    app_commands.Choice(name="Craft Essence", value="ce")
], region=[
    app_commands.Choice(name="North America", value="NA"),
    app_commands.Choice(name="Japan", value="JP")
])
async def art_command(
    interaction: discord.Interaction, 
    query: str, 
    type: str = "servant",
    region: str = "NA"
):
    await interaction.response.defer()
    
    data = None
    is_servant = type == "servant"
    
    if is_servant:
        data = await search_servant(query, region)
        if not data:
            await interaction.followup.send(f"❌ Could not find servant: **{query}**")
            return
        arts = get_servant_arts(data)
        title = f"🎨 {data['name']} - Art Gallery"
        color = discord.Color.blue()
        description = f"Class: {data.get('className', 'Unknown')} | ID: {data['id']}"
    else:
        data = await search_ce(query, region)
        if not data:
            await interaction.followup.send(f"❌ Could not find Craft Essence: **{query}**")
            return
        arts = get_ce_arts(data)
        title = f"🎴 {data['name']} - Art Gallery"
        color = discord.Color.gold()
        description = f"Rarity: {'⭐' * data.get('rarity', 1)} | ID: {data['id']}"
    
    if not arts:
        await interaction.followup.send("❌ No artwork found for this entry.")
        return
    
    embed = discord.Embed(
        title=title,
        description=description,
        color=color
    )
    
    art_types = list(arts.keys())
    embed.add_field(
        name="Available Artwork", 
        value="\n".join([f"• {art}" for art in art_types[:15]]) + 
              (f"\n*...and {len(art_types) - 15} more*" if len(art_types) > 15 else ""),
        inline=False
    )
    
    if art_types:
        first_art = arts[art_types[0]]
        embed.set_image(url=first_art)
    
    await interaction.followup.send(embed=embed)
    
    main_arts = {k: v for k, v in arts.items() if "Command" not in k and "Icon" not in k and "Status" not in k}
    
    if len(main_arts) > 1:
        art_items = list(main_arts.items())
        for i in range(1, len(art_items), 4):
            batch = art_items[i:i+4]
            embeds = []
            for art_name, art_url in batch:
                art_embed = discord.Embed(
                    title=art_name,
                    color=color
                )
                art_embed.set_image(url=art_url)
                embeds.append(art_embed)
            
            if embeds:
                await interaction.channel.send(embeds=embeds)
                await asyncio.sleep(0.5)
    
    sprite_arts = {k: v for k, v in arts.items() if any(x in k for x in ["Command", "Icon", "Face"])}
    if sprite_arts:
        sprite_embed = discord.Embed(
            title="🎭 Sprites & Icons",
            color=discord.Color.greyple()
        )
        for art_name, art_url in list(sprite_arts.items())[:4]:
            sprite_embed.add_field(name=art_name, value=f"[View]({art_url})", inline=True)
        
        if len(sprite_arts) > 4:
            sprite_embed.set_footer(text=f"+ {len(sprite_arts) - 4} more sprites available")
        
        await interaction.channel.send(embed=sprite_embed)

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
    
    servant = await search_servant(query, region)
    
    if not servant:
        await interaction.followup.send(
            f"❌ Could not find servant: **{query}**\n"
            f"💡 Tips: Try partial names like `Gil` instead of `Gilgamesh`, or use the ID number."
        )
        return
    
    embed = discord.Embed(
        title=f"⭐ {servant['name']}",
        description=servant.get("className", "Unknown Class"),
        color=discord.Color.blue()
    )
    
    if "extraAssets" in servant and "charaGraph" in servant["extraAssets"]:
        chara = servant["extraAssets"]["charaGraph"]
        if "ascension" in chara:
            asc = chara["ascension"]
            img_url = asc.get("1") or asc.get("0") or list(asc.values())[0] if asc else None
            if img_url:
                embed.set_thumbnail(url=img_url)
    
    rarity = "⭐" * servant.get("rarity", 1)
    embed.add_field(name="Rarity", value=rarity, inline=True)
    embed.add_field(name="Cost", value=servant.get("cost", "N/A"), inline=True)
    embed.add_field(name="ID", value=servant["id"], inline=True)
    
    if "atkMax" in servant:
        embed.add_field(name="Max ATK", value=f"{servant['atkMax']:,}", inline=True)
    if "hpMax" in servant:
        embed.add_field(name="Max HP", value=f"{servant['hpMax']:,}", inline=True)
    
    if "cards" in servant:
        card_emojis = {"buster": "🔴", "arts": "🔵", "quick": "🟢"}
        card_str = " ".join([card_emojis.get(c, c.upper()) for c in servant["cards"]])
        embed.add_field(name="Command Cards", value=card_str, inline=False)
    
    # Show all 3 skills summary
    if "skills" in servant and servant["skills"]:
        skill_lines = []
        for i in range(1, 4):  # Skills 1, 2, 3
            skill = next((s for s in servant["skills"] if s.get("num") == i), None)
            if skill:
                skill_lines.append(f"**{i}.** {skill.get('name', 'Unknown')}")
        if skill_lines:
            embed.add_field(name="Skills", value="\n".join(skill_lines), inline=False)
    
    if "noblePhantasms" in servant and servant["noblePhantasms"]:
        np = servant["noblePhantasms"][0]
        np_name = np.get("name", "Unknown")
        np_card = np.get("card", "").upper()
        embed.add_field(name="Noble Phantasm", value=f"[{np_card}] {np_name}", inline=False)
    
    if "traits" in servant and servant["traits"]:
        traits = ", ".join([t.get("name", "") for t in servant["traits"][:5]])
        embed.set_footer(text=f"Traits: {traits}")
    
    embed.add_field(name="🎨 Artwork", value="Use `/art` to see all ascension arts!", inline=False)
    
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="skills", description="Show all 3 skills of a servant at once")
@app_commands.describe(
    servant_name="Name of the servant (not case-sensitive)",
    region="Game region"
)
@app_commands.choices(region=[
    app_commands.Choice(name="North America", value="NA"),
    app_commands.Choice(name="Japan", value="JP")
])
async def skills_command(interaction: discord.Interaction, servant_name: str, region: str = "NA"):
    """Show all 3 skills with full details"""
    await interaction.response.defer()
    
    servant = await search_servant(servant_name, region)
    if not servant:
        await interaction.followup.send(f"❌ Servant not found: **{servant_name}**")
        return
    
    # Send initial embed with servant info
    main_embed = discord.Embed(
        title=f"🎯 {servant['name']} - All Skills",
        description=f"Class: {servant.get('className', 'Unknown')}",
        color=discord.Color.red()
    )
    
    if "extraAssets" in servant and "faces" in servant["extraAssets"]:
        faces = servant["extraAssets"]["faces"]
        if faces:
            main_embed.set_thumbnail(url=list(faces.values())[0])
    
    await interaction.followup.send(embed=main_embed)
    
    # Send each skill as a separate embed for better formatting
    for skill_num in range(1, 4):
        skills = [s for s in servant.get("skills", []) if s.get("num") == skill_num]
        if not skills:
            continue
            
        skill = skills[0]
        
        embed = discord.Embed(
            title=f"Skill {skill_num}: {skill.get('name', 'Unknown')}",
            color=discord.Color.dark_red()
        )
        
        if "icon" in skill:
            embed.set_thumbnail(url=skill["icon"])
        
        if "coolDown" in skill:
            cd = skill["coolDown"]
            embed.add_field(name="Cooldown", value=f"{cd[0]} → {cd[-1]} turns", inline=True)
        
        # Get skill effects
        if "functions" in skill:
            effects = []
            for func in skill["functions"]:
                popup = func.get("popupText", "")
                if popup:
                    effects.append(f"• {popup}")
            if effects:
                # Split into multiple fields if too long
                effect_text = "\n".join(effects)
                if len(effect_text) > 1024:
                    effect_text = effect_text[:1021] + "..."
                embed.add_field(name="Effects", value=effect_text, inline=False)
        
        await interaction.channel.send(embed=embed)
        await asyncio.sleep(0.3)  # Prevent rate limiting

@bot.tree.command(name="skill", description="Get specific skill information (1, 2, or 3)")
@app_commands.describe(
    servant_name="Name of the servant",
    skill_num="Skill number (1, 2, or 3) - Optional, leave empty to see all skills",
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
    """Single skill lookup or all skills if no number provided"""
    await interaction.response.defer()
    
    servant = await search_servant(servant_name, region)
    if not servant:
        await interaction.followup.send(f"❌ Servant not found: **{servant_name}**")
        return
    
    # If no skill number provided, show all skills (redirect to skills command logic)
    if skill_num is None:
        # Show compact view of all skills
        embed = discord.Embed(
            title=f"🎯 {servant['name']} - Skills Overview",
            color=discord.Color.red()
        )
        
        for i in range(1, 4):
            skill = next((s for s in servant.get("skills", []) if s.get("num") == i), None)
            if skill:
                name = skill.get('name', 'Unknown')
                cd = skill.get('coolDown', [0, 0])
                effects = []
                if "functions" in skill:
                    effects = [f.get("popupText", "") for f in skill["functions"] if f.get("popupText")]
                
                value = f"**{name}**\n"
                value += f"Cooldown: {cd[0]}/{cd[-1]}\n"
                if effects:
                    value += f"*{effects[0]}*"
                
                embed.add_field(name=f"Skill {i}", value=value[:1024], inline=False)
        
        await interaction.followup.send(embed=embed)
        return
    
    # Specific skill requested
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
        description=f"**{servant['name']}** - Skill {skill_num}",
        color=discord.Color.red()
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
    
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="ce", description="Search for a Craft Essence")
@app_commands.describe(
    query="Craft Essence name or ID (not case-sensitive)",
    region="Game region (NA or JP)"
)
@app_commands.choices(region=[
    app_commands.Choice(name="North America", value="NA"),
    app_commands.Choice(name="Japan", value="JP")
])
async def ce_command(interaction: discord.Interaction, query: str, region: str = "NA"):
    await interaction.response.defer()
    
    ce = await search_ce(query, region)
    
    if not ce:
        await interaction.followup.send(
            f"❌ Could not find Craft Essence: **{query}**\n"
            f"💡 Try using partial names or the ID number!"
        )
        return
    
    embed = discord.Embed(
        title=f"🎴 {ce['name']}",
        description=f"ID: {ce['id']} | Cost: {ce.get('cost', 'N/A')}",
        color=discord.Color.gold()
    )
    
    if "extraAssets" in ce and "equip" in ce["extraAssets"]:
        equip = ce["extraAssets"]["equip"]
        img_url = equip.get("1") or list(equip.values())[0] if equip else None
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
    
    if "profile" in ce and ce["profile"]:
        comments = ce["profile"].get("comments", [])
        for comment in comments:
            if "illustrator" in comment:
                embed.set_footer(text=f"Illustrator: {comment['illustrator']}")
                break
    
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="np", description="Get Noble Phantasm details")
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
    
    servant = await search_servant(servant_name, region)
    if not servant:
        await interaction.followup.send(f"❌ Servant not found: **{servant_name}**")
        return
    
    nps = servant.get("noblePhantasms", [])
    if not nps:
        await interaction.followup.send("❌ No Noble Phantasm found!")
        return
    
    np = nps[0]
    
    embed = discord.Embed(
        title=f"⚔️ {np.get('name', 'Unknown')}",
        description=f"**Rank:** {np.get('rank', '?')} | **Type:** {np.get('card', '').upper()}",
        color=discord.Color.purple()
    )
    
    card_type = np.get("card", "")
    card_emojis = {"buster": "🔴", "arts": "🔵", "quick": "🟢"}
    embed.description = f"{card_emojis.get(card_type, '⚔️')} {embed.description}"
    
    if "functions" in np:
        effects = []
        for func in np["functions"]:
            desc = func.get("popupText", "")
            if desc:
                effects.append(desc)
        if effects:
            embed.add_field(name="Effects", value="\n".join(effects[:8]), inline=False)
    
    if "functions" in np and len(np["functions"]) > 0:
        oc_effects = []
        for func in np["functions"]:
            svals = func.get("svals", [])
            if len(svals) > 1:
                oc_effects.append(f"{func.get('popupText', 'Effect')}: {len(svals)} levels")
        if oc_effects:
            embed.add_field(name="Overcharge", value="\n".join(oc_effects), inline=False)
    
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="help", description="Show bot commands")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="📖 FGO Atlas Bot Commands",
        description="Search Fate/Grand Order data from Atlas Academy",
        color=discord.Color.green()
    )
    
    commands_info = [
        ("`/servant <name/id>`", "Search for servant info (case-insensitive!)"),
        ("`/ce <name/id>`", "Search for Craft Essence"),
        ("`/art <name/id> [type]`", "Display all ascension arts and sprites"),
        ("`/skills <servant>`", "🆕 **NEW:** Show all 3 skills at once with full details"),
        ("`/skill <servant> [1-3]`", "View specific skill (or leave empty for all)"),
        ("`/np <servant>`", "View Noble Phantasm details"),
        ("`/help`", "Show this help message")
    ]
    
    for name, value in commands_info:
        embed.add_field(name=name, value=value, inline=False)
    
    embed.add_field(
        name="🔍 Search Tips",
        value="• **Not case-sensitive**: `gilgamesh`, `GILGAMESH`, `Gil` all work\n"
              "• **Partial names**: `artoria` finds Artoria Pendragon\n"
              "• **Fuzzy matching**: Typos are automatically corrected\n"
              "• **ID numbers**: Use exact ID for precise results",
        inline=False
    )
    
    await interaction.response.send_message(embed=embed)

# Run the bot
import os
TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise ValueError("No DISCORD_TOKEN environment variable found!")

bot.run(TOKEN)
