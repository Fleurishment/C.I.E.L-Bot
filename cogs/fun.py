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

class BombView(discord.ui.View):
    def __init__(self, correct_wire, timeout=10):
        super().__init__(timeout=timeout)
        self.correct_wire = correct_wire
        self.exploded = False
        
        colors = [("🔴 Red", "red"), ("🔵 Blue", "blue"), ("🟢 Green", "green")]
        random.shuffle(colors)
        
        for label, value in colors:
            btn = discord.ui.Button(label=label, style=discord.ButtonStyle.grey, custom_id=value)
            btn.callback = self.wire_callback
            self.add_item(btn)
    
    async def wire_callback(self, interaction: discord.Interaction):
        if self.exploded:
            return
        
        wire = interaction.data['custom_id']
        
        for child in self.children:
            child.disabled = True
        
        if wire == self.correct_wire:
            embed = discord.Embed(
                title="💣 Bomb Defused!",
                description=f"✅ You cut the {wire} wire! Safe!",
                color=0x2ecc71
            )
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            embed = discord.Embed(
                title="💥 BOOM!",
                description=f"❌ Wrong wire! It was **{self.correct_wire}**!",
                color=0xe74c3c
            )
            await interaction.response.edit_message(embed=embed, view=self)
        
        self.exploded = True
        self.stop()

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
    
    # NEW COMMANDS START HERE
    
    @app_commands.command(name="roast", description="🔥 Get roasted!")
    @app_commands.describe(user="Who to roast (default: yourself)")
    async def roast(self, interaction: discord.Interaction, user: discord.Member = None):
        """Roast someone"""
        target = user or interaction.user
        
        roasts = [
            f"{target.display_name} is like a cloud. When they disappear, it's a beautiful day.",
            f"I'm not saying {target.display_name} is dumb, but they think a quarterback is a refund.",
            f"{target.display_name} is proof that evolution can go in reverse.",
            f"Roses are red, violets are blue, {target.display_name} has the face only a mother could love.",
            f"{target.display_name} is so slow, they got lapped by a statue.",
            f"I'd agree with {target.display_name} but then we'd both be wrong.",
            f"{target.display_name} brings everyone so much joy... when they leave the room.",
            f"{target.display_name} is the reason the gene pool needs a lifeguard."
        ]
        
        embed = discord.Embed(
            title="🔥 Roast",
            description=random.choice(roasts),
            color=0xe74c3c
        )
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="wouldyou", description="🤔 Would You Rather questions")
    async def wouldyou(self, interaction: discord.Interaction):
        """Random would you rather"""
        questions = [
            "Would you rather have unlimited IQ but no friends, or average IQ with many friends?",
            "Would you rather always speak your mind or never speak again?",
            "Would you rather be a master at FGO but broke, or rich but never win a gacha roll?",
            "Would you rather fight 100 duck-sized horses or 1 horse-sized duck?",
            "Would you rather have spaghetti for hair or sweat maple syrup?",
            "Would you rather be able to fly but only 1 inch off the ground, or run at 100mph but only backwards?"
        ]
        
        embed = discord.Embed(
            title="🤔 Would You Rather",
            description=random.choice(questions),
            color=0x9b59b6
        )
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="color", description="🎨 Get a random color or color info")
    @app_commands.describe(hex_code="Hex color code (optional)")
    async def color(self, interaction: discord.Interaction, hex_code: str = None):
        """Show color info"""
        if hex_code:
            hex_clean = hex_code.lstrip('#')
            if len(hex_clean) != 6 or not all(c in '0123456789ABCDEFabcdef' for c in hex_clean):
                await interaction.response.send_message("❌ Invalid hex code!", ephemeral=True)
                return
            color_val = int(hex_clean, 16)
        else:
            color_val = random.randint(0, 0xFFFFFF)
            hex_clean = f"{color_val:06x}"
        
        embed = discord.Embed(
            title=f"🎨 Color #{hex_clean.upper()}",
            color=color_val
        )
        embed.add_field(name="Hex", value=f"#{hex_clean.upper()}", inline=True)
        embed.add_field(name="Decimal", value=str(color_val), inline=True)
        embed.add_field(name="RGB", value=f"{(color_val >> 16) & 255}, {(color_val >> 8) & 255}, {color_val & 255}", inline=True)
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="bomb", description="💣 Defuse the bomb!")
    async def bomb(self, interaction: discord.Interaction):
        """Wire cutting game"""
        correct = random.choice(["red", "blue", "green"])
        
        embed = discord.Embed(
            title="💣 Bomb Defusal",
            description="**10 SECONDS!** Cut the correct wire!\n🔴 Red | 🔵 Blue | 🟢 Green",
            color=0xe74c3c
        )
        
        view = BombView(correct, timeout=10)
        await interaction.response.send_message(embed=embed, view=view)
        
        # Wait for timeout
        await view.wait()
        if not view.exploded:
            for child in view.children:
                child.disabled = True
            await interaction.edit_original_response(view=view)
    
    @app_commands.command(name="aim", description="🎯 Test your reaction speed")
    async def aim(self, interaction: discord.Interaction):
        """Reaction time game"""
        await interaction.response.send_message("🎯 Get ready...")
        
        wait_time = random.uniform(2, 5)
        await asyncio.sleep(wait_time)
        
        start_time = datetime.datetime.now()
        
        embed = discord.Embed(
            title="🎯 CLICK NOW!",
            description="Press the button as fast as you can!",
            color=0x2ecc71
        )
        
        view = discord.ui.View(timeout=10)
        btn = discord.ui.Button(label="SHOOT!", style=discord.ButtonStyle.red)
        
        clicked = [False]
        
        async def callback(inter):
            if clicked[0]:
                return
            clicked[0] = True
            reaction_time = (datetime.datetime.now() - start_time).total_seconds() * 1000
            
            rating = "⚡ GODLIKE!" if reaction_time < 200 else "💨 Fast!" if reaction_time < 400 else "🐢 Slow..."
            
            result_embed = discord.Embed(
                title="🎯 Result",
                description=f"Time: **{reaction_time:.0f}ms**\n{rating}",
                color=0x2ecc71 if reaction_time < 400 else 0xe74c3c
            )
            await inter.response.edit_message(embed=result_embed, view=None)
        
        btn.callback = callback
        view.add_item(btn)
        
        await interaction.edit_original_response(embed=embed, view=view)
    
    @app_commands.command(name="life", description="🧠 Get life advice")
    async def life(self, interaction: discord.Interaction):
        """Random life advice"""
        advice = [
            "Don't lick frozen poles in winter.",
            "If you stare at the sun, you won't have to worry about eye strain anymore.",
            "The early bird gets the worm, but the second mouse gets the cheese.",
            "Always check if the toilet seat is down... the hard way.",
            "Never trust a fart after taco night.",
            "If at first you don't succeed, skydiving is not for you.",
            "Life is like a box of chocolates. It doesn't last long if you're fat.",
            "Drink water so you can be hydrated for your inevitable doom."
        ]
        
        embed = discord.Embed(
            title="🧠 Life Advice",
            description=random.choice(advice),
            color=0x3498db
        )
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="who", description="🕵️ Pick a random server member")
    async def who(self, interaction: discord.Interaction):
        """Pick random user"""
        members = [m for m in interaction.guild.members if not m.bot]
        if not members:
            await interaction.response.send_message("❌ No members found!", ephemeral=True)
            return
        
        chosen = random.choice(members)
        
        embed = discord.Embed(
            title="🕵️ The Chosen One",
            description=f"**{chosen.mention}** has been selected!",
            color=chosen.color
        )
        if chosen.avatar:
            embed.set_thumbnail(url=chosen.avatar.url)
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="resume", description="🧾 Generate a fake resume")
    @app_commands.describe(user="Whose resume to generate")
    async def resume(self, interaction: discord.Interaction, user: discord.Member = None):
        """Fake resume generator"""
        target = user or interaction.user
        
        jobs = ["Professional Sleeper", "Chocolate Taster", "Chief Procrastination Officer", "Meme Curator", "Discord Mod (supreme)", "Gacha Addict"]
        skills = ["Can sleep for 14 hours straight", "Speaks fluent emoji", "Survived 1000 FGO gacha rolls with no SSRs", "Can eat 20 tacos", "Typing speed: 3 WPM"]
        education = ["School of Hard Knocks", "University of Life", "Hogwarts (dropout)", "YouTube Academy", "Twitch Chat University"]
        
        embed = discord.Embed(
            title=f"🧾 Resume: {target.display_name}",
            color=0x95a5a6
        )
        embed.add_field(name="Current Position", value=random.choice(jobs), inline=False)
        embed.add_field(name="Skills", value="\n".join(f"• {s}" for s in random.sample(skills, 3)), inline=False)
        embed.add_field(name="Education", value=random.choice(education), inline=False)
        embed.add_field(name="Experience", value=f"{random.randint(0, 50)} years in {random.choice(['suffering', 'gaming', 'shitposting', 'gacha'])}", inline=False)
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="future", description="🔮 See your future")
    @app_commands.describe(user="Whose future to read")
    async def future(self, interaction: discord.Interaction, user: discord.Member = None):
        """Random future prediction"""
        target = user or interaction.user
        
        futures = [
            "will embarrass themselves tomorrow in front of everyone.",
            "will find a penny on the ground but lose their wallet.",
            "will get an SSR on their next single roll.",
            "will trip over nothing in the next 24 hours.",
            "will become a famous meme... for the wrong reasons.",
            "will discover that their fridge is actually empty.",
            "will accidentally like their crush's 3-year-old photo.",
            "will step on a LEGO today. Fate is cruel."
        ]
        
        embed = discord.Embed(
            title="🔮 Future Prediction",
            description=f"**{target.display_name}** {random.choice(futures)}",
            color=0x9b59b6
        )
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="probability", description="📊 Calculate probability of anything")
    @app_commands.describe(event="What to calculate")
    async def probability(self, interaction: discord.Interaction, event: str):
        """Random probability"""
        chance = random.randint(0, 100)
        
        embed = discord.Embed(
            title="📊 Probability Calculator",
            description=f"Chance of **{event}**:",
            color=0x3498db
        )
        
        bar = "█" * (chance // 10) + "░" * (10 - (chance // 10))
        embed.add_field(name=f"{bar} {chance}%", value="Probably accurate!", inline=False)
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="trivia", description="❓ Answer a trivia question")
    async def trivia(self, interaction: discord.Interaction):
        """Trivia game"""
        questions = [
            {"q": "What does FGO stand for?", "a": ["fate grand order", "fate/grand order"], "hint": "Fate ___ ____"},
            {"q": "Who is the Saber Class iconic servant?", "a": ["artoria", "saber", "arthuria"], "hint": "King of Knights"},
            {"q": "What is the currency used in FGO gacha?", "a": ["saint quartz", "sq", "quartz"], "hint": "Saint _____"},
            {"q": "What year was FGO released in Japan?", "a": ["2015"], "hint": "201X"},
            {"q": "Who is Mash Kyrielight's voice actor?", "a": ["rie takahashi", "takahashi rie"], "hint": "Rie ________"}
        ]
        
        q = random.choice(questions)
        
        embed = discord.Embed(
            title="❓ FGO Trivia",
            description=q['q'],
            color=0xe74c3c
        )
        embed.set_footer(text="Type your answer in chat!")
        
        await interaction.response.send_message(embed=embed)
        
        def check(m):
            return m.author.id == interaction.user.id and m.channel.id == interaction.channel_id
        
        try:
            msg = await self.bot.wait_for('message', timeout=30.0, check=check)
            if any(ans in msg.content.lower() for ans in q['a']):
                await msg.reply("🎉 Correct!")
            else:
                await msg.reply(f"❌ Wrong! Answer: {q['a'][0]}")
        except asyncio.TimeoutError:
            await interaction.followup.send(f"⏰ Time's up! Answer: {q['a'][0]}")

async def setup(bot):
    await bot.add_cog(FunCog(bot))
