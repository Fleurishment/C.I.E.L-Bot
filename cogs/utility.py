import discord
from discord import app_commands
from discord.ext import commands
import time

class UtilityCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.start_time = time.time()
    
    @app_commands.command(name="ping", description="Check bot latency")
    async def ping(self, interaction: discord.Interaction):
        latency = round(self.bot.latency * 1000)
        embed = discord.Embed(
            title="🏓 Pong!",
            description=f"Latency: `{latency}ms`",
            color=0x00ff00 if latency < 200 else 0xff0000
        )
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="help", description="Show all available commands")
    async def help_command(self, interaction: discord.Interaction):
        """Auto-generates help from all loaded cogs"""
        
        embed = discord.Embed(
            title="C.I.E.L Commands",
            description="Your Chaldea Assistant - Use `/help [category]` for specific sections",
            color=0x3498db
        )
        
        # Organize commands by cog
        categories = {
            "FGO": {"emoji": "🎮", "commands": []},
            "Servant": {"emoji": "🔍", "commands": []},
            "Fun": {"emoji": "😄", "commands": []},
            "Utility": {"emoji": "⚙️", "commands": []},
            "Other": {"emoji": "📦", "commands": []}
        }
        
        # Get all app commands from all cogs
        for cog_name, cog in self.bot.cogs.items():
            cog_category = "Other"
            
            # Determine category based on cog name
            if any(word in cog_name.lower() for word in ["servant", "fgo", "atlas"]):
                cog_category = "FGO" if "fun" not in cog_name.lower() else "Fun"
            elif "fun" in cog_name.lower():
                cog_category = "Fun"
            elif "utility" in cog_name.lower():
                cog_category = "Utility"
            elif "servant" in cog_name.lower():
                cog_category = "Servant"
            
            # Get commands from this cog
            for command in cog.walk_app_commands():
                if command.parent is None:  # Only top-level commands
                    categories[cog_category]["commands"].append({
                        "name": command.name,
                        "description": command.description
                    })
        
        # Build embed fields
        for category, data in categories.items():
            if data["commands"]:
                # Sort commands alphabetically
                sorted_cmds = sorted(data["commands"], key=lambda x: x["name"])
                
                # Format: `/name` - description
                cmd_text = "\n".join([
                    f"`/{cmd['name']}` - {cmd['description'][:50]}{'...' if len(cmd['description']) > 50 else ''}"
                    for cmd in sorted_cmds[:10]  # Max 10 per category
                ])
                
                if len(sorted_cmds) > 10:
                    cmd_text += f"\n*...and {len(sorted_cmds) - 10} more*"
                
                embed.add_field(
                    name=f"{data['emoji']} {category}",
                    value=cmd_text,
                    inline=False
                )
        
        # Add stats
        total_commands = sum(len(c["commands"]) for c in categories.values())
        embed.add_field(
            name="📊 Stats",
            value=f"Total Commands: **{total_commands}**\nUse `/ping` to check status",
            inline=False
        )
        
        embed.set_footer(text="Made by krlnel | Data provided by Atlas Academy API")
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="uptime", description="⏱️ Check how long the bot has been running")
    async def uptime(self, interaction: discord.Interaction):
        """Show bot uptime"""
        current_time = time.time()
        uptime_seconds = int(current_time - self.start_time)
        
        days = uptime_seconds // 86400
        hours = (uptime_seconds % 86400) // 3600
        minutes = (uptime_seconds % 3600) // 60
        seconds = uptime_seconds % 60
        
        time_parts = []
        if days > 0:
            time_parts.append(f"{days}d")
        if hours > 0:
            time_parts.append(f"{hours}h")
        if minutes > 0:
            time_parts.append(f"{minutes}m")
        time_parts.append(f"{seconds}s")
        
        uptime_str = " ".join(time_parts)
        
        embed = discord.Embed(
            title="⏱️ Bot Uptime",
            description=f"Running for: **{uptime_str}**",
            color=0x2ecc71
        )
        
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(UtilityCog(bot))
