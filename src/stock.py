import yfinance as yf
import aiohttp 
from discord.ext import commands

class Stock(commands.Cog):
    """Handles stock price commands"""

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def price(self, ctx, symbol: str):
        """Fetches and displays the latest stock price"""
        try:
            stock_info = yf.Ticker(symbol)
            price = stock_info.history(period="1d")["Close"].iloc[-1]
            currency = stock_info.info.get("currency", "USD")
            await ctx.send(f"📈 {symbol.upper()} is currently **${price:.2f} {currency}**")
        except Exception as e:
            await ctx.send(f"❌ Could not fetch data for {symbol.upper()}")

    @commands.command()
    async def news(self, ctx, symbol: str,  num: int = 3):
        """Fetches latest news articles about a stock"""
        url = f"https://news.google.com/rss/search?q={symbol}+stock&hl=en-US&gl=US&ceid=US:en"

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    await ctx.send(f"❌ Could not fetch news for {symbol.upper()}")
                    return
                
                text = await response.text()

                import xml.etree.ElementTree as ET
                root = ET.fromstring(text)
                items = root.findall(".//item")

                if not items:
                    await ctx.send(f"❌ No news found for {symbol.upper()}")
                    return
                
                news_links = [f"🔗 [{item.find('title').text}]({item.find('link').text})" for item in items[:num]]

                await ctx.send(f"📰 Latest news for {symbol.upper()}:\n" + "\n".join(news_links))

    @commands.command()
    async def commands(self, ctx):
        """Displays the help command list"""
        help_text = """
        **Available Commands:**

        - `!commands`: Display all commands.
        - `!price <symbol>`: Fetches the latest stock price for `<symbol>`.
        - `!news <symbol>`: Fetches the latest news articles about `<symbol>`.
        - `!news <symbol> <count>`: Fetches the latest `<count>` news articles about `<symbol>` (default is 3).
        - `!portfolio`: Displays your current portfolio and holdings.
        - `!myNews`: Fetches news about each of your portfolio holdings.
        - `!buy <symbol> <amount>`: Buy `<amount>` of `<symbol>` and add to your portfolio.
        - `!sell <symbol> <amount>`: Sell `<amount>` of `<symbol>` and subtract from your portfolio.
        - `!resetportfolio`: Deletes your entire portfolio.

        """
        await ctx.send(help_text)
    

# Add cog to bot (async version)
async def setup(bot):
    await bot.add_cog(Stock(bot))
