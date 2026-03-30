import discord
from discord import app_commands
from discord.ext import commands
import aiohttp
import os
from datetime import datetime

class RayshiftCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Store user rayshift data: {user_id: {"friend_code": str, "region": str, "image_url": str, "updated": datetime}}
        if not hasattr(self.bot, 'rayshift_data'):
            self.bot.rayshift_data = {}
    
    @app_commands.command(name="setrayshift", description="📸 Submit your Rayshift support list screenshot")
    @app_commands.describe(
        image="Screenshot of your Rayshift support list",
        friend_code="Your 9-digit FGO friend code (optional, for reference)",
        region="Game region (optional, for reference)"
    )
    @app_commands.choices(region=[
        app_commands.Choice(name="Japan", value="jp"),
        app_commands.Choice(name="North America", value="na")
    ])
    async def setrayshift(
        self,
        interaction: discord.Interaction,
        image: discord.Attachment,
        friend_code: str = None,
        region: app_commands.Choice[str] = None
    ):
        """Save your Rayshift support list image to the bot"""
        
        # Validate image
        if not image.content_type or not image.content_type.startswith('image/'):
            await interaction.response.send_message(
                "❌ Please upload a valid image file (PNG, JPG, etc.)!",
                ephemeral=True
            )
            return
        
        # Check file size (max 8MB)
        if image.size > 8 * 1024 * 1024:
            await interaction.response.send_message(
                "❌ Image too large! Max size is 8MB.",
                ephemeral=True
            )
            return
        
        # Validate friend code if provided
        cleaned_code = None
        if friend_code:
            cleaned_code = friend_code.replace("-", "").replace(" ", "")
            if not cleaned_code.isdigit() or len(cleaned_code) != 9:
                await interaction.response.send_message(
                    "❌ Friend code must be exactly 9 digits!",
                    ephemeral=True
                )
                return
        
        region_code = region.value if isinstance(region, app_commands.Choice) else (region if region else "unknown")
        
        # Save data
        self.bot.rayshift_data[interaction.user.id] = {
            "friend_code": cleaned_code,
            "region": region_code,
            "image_url": image.url,
            "updated": datetime.now().strftime("%Y-%m-%d %H:%M")
        }
        
        embed = discord.Embed(
            title="✅ Support List Saved!",
            description=f"Your Rayshift support list has been saved.",
            color=0x2ecc71,
            timestamp=datetime.now()
        )
        
        if cleaned_code:
            embed.add_field(name="Friend Code", value=f"`{cleaned_code}`", inline=True)
        embed.add_field(name="Region", value=region_code.upper() if region_code != "unknown" else "Not specified", inline=True)
        
        # Show preview
        embed.set_image(url=image.url)
        embed.set_footer(text="Use /rayshift to view anytime | Use /setrayshift to update")
        
        await interaction.response.send_message(embed=embed, ephemeral=False)
    
    @app_commands.command(name="rayshift", description="🔍 View a user's Rayshift support list")
    @app_commands.describe(
        user="User to look up (default: yourself)",
        friend_code="Get Rayshift.io link for a friend code instead"
    )
    async def rayshift(
        self,
        interaction: discord.Interaction,
        user: discord.Member = None,
        friend_code: str = None
    ):
        """View saved Rayshift support list or generate Rayshift.io link"""
        
        # If friend code provided, generate old-style link
        if friend_code:
            cleaned_code = friend_code.replace("-", "").replace(" ", "")
            if not cleaned_code.isdigit() or len(cleaned_code) != 9:
                await interaction.response.send_message(
                    "❌ Friend code must be exactly 9 digits!",
                    ephemeral=True
                )
                return
            
            # Default to JP if not specified
            url = f"https://rayshift.io/jp/{cleaned_code}"
            
            embed = discord.Embed(
                title=f"🔍 Rayshift Profile",
                description=f"**Friend Code:** `{cleaned_code}`",
                url=url,
                color=0x3498db
            )
            
            view = discord.ui.View()
            view.add_item(discord.ui.Button(
                label="🔗 Open Rayshift Profile",
                style=discord.ButtonStyle.link,
                url=url
            ))
            
            await interaction.response.send_message(embed=embed, view=view)
            return
        
        # View saved support list
        target = user or interaction.user
        
        if target.id not in self.bot.rayshift_data:
            if target.id == interaction.user.id:
                await interaction.response.send_message(
                    "❌ You haven't set your support list yet!\n"
                    "Use `/setrayshift` to upload a screenshot from rayshift.io",
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    f"❌ {target.display_name} hasn't set their support list yet!",
                    ephemeral=True
                )
            return
        
        data = self.bot.rayshift_data[target.id]
        
        embed = discord.Embed(
            title=f"🔍 {target.display_name}'s Support List",
            color=0x3498db,
            timestamp=datetime.now()
        )
        
        if data.get("friend_code"):
            embed.add_field(name="Friend Code", value=f"`{data['friend_code']}`", inline=True)
            # Add Rayshift.io link
            region = data.get("region", "jp")
            url = f"https://rayshift.io/{region}/{data['friend_code']}"
            embed.add_field(name="Rayshift.io", value=f"[View Live]({url})", inline=True)
        
        if data.get("region") and data["region"] != "unknown":
            embed.add_field(name="Region", value=data["region"].upper(), inline=True)
        
        if data.get("updated"):
            embed.add_field(name="Last Updated", value=data["updated"], inline=True)
        
        # Show the saved image
        embed.set_image(url=data["image_url"])
        
        # Add button to view on Rayshift.io if friend code exists
        view = discord.ui.View()
        if data.get("friend_code"):
            view.add_item(discord.ui.Button(
                label="🔗 Open on Rayshift.io",
                style=discord.ButtonStyle.link,
                url=f"https://rayshift.io/{data.get('region', 'jp')}/{data['friend_code']}"
            ))
        
        await interaction.response.send_message(embed=embed, view=view)
    
    @app_commands.command(name="rayshiftlink", description="🔗 Get just the Rayshift.io profile link")
    @app_commands.describe(
        friend_code="Your 9-digit FGO friend code",
        region="Game region"
    )
    @app_commands.choices(region=[
        app_commands.Choice(name="Japan", value="jp"),
        app_commands.Choice(name="North America", value="na")
    ])
    async def rayshiftlink(
        self,
        interaction: discord.Interaction,
        friend_code: str,
        region: app_commands.Choice[str] = "jp"
    ):
        """Generate a Rayshift.io profile link (original functionality)"""
        
        cleaned_code = friend_code.replace("-", "").replace(" ", "")
        
        if not cleaned_code.isdigit() or len(cleaned_code) != 9:
            await interaction.response.send_message(
                "❌ Friend code must be exactly 9 digits!\n"
                "Examples: `801625519` or `801-625-519`",
                ephemeral=True
            )
            return
        
        region_code = region.value if isinstance(region, app_commands.Choice) else region
        url = f"https://rayshift.io/{region_code}/{cleaned_code}"
        
        embed = discord.Embed(
            title=f"🔍 Rayshift Profile",
            description=f"**Friend Code:** `{cleaned_code}`\n**Region:** {region_code.upper()}",
            url=url,
            color=0x3498db
        )
        
        embed.add_field(
            name="What is Rayshift?",
            value="Rayshift.io lets you view FGO support lists online without opening the game.",
            inline=False
        )
        
        embed.set_footer(text="Rayshift.io - FGO Support Viewer")
        
        view = discord.ui.View()
        view.add_item(discord.ui.Button(
            label="🔗 Open Rayshift Profile",
            style=discord.ButtonStyle.link,
            url=url
        ))
        
        await interaction.response.send_message(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(RayshiftCog(bot))
