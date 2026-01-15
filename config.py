import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# File Paths
DB_FILE = "data.json"
ITEMS_FILE = "items.json"
EFFECTS_FILE = "effects.json"
RECIPES_FILE = "recipes.json"
PATHWAYS_DIR = "pathways"

# Stat config
COC_STATS = ["STR", "CON", "SIZ", "DEX", "APP", "INT", "POW", "EDU"]
STAT_NAMES = {
    "STR": "Strength",
    "CON": "Constitution",
    "SIZ": "Size",
    "DEX": "Dexterity",
    "APP": "Appearance",
    "INT": "Intelligence",
    "POW": "Power",
    "EDU": "Education"
}

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
