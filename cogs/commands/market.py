import heapq
import time

from discord.ext import commands
from discord.ext.commands import Bot, Context, check, clean_content

from utils.utils import is_compsoc_exec_in_guild

LONG_HELP_TEXT = """
Create a Market to Trade!
"""

SHORT_HELP_TEXT = """Make the bot repeat after you."""


class Order:
    def __init__(self, price, order_type, user_id):
        self.user_id = user_id
        self.price = price
        self.order_type = order_type
        self.order_time = time.time()
        
    def __lt__(self, other):
        if self.order_type == 'ask':
            # if bidding you want to buy, highest bid first (so lower)
            return self.price < other.price or (self.price == other.price and self.order_time < other.order_time)
        else:
            return self.price > other.price or (self.price == other.price and self.order_time < other.order_time)
        
    def __eq__(self, other):
        return self.price == other.price and self.order_time == other.order_time
    
    def __gt__(self, other):
        if self.order_type == 'ask':
            return self.price > other.price or (self.price == other.price and self.order_time > other.order_time)
        else:
            return self.price < other.price or (self.price == other.price and self.order_time > other.order_time)
        
    def __str__(self):
        return f'{self.order_type} <@{self.price}> <@{self.user_id}>'

class Market:
    def __init__(self, stock_name):        
        self.stock_name = stock_name
        self.bids: list[Order] = []
        self.asks: list[Order] = []
        
        self.trade_history: dict[str, list[Order]] = {}
        
        self.last_trade = None
        self.open = True
        
    def bid(self, price, user_id):
        self.bids.append(Order(price, 'bid', user_id))
        heapq.heapify(self.bids)
        return self.match()
        
    def ask(self, price, user_id):
        self.asks.append(Order(price, 'ask', user_id))
        heapq.heapify(self.asks)
        return self.match()
        
    def match(self):
        if len(self.bids) == 0 or len(self.asks) == 0:
            return None
        
        if self.bids[0].price >= self.asks[0].price:
            bid = heapq.heappop(self.bids)
            ask = heapq.heappop(self.asks)
            
            if bid.user_id not in self.trade_history:
                self.trade_history[bid.user_id] = []
                
            if ask.user_id not in self.trade_history:
                self.trade_history[ask.user_id] = []
                
            earliest_trade = min(bid, ask, key=lambda x: x.order_time)
            
            bid.price = earliest_trade.price
            ask.price = earliest_trade.price
                
            self.trade_history[bid.user_id].append(bid)
            self.trade_history[ask.user_id].append(ask)
            
            self.last_trade = f"<@{bid.user_id}> bought from <@{ask.user_id}> at {bid.price}"
            
            return self.last_trade
        return None
            
            
            
    def close_market(self, valuation):
        user_to_profit = {}
        for user in self.trade_history:
            user_valuation = 0
            for trade in self.trade_history[user]:
                if trade.order_type == 'bid':
                    user_valuation -= trade.price
                    user_valuation += valuation
                else:
                    user_valuation += trade.price
                    user_valuation -= valuation
                    
            user_to_profit[user] = user_valuation
        
        self.open = False
            
        return user_to_profit

    def is_open(self):
        return self.open
    
    def current_bids(self):
        return list(self.bids)
    
    def current_asks(self):
        return list(self.asks)
    
    def __str__(self):
        """
        Want something of the format:
        # Market Status
        (whether market is open or closed)

        # Order Book
        bid volume (no. of bids) | price | ask volume (no. of asks)
        123                      | 20.25 | 321
        (blank - no bids)        | 10.10 | 123
        123                      | 5.20  | (blank - no asks)

        # Previous Trades
        (whatever)
        """

        ret_str = "Market is: "
        ret_str += "OPEN\n\n" if self.open else "CLOSED\n\n"

        # Count bids and asks for each price level
        bid_counts = {}
        ask_counts = {}
        for bid in self.bids:
            bid_counts[bid.price] = bid_counts.get(bid.price, 0) + 1
        for ask in self.asks:
            ask_counts[ask.price] = ask_counts.get(ask.price, 0) + 1

        # Get price levels; highest first
        all_prices = sorted(set(bid_counts.keys()).union(set(ask_counts.keys())), reverse=True)

        # Build string
        order_book_lines = []
        if len(all_prices) == 0:
            order_book_lines.append("No outstanding orders\n")
        else:
            order_book_lines.append("```")
            order_book_lines.append(f"{'Bid Volume':<15} | {'Price':<10} | {'Ask Volume'}")

            for price in all_prices:
                bid_vol = bid_counts.get(price, " " * 15)
                ask_vol = ask_counts.get(price, " " * 10)
                formatted_price = f"{price:.2f}"
                order_book_lines.append(f"{str(bid_vol):<15} | {str(formatted_price):<10} | {str(ask_vol)}")

            order_book_lines.append("```")

        ret_str += f"📊 **{self.stock_name} Order Book** 📊\n" + "\n".join(order_book_lines) + "\n"

        # TODO: Orders done; now previous trades
        ret_str += f"Last Trade: {self.last_trade}"
        return ret_str


