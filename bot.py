import discord
from discord import app_commands
from discord.ext import commands
import aiohttp
import asyncio
from typing import Optional, Dict, List
import json
import re

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

# Search Helpers (keep existing ones and add these)
async def search_servant(query: str, region: str = "NA"):
    """Search for servant by name or ID"""
    if query.isdigit():
        async with bot.session.get(f"{NICE_URL}/{region}/servant/{query}") as resp:
            if resp.status == 200:
                return await resp.json()
    
    async with bot.session.get(f"{BASIC_URL}/{region}/servant") as resp:
        if resp.status == 200:
            servants = await resp.json()
            query_lower = query.lower()
            matches = [s for s in servants if query_lower in s["name"].lower()]
            if matches:
                servant_id = matches[0]["id"]
                async with bot.session.get(f"{NICE_URL}/{region}/servant/{servant_id}") as resp2:
                    if resp2.status == 200:
                        return await resp2.json()
    return None

async def search_ce(query: str, region: str = "NA"):
    """Search for craft essence"""
    if query.isdigit():
        async with bot.session.get(f"{NICE_URL}/{region}/craft-essence/{query}") as resp:
            if resp.status == 200:
                return await resp.json()
    
    async with bot.session.get(f"{BASIC_URL}/{region}/craft-essence") as resp:
        if resp.status == 200:
            ces = await resp.json()
            query_lower = query.lower()
            matches = [c for c in ces if query_lower in c["name"].lower()]
            if matches:
                ce_id = matches[0]["id"]
                async with bot.session.get(f"{NICE_URL}/{region}/craft-essence/{ce_id}") as resp2:
                    if resp2.status == 200:
                        return await resp2.json()
    return None

def get_servant_arts(data: dict) -> dict:
    """Extract all art URLs from servant data"""
    arts = {}
    if "extraAssets" not in data:
        return arts
    
    extra = data["extraAssets"]
    
    # Main character artwork (ascensions)
    if "charaGraph" in extra and "ascension" in extra["charaGraph"]:
        ascension = extra["charaGraph"]["ascension"]
        for key in ["0", "1", "2", "3", "4"]:
            if key in ascension:
                arts[f"Ascension {key}"] = ascension[key]
    
    # Costume/dress arts
    if "charaGraph" in extra and "costume" in extra["charaGraph"]:
        costumes = extra["charaGraph"]["costume"]
        for costume_id, url in costumes.items():
            # Try to get costume name from costumeAssets if available
            costume_name = f"Costume {costume_id}"
            if "costumeAssets" in data and "items" in data["costumeAssets"]:
                for item in data["costumeAssets"]["items"]:
                    if str(item.get("id")) == costume_id:
                        costume_name = item.get("name", f"Costume {costume_id}")
                        break
            arts[costume_name] = url
    
    # Command codes (small sprites)
    if "commands" in extra:
        cmds = extra["commands"]
        if "ascension" in cmds:
            for key, url in cmds["ascension"].items():
                arts[f"Command Card {key}"] = url
    
    # Status screen images
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
    
    # Main CE artwork
    if "equip" in extra:
        equip = extra["equip"]
        if "1" in equip:
            arts["Base Art"] = equip["1"]
        if "2" in equip:
            arts["Max Limit Broken"] = equip["2"]
        # Fallback for any other keys
        for key, url in equip.items():
            if key not in ["1", "2"]:
                arts[f"Art {key}"] = url
    
    # Face/icon
    if "faces" in extra and "equip" in extra["faces"]:
        faces = extra["faces"]["equip"]
        for key, url in faces.items():
            arts[f"Icon {key}"] = url
    
    return arts

# ART COMMAND
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
    
    # Create main embed with summary
    embed = discord.Embed(
        title=title,
        description=description,
        color=color
    )
    
    # Show available art types
    art_types = list(arts.keys())
    embed.add_field(
        name="Available Artwork", 
        value="\n".join([f"• {art}" for art in art_types[:15]]) + 
              (f"\n*...and {len(art_types) - 15} more*" if len(art_types) > 15 else ""),
        inline=False
    )
    
    # Set thumbnail to first available art
    if art_types:
        first_art = arts[art_types[0]]
        embed.set_image(url=first_art)
    
    await interaction.followup.send(embed=embed)
    
    # Send additional embeds for each major art piece (Discord allows up to 10 images per message technically, 
    # but we'll send separate messages to avoid cluttering)
    main_arts = {k: v for k, v in arts.items() if "Command" not in k and "Icon" not in k and "Status" not in k}
    
    if len(main_arts) > 1:
        # Group by 4 images per message
        art_items = list(main_arts.items())
        for i in range(1, len(art_items), 4):  # Skip first one (already shown)
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
                await asyncio.sleep(0.5)  # Rate limit protection
    
    # Show sprites/command cards in a separate summary if available
    sprite_arts = {k: v for k, v in arts.items() if any(x in k for x in ["Command", "Icon", "Face"])}
    if sprite_arts:
        sprite_embed = discord.Embed(
            title="🎭 Sprites & Icons",
            color=discord.Color.greyple()
        )
        # Show first 4 sprites
        for art_name, art_url in list(sprite_arts.items())[:4]:
            sprite_embed.add_field(name=art_name, value=f"[View]({art_url})", inline=True)
        
        if len(sprite_arts) > 4:
            sprite_embed.set_footer(text=f"+ {len(sprite_arts) - 4} more sprites available")
        
        await interaction.channel.send(embed=sprite_embed)

