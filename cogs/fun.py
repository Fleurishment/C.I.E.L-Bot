import discord
from discord import app_commands
from discord.ext import commands
import aiohttp
import random
import datetime
import textwrap

class FunCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="joke", description="😂 Get a random joke")
    async def joke(self, interaction: discord.Interaction):
        """Fetch a random joke"""
        await interaction.response.defer()
        
        try:
            # Official Joke API
            async with aiohttp.ClientSession() as session:
                async with session.get("https://official-joke-api.appspot.com/random_joke") as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        embed = discord.Embed(
                            title="😂 Random Joke",
                            description=f"**{data['setup']}**\n\n||{data['punchline']}||",
                            color=0xffd700
                        )
                        await interaction.followup.send(embed=embed)
                    else:
                        # Fallback jokes if API fails
                        fallback_jokes = [
                            ("Why don't scientists trust atoms?", "Because they make up everything!"),
                            ("What do you call a fake noodle?", "An impasta!"),
                            ("Why did the scarecrow win an award?", "He was outstanding in his field!")
                        ]
                        setup, punchline = random.choice(fallback_jokes)
                        embed = discord.Embed(
                            title="😂 Joke (Offline Mode)",
                            description=f"**{setup}**\n\n||{punchline}||",
                            color=0xffd700
                        )
                        await interaction.followup.send(embed=embed)
        except Exception as e:
            await interaction.followup.send("❌ Couldn't fetch a joke right now!")
    
    @app_commands.command(name="coinflip", description="🪙 Flip a coin")
    @app_commands.describe(bet="Heads or Tails?")
    @app_commands.choices(bet=[
        app_commands.Choice(name="Heads", value="heads"),
        app_commands.Choice(name="Tails", value="tails")
    ])
    async def coinflip(self, interaction: discord.Interaction, bet: app_commands.Choice[str] = None):
        """Flip a coin"""
        result = random.choice(["Heads", "Tails"])
        bet_value = bet.value if isinstance(bet, app_commands.Choice) else None
        
        embed = discord.Embed(
            title="🪙 Coin Flip",
            description=f"**{result}**",
            color=0xc0c0c0 if result == "Heads" else 0xffd700
        )
        
        if bet_value:
            won = bet_value.lower() == result.lower()
            embed.add_field(
                name="Your Bet",
                value=f"{'✅ You won!' if won else '❌ You lost!'}",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="roll", description="🎲 Roll dice")
    @app_commands.describe(sides="Number of sides (default 6)", amount="How many dice (max 10)")
    async def roll(self, interaction: discord.Interaction, sides: int = 6, amount: int = 1):
        """Roll dice"""
        if sides < 2 or sides > 100:
            await interaction.response.send_message("❌ Sides must be between 2-100!", ephemeral=True)
            return
        
        if amount < 1 or amount > 10:
            await interaction.response.send_message("❌ Can only roll 1-10 dice at once!", ephemeral=True)
            return
        
        results = [random.randint(1, sides) for _ in range(amount)]
        total = sum(results)
        
        if amount == 1:
            embed = discord.Embed(
                title="🎲 Dice Roll",
                description=f"Rolled a **{results[0]}** (d{sides})",
                color=0xe74c3c
            )
        else:
            embed = discord.Embed(
                title=f"🎲 Rolling {amount}d{sides}",
                description=f"**Results:** {', '.join(map(str, results))}\n**Total:** {total}",
                color=0xe74c3c
            )
            
            # Check for crits (max rolls)
            crits = results.count(sides)
            if crits > 0:
                embed.add_field(name="🔥 Critical!", value=f"Rolled max value {crits} time(s)!", inline=False)
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="8ball", description="🎱 Ask the Magic 8-Ball")
    @app_commands.describe(question="What do you want to ask?")
    async def eightball(self, interaction: discord.Interaction, question: str):
        """Magic 8-ball"""
        responses = [
            "It is certain.", "It is decidedly so.", "Without a doubt.",
            "Yes definitely.", "You may rely on it.", "As I see it, yes.",
            "Most likely.", "Outlook good.", "Yes.", "Signs point to yes.",
            "Reply hazy, try again.", "Ask again later.", "Better not tell you now.",
            "Cannot predict now.", "Concentrate and ask again.",
            "Don't count on it.", "My reply is no.", "My sources say no.",
            "Outlook not so good.", "Very doubtful."
        ]
        
        embed = discord.Embed(
            title="🎱 Magic 8-Ball",
            color=0x2c3e50
        )
        embed.add_field(name="Question", value=question, inline=False)
        embed.add_field(name="Answer", value=f"**{random.choice(responses)}**", inline=False)
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="choose", description="🤔 Let the bot choose for you")
    @app_commands.describe(options="Separate options with commas (e.g., 'pizza, sushi, burger')")
    async def choose(self, interaction: discord.Interaction, options: str):
        """Choose between options"""
        choices = [opt.strip() for opt in options.split(",") if opt.strip()]
        
        if len(choices) < 2:
            await interaction.response.send_message("❌ Give me at least 2 options separated by commas!", ephemeral=True)
            return
        
        chosen = random.choice(choices)
        
        embed = discord.Embed(
            title="🤔 The Bot Has Spoken",
            description=f"I choose: **{chosen}**",
            color=0x9b59b6
        )
        embed.add_field(name="Options were", value="\n".join([f"• {c}" for c in choices]), inline=False)
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="fact", description="🧠 Get a random useless fact")
    async def fact(self, interaction: discord.Interaction):
        """Random useless fact"""
        await interaction.response.defer()
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get("https://uselessfacts.jsph.pl/random.json?language=en") as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        embed = discord.Embed(
                            title="🧠 Useless Fact",
                            description=data['text'],
                            color=0x3498db
                        )
                        await interaction.followup.send(embed=embed)
                    else:
                        raise Exception("API failed")
        except:
            # Fallback facts
            facts = [
                "Octopuses have three hearts.",
                "Bananas are berries, but strawberries aren't.",
                "A group of flamingos is called a 'flamboyance'.",
                "Wombat poop is cube-shaped.",
                "Honey never spoils.",
                "Sloths can hold their breath longer than dolphins can."
            ]
            embed = discord.Embed(
                title="🧠 Random Fact",
                description=random.choice(facts),
                color=0x3498db
            )
            await interaction.followup.send(embed=embed)
    
    @app_commands.command(name="owoify", description="🐱 UwU-fy your text")
    @app_commands.describe(text="Text to transform", intensity="How much uwu (1-3)")
    async def owoify(self, interaction: discord.Interaction, text: str, intensity: int = 2):
        """Transform text to uwu speak"""
        if intensity < 1 or intensity > 3:
            await interaction.response.send_message("❌ Intensity must be 1-3!", ephemeral=True)
            return
        
        # Transformations
        result = text
        
        if intensity >= 1:
            result = result.replace("r", "w").replace("R", "W")
            result = result.replace("l", "w").replace("L", "W")
        
        if intensity >= 2:
            result = result.replace("n", "ny").replace("N", "Ny")
            result = result.replace("th", "d").replace("Th", "D")
            result = result.replace("ove", "uv")
        
        if intensity >= 3:
            result = result.replace("!", "!!! UwU")
            result = result.replace("?", "? OwO")
            faces = [" (・`ω´・)", " uwu", " owo", " >w<", " ^w^"]
            result += random.choice(faces)
        
        embed = discord.Embed(
            title="🐱 UwU Translator",
            description=f"**Original:** {text[:200]}\n\n**Result:** {result[:500]}",
            color=0xff69b4
        )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="reverse", description="🔃 Reverse text")
    @app_commands.describe(text="Text to reverse")
    async def reverse(self, interaction: discord.Interaction, text: str):
        """Reverse text"""
        reversed_text = text[::-1]
        embed = discord.Embed(
            title="🔃 Reversed",
            description=f"**{reversed_text}**",
            color=0x95a5a6
        )
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="mock", description="🦆 sPoNgEbOb MoCkInG tExT")
    @app_commands.describe(text="Text to mock")
    async def mock(self, interaction: discord.Interaction, text: str):
        """SpongeBob mocking text"""
        mocked = ""
        for i, char in enumerate(text):
            if i % 2 == 0:
                mocked += char.upper()
            else:
                mocked += char.lower()
        
        embed = discord.Embed(
            description=f"🦆 {mocked}",
            color=0xffd700
        )
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="time", description="🕐 Current time in different timezones")
    @app_commands.describe(timezone="Timezone (UTC, JST, EST, PST, etc.)")
    async def time_cmd(self, interaction: discord.Interaction, timezone: str = "UTC"):
        """Show current time"""
        tz_offsets = {
            "UTC": 0, "GMT": 0,
            "JST": 9, "JP": 9, "Tokyo": 9,
            "EST": -5, "EDT": -4,
            "PST": -8, "PDT": -7,
            "CET": 1, "CEST": 2
        }
        
        offset = tz_offsets.get(timezone.upper(), 0)
        current_time = datetime.datetime.utcnow() + datetime.timedelta(hours=offset)
        
        embed = discord.Embed(
            title=f"🕐 Current Time ({timezone.upper()})",
            description=current_time.strftime("%Y-%m-%d %H:%M:%S"),
            color=0x2ecc71
        )
        
        # Add other major cities
        other_times = []
        for tz, off in [("JST", 9), ("UTC", 0), ("EST", -5)]:
            if tz != timezone.upper():
                t = datetime.datetime.utcnow() + datetime.timedelta(hours=off)
                other_times.append(f"{tz}: {t.strftime('%H:%M')}")
        
        embed.add_field(name="Other Zones", value=" | ".join(other_times), inline=False)
        
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(FunCog(bot))
