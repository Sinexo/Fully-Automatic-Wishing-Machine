import discord
from discord.ext import commands
from datetime import datetime
import random
from config import DB_FILE
from data_manager import get_player, save_json, player_data, items_db, pathways_db
from utils import check_cooldown, format_timedelta, format_currency, gain_xp

class Adventure(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="expedition")
    async def expedition(self, ctx):
        player = get_player(ctx.author.id)
        can_run, rem = check_cooldown(player, "last_expedition", 3)
        if not can_run: return await ctx.send(f"⏳ **Cooldown:** Wait **{format_timedelta(rem)}**.")
        if not player["pathway"]: return await ctx.send("⚠️ Choose a pathway first.")
        
        player["last_expedition"] = datetime.now().isoformat()
        if random.random() > 0.3: # 70% success rate
            reward = random.randint(120, 480)
            xp_gain = random.randint(20, 40)
            acting_gain = random.randint(5, 15)
            sanity_loss = random.randint(3, 5)
            player["balance"] += reward
            
            leveled, new_lvl = gain_xp(player, xp_gain)
            player["acting_xp"] = min(player.get("acting_max_xp", 200), player.get("acting_xp", 0) + acting_gain)
            player["sanity"] = max(0, player["sanity"] - sanity_loss)
            
            # Always give an item
            item_id = random.choice(list(items_db.keys()))
            player["inventory"].append(item_id)
            item_name = items_db[item_id]["name"]
            
            save_json(DB_FILE, player_data)
            
            msg = f"🕵️ **Expedition Success!**\n💰 Found {format_currency(reward)}.\n🆙 +{xp_gain} XP\n🎭 +{acting_gain} Acting\n🧠 Sanity: -{sanity_loss}%\n🎒 Loot: **{item_name}**"
            if leveled:
                msg += f"\n\n🎊 **LEVEL UP!** You are now level **{new_lvl}**!"
            await ctx.send(msg)
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

    @commands.command(name="act")
    async def act(self, ctx):
        """Perform a ritual of Acting to digest your potion."""
        player = get_player(ctx.author.id)
        if not player["pathway"]:
            return await ctx.send("⚠️ Civilians have no role to act. Choose a pathway first.")

        can_run, rem = check_cooldown(player, "last_act", 12)
        if not can_run:
            return await ctx.send(f"⏳ **Cooldown:** You must wait **{format_timedelta(rem)}** before acting again.")

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
        
        player["acting_xp"] = min(player.get("acting_max_xp", 200), player.get("acting_xp", 0) + total_gain)
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

    @commands.command(name="advance")
    async def advance_sequence(self, ctx):
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
        acting_percent = (player.get("acting_xp", 0) / player.get("acting_max_xp", 200)) * 100
        
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
        
        # Set new acting max xp for the sequence (gets harder)
        player["acting_max_xp"] = 200 + ((9 - next_seq) * 100)
        
        player["sanity"] = max(0, player["sanity"] - sanity_loss)

        save_json(DB_FILE, player_data)

        embed = discord.Embed(title="🌌 Sequence Advancement!", color=0x9B59B6)
        embed.description = f"You have consumed the **{next_seq_data['name']} Potion**.\nYour soul screams as it reshapes itself to hold more divinity."
        embed.add_field(name="📜 New Sequence", value=f"S{next_seq}: **{player['acting_name']}**", inline=True)
        embed.add_field(name="🧠 Sanity Loss", value=f"-{sanity_loss}%", inline=True)
        
        if acting_percent < 100:
            embed.set_footer(text="The remaining will of the potion fought against yours. You barely advanced without losing control, your mind is fragile.")
        else:
            embed.set_footer(text="The transition was stabilized by your perfect acting. You feel more solid.")

        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Adventure(bot))
