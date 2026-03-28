import discord
from discord import app_commands
from discord.ext import commands
import time
import asyncio
from datetime import datetime, timedelta

class HelpView(discord.ui.View):
    def __init__(self, cog_data, timeout=180):
        super().__init__(timeout=timeout)
        self.cog_data = cog_data
        self.current_category = None
        
        # Add select menu for categories
        options = []
        for category in sorted(cog_data.keys()):
            emoji = cog_data[category]['emoji']
            count = len(cog_data[category]['commands'])
            options.append(
                discord.SelectOption(
                    label=category,
                    description=f"{count} commands",
                    emoji=emoji,
                    value=category
                )
            )
        
        select = discord.ui.Select(
            placeholder="Choose a category to view all commands...",
            options=options,
            min_values=1,
            max_values=1
        )
        select.callback = self.select_callback
        self.add_item(select)
    
    async def select_callback(self, interaction: discord.Interaction):
        category = self.children[0].values[0]
        await self.show_category(interaction, category)
    
    async def show_category(self, interaction: discord.Interaction, category: str):
        data = self.cog_data[category]
        emoji = data['emoji']
        commands_list = data['commands']
        
        # Split into chunks of 25 fields (Discord limit) if needed, but use description for bulk
        embed = discord.Embed(
            title=f"{emoji} {category} Commands",
            color=0x3498db,
            timestamp=datetime.now()
        )
        
        # Build description with all commands to avoid field limits
        desc_lines = []
        for cmd in sorted(commands_list, key=lambda x: x['name']):
            desc_lines.append(f"`/{cmd['name']}` - {cmd['description']}")
        
        # If too long, split into pages in description or use fields wisely
        full_desc = "\n".join(desc_lines)
        if len(full_desc) > 4000:
            # Paginate within the embed using fields by alphabet
            chunks = []
            current_chunk = []
            current_len = 0
            
            for line in desc_lines:
                if current_len + len(line) > 900:
                    chunks.append("\n".join(current_chunk))
                    current_chunk = [line]
                    current_len = len(line)
                else:
                    current_chunk.append(line)
                    current_len += len(line) + 1
            
            if current_chunk:
                chunks.append("\n".join(current_chunk))
            
            for i, chunk in enumerate(chunks[:25]):  # Max 25 fields
                embed.add_field(name=f"Commands {i+1}", value=chunk, inline=False)
        else:
            embed.description = full_desc
        
        embed.set_footer(text=f"Total: {len(commands_list)} commands • Use buttons to navigate categories")
        await interaction.response.edit_message(embed=embed, view=self)

class UtilityCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.start_time = time.time()
        self.afk_users = {}  # user_id: {"reason": str, "time": datetime}
    
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
        """Auto-generates help from all loaded cogs - Shows ALL commands"""
        
        # Organize commands by cog
        categories = {
            "FGO": {"emoji": "🎮", "commands": []},
            "Servant": {"emoji": "🔍", "commands": []},
            "Fun": {"emoji": "😄", "commands": []},
            "Utility": {"emoji": "⚙️", "commands": []},
            "Battle": {"emoji": "⚔️", "commands": []},
            "Other": {"emoji": "📦", "commands": []}
        }
        
        # Get all app commands from all cogs
        for cog_name, cog in self.bot.cogs.items():
            cog_category = "Other"
            lower_name = cog_name.lower()
            
            if "battle" in lower_name or "master" in lower_name:
                cog_category = "Battle"
            elif any(word in lower_name for word in ["servant", "fgo", "atlas", "material", "grail", "mystic"]):
                cog_category = "FGO"
            elif "fun" in lower_name:
                cog_category = "Fun"
            elif "utility" in lower_name:
                cog_category = "Utility"
            
            # Get commands from this cog
            for command in cog.walk_app_commands():
                if command.parent is None:  # Only top-level commands
                    categories[cog_category]["commands"].append({
                        "name": command.name,
                        "description": command.description or "No description"
                    })
        
        # Initial embed showing overview
        total_commands = sum(len(c["commands"]) for c in categories.values())
        embed = discord.Embed(
            title="C.I.E.L Commands",
            description=f"**Total Commands: {total_commands}**\n\nUse the dropdown below to view ALL commands in each category.\nNo more '10 more' limits!",
            color=0x3498db,
            timestamp=datetime.now()
        )
        
        for category, data in categories.items():
            if data["commands"]:
                embed.add_field(
                    name=f"{data['emoji']} {category} ({len(data['commands'])} cmds)",
                    value=f"Select from dropdown to view",
                    inline=True
                )
        
        embed.set_footer(text="Made by krlnel | Data provided by Atlas Academy API")
        
        view = HelpView(categories)
        await interaction.response.send_message(embed=embed, view=view)
    
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
    
    @app_commands.command(name="userinfo", description="📋 Display user information")
    @app_commands.describe(user="User to check (default: you)")
    async def userinfo(self, interaction: discord.Interaction, user: discord.Member = None):
        """Show detailed user information"""
        target = user or interaction.user
        
        embed = discord.Embed(
            title=f"📋 User Info: {target.display_name}",
            color=target.color,
            timestamp=datetime.now()
        )
        embed.set_thumbnail(url=target.display_avatar.url)
        
        embed.add_field(name="Username", value=str(target), inline=True)
        embed.add_field(name="User ID", value=target.id, inline=True)
        embed.add_field(name="Bot?", value="Yes" if target.bot else "No", inline=True)
        
        embed.add_field(name="Account Created", value=target.created_at.strftime("%Y-%m-%d"), inline=True)
        embed.add_field(name="Joined Server", value=target.joined_at.strftime("%Y-%m-%d") if target.joined_at else "Unknown", inline=True)
        embed.add_field(name="Top Role", value=target.top_role.mention if target.top_role else "None", inline=True)
        
        roles = [r.mention for r in target.roles[1:]]  # Exclude @everyone
        if roles:
            embed.add_field(name=f"Roles [{len(roles)}]", value=" ".join(roles[:10]) + ("..." if len(roles) > 10 else ""), inline=False)
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="serverinfo", description="🏰 Display server information")
    async def serverinfo(self, interaction: discord.Interaction):
        """Show server statistics"""
        guild = interaction.guild
        
        embed = discord.Embed(
            title=f"🏰 {guild.name}",
            color=0x3498db,
            timestamp=datetime.now()
        )
        
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        
        embed.add_field(name="Server ID", value=guild.id, inline=True)
        embed.add_field(name="Owner", value=guild.owner.mention if guild.owner else "Unknown", inline=True)
        embed.add_field(name="Created", value=guild.created_at.strftime("%Y-%m-%d"), inline=True)
        
        embed.add_field(name="Members", value=guild.member_count or "Unknown", inline=True)
        embed.add_field(name="Channels", value=f"{len(guild.text_channels)}T / {len(guild.voice_channels)}V", inline=True)
        embed.add_field(name="Roles", value=len(guild.roles), inline=True)
        
        embed.add_field(name="Boost Level", value=f"Level {guild.premium_tier} ({guild.premium_subscription_count} boosts)", inline=True)
        embed.add_field(name="Emojis", value=len(guild.emojis), inline=True)
        embed.add_field(name="Verification", value=str(guild.verification_level).title(), inline=True)
        
        if guild.description:
            embed.add_field(name="Description", value=guild.description, inline=False)
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="poll", description="📊 Create a poll")
    @app_commands.describe(question="The poll question", option1="First option", option2="Second option", option3="Third option (optional)", option4="Fourth option (optional)")
    async def poll(self, interaction: discord.Interaction, question: str, option1: str, option2: str, option3: str = None, option4: str = None):
        """Create a reaction poll"""
        options = [opt for opt in [option1, option2, option3, option4] if opt]
        
        if len(options) < 2:
            await interaction.response.send_message("Need at least 2 options!", ephemeral=True)
            return
        
        emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣"]
        
        embed = discord.Embed(
            title="📊 Poll",
            description=f"**{question}**",
            color=0x9b59b6,
            timestamp=datetime.now()
        )
        
        for i, opt in enumerate(options):
            embed.add_field(name=f"Option {i+1}", value=f"{emojis[i]} {opt}", inline=False)
        
        embed.set_footer(text=f"Poll by {interaction.user.display_name}")
        
        await interaction.response.send_message(embed=embed)
        message = await interaction.original_response()
        
        for i in range(len(options)):
            await message.add_reaction(emojis[i])
    
    @app_commands.command(name="afk", description="💤 Set AFK status")
    @app_commands.describe(reason="Why you're AFK")
    async def afk(self, interaction: discord.Interaction, reason: str = "AFK"):
        """Set AFK status - Bot will reply to mentions"""
        self.afk_users[interaction.user.id] = {
            "reason": reason,
            "time": datetime.now(),
            "display_name": interaction.user.display_name
        }
        
        embed = discord.Embed(
            title="💤 AFK Set",
            description=f"{interaction.user.mention} is now AFK: **{reason}**",
            color=0x95a5a6
        )
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="remind", description="⏰ Set a reminder")
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

async def setup(bot):
    await bot.add_cog(UtilityCog(bot))