# Existing commands (servant, ce, skill, np, help) - keep these from previous code
@bot.tree.command(name="servant", description="Search for a Servant by name or ID")
@app_commands.describe(
    query="Servant name or ID number",
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
        await interaction.followup.send(f"❌ Could not find servant: **{query}**")
        return
    
    embed = discord.Embed(
        title=f"⭐ {servant['name']}",
        description=servant.get("className", "Unknown Class"),
        color=discord.Color.blue()
    )
    
    # Add image (first ascension art)
    if "extraAssets" in servant and "charaGraph" in servant["extraAssets"]:
        chara = servant["extraAssets"]["charaGraph"]
        if "ascension" in chara:
            asc = chara["ascension"]
            # Prefer ascension 1 or 0
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
    
    if "skills" in servant and servant["skills"]:
        skill_text = ""
        for skill in servant["skills"][:3]:
            skill_name = skill.get("name", "Unknown")
            skill_text += f"• {skill_name}\n"
        if skill_text:
            embed.add_field(name="Skills", value=skill_text[:1024], inline=False)
    
    if "noblePhantasms" in servant and servant["noblePhantasms"]:
        np = servant["noblePhantasms"][0]
        np_name = np.get("name", "Unknown")
        np_card = np.get("card", "").upper()
        embed.add_field(name="Noble Phantasm", value=f"[{np_card}] {np_name}", inline=False)
    
    if "traits" in servant and servant["traits"]:
        traits = ", ".join([t.get("name", "") for t in servant["traits"][:5]])
        embed.set_footer(text=f"Traits: {traits}")
    
    # Add hint about art command
    embed.add_field(name="🎨 Artwork", value="Use `/art` to see all ascension arts!", inline=False)
    
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="ce", description="Search for a Craft Essence")
@app_commands.describe(
    query="Craft Essence name or ID",
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
        await interaction.followup.send(f"❌ Could not find Craft Essence: **{query}**")
        return
    
    embed = discord.Embed(
        title=f"🎴 {ce['name']}",
        description=f"ID: {ce['id']} | Cost: {ce.get('cost', 'N/A')}",
        color=discord.Color.gold()
    )
    
    # Add CE image
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

@bot.tree.command(name="skill", description="Get detailed skill information")
@app_commands.describe(
    servant_name="Name of the servant",
    skill_num="Skill number (1, 2, or 3)",
    region="Game region"
)
@app_commands.choices(region=[
    app_commands.Choice(name="North America", value="NA"),
    app_commands.Choice(name="Japan", value="JP")
])
async def skill_command(interaction: discord.Interaction, servant_name: str, skill_num: int, region: str = "NA"):
    if skill_num not in [1, 2, 3]:
        await interaction.response.send_message("❌ Skill number must be 1, 2, or 3!", ephemeral=True)
        return
    
    await interaction.response.defer()
    
    servant = await search_servant(servant_name, region)
    if not servant:
        await interaction.followup.send(f"❌ Servant not found: **{servant_name}**")
        return
    
    skills = [s for s in servant.get("skills", []) if s.get("num") == skill_num]
    if not skills:
        await interaction.followup.send("❌ Skill not found!")
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
        embed.add_field(name="Cooldown", value=f"{cd[0]}/{cd[-1]}", inline=True)
    
    if "functions" in skill:
        effects = []
        for func in skill["functions"]:
            popup = func.get("popupText", "")
            if popup:
                effects.append(f"• {popup}")
        if effects:
            embed.add_field(name="Effects", value="\n".join(effects[:10]), inline=False)
    
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="np", description="Get Noble Phantasm details")
@app_commands.describe(
    servant_name="Servant name",
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
        ("`/servant <name/id>`", "Search for servant information, stats, and skills"),
        ("`/ce <name/id>`", "Search for Craft Essence details"),
        ("`/art <name/id> [type]`", "🎨 **NEW:** Display all ascension arts, costumes, and sprites"),
        ("`/skill <servant> <1-3>`", "Get detailed skill information"),
        ("`/np <servant>`", "View Noble Phantasm details"),
        ("`/help`", "Show this help message")
    ]
    
    for name, value in commands_info:
        embed.add_field(name=name, value=value, inline=False)
    
    embed.add_field(
        name="🎨 Art Command Tips",
        value="• Shows all 4 ascension stages\n"
              "• Includes costume/dress arts if available\n"
              "• Shows CE base and Max Limit Broken art\n"
              "• Displays command card sprites",
        inline=False
    )
    
    await interaction.response.send_message(embed=embed)

# Run the bot
import os
TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise ValueError("No DISCORD_TOKEN environment variable found!")

bot.run(TOKEN)