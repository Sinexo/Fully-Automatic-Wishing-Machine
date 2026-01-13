import discord
from discord.ext import commands
import random
import os
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
DB_FILE = "data.json"
ITEMS_FILE = "items.json"
EFFECTS_FILE = "effects.json"
RECIPES_FILE = "recipes.json"
PATHWAYS_DIR = "pathways"

# Bot configuration
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

# --- Data Management ---

def load_json(filename):
    if os.path.exists(filename):
        try:
            with open(filename, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_json(filename, data):
    with open(filename, 'w') as f:
        json.dump(data, f, indent=4)

def load_pathways():
    pathways = {}
    if os.path.exists(PATHWAYS_DIR):
        for filename in os.listdir(PATHWAYS_DIR):
            if filename.endswith(".json"):
                pathway_data = load_json(os.path.join(PATHWAYS_DIR, filename))
                if "name" in pathway_data:
                    pathways[pathway_data["name"]] = pathway_data
    return pathways

player_data = load_json(DB_FILE)
items_db = load_json(ITEMS_FILE)
effects_db = load_json(EFFECTS_FILE)
recipes_db = load_json(RECIPES_FILE)
pathways_db = load_pathways()

def get_player(user_id):
    user_id = str(user_id)
    if user_id not in player_data:
        player_data[user_id] = {
            "balance": 120,
            "pathway": None,
            "sequence": 9,
            "acting_name": "Civilian",
            "xp": 0,
            "max_xp": 100,
            "sanity": 100,
            "inventory": [],
            "last_daily": None,
            "last_work": None,
            "last_expedition": None
        }
    if "inventory" not in player_data[user_id]:
        player_data[user_id]["inventory"] = []
    return player_data[user_id]

def get_npc(npc_id):
    if npc_id not in player_data:
        if npc_id == "will_auceptin":
            player_data[npc_id] = {
                "name": "Will Auceptin",
                "bankroll": 0,
                "wins": 0
            }
    return player_data[npc_id]

def format_currency(total_pence):
    pounds = total_pence // 240
    soli = (total_pence % 240) // 12
    pence = total_pence % 12
    parts = []
    if pounds > 0: parts.append(f"**{pounds}** Gold Pound{'s' if pounds > 1 else ''}")
    if soli > 0: parts.append(f"**{soli}** Soli")
    if pence > 0 or not parts: parts.append(f"**{pence}** Pence")
    return ", ".join(parts)

def check_cooldown(player, command_key, hours):
    last_time_str = player.get(command_key)
    if not last_time_str: return True, 0
    try: last_time = datetime.fromisoformat(last_time_str)
    except: return True, 0
    now = datetime.now()
    delta = now - last_time
    if delta >= timedelta(hours=hours): return True, 0
    return False, timedelta(hours=hours) - delta

def format_timedelta(td):
    total_seconds = int(td.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    parts = []
    if hours > 0: parts.append(f"{hours}h")
    if minutes > 0: parts.append(f"{minutes}m")
    if seconds > 0 or not parts: parts.append(f"{seconds}s")
    return " ".join(parts)

# --- Crafting Helper ---
def craft_item(player, recipe_category, recipe_id):
    recipe = recipes_db.get(recipe_category, {}).get(recipe_id)
    if not recipe: return False, "Recipe not found."
    temp_inv = player["inventory"].copy()
    for ing_id, count in recipe["ingredients"].items():
        for _ in range(count):
            if ing_id in temp_inv: temp_inv.remove(ing_id)
            else: return False, f"Missing ingredient: {items_db.get(ing_id, {}).get('name', ing_id)} (needs {count})."
    player["inventory"] = temp_inv
    return True, recipe

# --- Events ---

@bot.event
async def on_ready():
    print(f'✅ LoM RPG Bot started: {bot.user.name}')
    print(f'📚 Pathways loaded: {len(pathways_db)}')

@bot.command(name="help")
async def custom_help(ctx):
    embed = discord.Embed(title="📖 Beyonder's Handbook (Help)", color=0x34495E)
    embed.add_field(name="🧬 Progression", value="`!pathways`, `!choose [name]`, `!profile`, `!abilities`", inline=False)
    embed.add_field(name="💰 Economy", value="`!balance`, `!daily`, `!work`, `!casino`", inline=False)
    embed.add_field(name="🎒 Mysticism", value="`!expedition`, `!inventory`, `!item [name]`, `!recipes`", inline=False)
    embed.add_field(name="⚗️ Crafting", value="`!alchemy`, `!forge`", inline=False)
    if ctx.author.guild_permissions.administrator:
        embed.add_field(name="⚙️ Admin", value="`!reset`", inline=False)
    await ctx.send(embed=embed)

@bot.command(name="reset")
@commands.has_permissions(administrator=True)
async def reset_data(ctx):
    global player_data
    player_data = {}
    save_json(DB_FILE, player_data)
    await ctx.send("🧹 **SYSTEM RESET**.")

# --- RPG & Profile ---

@bot.command(name="pathways")
async def list_pathways(ctx):
    """Displays the list of loaded pathways."""
    if not pathways_db:
        return await ctx.send("❌ No pathways loaded.")
    
    description = "\n".join([f"• **{pw['name']}** (S9: {pw['sequences']['9']['name']})" for pw in pathways_db.values()])
    embed = discord.Embed(title="🌌 The Divine Pathways", description=description, color=0x3498DB)
    await ctx.send(embed=embed)

@bot.command(name="choose")
async def choose_pathway(ctx, *, name: str = None):
    player = get_player(ctx.author.id)
    if player["pathway"]: return await ctx.send("❌ Destiny is already set.")
    if name is None: return await ctx.send("❓ Usage: `!choose [pathway name]`")
    
    choice = next((pw for pw in pathways_db.values() if pw["name"].lower() == name.lower()), None)
    if choice:
        player["pathway"] = choice["name"]
        player["acting_name"] = choice["sequences"]["9"]["name"]
        player["sequence"] = 9
        save_json(DB_FILE, player_data)
        await ctx.send(f"🔮 Welcome, **{player['acting_name']}** (Pathway: {player['pathway']}).")
    else: await ctx.send("❌ Pathway not found.")

@bot.command(name="profile", aliases=["profil"])
async def profile(ctx, member: discord.Member = None):
    target = member or ctx.author
    player = get_player(target.id)
    color = 0x2ECC71 if player["pathway"] else 0x95A5A6
    embed = discord.Embed(title=f"👤 {target.display_name}", color=color)
    if target.avatar: embed.set_thumbnail(url=target.avatar.url)
    embed.add_field(name="🧬 Pathway", value=player["pathway"] or "Civilian", inline=True)
    seq_val = f"{player['acting_name']} (S{player['sequence']})" if player["pathway"] else "Civilian"
    embed.add_field(name="📜 Sequence", value=seq_val, inline=True)
    embed.add_field(name="💰 Wealth", value=format_currency(player['balance']), inline=False)
    
    # Acting bar
    acting_progress = player.get("xp", 0)
    max_xp = player.get("max_xp", 100)
    percent = min(100, int((acting_progress / max_xp) * 100))
    acting_bar = "🟢" * (percent // 10) + "⚪" * (10 - (percent // 10))
    embed.add_field(name="🎭 Acting Progress", value=f"{acting_bar} ({percent}%)", inline=False)

    sanity_bar = "🟦" * (player["sanity"] // 10) + "⬜" * (10 - (player["sanity"] // 10))
    embed.add_field(name="🧠 Sanity", value=f"{sanity_bar} ({player['sanity']}%)", inline=False)
    embed.add_field(name="🎒 Inventory", value=f"{len(player['inventory'])} items. Use `!inv`", inline=True)
    await ctx.send(embed=embed)

@bot.command(name="abilities")
async def show_abilities(ctx):
    """View your current Beyonder abilities."""
    player = get_player(ctx.author.id)
    if not player["pathway"]:
        return await ctx.send("⚠️ Civilians have no mystical abilities.")
    
    pathway = pathways_db.get(player["pathway"])
    seq_num = str(player["sequence"])
    abilities = pathway["sequences"].get(seq_num, {}).get("abilities", [])
    
    embed = discord.Embed(title=f"✨ {player['acting_name']} Abilities", color=0x9B59B6)
    embed.description = "\n".join([f"• {a}" for a in abilities]) if abilities else "None found."
    await ctx.send(embed=embed)

# --- Mysticism Commands (Placeholder/Inv) ---

@bot.command(name="inventory", aliases=["inv"])
async def inventory(ctx):
    player = get_player(ctx.author.id)
    if not player["inventory"]: return await ctx.send("🎒 Empty inventory.")
    counts = {}
    for item_id in player["inventory"]:
        name = items_db.get(item_id, {}).get("name", item_id)
        counts[name] = counts.get(name, 0) + 1
    inv_str = "\n".join([f"• {name} (x{count})" for name, count in counts.items()])
    await ctx.send(f"🎒 **{ctx.author.display_name}'s Inventory:**\n{inv_str}")

@bot.command(name="item")
async def item_info(ctx, *, name: str):
    item_id = next((k for k, v in items_db.items() if v["name"].lower() == name.lower()), None)
    if not item_id: return await ctx.send("❌ Item not found.")
    item = items_db[item_id]
    embed = discord.Embed(title=item["name"], description=item["description"], color=0xE91E63)
    if item.get("effects"):
        embed.add_field(name="Effects", value="\n".join([f"✨ {effects_db.get(e, {}).get('name', e)}" for e in item["effects"]]), inline=False)
    await ctx.send(embed=embed)

@bot.command(name="recipes")
async def show_recipes(ctx):
    embed = discord.Embed(title="📜 Book of Recipes", color=0x795548)
    for cat, items in recipes_db.items():
        text = ""
        for r_id, r in items.items():
            ings = ", ".join([f"{count}x {items_db.get(i, {}).get('name', i)}" for i, count in r['ingredients'].items()])
            text += f"• **{r['name']}** (`{r_id}`): {ings}\n"
        embed.add_field(name=cat.capitalize(), value=text or "None", inline=False)
    await ctx.send(embed=embed)

# --- Economy ---

@bot.command(name="work")
async def work(ctx):
    player = get_player(ctx.author.id)
    can_run, rem = check_cooldown(player, "last_work", 1)
    if not can_run: return await ctx.send(f"⏳ **Cooldown:** Wait **{format_timedelta(rem)}**.")
    reward = random.randint(10, 20)
    player["balance"] += reward
    player["last_work"] = datetime.now().isoformat()
    save_json(DB_FILE, player_data)
    await ctx.send(f"💼 Earned {format_currency(reward)}.")

@bot.command(name="daily")
async def daily(ctx):
    player = get_player(ctx.author.id)
    can_run, rem = check_cooldown(player, "last_daily", 24)
    if not can_run: return await ctx.send(f"⏳ **Cooldown:** Wait **{format_timedelta(rem)}**.")
    player["balance"] += 120
    player["xp"] = min(player["max_xp"], player.get("xp", 0) + 20)
    
    # Random item
    item_id = random.choice(list(items_db.keys()))
    player["inventory"].append(item_id)
    item_name = items_db[item_id]["name"]
    
    player["last_daily"] = datetime.now().isoformat()
    save_json(DB_FILE, player_data)
    await ctx.send(f"🎁 **Daily Rewards Claimed!**\n💰 +10 Soli\n🎭 +20 XP\n🎒 Found: **{item_name}**")

@bot.command(name="balance")
async def balance(ctx):
    p = get_player(ctx.author.id)
    await ctx.send(f"💰 Balance: {format_currency(p['balance'])}")

@bot.command(name="casino")
async def casino(ctx, amount: str = None):
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

@bot.command(name="will", aliases=["willinfo"])
async def will_stats(ctx):
    will = get_npc("will_auceptin")
    embed = discord.Embed(title="🧒 Will Auceptin", description="The silver-haired child.", color=0xBDC3C7)
    embed.add_field(name="💰 Wealth", value=format_currency(will["bankroll"]))
    embed.add_field(name="🏆 Wins", value=will["wins"])
    await ctx.send(embed=embed)

@bot.command(name="expedition")
async def expedition(ctx):
    player = get_player(ctx.author.id)
    can_run, rem = check_cooldown(player, "last_expedition", 3)
    if not can_run: return await ctx.send(f"⏳ **Cooldown:** Wait **{format_timedelta(rem)}**.")
    if not player["pathway"]: return await ctx.send("⚠️ Choose a pathway first.")
    
    player["last_expedition"] = datetime.now().isoformat()
    if random.random() > 0.3: # 70% success rate
        reward = random.randint(120, 480)
        xp_gain = random.randint(10, 25)
        player["balance"] += reward
        player["xp"] = min(player.get("max_xp", 100), player.get("xp", 0) + xp_gain)
        player["sanity"] = max(0, player["sanity"] - random.randint(5, 12))
        
        # Always give an item
        item_id = random.choice(list(items_db.keys()))
        player["inventory"].append(item_id)
        item_name = items_db[item_id]["name"]
        
        save_json(DB_FILE, player_data)
        await ctx.send(f"🕵️ **Expedition Success!**\n💰 Found {format_currency(reward)}.\n🎭 +{xp_gain} XP\n🎒 Loot: **{item_name}**")
    else:
        player["sanity"] = max(0, player["sanity"] - 20)
        save_json(DB_FILE, player_data)
        await ctx.send("💀 **A terrifying encounter.** You fled with barely your life, finding nothing.")

if __name__ == "__main__":
    bot.run(TOKEN)
