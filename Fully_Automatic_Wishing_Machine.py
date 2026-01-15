import discord
from discord.ext import commands
from config import TOKEN

# Bot configuration
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

@bot.event
async def on_ready():
    # This might conflict with the Basic cog's on_ready, but usually both run.
    # However, to be clean, let's keep the extension loading log here.
    print(f'🤖 Bot is ready: {bot.user.name}')

async def load_extensions():
    # Load cogs
    initial_extensions = [
        'cogs.basic',
        'cogs.profile',
        'cogs.economy',
        'cogs.adventure',
        'cogs.inventory'
    ]
    for extension in initial_extensions:
        try:
            await bot.load_extension(extension)
            print(f'✅ Loaded extension: {extension}')
        except Exception as e:
            print(f'❌ Failed to load extension {extension}: {e}')

# Main execution
if __name__ == "__main__":
    import asyncio
    async def main():
        async with bot:
            await load_extensions()
            await bot.start(TOKEN)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        # Handle ctrl-c gracefully
        pass
