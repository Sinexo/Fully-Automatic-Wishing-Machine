import discord
from discord.ext import commands
from config import PATHWAY_STATS, COC_STATS, STAT_NAMES, DB_FILE
from data_manager import get_player, pathways_db, save_json, player_data
from utils import format_currency

class Profile(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="pathways")
    async def list_pathways(self, ctx):
        """Displays the list of loaded pathways."""
        if not pathways_db:
            return await ctx.send("❌ No pathways loaded.")
        
        description = "\n".join([f"• **{pw['name']}** (S9: {pw['sequences']['9']['name']})" for pw in pathways_db.values()])
        embed = discord.Embed(title="🌌 The Divine Pathways", description=description, color=0x3498DB)
        await ctx.send(embed=embed)

    @commands.command(name="choose")
    async def choose_pathway(self, ctx, *, name: str = None):
        player = get_player(ctx.author.id)
        if player["pathway"]: return await ctx.send("❌ Destiny is already set.")
        if name is None: return await ctx.send("❓ Usage: `!choose [pathway name]`")
        
        choice = next((pw for pw in pathways_db.values() if pw["name"].lower() == name.lower()), None)
        if choice:
            player["pathway"] = choice["name"]
            if player.get("affiliation") == "Neutral":
                player["affiliation"] = "Unofficial Beyonder"
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

    @commands.command(name="profile", aliases=["profil"])
    async def profile(self, ctx, member: discord.Member = None):
        target = member or ctx.author
        player = get_player(target.id)
        color = 0x2ECC71 if player["pathway"] else 0x95A5A6
        embed = discord.Embed(title=f"👤 {target.display_name}", color=color)
        if target.avatar: embed.set_thumbnail(url=target.avatar.url)
        
        pathway_name = player["pathway"] or "Civilian"
        acting_title = player["acting_name"] if player["pathway"] else "Civilian"
        
        # 1. Player Level & XP
        level = player.get("level", 1)
        xp = player.get("xp", 0)
        max_xp = player.get("max_xp", 100)
        xp_percent = min(100, int((xp / max_xp) * 100))
        xp_bar = "" * (xp_percent // 10) + "⬛" * (10 - (xp_percent // 10))
        
        embed.add_field(name=f"🆙 Level {level}", value=f"{xp_bar} ({xp_percent}%)\n{xp}/{max_xp} XP", inline=False)
        
        # 2. Beyonder Status
        embed.add_field(name="🧬 Pathway", value=f"**{pathway_name}**", inline=True)
        embed.add_field(name="📜 Sequence", value=f"**S{player['sequence']}**: {acting_title}", inline=True)
        embed.add_field(name="🤝 Affiliation", value=f"**{player.get('affiliation', 'Neutral')}**", inline=True)
        embed.add_field(name="💰 Wealth", value=format_currency(player['balance']), inline=True)
        
        # 3. Acting
        act_xp = player.get("acting_xp", 0)
        act_max = player.get("acting_max_xp", 200)
        acting_percent = min(100, int((act_xp / act_max) * 100))
        acting_bar = "🟢" * (acting_percent // 10) + "⚪" * (10 - (acting_percent // 10))
        embed.add_field(name="🎭 Digestion", value=f"{acting_bar} ({acting_percent}%)", inline=True)

        # 4. Sanity Bar
        sanity = player.get("sanity", 100)
        sanity_bar = "🟦" * (sanity // 10) + "🖤" * (10 - (sanity // 10))
        embed.add_field(name="🧠 Sanity", value=f"{sanity_bar} ({sanity}%)", inline=True)
        
        embed.add_field(name="🎒 Inventory", value=f"{len(player['inventory'])} items. Use `!inv`", inline=True)
        
        # 5. Stats
        stats = player.get("stats", {s: 1 for s in COC_STATS})
        mid = len(COC_STATS) // 2
        stats_col1 = "\n".join([f"**{STAT_NAMES.get(s, s)}**: {stats.get(s,1)}" for s in COC_STATS[:mid]])
        stats_col2 = "\n".join([f"**{STAT_NAMES.get(s, s)}**: {stats.get(s,1)}" for s in COC_STATS[mid:]])
        
        embed.add_field(name="📊 Statistiques", value=stats_col1, inline=True)
        embed.add_field(name="\u200b", value=stats_col2, inline=True)
        
        points = player.get("stat_points", 0)
        if points > 0:
            embed.set_footer(text=f"✨ You have {points} stat points! Use !stats to open the menu.")
        
        await ctx.send(embed=embed)

    @commands.command(name="stats", aliases=["stat"])
    async def assign_stat_menu(self, ctx):
        """Open an interactive menu to assign stat points."""
        player = get_player(ctx.author.id)
        points = player.get("stat_points", 0)
        
        if points <= 0:
            return await ctx.send("❌ You have no stat points to assign.")

        view = StatView(ctx.author.id)
        embed = view.create_embed(player)
        await ctx.send(embed=embed, view=view)

    @commands.command(name="abilities")
    async def show_abilities(self, ctx):
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


class StatView(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.history = [] # Track changes for undo
        for stat in COC_STATS:
            self.add_item(self.create_stat_button(stat))
        self.add_item(self.create_undo_button())

    def create_stat_button(self, stat_name):
        button = discord.ui.Button(label=stat_name, style=discord.ButtonStyle.primary)
        
        async def callback(interaction: discord.Interaction):
            if interaction.user.id != self.user_id:
                return await interaction.response.send_message("❌ This is not your menu.", ephemeral=True)
            
            player = get_player(self.user_id)
            if player["stat_points"] <= 0:
                return await interaction.response.edit_message(view=None)
            
            player["stats"][stat_name] += 1
            player["stat_points"] -= 1
            self.history.append(stat_name)
            save_json(DB_FILE, player_data)
            
            await interaction.response.edit_message(embed=self.create_embed(player), view=self)
        
        button.callback = callback
        return button

    def create_undo_button(self):
        button = discord.ui.Button(label="↩️ Undo", style=discord.ButtonStyle.danger)
        
        async def callback(interaction: discord.Interaction):
            if interaction.user.id != self.user_id:
                return await interaction.response.send_message("❌ This is not your menu.", ephemeral=True)
            
            if not self.history:
                return await interaction.response.send_message("❌ Nothing to undo.", ephemeral=True)
            
            player = get_player(self.user_id)
            last_stat = self.history.pop()
            player["stats"][last_stat] -= 1
            player["stat_points"] += 1
            save_json(DB_FILE, player_data)
            
            await interaction.response.edit_message(embed=self.create_embed(player), view=self)
            
        button.callback = callback
        return button

    def create_embed(self, player):
        embed = discord.Embed(title="📊 Characteristics Management", color=0x3498DB)
        stats = player["stats"]
        stats_str = "\n".join([f"**{s}**: {stats.get(s,1)}" for s in COC_STATS])
        embed.add_field(name="Stats", value=stats_str, inline=True)
        embed.add_field(name="Available Points", value=f"✨ **{player['stat_points']}**", inline=True)
        embed.set_footer(text="Click a button to add +1 | Use Undo to revert session changes")
        return embed

async def setup(bot):
    await bot.add_cog(Profile(bot))
