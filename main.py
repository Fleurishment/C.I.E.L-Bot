import os
import asyncio
import discord
from discord.ext import commands
from dotenv import load_dotenv
from threading import Thread
from flask import Flask

load_dotenv()

# === WEB SERVER FOR RENDER ===
app = Flask(__name__)

@app.route('/')
def home():
    return "C.I.E.L Bot is online! ✅"

@app.route('/health')
def health():
    return {"status": "alive"}, 200

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# === DISCORD BOT ===
class FGOBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        
        super().__init__(
            command_prefix=commands.when_mentioned_or(os.getenv('COMMAND_PREFIX', '!')),
            intents=intents,
            help_command=None
        )
        self.session = None
    
    async def setup_hook(self):
        import aiohttp
        self.session = aiohttp.ClientSession()
        
        await self.load_extension('cogs.servant')
        await self.load_extension('cogs.utility')
        await self.load_extension('cogs.fun')
        await self.load_extension('cogs.rayshift')
        await self.load_extension('cogs.servantbattle')
        
        try:
            synced = await self.tree.sync()
            print(f"Synced {len(synced)} slash commands globally")
        except Exception as e:
            print(f"Failed to sync commands: {e}")
    
    async def on_ready(self):
        print(f'{self.user} has connected to Discord!')
        print(f'Bot is in {len(self.guilds)} guilds')
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching, 
                name="Over you~ | /help"
            )
        )
    
    async def on_message(self, message):
        if message.author.bot:
            return
        
        utility_cog = self.get_cog("UtilityCog")
        if utility_cog and message.author.id in utility_cog.afk_users:
            del utility_cog.afk_users[message.author.id]
            await message.reply("Welcome back! I removed your AFK status.", delete_after=5)
        
        for mention in message.mentions:
            if utility_cog and mention.id in utility_cog.afk_users:
                data = utility_cog.afk_users[mention.id]
                await message.reply(f"💤 {mention.display_name} is AFK: {data['reason']}", delete_after=10)
        
        await self.process_commands(message)
    
    async def close(self):
        if self.session:
            await self.session.close()
        await super().close()

async def main():
    # Start Flask web server in background thread
    web_thread = Thread(target=run_web)
    web_thread.daemon = True
    web_thread.start()
    print(f"Web server started on port {os.environ.get('PORT', 8080)}")
    
    async with FGOBot() as bot:
        await bot.start(os.getenv('DISCORD_TOKEN'))

if __name__ == '__main__':
    asyncio.run(main())
