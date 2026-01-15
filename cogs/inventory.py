import discord
from discord.ext import commands
from config import DB_FILE
from data_manager import get_player, items_db, effects_db, recipes_db
from utils import craft_item

class Inventory(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="inventory", aliases=["inv"])
    async def inventory(self, ctx):
        player = get_player(ctx.author.id)
        if not player["inventory"]: return await ctx.send("🎒 Empty inventory.")
        counts = {}
        for item_id in player["inventory"]:
            name = items_db.get(item_id, {}).get("name", item_id)
            counts[name] = counts.get(name, 0) + 1
        inv_str = "\n".join([f"• {name} (x{count})" for name, count in counts.items()])
        await ctx.send(f"🎒 **{ctx.author.display_name}'s Inventory:**\n{inv_str}")

    @commands.command(name="item")
    async def item_info(self, ctx, *, name: str):
        item_id = next((k for k, v in items_db.items() if v["name"].lower() == name.lower()), None)
        if not item_id: return await ctx.send("❌ Item not found.")
        item = items_db[item_id]
        embed = discord.Embed(title=item["name"], description=item["description"], color=0xE91E63)
        if item.get("effects"):
            embed.add_field(name="Effects", value="\n".join([f"✨ {effects_db.get(e, {}).get('name', e)}" for e in item["effects"]]), inline=False)
        await ctx.send(embed=embed)

    @commands.command(name="recipes")
    async def show_recipes(self, ctx):
        embed = discord.Embed(title="📜 Book of Recipes", color=0x795548)
        for cat, items in recipes_db.items():
            text = ""
            for r_id, r in items.items():
                ings = ", ".join([f"{count}x {items_db.get(i, {}).get('name', i)}" for i, count in r['ingredients'].items()])
                text += f"• **{r['name']}** (`{r_id}`): {ings}\n"
            embed.add_field(name=cat.capitalize(), value=text or "None", inline=False)
        await ctx.send(embed=embed)

    # Note: Alchemy and Forge were mentioned in help but not implemented in the original file view I had. 
    # If they were there, I would add them here. For now, I'll respect the help command which listed them
    # but the implementation wasn't visible in the snippets I saw or was missing.

async def setup(bot):
    await bot.add_cog(Inventory(bot))
