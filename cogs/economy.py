import discord
from discord.ext import commands
from datetime import datetime
import random
from config import DB_FILE
from data_manager import get_player, save_json, player_data, get_npc
from utils import check_cooldown, format_timedelta, format_currency, gain_xp

class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="work")
    async def work(self, ctx):
        player = get_player(ctx.author.id)
        can_run, rem = check_cooldown(player, "last_work", 1)
        if not can_run: return await ctx.send(f"⏳ **Cooldown:** Wait **{format_timedelta(rem)}**.")
        reward = random.randint(10, 20)
        player["balance"] += reward
        xp_gain = 5
        leveled, new_lvl = gain_xp(player, xp_gain)
        player["last_work"] = datetime.now().isoformat()
        save_json(DB_FILE, player_data)
        
        msg = f"💼 Earned {format_currency(reward)} and **+{xp_gain} XP**."
        if leveled:
            msg += f"\n🎊 **LEVEL UP!** You are now level **{new_lvl}**!"
        await ctx.send(msg)

    @commands.command(name="daily")
    async def daily(self, ctx):
        player = get_player(ctx.author.id)
        can_run, rem = check_cooldown(player, "last_daily", 24)
        if not can_run: return await ctx.send(f"⏳ **Cooldown:** Wait **{format_timedelta(rem)}**.")
        player["balance"] += 120
        
        xp_gain = 50
        leveled, new_lvl = gain_xp(player, xp_gain)
        player["acting_xp"] = min(player.get("acting_max_xp", 200), player.get("acting_xp", 0) + 15)
        
        # We need access to items_db to give random item
        from data_manager import items_db
        item_id = random.choice(list(items_db.keys()))
        player["inventory"].append(item_id)
        item_name = items_db[item_id]["name"]
        
        player["last_daily"] = datetime.now().isoformat()
        save_json(DB_FILE, player_data)
        
        msg = f"🎁 **Daily Rewards Claimed!**\n💰 +120 Pence\n🆙 +{xp_gain} XP\n🎭 +15 Acting XP\n🎒 Found: **{item_name}**"
        if leveled:
            msg += f"\n\n🎊 **LEVEL UP!** You are now level **{new_lvl}**!"
        await ctx.send(msg)

    @commands.command(name="balance")
    async def balance(self, ctx):
        p = get_player(ctx.author.id)
        await ctx.send(f"💰 Balance: {format_currency(p['balance'])}")

    @commands.command(name="casino")
    async def casino(self, ctx, amount: str = None):
        player = get_player(ctx.author.id)
        will = get_npc("will_auceptin")
        if not amount: return await ctx.send("❓ Amount?")
        try: bet = int(amount) if amount.lower() != "allin" else player["balance"]
        except: return await ctx.send("❌ Error.")
        if bet <= 0 or player["balance"] < bet: return await ctx.send("❌ Funds?")
        
        p_roll, w_roll = random.randint(2, 12), random.randint(2, 12)
        embed = discord.Embed(title="🎰 Will Auceptin's Casino", color=0xF1C40F)
        embed.add_field(name="You", value=f"🎲 **{p_roll}**")
        embed.add_field(name="Will", value=f"🎲 **{w_roll}**")

        if p_roll > w_roll:
            player["balance"] += bet
            embed.description = f"🎉 Won {format_currency(bet)}!"
        elif p_roll < w_roll:
            player["balance"] -= bet
            will["bankroll"] += bet
            will["wins"] += 1
            embed.description = f"💀 Lost {format_currency(bet)}."
        else: embed.description = "🤝 Draw."
        save_json(DB_FILE, player_data)
        await ctx.send(embed=embed)

    @commands.command(name="will", aliases=["willinfo"])
    async def will_stats(self, ctx):
        will = get_npc("will_auceptin")
        embed = discord.Embed(title="🧒 Will Auceptin", description="The silver-haired child.", color=0xBDC3C7)
        embed.add_field(name="💰 Wealth", value=format_currency(will["bankroll"]))
        embed.add_field(name="🏆 Wins", value=will["wins"])
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Economy(bot))
