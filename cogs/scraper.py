import discord
from discord import app_commands
from discord.ext import commands
from utils.scrapers import FandomScraper, GamePressScraper

class ScraperCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.fandom = FandomScraper()
        self.gamepress = GamePressScraper()
    
    @app_commands.command(name="lore", description="Get servant lore and background from Fandom Wiki")
    @app_commands.describe(servant_name="Name of the servant")
    async def lore(self, interaction: discord.Interaction, servant_name: str):
        await interaction.response.defer()
        
        data = await self.fandom.get_servant_lore(servant_name)
        
        if not data:
            await interaction.followup.send(
                f"❌ Could not find lore for '{servant_name}' on Fandom Wiki.\n"
                f"Try the exact name (e.g., 'Artoria Pendragon' instead of 'Saber')."
            )
            return
        
        embed = discord.Embed(
            title=f"{servant_name} - Lore & Background",
            description=data.get('lore', 'No lore available'),
            color=0x9b59b6
        )
        
        if data.get('biography'):
            embed.add_field(
                name="Biography",
                value=data['biography'][:1024],
                inline=False
            )
        
        if data.get('interludes'):
            embed.add_field(
                name="Interludes & Strengthening",
                value="\n".join(data['interludes']),
                inline=False
            )
        
        if data.get('image_url'):
            embed.set_thumbnail(url=data['image_url'])
        
        embed.set_footer(text="Source: Fate/Grand Order Fandom Wiki")
        await interaction.followup.send(embed=embed)
    
    @app_commands.command(name="rating", description="Get GamePress tier list rating and analysis")
    @app_commands.describe(servant_name="Name of the servant")
    async def rating(self, interaction: discord.Interaction, servant_name: str):
        await interaction.response.defer()
        
        data = await self.gamepress.get_servant_rating(servant_name)
        
        if not data:
            await interaction.followup.send(
                f"❌ Could not find rating for '{servant_name}' on GamePress.\n"
                f"Note: GamePress uses specific naming (e.g., 'Gilgamesh' not 'Archer')."
            )
            return
        
        embed = discord.Embed(
            title=f"{servant_name} - GamePress Analysis",
            color=0xe74c3c
        )
        
        if data.get('tier'):
            embed.add_field(name="Tier", value=data['tier'], inline=True)
        
        if data.get('ratings'):
            ratings_text = "\n".join([f"**{k}**: {v}" for k, v in data['ratings'].items()])
            embed.add_field(name="Ratings", value=ratings_text, inline=True)
        
        if data.get('pros'):
            embed.add_field(
                name="✅ Pros",
                value="\n".join([f"• {p}" for p in data['pros']]),
                inline=False
            )
        
        if data.get('cons'):
            embed.add_field(
                name="❌ Cons",
                value="\n".join([f"• {c}" for c in data['cons']]),
                inline=False
            )
        
        if data.get('tips'):
            embed.add_field(
                name="💡 Gameplay Tips",
                value="\n".join([f"• {t}" for t in data['tips']]),
                inline=False
            )
        
        embed.set_footer(text="Source: GamePress.gg | Ratings are subjective")
        await interaction.followup.send(embed=embed)
    
    @app_commands.command(name="events", description="Get current and upcoming FGO events")
    async def events(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        events = await self.fandom.get_events()
        
        if not events:
            await interaction.followup.send("❌ Could not fetch event information.")
            return
        
        embed = discord.Embed(
            title="📅 Current & Upcoming Events",
            description="Latest events from Fandom Wiki",
            color=0x2ecc71
        )
        
        for event in events[:5]:
            embed.add_field(
                name=event['name'],
                value=f"**Duration:** {event['duration']}\n**Type:** {event['type']}",
                inline=False
            )
        
        embed.set_footer(text="Check Fandom Wiki for full details")
        await interaction.followup.send(embed=embed)
    
    @app_commands.command(name="tierlist", description="Show current GamePress tier list overview")
    async def tierlist(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        tiers = await self.gamepress.get_tier_list()
        
        if not tiers:
            await interaction.followup.send("❌ Could not fetch tier list.")
            return
        
        embed = discord.Embed(
            title="🏆 GamePress Tier List Overview",
            description="Top servants in each tier",
            color=0xf1c40f
        )
        
        for tier_data in tiers[:5]:
            servants = ", ".join(tier_data['servants'][:5])
            embed.add_field(
                name=f"Tier {tier_data['tier']}",
                value=servants or "No data",
                inline=False
            )
        
        embed.set_footer(text="Full tier list: grandorder.gamepress.gg/tier-list")
        await interaction.followup.send(embed=embed)
    
    @app_commands.command(name="farm", description="Get farming locations for materials")
    @app_commands.describe(material="Material name (e.g., 'Hero Proof', 'Void Dust')")
    async def farm(self, interaction: discord.Interaction, material: str):
        await interaction.response.defer()
        
        data = await self.gamepress.get_farming_guide(material)
        
        if not data:
            await interaction.followup.send(
                f"❌ Could not find farming data for '{material}'.\n"
                f"Try common names like 'Hero Proof', 'Void Dust', 'Dragon Fang', etc."
            )
            return
        
        embed = discord.Embed(
            title=f"🌾 Farming Guide: {material}",
            description="Best AP-efficient locations",
            color=0x1abc9c
        )
        
        if data.get('locations'):
            embed.add_field(
                name="Recommended Quests",
                value="\n".join(data['locations']),
                inline=False
            )
        
        embed.set_footer(text="Source: GamePress Farming Guide")
        await interaction.followup.send(embed=embed)

async def setup(bot):
    await bot.add_cog(ScraperCog(bot))
