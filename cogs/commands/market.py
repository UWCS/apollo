import heapq
import time
from collections import defaultdict

from discord.ext import commands
from discord.ext.commands import Bot, Context, check, clean_content

from utils.utils import is_compsoc_exec_in_guild

LONG_HELP_TEXT = """
Create a Market to Trade!
"""

SHORT_HELP_TEXT = """Make the bot repeat after you."""


class Order:
    def __init__(self, price, order_type, user_id, qty, order_time):
        self.user_id = user_id
        self.price = price
        self.order_type = order_type
        self.qty = qty
        self.order_time = order_time
        
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
        return f'{self.order_type} {self.qty}@<@{self.price}> <@{self.user_id}>'

class Market:
    def __init__(self, stock_name):        
        self.stock_name = stock_name
        self.bids: list[Order] = []
        self.asks: list[Order] = []
        
        self.trade_history: dict[str, list[Order]] = {}
        
        self.last_trade = None
        self.open = True
        
    def bid(self, price, user_id, qty, time=time.time()):
        heapq.heappush(self.bids, Order(price, 'bid', user_id, qty, time))
        return self.match()
        
    def ask(self, price, user_id, qty, time=time.time()):
        heapq.heappush(self.asks, Order(price, 'ask', user_id, qty, time))
        return self.match()
        
    def match(self):
        matched = []
        while len(self.bids) > 0 and len(self.asks) > 0 and self.bids[0].price >= self.asks[0].price:
            bid = heapq.heappop(self.bids)
            ask = heapq.heappop(self.asks)
            qty = min(bid.qty, ask.qty)
            
            if bid.user_id not in self.trade_history:
                self.trade_history[bid.user_id] = []
                
            if ask.user_id not in self.trade_history:
                self.trade_history[ask.user_id] = []
                
            earliest_trade = min(bid, ask, key=lambda x: x.order_time)
            
            bid.price = earliest_trade.price
            ask.price = earliest_trade.price

            bought = Order(earliest_trade.price, 'bid', bid.price, qty, bid.order_time)
            sold   = Order(earliest_trade.price, 'ask', ask.user_id, qty, ask.order_time)
                
            self.trade_history[bid.user_id].append(bought)
            self.trade_history[ask.user_id].append(sold)
            
            self.last_trade = f"<@{bid.user_id}> bought {qty} from <@{ask.user_id}> at {bid.price}"

            if ask.qty > qty:
                heapq.heappush(self.asks, Order(ask.price, 'ask', ask.user_id, ask.qty - qty, ask.order_time))
            elif bid.qty > qty:
                heapq.heappush(self.bids, Order(bid.price, 'bid', bid.user_id, bid.qty - qty, bid.order_time))

            matched.append(self.last_trade)

        return "\n".join(matched) if len(matched) > 0 else None
            
            
            
    def close_market(self, valuation):
        user_to_profit = {}
        for user in self.trade_history:
            closing = valuation * sum(trade.qty if trade.order_type == 'bid' else -trade.qty for trade in self.trade_history[user])
            # Note: accumulating _value_ not position, so signs are reversed
            pnl = sum(trade.price * (trade.qty if trade.order_type == 'ask' else -trade.qty) for trade in self.trade_history[user])
            user_to_profit[user] = closing + pnl
       
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

        # Count bids and asks and sum quantity for each price level
        bid_counts = defaultdict(lambda: [0,0])
        ask_counts = defaultdict(lambda: [0,0])
        for bid in self.bids:
            level = bid_counts[bid.price]
            level[0] += 1
            level[1] += bid.qty
        for ask in self.asks:
            level = ask_counts[ask.price]
            level[0] += 1
            level[1] += ask.qty

        # Get price levels; highest first
        all_prices = sorted(set(bid_counts.keys()).union(set(ask_counts.keys())), reverse=True)

        # Build string
        order_book_lines = []
        if len(all_prices) == 0:
            order_book_lines.append("No outstanding orders\n")
        else:
            order_book_lines.append("```")
            order_book_lines.append(f"{'Bid Orders':<15} | {'Bid Volume':<15} | {'Price':<10} | {'Ask Volume':<15} | {'Ask Orders'}")

            for price in all_prices:
                bid_vol = bid_counts.get(price, [" " * 15] * 2)
                ask_vol = ask_counts.get(price, [" " * 10] * 2)
                formatted_price = f"{price:.2f}"
                order_book_lines.append(f"{str(bid_vol[0])} | {str(bid_vol[1]):<15} | {str(formatted_price):<10} | {str(ask_vol[1]):<15} | {str(ask_vol)[0]}")

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
    async def bid_market(self, ctx: Context, price: float, qty: int, *, market: clean_content):
        """You would place a bid by using this command
        '!bid_market 123.4 15 "AAPL"'
        """
        if market not in self.live_markets:
            await ctx.reply("Market does not exist", ephemeral=True)
            return
        
        market_obj = self.live_markets[market]

        if not market_obj.is_open():
            await ctx.reply("Market is closed", ephemeral=True)
            return
        
        did_trade = market_obj.bid(price, ctx.author.id, qty)
        
        await ctx.reply("Bid placed", ephemeral=True)
        
        if did_trade is not None:
            await ctx.reply(did_trade, ephemeral=False)
        
    @commands.hybrid_command(help=LONG_HELP_TEXT, brief=SHORT_HELP_TEXT)
    async def ask_market(self, ctx: Context, price: float, qty: int, *, market: clean_content):
        """You would place a bid by using this command
        '!ask_market 123.4 15 "AAPL"'
        """

        if market not in self.live_markets:
            await ctx.reply("Market does not exist", ephemeral=True)
            return

        market_obj = self.live_markets[market]

        if not market_obj.is_open():
            await ctx.reply("Market is closed", ephemeral=True)
            return
        
        
        did_trade = market_obj.ask(price, ctx.author.id, qty)
        
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
        user_asks = "\n".join(f"{trade.qty}@{trade.price}" for trade in user_trades if trade.order_type == 'ask')
        user_bids = "\n".join(f"{trade.qty}@{trade.price}" for trade in user_trades if trade.order_type == 'bid')
        net = sum(trade.qty if trade.order_type == 'bid' else -trade.qty for trade in user_trades)
        
        positions = f"Positions for <@{ctx.author.id}> in {market_obj.stock_name}\n"
        positions += f"Net position: {net}\n"
        positions += f"Bids\n{user_bids}"
        positions += f"Asks\n{user_asks}"
        
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