class MarketCog(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.live_markets = {}

    # !market new_market "Stock Name"
    @check(is_compsoc_exec_in_guild)
    @commands.hybrid_command(help=LONG_HELP_TEXT, brief=SHORT_HELP_TEXT)
    async def new_market(self, ctx: Context, *, market: clean_content):
        if market in self.live_markets:
            await ctx.send("Market already exists")
            return
        
        market_obj = Market(market)
        self.live_markets[market] = market_obj
        
        await ctx.send(f"Market created '{market}'")
        
    @commands.hybrid_command(help=LONG_HELP_TEXT, brief=SHORT_HELP_TEXT)
    async def view_market(self, ctx: Context, *, market: clean_content):
        if market not in self.live_markets:
            await ctx.reply("Market does not exist", ephemeral=True)
            return
        
        market_obj = self.live_markets[market]
        
        market_str = str(market_obj)
        
        await ctx.reply(market_str, ephemeral=True)
        
    @commands.hybrid_command(help=LONG_HELP_TEXT, brief=SHORT_HELP_TEXT)
    async def bid_market(self, ctx: Context, price: float, *, market: clean_content):
        """You would place a bid by using this command
        '!bid_market 100 "AAPL"'
        """
        if market not in self.live_markets:
            await ctx.reply("Market does not exist", ephemeral=True)
            return
        
        market_obj = self.live_markets[market]

        if not market_obj.is_open():
            await ctx.reply("Market is closed", ephemeral=True)
            return
        
        did_trade = market_obj.bid(price, ctx.author.id)
        
        await ctx.reply("Bid placed", ephemeral=True)
        
        if did_trade is not None:
            await ctx.reply(did_trade, ephemeral=False)
        
    @commands.hybrid_command(help=LONG_HELP_TEXT, brief=SHORT_HELP_TEXT)
    async def ask_market(self, ctx: Context, price: float, *, market: clean_content):
        if market not in self.live_markets:
            await ctx.reply("Market does not exist", ephemeral=True)
            return

        market_obj = self.live_markets[market]

        if not market_obj.is_open():
            await ctx.reply("Market is closed", ephemeral=True)
            return
        
        
        did_trade = market_obj.ask(price, ctx.author.id)
        
        await ctx.reply("Ask placed", ephemeral=True)
        
        if did_trade is not None:
            await ctx.reply(did_trade, ephemeral=False)
        
    @commands.hybrid_command(help=LONG_HELP_TEXT, brief=SHORT_HELP_TEXT)
    async def positions_market(self, ctx: Context, *, market: clean_content):
        if market not in self.live_markets:
            await ctx.reply("Market does not exist", ephemeral=True)
            return
        
        market_obj = self.live_markets[market]
        
        user_trades = market_obj.trade_history.get(ctx.author.id, [])
        user_asks = [trade.price for trade in user_trades if trade.order_type == 'ask']
        user_bids = [trade.price for trade in user_trades if trade.order_type == 'bid']
        
        positions = f"Positions for <@{ctx.author.id}> in {market_obj.stock_name}\n"
        positions += "Bids\n"
        positions += "\n".join([str(bid) for bid in user_bids])
        positions += "\n\nAsks\n"
        positions += "\n".join([str(ask) for ask in user_asks])
        
        await ctx.reply(str(positions), ephemeral=True)
        
    @check(is_compsoc_exec_in_guild)
    @commands.hybrid_command(help=LONG_HELP_TEXT, brief=SHORT_HELP_TEXT)
    async def close_market(self, ctx: Context, valuation: float, *, market: clean_content):
        if market not in self.live_markets:
            await ctx.reply("Market does not exist", ephemeral=True)
            return
        
        market_obj = self.live_markets[market]
        
        user_to_profit = market_obj.close_market(valuation)
        
        profit_str = "User profits\n"
        for user in user_to_profit:
            profit_str += f"<@{user}>: {user_to_profit[user]}\n"
            
        await ctx.reply(profit_str, ephemeral=False)


async def setup(bot: Bot):
    await bot.add_cog(MarketCog(bot))
