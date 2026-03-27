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
    
    async def setup_hook(self):
        # Load all cogs
        await self.load_extension('cogs.servant')
        await self.load_extension('cogs.scraper')
        await self.load_extension('cogs.utility')
        
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
                name="over Chaldea | /servant"
            )
        )
    
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandNotFound):
            return
        print(f"Command error: {error}")

async def main():
    async with FGOBot() as bot:
        await bot.start(os.getenv('DISCORD_TOKEN'))

if __name__ == '__main__':
    asyncio.run(main())
