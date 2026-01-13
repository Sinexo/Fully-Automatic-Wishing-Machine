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

# Stat config
COC_STATS = ["STR", "CON", "SIZ", "DEX", "APP", "INT", "POW", "EDU"]

PATHWAY_STATS = {
    "Fool": {"INT": 3, "POW": 2},
    "Error": {"DEX": 3, "INT": 2},
    "Door": {"POW": 3, "INT": 2},
    "Visionary": {"INT": 3, "APP": 2},
    "Tyrant": {"STR": 3, "CON": 2},
    "Sun": {"POW": 3, "APP": 2},
    "Darkness": {"POW": 3, "CON": 2},
    "Death": {"CON": 3, "POW": 2},
    "Twilight Giant": {"STR": 3, "SIZ": 2},
    "Red Priest": {"STR": 2, "DEX": 2, "CON": 1},
    "Demoness": {"DEX": 3, "APP": 2},
    "Hanged Man": {"POW": 3, "CON": 2},
    "Abyss": {"CON": 3, "STR": 2},
    "Chained": {"CON": 3, "POW": 2},
    "Wheel of Fortune": {"POW": 5},
    "Hermit": {"INT": 3, "EDU": 2},
    "White Tower": {"EDU": 3, "INT": 2},
    "Black Emperor": {"INT": 3, "APP": 2},
    "Justiciar": {"POW": 3, "STR": 2},
    "Mother": {"CON": 3, "EDU": 2},
    "Moon": {"EDU": 3, "CON": 2},
    "Paragon": {"INT": 3, "EDU": 2}
}

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
            "ascension_xp": 0,
            "ascension_max_xp": 100,
            "acting_xp": 0,
            "acting_max_xp": 100,
            "sanity": 100,
            "inventory": [],
            "last_daily": None,
            "last_work": None,
            "last_expedition": None,
            "last_act": None,
            "acting_mastery": 0,
            "stats": {s: 1 for s in COC_STATS},
            "stat_points": 10  # Starting points to assign
        }
    if "stats" not in player_data[user_id]:
        player_data[user_id]["stats"] = {s: 1 for s in COC_STATS}
        # Retroactive bonuses for players who already have a pathway
        pathway = player_data[user_id].get("pathway")
        if pathway:
            bonuses = PATHWAY_STATS.get(pathway, {})
            for stat, bonus in bonuses.items():
                player_data[user_id]["stats"][stat] += bonus
            
            # Retroactive points for ascension
            levels = 9 - player_data[user_id].get("sequence", 9)
            player_data[user_id]["stat_points"] = 10 + (levels // 2)
    
    if "stat_points" not in player_data[user_id]:
        player_data[user_id]["stat_points"] = 10
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
    embed.add_field(name="🧬 Progression", value="`!pathways`, `!choose [name]`, `!profile`, `!abilities`, `!act`, `!advance`, `!stat [name]` (New!)", inline=False)
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
        player["acting_mastery"] = 0
        
        # Apply Pathway Bonuses
        bonuses = PATHWAY_STATS.get(choice["name"], {})
        for stat, bonus in bonuses.items():
            player["stats"][stat] += bonus
            
        save_json(DB_FILE, player_data)
        await ctx.send(f"🔮 Welcome, **{player['acting_name']}** (Pathway: {player['pathway']}).\nYour characteristics have been enhanced!")
    else: await ctx.send("❌ Pathway not found.")

@bot.command(name="profile", aliases=["profil"])
async def profile(ctx, member: discord.Member = None):
    target = member or ctx.author
    player = get_player(target.id)
    color = 0x2ECC71 if player["pathway"] else 0x95A5A6
    embed = discord.Embed(title=f"👤 {target.display_name}", color=color)
    if target.avatar: embed.set_thumbnail(url=target.avatar.url)
    
    pathway_name = player["pathway"] or "Civilian"
    acting_title = player["acting_name"] if player["pathway"] else "Civilian"
    
    embed.add_field(name="🧬 Pathway", value=f"**{pathway_name}**", inline=True)
    embed.add_field(name="📜 Current Title", value=f"**{acting_title}**", inline=True)
    embed.add_field(name="💰 Wealth", value=format_currency(player['balance']), inline=False)
    
    # 1. Ascension Progress (XP to next sequence)
    asc_xp = player.get("ascension_xp", 0)
    asc_max = player.get("ascension_max_xp", 100)
    asc_percent = min(100, int((asc_xp / asc_max) * 100))
    asc_bar = "🔶" * (asc_percent // 10) + "🔸" * (10 - (asc_percent // 10))
    embed.add_field(name=f"🆙 Ascension (Sequence {player['sequence']})", value=f"{asc_bar} ({asc_percent}%)", inline=False)

    # 2. Acting Digestion (XP for the role)
    act_xp = player.get("acting_xp", 0)
    act_max = player.get("acting_max_xp", 100)
    acting_percent = min(100, int((act_xp / act_max) * 100))
    acting_bar = "🟢" * (acting_percent // 10) + "⚪" * (10 - (acting_percent // 10))
    embed.add_field(name="🎭 Acting Digestion", value=f"{acting_bar} ({acting_percent}%)", inline=False)

    # 3. Sanity Bar
    sanity = player.get("sanity", 100)
    sanity_bar = "🟦" * (sanity // 10) + "⬜" * (10 - (sanity // 10))
    embed.add_field(name="🧠 Sanity", value=f"{sanity_bar} ({sanity}%)", inline=False)
    
    embed.add_field(name="🎒 Inventory", value=f"{len(player['inventory'])} items. Use `!inv`", inline=True)
    
    # 4. Characteristics
    stats = player.get("stats", {s: 1 for s in COC_STATS})
    stats_str = "\n".join([f"**{s}**: {stats.get(s,1)}" for s in COC_STATS])
    embed.add_field(name="📊 Characteristics", value=stats_str, inline=True)
    
    points = player.get("stat_points", 0)
    if points > 0:
        embed.set_footer(text=f"✨ You have {points} stat points! Use !stat to open the menu.")
    
    await ctx.send(embed=embed)

@bot.command(name="stat")
async def assign_stat_menu(ctx):
    """Open an interactive menu to assign stat points."""
    player = get_player(ctx.author.id)
    points = player.get("stat_points", 0)
    
    if points <= 0:
        return await ctx.send("❌ You have no stat points to assign.")

    class StatView(discord.ui.View):
        def __init__(self, user_id):
            super().__init__(timeout=60)
            self.user_id = user_id
            for stat in COC_STATS:
                self.add_item(self.create_button(stat))

        def create_button(self, stat_name):
            button = discord.ui.Button(label=stat_name, style=discord.ButtonStyle.primary, custom_id=stat_name)
            
            async def callback(interaction: discord.Interaction):
                if interaction.user.id != self.user_id:
                    return await interaction.response.send_message("❌ This is not your menu.", ephemeral=True)
                
                player = get_player(self.user_id)
                if player["stat_points"] <= 0:
                    return await interaction.response.edit_message(view=None)
                
                player["stats"][stat_name] += 1
                player["stat_points"] -= 1
                save_json(DB_FILE, player_data)
                
                # Update embed
                new_embed = self.create_embed(player)
                if player["stat_points"] <= 0:
                    await interaction.response.edit_message(embed=new_embed, view=None)
                    self.stop()
                else:
                    await interaction.response.edit_message(embed=new_embed)
            
            button.callback = callback
            return button

        def create_embed(self, player):
            embed = discord.Embed(title="📊 Characteristics Management", color=0x3498DB)
            stats = player["stats"]
            stats_str = "\n".join([f"**{s}**: {stats.get(s,1)}" for s in COC_STATS])
            embed.add_field(name="Stats", value=stats_str, inline=True)
            embed.add_field(name="Available Points", value=f"✨ **{player['stat_points']}**", inline=True)
            embed.set_footer(text="Click a button to add +1 point")
            return embed

    view = StatView(ctx.author.id)
    embed = view.create_embed(player)
    await ctx.send(embed=embed, view=view)

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
    player["ascension_xp"] = min(player.get("ascension_max_xp", 100), player.get("ascension_xp", 0) + 20)
    player["acting_xp"] = min(player.get("acting_max_xp", 100), player.get("acting_xp", 0) + 15)
    
    # Random item
    item_id = random.choice(list(items_db.keys()))
    player["inventory"].append(item_id)
    item_name = items_db[item_id]["name"]
    
    player["last_daily"] = datetime.now().isoformat()
    save_json(DB_FILE, player_data)
    await ctx.send(f"🎁 **Daily Rewards Claimed!**\n💰 +10 Soli\n� +20 Ascension XP\n🎭 +15 Acting XP\n🎒 Found: **{item_name}**")

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
        acting_gain = random.randint(5, 15)
        sanity_loss = random.randint(3, 5)
        player["balance"] += reward
        player["ascension_xp"] = min(player.get("ascension_max_xp", 100), player.get("ascension_xp", 0) + xp_gain)
        player["acting_xp"] = min(player.get("acting_max_xp", 100), player.get("acting_xp", 0) + acting_gain)
        player["sanity"] = max(0, player["sanity"] - sanity_loss)
        
        # Always give an item
        item_id = random.choice(list(items_db.keys()))
        player["inventory"].append(item_id)
        item_name = items_db[item_id]["name"]
        
        save_json(DB_FILE, player_data)
        await ctx.send(f"🕵️ **Expedition Success!**\n💰 Found {format_currency(reward)}.\n� +{xp_gain} XP\n🎭 +{acting_gain} Acting\n🧠 Sanity: -{sanity_loss}%\n🎒 Loot: **{item_name}**")
    else:
        # Decreasing probability for higher sanity loss (6 to 20)
        sanity_loss = 6 + int(14 * (random.random()**2))
        player["sanity"] = max(0, player["sanity"] - sanity_loss)
        
        failure_lore = [
            "The fog thickened, and you heard whispers in a language that doesn't exist.",
            "A pair of vertical pupils watched you from the darkness between the trees.",
            "You found a mirror in the ruins, but the reflection didn't move when you did.",
            "The walls began to bleed a silver liquid, and the air grew thin.",
            "You stepped on a shadow that felt like flesh. You didn't stay to find out what it was."
        ]
        
        critical_lore = [
            "The stars moved. No, the sky itself blinked. You have seen something no mortal should witness.",
            "You felt a cold hand wrap around your heart, squeezing tight. A piece of your soul stayed behind in that place.",
            "The Ravings of the Abyss echoed in your mind, shattering your perception of reality.",
            "You encountered a figure with no face, wearing your own clothes. It smiled with its entire body."
        ]
        
        msg = "❌ **Expedition Failed!**\n"
        if sanity_loss >= 18:
            msg += f"⚠️ **CRITICAL FAILURE!** *\"{random.choice(critical_lore)}\"*\nYour mind is screaming in agony."
        else:
            msg += f"💀 **A terrifying encounter.** *\"{random.choice(failure_lore)}\"*"
        
        msg += f"\n\n🧠 Sanity: -{sanity_loss}%"
        save_json(DB_FILE, player_data)
        await ctx.send(msg)

@bot.command(name="act")
async def act(ctx):
    """Perform a ritual of Acting to digest your potion."""
    player = get_player(ctx.author.id)
    if not player["pathway"]:
        return await ctx.send("⚠️ Civilians have no role to act. Choose a pathway first.")

    can_run, rem = check_cooldown(player, "last_act", 12)
    if not can_run:
        return await ctx.send(f"⏳ **Cooldown:** You must wait **{format_timedelta(rem)}** before acting again.")

    pathway = pathways_db.get(player["pathway"])
    seq_num = str(player["sequence"])
    seq_name = player["acting_name"]
    
    # Mastery logic
    mastery = player.get("acting_mastery", 0)
    # Thresholds to level up mastery (gradually harder)
    # 0 -> 1: 3 acts, 1 -> 2: 7 acts, 2 -> 3: 15 acts
    thresholds = [3, 7, 15, 30, 50]
    mastery_level = sum(1 for t in thresholds if mastery >= t)
    
    # Lore phrases mapping (Fallback for generic names)
    lore_map = {
        "Seer": [
            "You sit in front of a crystal ball, the flickering candlelight casting long shadows.",
            "You read the tea leaves of a local baker, whispering of a fortune they don't yet understand.",
            "The spirit world whispers to you; you listen carefully, maintaining the stoic face of a Seer."
        ],
        "Clown": [
            "You perform a perfect somersault, your exaggerated smile masking the sharp focus in your eyes.",
            "You juggle three daggers for a crowd, each catch a precise movement of balance.",
            "Behind the makeup, you observe the world's absurdity, embracing the role of the fool."
        ],
        "Magician": [
            "You snap your fingers, and a small flame dances across your knuckles before vanishing.",
            "You pull a bouquet of paper roses from an empty hat, much to the delight of the street orphans.",
            "The boundary between trickery and mysticism blurs as you perform your daily 'miracles'."
        ],
        "Marauder": [
            "You slip through the shadows, your fingers light as air as you 'borrow' a trinket from a corrupt noble.",
            "You observe a target from the rooftops, calculating the exact moment their guard will drop.",
            "The thrill of the theft pulses in your veins, but you remain as silent as a ghost."
        ],
        "Apprentice": [
            "You touch the surface of a locked door, sensing the intricate mechanism with your spirit vision.",
            "You meticulously record the patterns of the stars, seeking the hidden exits of the world.",
            "You practice the art of 'arrival,' stepping through a threshold that wasn't there a moment ago."
        ],
        "Bard": [
            "You sing a hymn to the Eternal Blazing Sun, your voice carrying a warmth that calms the weary.",
            "Your music weaves a tapestry of light, warding off the creeping chill of the night.",
            "You praise the dawn, each note a prayer to the divinity that fuels your spirit."
        ]
    }

    # Default lore if not explicitly defined
    default_lore = [
        f"You immerse yourself in the life of a {seq_name}, strictly following the principles of the role.",
        f"You perform the daily duties of a {seq_name}, feeling the potion in your blood begin to settle.",
        f"The principles of a {seq_name} are clear to you now; you act with conviction and purpose."
    ]

    lore_list = lore_map.get(seq_name, default_lore)
    phrase = random.choice(lore_list)

    # Calculate rewards
    # Base reward increases with mastery
    base_gain = random.randint(20, 35)
    bonus = int(base_gain * (mastery_level * 0.5)) # +50% per mastery level
    total_gain = base_gain + bonus
    
    player["acting_xp"] = min(player.get("acting_max_xp", 100), player.get("acting_xp", 0) + total_gain)
    player["acting_mastery"] = mastery + 1
    player["last_act"] = datetime.now().isoformat()
    
    # Check for mastery level up message
    new_mastery_level = sum(1 for t in thresholds if player["acting_mastery"] >= t)
    mastery_msg = ""
    if new_mastery_level > mastery_level:
        mastery_msg = "\n✨ *\"Your understanding of the acting principles of your sequences has grown, you'll act better next time.\"*"

    embed = discord.Embed(title=f"🎭 Acting: {seq_name}", description=f"*{phrase}*", color=0x1ABC9C)
    embed.add_field(name="📈 Progress", value=f"**+{total_gain}** Acting XP")
    if mastery_msg:
        embed.set_footer(text="A sudden realization washes over you.")
    
    save_json(DB_FILE, player_data)
    await ctx.send(embed=embed, content=mastery_msg if mastery_msg else None)

@bot.command(name="advance")
async def advance_sequence(ctx):
    """Consume the next sequence potion to advance your divinity."""
    player = get_player(ctx.author.id)
    if not player["pathway"]:
        return await ctx.send("⚠️ You are but a civilian. Use `!choose` to start your journey.")

    current_seq = player["sequence"]
    if current_seq <= 0:
        return await ctx.send("🌌 You have already reached the pinnacle of divinity.")

    next_seq = current_seq - 1
    pathway_name = player["pathway"]
    pathway = pathways_db.get(pathway_name)
    next_seq_data = pathway["sequences"].get(str(next_seq))

    if not next_seq_data:
        return await ctx.send(f"❌ Sequence {next_seq} for {pathway_name} is not yet implemented.")

    # Find the potion in inventory
    # Following the naming convention in recipes.json (e.g., clown_potion)
    # We look for an item that matches the next sequence's name or a dedicated potion item
    potion_id = f"{next_seq_data['name'].lower().replace(' ', '_')}_potion"
    
    if potion_id not in player["inventory"]:
        # Fallback: check if they have any item named "X Potion" where X is the seq name
        potion_id = next((item for item in player["inventory"] if next_seq_data['name'].lower() in item.lower() and "potion" in item.lower()), None)
    
    if not potion_id:
        return await ctx.send(f"⚠️ You need the **{next_seq_data['name']} Potion** to advance.")

    # Calculate Sanity Loss
    acting_percent = (player.get("acting_xp", 0) / player.get("acting_max_xp", 100)) * 100
    
    if acting_percent >= 100:
        sanity_loss = random.randint(10, 35) # Acting is 100% -> Max 35% loss
    else:
        sanity_loss = random.randint(20, 75)

    # Apply changes
    player["inventory"].remove(potion_id)
    player["sequence"] = next_seq
    player["acting_name"] = next_seq_data["name"]
    player["acting_xp"] = 0 # Reset acting for the new potion
    player["acting_mastery"] = 0 # Reset mastery for the new role
    player["ascension_xp"] = 0 # Reset ascension xp
    
    # Gain 1 stat point every 2 levels (Sequence 7, 5, 3, 1)
    levels_ascended = 9 - next_seq
    if levels_ascended % 2 == 0:
        player["stat_points"] = player.get("stat_points", 0) + 1
        
    player["sanity"] = max(0, player["sanity"] - sanity_loss)

    save_json(DB_FILE, player_data)

    embed = discord.Embed(title="🌌 Ascension Successful!", color=0x9B59B6)
    embed.description = f"You have consumed the **{next_seq_data['name']} Potion**.\n Your soul screams as it reshapes itself to hold more divinity."
    embed.add_field(name="📜 New Sequence", value=f"S{next_seq}: **{player['acting_name']}**", inline=True)
    embed.add_field(name="🧠 Sanity Loss", value=f"-{sanity_loss}%", inline=True)
    
    if acting_percent < 100:
        embed.set_footer(text="The remains of the previous potion fought against the new one. Your mind is fragile.")
    else:
        embed.set_footer(text="The transition was stabilized by your perfect acting. You feel more solid.")

    await ctx.send(embed=embed)

if __name__ == "__main__":
    bot.run(TOKEN)
