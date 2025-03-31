import time

from discord.ext import commands
from discord.ext.commands import Bot, Context, check

from utils.utils import is_compsoc_exec_in_guild

LONG_HELP_TEXT = """
Place a bid on an Exec position!
"""

SHORT_HELP_TEXT = """Make the bot repeat after you."""


class Bid:
    def __init__(self, price, user_id):
        self.user_id = user_id
        self.price = price
        self.order_time = time.time()
        
    def __lt__(self, other):
        if self.price == other.price:
            return self.order_time > other.order_time
        return self.price < other.price
        
    def __eq__(self, other):
        return self.price == other.price and self.order_time == other.order_time
    
    def __gt__(self, other):
        if self.price == other.price:
            return self.order_time < other.order_time
        return self.price > other.price
        
    def __str__(self):
        return f'{self.order_time} <@{self.price}> <@{self.user_id}>'

class Bids:
    def __init__(self):        
        self.bids = {
            "President" : [],
            "Treasurer" : [],
            "Welfare" : [],
            "Secretary" : [],
            "Events" : [],
            "Academic" : [],
            "Gaming" : [],
            "Gender Inclusivity" : [],
            "Social" : [],
            "Sports" : [],
            "Tech" : [],
            "Publicity" : []
        }
        self.open = True
        
    def bid(self, role, price, user_id):
        bid = Bid(price, user_id)
        self.bids[role.title()].append(bid)
        self.bids[role.title()].sort(reverse=True)
        return bid.order_time
            
    def close(self, valuation):
        # Get the highest and earliest bid for each role
        winning_bids = {}
        for role in self.bids.keys():
            if len(winning_bids[role]) > 0:
                winning_bids[role] = self.bids[role][0]
            else:
                winning_bids[role] = None

        self.open = False
        return winning_bids
    
    def __str__(self):
        """
        Role | Highest Bid (Time of bid) | Number of bids
        # You get the idea
        """

        ret_str = "📊 **Current Winning Bids** 📊\n\n"
        for role in self.bids.keys():
            if len(self.bids[role]) > 0:
                ret_str += f"{role} | {self.bids[role][0].price} ({self.bids[role][0].order_time}) | ({len(self.bids[role])})\n"
            else:
                ret_str += f"{role} | No bids\n"

        return ret_str


class BidCog(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.bids = None

    # !bid new_bid
    @check(is_compsoc_exec_in_guild)
    @commands.hybrid_command(help=LONG_HELP_TEXT, brief=SHORT_HELP_TEXT)
    async def new_market(self, ctx: Context):       
        self.bids = Bids()
        
        await ctx.send("Bidding created")
        
    @commands.hybrid_command(help=LONG_HELP_TEXT, brief=SHORT_HELP_TEXT)
    async def view_market(self, ctx: Context):
        if self.bids is None:
            await ctx.reply("Bidding does not exist, it may have been reset", ephemeral=True)
            return
        
        bids_str = str(self.bids)
        
        await ctx.reply(bids_str, ephemeral=True)
        
    @commands.hybrid_command(help=LONG_HELP_TEXT, brief=SHORT_HELP_TEXT)
    async def bid_market(self, ctx: Context, price: float):
        """You would place a bid by using this command
        '!bid <role> <price>'
        """
        if self.bids is None:
            await ctx.reply("Bidding does not exist, it may have been reset", ephemeral=True)
            return
        if not self.bids.open:
            await ctx.reply("Bidding is closed", ephemeral=True)
            return
        
        placed_bid = self.bids.bid(price, ctx.author.id)
        
        await ctx.reply("Bid placed", ephemeral=True)
        
        if placed_bid is not None:
            await ctx.reply(placed_bid, ephemeral=False)
        
    @check(is_compsoc_exec_in_guild)
    @commands.hybrid_command(help=LONG_HELP_TEXT, brief=SHORT_HELP_TEXT)
    async def close_market(self, ctx: Context, valuation: float):
        if self.bids is None:
            await ctx.reply("Bidding does not exist, it may have been reset", ephemeral=True)
            return
        if not self.bids.open:
            await ctx.reply("Bidding is closed", ephemeral=True)
            return
        
        winning_bids = self.bids.close_market(valuation)
        
        winners_str = "**Winning Users**\n"
        for role,bid in winning_bids.values():
            winners_str += f"{role}: <@{bid.user_id}> ({bid.price})\n"

        self.bids.open = False
            
        await ctx.reply(winners_str, ephemeral=False)

    @check(is_compsoc_exec_in_guild)
    @commands.hybrid_command(help=LONG_HELP_TEXT, brief=SHORT_HELP_TEXT)
    async def reset(self, ctx: Context):
        self.bids = None
        await ctx.send("Bidding reset")


async def setup(bot: Bot):
    await bot.add_cog(BidCog(bot))
