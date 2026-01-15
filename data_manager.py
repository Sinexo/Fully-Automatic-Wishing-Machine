import json
import os
from config import DB_FILE, ITEMS_FILE, EFFECTS_FILE, RECIPES_FILE, PATHWAYS_DIR, COC_STATS, PATHWAY_STATS

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

# Global Data Containers
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
            "level": 1,
            "xp": 0,
            "max_xp": 100,
            "acting_xp": 0,
            "acting_max_xp": 200,
            "sanity": 100,
            "inventory": [],
            "last_daily": None,
            "last_work": None,
            "last_expedition": None,
            "last_act": None,
            "acting_mastery": 0,
            "affiliation": "Neutral",
            "stats": {s: 1 for s in COC_STATS},
            "stat_points": 10  # Starting points to assign
        }
    
    player = player_data[user_id]
    
    # --- Migrations & Defaults ---
    if "level" not in player:
        player["level"] = 1
    if "xp" not in player:
        # Migrate old ascension_xp if it exists
        player["xp"] = player.get("ascension_xp", 0)
    if "max_xp" not in player:
        player["max_xp"] = player.get("ascension_max_xp", 100)
    
    # Cleanup old keys
    if "ascension_xp" in player: del player["ascension_xp"]
    if "ascension_max_xp" in player: del player["ascension_max_xp"]

    if "stats" not in player:
        player["stats"] = {s: 1 for s in COC_STATS}
        # Retroactive bonuses for players who already have a pathway
        pathway = player.get("pathway")
        if pathway:
            bonuses = PATHWAY_STATS.get(pathway, {})
            for stat, bonus in bonuses.items():
                player["stats"][stat] += bonus
            
            # Retroactive points for ascension
            seq_levels = 9 - player.get("sequence", 9)
            player["stat_points"] = 10 + (seq_levels // 2)
    
    if "stat_points" not in player:
        player["stat_points"] = 10
    if "affiliation" not in player:
        player["affiliation"] = "Neutral"
    if "inventory" not in player:
        player["inventory"] = []
    
    return player

def get_npc(npc_id):
    if npc_id not in player_data:
        if npc_id == "will_auceptin":
            player_data[npc_id] = {
                "name": "Will Auceptin",
                "bankroll": 0,
                "wins": 0
            }
    return player_data[npc_id]
