import asyncpg
from discord.ext import commands
import yfinance as yf
import os
import matplotlib.pyplot as plt
import io
import discord
import aiohttp 

DB_URL = os.getenv("DATABASE_URL")

class Portfolio(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.pool = None
        bot.loop.create_task(self.setup_db())

    async def setup_db(self):
        """Initializes the connection pool and creates table if not exists."""
        self.pool = await asyncpg.create_pool(dsn=DB_URL)
        async with self.pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS portfolio (
                    user_id BIGINT,
                    symbol TEXT,
                    shares REAL,
                    PRIMARY KEY (user_id, symbol)
                );
            """)

    @commands.command()
    async def buy(self, ctx, symbol: str, amount: float):
        """Buy a number of shares of a stock"""
        symbol = symbol.upper()
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO portfolio (user_id, symbol, shares)
                VALUES ($1, $2, $3)
                ON CONFLICT (user_id, symbol)
                DO UPDATE SET shares = portfolio.shares + EXCLUDED.shares;
            """, ctx.author.id, symbol, amount)
        await ctx.send(f"✅ Bought {amount} shares of {symbol}.")

    @commands.command()
    async def sell(self, ctx, symbol: str, amount: float):
        """Sell a number of shares of a stock"""
        symbol = symbol.upper()
        async with self.pool.acquire() as conn:
            result = await conn.fetchrow("SELECT shares FROM portfolio WHERE user_id = $1 AND symbol = $2", ctx.author.id, symbol)
            if not result or result["shares"] < amount:
                await ctx.send("❌ Not enough shares to sell.")
                return

            await conn.execute("UPDATE portfolio SET shares = shares - $1 WHERE user_id = $2 AND symbol = $3", amount, ctx.author.id, symbol)
            await conn.execute("DELETE FROM portfolio WHERE shares <= 0;")
        await ctx.send(f"✅ Sold {amount} shares of {symbol}.")

    @commands.command()
    async def portfolio(self, ctx):
        """Display your current portfolio and total value, with a visual pie chart"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("SELECT symbol, shares FROM portfolio WHERE user_id = $1", ctx.author.id)
            if not rows:
                await ctx.send("📭 Your portfolio is empty.")
                return

        total_value = 0
        symbols = []
        values = []
        message = f"📊 **{ctx.author.name}'s Portfolio:**\n"

        for row in rows:
            symbol = row["symbol"]
            shares_count = row["shares"]
            try:
                price = yf.Ticker(symbol).history(period="1d")["Close"].iloc[-1]
                value = shares_count * price
                total_value += value
                symbols.append(symbol)
                values.append(value)
                message += f"• {symbol}: {shares_count:.2f} @ ${price:.2f} = **${value:.2f}**\n"
            except:
                message += f"• {symbol}: {shares_count:.2f} — price unavailable\n"

        message += f"\n💰 **Total Value:** ${total_value:,.2f}"

        # Create a pie chart visualizing the portfolio
        fig, ax = plt.subplots(figsize=(8, 5))
        ax.pie(values, labels=symbols, autopct='%1.1f%%', startangle=90, colors=plt.cm.Paired.colors)

        ax.set_title(f'{ctx.author.name} Portfolio Value Breakdown')

        # Save the chart to a bytes buffer
        buf = io.BytesIO()
        plt.tight_layout()
        plt.savefig(buf, format='png')
        buf.seek(0)

        # Send the chart as an image in the Discord message
        file = discord.File(buf, filename="portfolio_pie_chart.png")
        await ctx.send(message, file=file)

        buf.close()


    @commands.command()
    async def myNews(self, ctx, num: int = 3):
        """Fetches the latest news articles about all stocks in the user's portfolio"""

        # Fetch the portfolio for the user
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("SELECT symbol FROM portfolio WHERE user_id = $1", ctx.author.id)
            if not rows:
                await ctx.send("📭 Your portfolio is empty.")
                return

        # List of all stock symbols in the portfolio
        symbols = [row["symbol"] for row in rows]
        news_links = []

        # Fetch news for each symbol
        for symbol in symbols:
            url = f"https://news.google.com/rss/search?q={symbol}+stock&hl=en-US&gl=US&ceid=US:en"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        news_links.append(f"❌ Could not fetch news for {symbol.upper()}")
                        continue
                    
                    import xml.etree.ElementTree as ET
                    text = await response.text()
                    root = ET.fromstring(text)
                    items = root.findall(".//item")

                    if not items:
                        await ctx.send(f"❌ No news found for {symbol.upper()}")
                        return
                
                    news_links = [f"🔗 [{item.find('title').text}]({item.find('link').text})" for item in items[:num]]

                    await ctx.send(f"📰 Latest news for {symbol.upper()}:\n" + "\n".join(news_links))

    @commands.command()
    async def resetportfolio(self, ctx):
        """Deletes all holdings for your user"""
        async with self.pool.acquire() as conn:
            await conn.execute("DELETE FROM portfolio WHERE user_id = $1", ctx.author.id)
        await ctx.send("🧼 Your portfolio has been reset.")

# Async cog setup
async def setup(bot):
    await bot.add_cog(Portfolio(bot))
