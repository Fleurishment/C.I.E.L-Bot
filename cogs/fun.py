import discord
from discord import app_commands
from discord.ext import commands
import aiohttp
import random
import datetime
import asyncio

class MemeView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=60)

    async def fetch_meme(self):
        url = "https://meme-api.com/gimme"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers={"User-Agent": "DiscordBot"}) as resp:
                if resp.status != 200:
                    return None
                return await resp.json()

    async def update(self, interaction: discord.Interaction):
        data = await self.fetch_meme()

        if not data:
            await interaction.followup.send("❌ Failed to fetch meme!", ephemeral=True)
            return

        if data.get("nsfw") and not interaction.channel.is_nsfw():
            await interaction.followup.send("⚠️ NSFW meme blocked.", ephemeral=True)
            return

        embed = discord.Embed(
            title=data["title"],
            url=data.get("postLink"),
            color=0xff9900
        )
        embed.set_image(url=data["url"])
        embed.set_footer(
            text=f"👍 {data.get('ups', 0)} | 💬 {data.get('num_comments', 0)} | r/{data.get('subreddit', 'unknown')}"
        )

        await interaction.followup.edit_message(interaction.message.id, embed=embed, view=self)

    @discord.ui.button(label="Next Meme ⏭️", style=discord.ButtonStyle.primary)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        await self.update(interaction)

    @discord.ui.button(label="Refresh 🔄", style=discord.ButtonStyle.secondary)
    async def refresh_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        await self.update(interaction)

class FunCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="joke", description="😂 Get a random joke")
    async def joke(self, interaction: discord.Interaction):
        """Fetch a random joke"""
        await interaction.response.defer()
        
        try:
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
                        raise Exception("API failed")
        except:
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
        
        emojis = {"Heads": "🪙", "Tails": "🪙"}
        
        if bet_value:
            won = bet_value.lower() == result.lower()
            color = 0x2ecc71 if won else 0xe74c3c
            result_text = f"{'✅ You won!' if won else '❌ You lost!'}"
        else:
            color = 0xffd700
            result_text = "🎲 Flip again?"
        
        embed = discord.Embed(
            title=f"{emojis[result]} Coin Flip: {result}",
            description=result_text,
            color=color
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
        
        other_times = []
        for tz, off in [("JST", 9), ("UTC", 0), ("EST", -5)]:
            if tz != timezone.upper():
                t = datetime.datetime.utcnow() + datetime.timedelta(hours=off)
                other_times.append(f"{tz}: {t.strftime('%H:%M')}")
        
        embed.add_field(name="Other Zones", value=" | ".join(other_times), inline=False)
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="rps", description="✊ Rock Paper Scissors")
    @app_commands.describe(choice="Your choice")
    @app_commands.choices(choice=[
        app_commands.Choice(name="Rock ✊", value="rock"),
        app_commands.Choice(name="Paper ✋", value="paper"),
        app_commands.Choice(name="Scissors ✌️", value="scissors")
    ])
    async def rps(self, interaction: discord.Interaction, choice: app_commands.Choice[str]):
        """Play Rock Paper Scissors"""
        user_choice = choice.value
        bot_choice = random.choice(["rock", "paper", "scissors"])
        
        emojis = {"rock": "✊", "paper": "✋", "scissors": "✌️"}
        
        if user_choice == bot_choice:
            result = "It's a tie!"
            color = 0x95a5a6
        elif (user_choice == "rock" and bot_choice == "scissors") or \
             (user_choice == "paper" and bot_choice == "rock") or \
             (user_choice == "scissors" and bot_choice == "paper"):
            result = "You win! 🎉"
            color = 0x2ecc71
        else:
            result = "You lose! 😢"
            color = 0xe74c3c
        
        embed = discord.Embed(
            title="✊ Rock Paper Scissors",
            color=color
        )
        embed.add_field(name="You", value=f"{emojis[user_choice]} {user_choice.title()}", inline=True)
        embed.add_field(name="Bot", value=f"{emojis[bot_choice]} {bot_choice.title()}", inline=True)
        embed.add_field(name="Result", value=result, inline=False)
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="rate", description="📊 Rate something 1-10")
    @app_commands.describe(thing="What to rate")
    async def rate(self, interaction: discord.Interaction, thing: str):
        """Rate anything"""
        rating = random.randint(1, 10)
        
        comments = {
            10: "Perfect! Absolutely flawless! ⭐",
            9: "Excellent! Nearly perfect! ✨",
            8: "Great! Very impressive! 👍",
            7: "Good! Above average! 😊",
            6: "Decent. Not bad, not great. 🤔",
            5: "Average. Right in the middle. 😐",
            4: "Below average. Could be better. 😕",
            3: "Poor. Needs improvement. 😬",
            2: "Bad. Very disappointing. 😞",
            1: "Terrible. Absolutely awful. 💀"
        }
        
        embed = discord.Embed(
            title="📊 Rating",
            description=f"I rate **{thing}** a **{rating}/10**",
            color=0x3498db
        )
        embed.add_field(name="Verdict", value=comments[rating], inline=False)
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="ship", description="💕 Ship two users")
    @app_commands.describe(user1="First user", user2="Second user")
    async def ship(self, interaction: discord.Interaction, user1: discord.Member, user2: discord.Member = None):
        """Calculate compatibility"""
        if user2 is None:
            user2 = interaction.user
        
        combined = str(user1.id) + str(user2.id)
        random.seed(combined)
        percentage = random.randint(0, 100)
        random.seed()
        
        name1 = user1.display_name[:len(user1.display_name)//2]
        name2 = user2.display_name[len(user2.display_name)//2:]
        ship_name = name1 + name2
        
        if percentage >= 90:
            comment = "💕 Soulmates! A match made in heaven!"
            color = 0xff69b4
        elif percentage >= 70:
            comment = "❤️ Great match! Very compatible!"
            color = 0xe74c3c
        elif percentage >= 50:
            comment = "💛 Decent match. Worth a shot!"
            color = 0xf1c40f
        elif percentage >= 30:
            comment = "💙 Could work... with effort."
            color = 0x3498db
        else:
            comment = "💔 Not meant to be... sorry."
            color = 0x95a5a6
        
        embed = discord.Embed(
            title="💕 Compatibility Check",
            description=f"**{user1.display_name}** 💞 **{user2.display_name}**",
            color=color
        )
        embed.add_field(name="Compatibility", value=f"**{percentage}%**", inline=True)
        embed.add_field(name="Ship Name", value=f"*{ship_name}*", inline=True)
        embed.add_field(name="Verdict", value=comment, inline=False)
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="quote", description="💬 Save a memorable quote")
    @app_commands.describe(quote="The quote to save", author="Who said it")
    async def save_quote(self, interaction: discord.Interaction, quote: str, author: str = None):
        """Save a quote"""
        if not hasattr(self.bot, 'quotes'):
            self.bot.quotes = []
        
        self.bot.quotes.append({
            'quote': quote,
            'author': author or "Unknown",
            'saved_by': interaction.user.display_name,
            'time': datetime.datetime.now().strftime("%Y-%m-%d")
        })
        
        embed = discord.Embed(
            title="💬 Quote Saved",
            description=f"\"*{quote}*\"",
            color=0x9b59b6
        )
        if author:
            embed.add_field(name="Author", value=f"- {author}", inline=False)
        embed.set_footer(text=f"Saved by {interaction.user.display_name}")
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="quotes", description="📜 View saved quotes")
    async def view_quotes(self, interaction: discord.Interaction):
        """View all saved quotes"""
        if not hasattr(self.bot, 'quotes') or len(self.bot.quotes) == 0:
            await interaction.response.send_message("📭 No quotes saved yet! Use `/quote` to add one.", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="📜 Saved Quotes",
            color=0x9b59b6
        )
        
        for i, q in enumerate(self.bot.quotes[-5:], 1):
            text = f"\"{q['quote'][:100]}...\"\n— {q['author']} | Saved by {q['saved_by']}"
            embed.add_field(name=f"Quote #{i}", value=text, inline=False)
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="countdown", description="⏰ Set a countdown")
    @app_commands.describe(seconds="Seconds to count down", message="What to countdown to")
    async def countdown(self, interaction: discord.Interaction, seconds: int, message: str = "Time's up!"):
        """Simple countdown timer"""
        if seconds < 1 or seconds > 300:
            await interaction.response.send_message("❌ Please choose between 1-300 seconds (5 minutes max)!", ephemeral=True)
            return
        
        await interaction.response.send_message(f"⏰ Countdown started: **{seconds}** seconds until \"{message}\"")
        
        await asyncio.sleep(seconds)
        
        try:
            await interaction.followup.send(f"⏰ **{message}**")
        except:
            await interaction.channel.send(f"⏰ **{message}**")
    
    @app_commands.command(name="meme", description="😂 Get a random meme")
    async def meme(self, interaction: discord.Interaction):
        await interaction.response.defer()

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get("https://meme-api.com/gimme", headers={"User-Agent": "DiscordBot"}) as resp:
                    if resp.status != 200:
                        raise Exception("API failed")

                    data = await resp.json()

                    if data.get("nsfw") and not interaction.channel.is_nsfw():
                        await interaction.followup.send("⚠️ NSFW meme blocked in this channel.")
                        return

                    embed = discord.Embed(
                        title=data["title"],
                        url=data.get("postLink"),
                        color=0xff9900
                    )
                    embed.set_image(url=data["url"])
                    embed.set_footer(
                        text=f"👍 {data.get('ups', 0)} | 💬 {data.get('num_comments', 0)} | r/{data.get('subreddit', 'unknown')}"
                    )

                    await interaction.followup.send(embed=embed, view=MemeView())

        except Exception as e:
            await interaction.followup.send("❌ Couldn't fetch a meme right now!")
    
    @app_commands.command(name="weather", description="🌤️ Check the weather (fake)")
    @app_commands.describe(city="City name")
    async def weather(self, interaction: discord.Interaction, city: str):
        """Fake weather report"""
        conditions = ["Sunny ☀️", "Cloudy ☁️", "Rainy 🌧️", "Stormy ⛈️", "Snowy ❄️", "Windy 💨", "Foggy 🌫️"]
        temp = random.randint(-10, 40)
        condition = random.choice(conditions)
        
        embed = discord.Embed(
            title=f"🌤️ Weather in {city.title()}",
            description=f"**{temp}°C** | {condition}",
            color=0x3498db
        )
        
        if temp > 30:
            embed.add_field(name="Advice", value="🔥 It's hot! Stay hydrated!", inline=False)
        elif temp < 0:
            embed.add_field(name="Advice", value="❄️ Freezing! Wear a jacket!", inline=False)
        elif "Rain" in condition:
            embed.add_field(name="Advice", value="☂️ Don't forget your umbrella!", inline=False)
        
        embed.set_footer(text="Disclaimer: This is randomly generated for fun!")
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="remind", description="🔔 Set a reminder")
    @app_commands.describe(minutes="Minutes from now", reminder="What to remind you about")
    async def remind(self, interaction: discord.Interaction, minutes: int, reminder: str):
        """Set a reminder"""
        if minutes < 1 or minutes > 1440:
            await interaction.response.send_message("❌ Please set a time between 1 minute and 24 hours!", ephemeral=True)
            return
        
        await interaction.response.send_message(f"🔔 Reminder set for **{minutes}** minute(s): \"{reminder}\"")
        
        await asyncio.sleep(minutes * 60)
        
        try:
            await interaction.user.send(f"🔔 Reminder: **{reminder}**")
        except:
            await interaction.channel.send(f"🔔 {interaction.user.mention} Reminder: **{reminder}**")
    
    @app_commands.command(name="ascii", description="📝 ASCII art text")
    @app_commands.describe(text="Text to convert (max 10 chars)")
    async def ascii_art(self, interaction: discord.Interaction, text: str):
        """Simple block letter ASCII art"""
        if len(text) > 10:
            await interaction.response.send_message("❌ Max 10 characters!", ephemeral=True)
            return
        
        letters = {
            'A': [" ██  ", "████ ", "██ ██", "████ ", "██ ██"],
            'B': ["████ ", "██ ██", "████ ", "██ ██", "████ "],
            'C': [" ████", "██   ", "██   ", "██   ", " ████"],
            'D': ["████ ", "██ ██", "██ ██", "██ ██", "████ "],
            'E': ["█████", "██   ", "████ ", "██   ", "█████"],
            'F': ["█████", "██   ", "████ ", "██   ", "██   "],
            'G': [" ████", "██   ", "██ ██", "██ ██", " ████"],
            'H': ["██ ██", "██ ██", "█████", "██ ██", "██ ██"],
            'I': ["█████", "  ██  ", "  ██  ", "  ██  ", "█████"],
            'J': ["█████", "   ██ ", "   ██ ", "██ ██ ", " ███  "],
            'K': ["██ ██", "███  ", "████ ", "███  ", "██ ██"],
            'L': ["██   ", "██   ", "██   ", "██   ", "█████"],
            'M': ["██   ██", "███ ███", "███████", "██ █ ██", "██   ██"],
            'N': ["██  ██", "███ ██", "██████", "██ ███", "██  ██"],
            'O': [" ████ ", "██  ██", "██  ██", "██  ██", " ████ "],
            'P': ["████ ", "██ ██", "████ ", "██   ", "██   "],
            'Q': [" ████ ", "██  ██", "██  ██", "██ ███", " █████"],
            'R': ["████ ", "██ ██", "████ ", "██ ██", "██ ██"],
            'S': [" █████", "██    ", " ████ ", "    ██", "█████ "],
            'T': ["█████", "  ██  ", "  ██  ", "  ██  ", "  ██  "],
            'U': ["██ ██", "██ ██", "██ ██", "██ ██", " ███ "],
            'V': ["██ ██", "██ ██", "██ ██", " ███ ", "  █  "],
            'W': ["██   ██", "██   ██", "██ █ ██", "███████", "██   ██"],
            'X': ["██ ██", " ███ ", "  █  ", " ███ ", "██ ██"],
            'Y': ["██ ██", "██ ██", " ███ ", "  ██  ", "  ██  "],
            'Z': ["█████", "   ██ ", "  ██  ", " ██   ", "█████"],
            ' ': ["     ", "     ", "     ", "     ", "     "],
            '!': ["  █  ", "  █  ", "  █  ", "     ", "  █  "],
            '?': [" ███ ", "█   █", "   ██", "  █  ", "     "]
        }
        
        text = text.upper()
        lines = ["", "", "", "", ""]
        
        for char in text:
            letter = letters.get(char, letters['?'])
            for i in range(5):
                lines[i] += letter[i] + "  "
        
        result = "```\n" + "\n".join(lines) + "\n```"
        
        embed = discord.Embed(
            title="📝 ASCII Art",
            description=result,
            color=0x95a5a6
        )
        
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(FunCog(bot))
