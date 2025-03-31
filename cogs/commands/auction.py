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
        return f'{self.order_time} {self.price} <@{self.user_id}>'

class Auction:
    def __init__(self):        
        self.auctions = {
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
    
    # A bid corresponds to the number of minutes a user is willing to be timed out for to get the role for a day
    # The higher the bid, the more time they are willing to be timed out for
    def bid(self, role, price, user_id):
        bid = Bid(price, user_id)
        self.auctions[role.title()].append(bid)
        self.auctions[role.title()].sort(reverse=True)

    # To ensure incentive compatibility, we implement the Second-Price Vickrey Auction
    # The highest bid wins, but the price is the value of the second highest bid
    def close(self):
        # Get the winning bid for each role, as well as the price
        winning_bids = {}
        for role in self.auctions.keys():
            if len(self.auctions[role]) > 0:
                winning_bid = self.auctions[role][0]
                for bid in self.auctions[role][1:]:
                    if bid.price != winning_bid.price:
                        winning_bids[role] = (winning_bid, bid.price)
                        break
                winning_bids[role] = (winning_bid, winning_bid.price)
                        
            else:
                winning_bids[role] = None

        self.open = False
        return winning_bids
    
    def __str__(self):
        """
        Role | Highest Bid (Time of bid) | Number of bids
        # You get the idea
        """

        ret_str = "📊 **Winning Bids** 📊\n\n"
        for role in self.auctions.keys():
            if len(self.auctions[role]) > 0:
                ret_str += f"{role} | {self.auctions[role][0].price} ({self.auctions[role][0].order_time}) | ({len(self.auctions[role])})\n"
            else:
                ret_str += f"{role} | No bids\n"

        return ret_str


class AuctionCog(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.auction = None

    # !auction new_auction
    @check(is_compsoc_exec_in_guild)
    @commands.hybrid_command(help=LONG_HELP_TEXT, brief=SHORT_HELP_TEXT)
    async def new_auction(self, ctx: Context):       
        self.auction = Auction()
        
        await ctx.send("Auction created")
        
    @commands.hybrid_command(help=LONG_HELP_TEXT, brief=SHORT_HELP_TEXT)
    async def view_auction(self, ctx: Context):
        if self.auction is None:
            await ctx.reply("Auction does not exist, it may have been reset", ephemeral=True)
            return
        if self.auction.open:
            await ctx.reply("Bids cannot be viewed while auction is open", ephemeral=True)
            return
        
        bids_str = str(self.auction)
        
        await ctx.reply(bids_str, ephemeral=True)
        
    @commands.hybrid_command(help=LONG_HELP_TEXT, brief=SHORT_HELP_TEXT)
    async def bid_auction(self, ctx: Context, price: int):
        """You would place a bid by using this command
        '!auction <role> <price>'
        """
        if self.auction is None:
            await ctx.reply("Auction does not exist, it may have been reset", ephemeral=True)
            return
        if not self.auction.open:
            await ctx.reply("Auction is closed", ephemeral=True)
            return
        
        self.auction.bid(price, ctx.author.id)
        
        await ctx.reply("Bid placed", ephemeral=True)
        
    @check(is_compsoc_exec_in_guild)
    @commands.hybrid_command(help=LONG_HELP_TEXT, brief=SHORT_HELP_TEXT)
    async def close_auction(self, ctx: Context):
        if self.auction is None:
            await ctx.reply("Auction does not exist, it may have been reset", ephemeral=True)
            return
        if not self.auction.open:
            await ctx.reply("Auction is closed", ephemeral=True)
            return
        
        winning_bids = self.auction.close_market()
        
        winners_str = "**Winning Users**\n"
        for role,bid in winning_bids.values():
            winners_str += f"{role}: <@{bid[0].user_id}> bid {bid[0].price} and pays {bid[1]}\n"

        self.auction.open = False
            
        await ctx.reply(winners_str, ephemeral=False)

    @check(is_compsoc_exec_in_guild)
    @commands.hybrid_command(help=LONG_HELP_TEXT, brief=SHORT_HELP_TEXT)
    async def reset(self, ctx: Context):
        self.auction = None
        await ctx.send("Auction reset")


async def setup(bot: Bot):
    await bot.add_cog(AuctionCog(bot))
