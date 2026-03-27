import discord
from discord import app_commands
from discord.ext import commands
import random
import asyncio

class CalculatorCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.api = None
    
    async def cog_load(self):
        from utils.atlas_api import AtlasAPI
        self.api = AtlasAPI(self.bot.session if hasattr(self.bot, 'session') else None)
    
    @app_commands.command(name="gacha", description="🎲 Roll the gacha!")
    @app_commands.describe(banner="Choose your banner type")
    @app_commands.choices(banner=[
        app_commands.Choice(name="Story Banner", value="story"),
        app_commands.Choice(name="Rate-Up SSR", value="rateup_ssr"),
        app_commands.Choice(name="Rate-Up SR", value="rateup_sr")
    ])
    async def gacha(self, interaction: discord.Interaction, banner: app_commands.Choice[str] = "story", quartz: int = 30):
        """Fun gacha simulator"""
        await interaction.response.defer()
        
        rates = {
            "story": {"SSR": 0.01, "SR": 0.03, "R": 0.40},
            "rateup_ssr": {"SSR": 0.008, "SR": 0.03, "R": 0.40},  # 0.8% for rate-up
            "rateup_sr": {"SSR": 0.01, "SR": 0.024, "R": 0.40}     # 2.4% for rate-up SR
        }
        
        banner_type = banner.value if isinstance(banner, app_commands.Choice) else banner
        current_rates = rates.get(banner_type, rates["story"])
        
        rolls = min(quartz // 3, 100)  # Max 100 rolls (300 SQ)
        
        results = {"SSR": 0, "SR": 0, "R": 0, "CE_SSR": 0, "CE_SR": 0, "CE_R": 0}
        roll_history = []
        
        # Featured servants (mock data for fun)
        featured_ssr = ["Space Ishtar", "Gilgamesh", "Kama", "Morgan", "Oberon"]
        featured_sr = ["Ishtar", "Ereshkigal", "Gawain", "Lancelot"]
        
        for i in range(rolls):
            roll = random.random()
            
            if roll < current_rates["SSR"]:
                servant = random.choice(featured_ssr) if banner_type == "rateup_ssr" and random.random() < 0.7 else "Random SSR"
                results["SSR"] += 1
                roll_history.append(f"⭐⭐⭐⭐⭐ **{servant}**")
            elif roll < current_rates["SSR"] + current_rates["SR"]:
                servant = random.choice(featured_sr) if banner_type == "rateup_sr" and random.random() < 0.7 else "Random SR"
                results["SR"] += 1
                roll_history.append(f"⭐⭐⭐⭐ {servant}")
            elif roll < current_rates["SSR"] + current_rates["SR"] + current_rates["R"]:
                results["R"] += 1
            else:
                # CE roll
                ce_roll = random.random()
                if ce_roll < 0.04:
                    results["CE_SSR"] += 1
                elif ce_roll < 0.12:
                    results["CE_SR"] += 1
                else:
                    results["CE_R"] += 1
        
        # Create embed
        embed = discord.Embed(
            title=f"🎲 Gacha Results ({rolls} rolls)",
            description=f"Banner: {banner_type.replace('_', ' ').title()}",
            color=0xffd700 if results["SSR"] > 0 else 0x3498db
        )
        
        embed.add_field(name="⭐⭐⭐⭐⭐ SSR Servants", value=results["SSR"], inline=True)
        embed.add_field(name="⭐⭐⭐⭐ SR Servants", value=results["SR"], inline=True)
        embed.add_field(name="⭐⭐⭐ R Servants", value=results["R"], inline=True)
        embed.add_field(name="🎴 SSR CEs", value=results["CE_SSR"], inline=True)
        embed.add_field(name="🎴 SR CEs", value=results["CE_SR"], inline=True)
        embed.add_field(name="🎴 R CEs", value=results["CE_R"], inline=True)
        
        if roll_history:
            recent = "\n".join(roll_history[-5:])  # Last 5 notable rolls
            embed.add_field(name="Recent Notable Rolls", value=recent, inline=False)
        
        # Pity check
        if results["SSR"] == 0 and rolls >= 30:
            embed.set_footer(text="😢 No SSRs? Maybe next time... (Pity system at 330 rolls)")
        elif results["SSR"] >= 2:
            embed.set_footer(text="🎉 Jackpot! Great rolls!")
        else:
            embed.set_footer(text=f"SQ Used: {rolls * 3} | Remaining: {quartz - (rolls * 3)}")
        
        await interaction.followup.send(embed=embed)
    
    @app_commands.command(name="sqcalc", description="📊 Calculate Saint Quartz needed")
    @app_commands.describe(
        target_np="Target NP level (1-5)",
        current_quartz="How many SQ you currently have",
        summon_tickets="How many summon tickets you have"
    )
    async def sqcalc(self, interaction: discord.Interaction, target_np: int = 1, current_quartz: int = 0, summon_tickets: int = 0):
        """Calculate Saint Quartz needed for NP targets"""
        
        # Average stats
        avg_rolls_per_ssr = 143  # 1% rate with soft pity
        np_requirements = {1: 1, 2: 2, 3: 3, 4: 5, 5: 8}  # Copies needed
        
        copies_needed = np_requirements.get(target_np, 1)
        expected_rolls = copies_needed * avg_rolls_per_ssr
        
        # Convert to SQ (3 SQ per roll, tickets = 3 SQ each)
        sq_needed = (expected_rolls * 3) - current_quartz - (summon_tickets * 3)
        rolls_possible = (current_quartz // 3) + summon_tickets
        
        embed = discord.Embed(
            title="📊 Saint Quartz Calculator",
            color=0x9b59b6
        )
        
        embed.add_field(
            name="Target",
            value=f"NP{target_np} ({copies_needed} copy/copies)",
            inline=True
        )
        embed.add_field(
            name="Expected Rolls",
            value=f"~{expected_rolls} rolls",
            inline=True
        )
        embed.add_field(
            name="Your Resources",
            value=f"{current_quartz} SQ + {summon_tickets} tickets\n= {rolls_possible} rolls",
            inline=True
        )
        
        if sq_needed > 0:
            # Daily login + missions
            days_to_save = sq_needed // 3  # Rough estimate
            embed.add_field(
                name="You Need",
                value=f"**{sq_needed}** more SQ (~{days_to_save} days of saving)",
                inline=False
            )
            embed.color = 0xe74c3c
        else:
            embed.add_field(
                name="Status",
                value="✅ You have enough! Good luck on your rolls!",
                inline=False
            )
            embed.color = 0x2ecc71
        
        embed.set_footer(text="Note: This is based on average rates (1% SSR). Your luck may vary!")
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="compare", description="⚔️ Compare two servants")
    @app_commands.describe(
        servant1="First servant",
        servant2="Second servant",
        region="Game region"
    )
    async def compare(self, interaction: discord.Interaction, servant1: str, servant2: str, region: app_commands.Choice[str] = "NA"):
        """Compare two servants side by side"""
        await interaction.response.defer()
        
        region_code = region.value if isinstance(region, app_commands.Choice) else region
        
        # Search for both
        results1 = await self.api.search_servant(servant1, region_code)
        results2 = await self.api.search_servant(servant2, region_code)
        
        if not results1 or not results2:
            await interaction.followup.send("❌ Could not find one or both servants.")
            return
        
        # Get first match for each
        data1 = await self.api.get_servant_details(results1[0]['id'], region_code)
        data2 = await self.api.get_servant_details(results2[0]['id'], region_code)
        
        if not data1 or not data2:
            await interaction.followup.send("❌ Error fetching servant data.")
            return
        
        embed = discord.Embed(
            title="⚔️ Servant Comparison",
            color=0x3498db
        )
        
        # Stats comparison
        stats1 = data1.get('atkGrowth', [0])
        stats2 = data2.get('atkGrowth', [0])
        hp1 = data1.get('hpGrowth', [0])
        hp2 = data2.get('hpGrowth', [0])
        
        embed.add_field(
            name=f"🅰️ {data1['name']} [{data1['rarity']}★]",
            value=f"Class: {data1['className']}\nATK: {stats1[-1]:,}\nHP: {hp1[-1]:,}\nNP: {data1.get('noblePhantasms', [{}])[0].get('name', 'N/A')[:20]}...",
            inline=True
        )
        
        embed.add_field(
            name=f"🅱️ {data2['name']} [{data2['rarity']}★]",
            value=f"Class: {data2['className']}\nATK: {stats2[-1]:,}\nHP: {hp2[-1]:,}\nNP: {data2.get('noblePhantasms', [{}])[0].get('name', 'N/A')[:20]}...",
            inline=True
        )
        
        # Winner by ATK
        winner = "Tie"
        if stats1[-1] > stats2[-1]:
            winner = data1['name']
        elif stats2[-1] > stats1[-1]:
            winner = data2['name']
        
        embed.add_field(name="🏆 ATK Winner", value=winner, inline=False)
        
        await interaction.followup.send(embed=embed)

async def setup(bot):
    await bot.add_cog(CalculatorCog(bot))
