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
    
    # Class triangle and special cases
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
    
    # Add class triangle image description
    if name in ["Saber", "Archer", "Lancer"]:
        embed.add_field(name="Class Triangle", value="Saber > Lancer > Archer > Saber", inline=False)
    
    await interaction.response.send_message(embed=embed)

@app_commands.command(name="banner", description="🎰 Check current/upcoming banners")
async def banner(self, interaction: discord.Interaction):
    """Show current and upcoming rate-up banners (mock data)"""
    # This would ideally be scraped, but we'll use mock data
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
    
    # Simplified EXP calculation
    exp_per_gold = 32400  # One 4★ EXP card
    levels_needed = target_level - current_level
    
    # Rough estimate: higher levels need more EXP
    avg_exp_per_level = 100000 if target_level <= 100 else 200000
    total_exp = levels_needed * avg_exp_per_level
    gold_cards = (total_exp // exp_per_gold) + 1
    
    qp_cost = total_exp * 10  # Rough QP cost
    
    embed = discord.Embed(
        title="📈 EXP Calculator",
        description=f"Level {current_level} → {target_level} ({rarity}★ servant)",
        color=0x9b59b6
    )
    embed.add_field(name="4★ EXP Cards Needed", value=f"~**{gold_cards}** cards", inline=True)
    embed.add_field(name="Approximate QP Cost", value=f"{qp_cost:,}", inline=True)
    embed.add_field(name="Tips", value="Run Ember Gathering daily quests!\n40 AP quest drops ~5-7 gold cards.", inline=False)
    
    await interaction.response.send_message(embed=embed)
