from datetime import datetime, timedelta
from data_manager import recipes_db, items_db

def gain_xp(player, amount):
    """Adds XP to the player and handles leveling up. Returns (leveled_up, new_level)"""
    player["xp"] += amount
    leveled_up = False
    while player["xp"] >= player["max_xp"]:
        player["xp"] -= player["max_xp"]
        player["level"] += 1
        # Increase max xp for next level (e.g., +20%)
        player["max_xp"] = int(player["max_xp"] * 1.2)
        # Grant 2 stat points every 5 levels
        if player["level"] % 5 == 0:
            player["stat_points"] += 2
        leveled_up = True
    return leveled_up, player["level"]

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
