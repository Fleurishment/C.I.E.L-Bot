import os
import asyncio
import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

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
        # Create session for API calls
        import aiohttp
        self.session = aiohttp.ClientSession()
        
        # Load ONLY these cogs (removed scraper)
        await self.load_extension('cogs.servant')
        await self.load_extension('cogs.utility')
        await self.load_extension('cogs.fun')
        await self.load_extension('cogs.rayshift')
        await self.load_extension('cogs.servantbattle')
        
        # Sync slash commands
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
        
        # Check if mentioning AFK user
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
    async with FGOBot() as bot:
        await bot.start(os.getenv('DISCORD_TOKEN'))

if __name__ == '__main__':
    asyncio.run(main())
