import discord
import os
import asyncio 
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_BOT_TOKEN")

intents = discord.Intents.default()
intents.message_content = True  
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")

async def load_cogs():
    try:
        await bot.load_extension("stock")
        print("✅ Stock cog loaded successfully")
    except Exception as e:
        print(f"❌ Failed to load stock cog: {e}")

    try:
        await bot.load_extension("portfolio")
        print("✅ Portfolio cog loaded successfully")
    except Exception as e:
        print(f"❌ Failed to load portfolio cog: {e}")

# Run bot asynchronously
async def main():
    async with bot:
        await load_cogs()  
        await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())





