from discord.ext import commands, tasks
from discord.ext.commands import Bot, Context, clean_content
from discord.ui import Button, View, button, TextInput, text_input
from discord import Interaction

LONG_HELP_TEXT = """
Create a Market to Trade!
"""

SHORT_HELP_TEXT = """Make the bot repeat after you."""

import heapq
import time

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
                
            self.trade_history[bid.user_id].append(ask)
            self.trade_history[ask.user_id].append(bid)
            
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
            
        return user_to_profit
    
    def current_bids(self):
        return list(self.bids)
    
    def current_asks(self):
        return list(self.asks)
    
    def __str__(self):
        best_bid = str(round(self.bids[0].price, 2)) if len(self.bids) > 0 else 'None'
        best_ask = str(round(self.asks[0].price, 2)) if len(self.asks) > 0 else 'None'
        
        return_string = f"{self.stock_name}\n"
        return_string += "Best Bid: " + best_bid + "\n"
        return_string += "Best Ask: " + best_ask + "\n"
        return_string += "Last Trade: " + str(self.last_trade)
        
        return return_string
    
    
    
class MarketCog(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.live_markets = {}

    # !market new_market "Stock Name"
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
