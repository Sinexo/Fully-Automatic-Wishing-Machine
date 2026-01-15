import discord
from discord.ext import commands
from data_manager import save_json, DB_FILE, player_data

class Basic(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print(f'✅ LoM RPG Bot started: {self.bot.user.name}')
    
    @commands.command(name="help")
    async def custom_help(self, ctx):
        embed = discord.Embed(title="📖 Beyonder's Handbook (Help)", color=0x34495E)
        embed.add_field(name="🧬 Progression", value="`!pathways`, `!choose [name]`, `!profile`, `!abilities`, `!act`, `!advance`, `!stats [name]` (New!)", inline=False)
        embed.add_field(name="💰 Economy", value="`!balance`, `!daily`, `!work`, `!casino`", inline=False)
        embed.add_field(name="🎒 Mysticism", value="`!expedition`, `!inventory`, `!item [name]`, `!recipes`", inline=False)
        embed.add_field(name="⚗️ Crafting", value="`!alchemy`, `!forge`", inline=False)
        if ctx.author.guild_permissions.administrator:
            embed.add_field(name="⚙️ Admin", value="`!reset`", inline=False)
        await ctx.send(embed=embed)

    @commands.command(name="reset")
    @commands.has_permissions(administrator=True)
    async def reset_data(self, ctx):
        player_data.clear()
        save_json(DB_FILE, player_data)
        await ctx.send("🧹 **SYSTEM RESET**.")

async def setup(bot):
    await bot.add_cog(Basic(bot))
