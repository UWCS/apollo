from datetime import datetime
from discord.ext import commands
from discord.ext.commands import Context, Bot, CommandError, check
import discord

from config import CONFIG
from models import db_session, Blacklist, User

class BlacklistError(CommandError):
    message = None
    def __init__(self, message=None, *args):
        self.message = message
        super().__init__(*args)

def is_blacklist_admin():
    async def predicate(ctx: Context):
        if not discord.utils.get(ctx.message.author.roles, name=CONFIG['BOT_ADMIN_ROLE']) is not None:
            await ctx.message.delete()
            raise BlacklistError(message='That command can only be run by the "{role}" role, <@{user_id}>.'.format(user_id=ctx.message.author.id,role=CONFIG['BOT_ADMIN_ROLE']))
        else:
            return True

    return check(predicate)

# Classname set to Blklist to not clash with SQL model name "Blacklist" (it broke everything)
class Blklist:
    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.group(help="Query and amend the karma blacklist.")
    async def blacklist(self, ctx: Context):
        if not ctx.invoked_subcommand:
            await ctx.send("Subcommand not found")

    @blacklist.command(help="Add a word to the karma blacklist.")
    @is_blacklist_admin()
    async def add(self, ctx: Context, item: str):
        authorid = db_session.query(User).filter(User.user_uid==ctx.message.author.id).first().id
        
        if not db_session.query(Blacklist).filter(Blacklist.name==item).all():
            blacklist = Blacklist(name=item, added_by=authorid, added_at=datetime.utcnow())
            db_session.add(blacklist)
            db_session.commit()
            await ctx.send(f'Added {item} to the karma blacklist. :flag_black:')
        else:
            await ctx.send(f'{item} is already in the karma blacklist. :page_with_curl:')

    @blacklist.command(help="Remove a word from the karma blacklist.")
    @is_blacklist_admin()
    async def remove(self, ctx: Context, item: str):
        if not db_session.query(Blacklist).filter(Blacklist.name==item).all():
            await ctx.send(f'{item} is not in the karma blacklist. :page_with_curl:')
        else:
            db_session.query(Blacklist).filter(Blacklist.name==item).delete()
            db_session.commit()
            await ctx.send(f'{item} has been removed from the karma blacklist. :flag_white:')

    @blacklist.command(help="List all blacklisted karma items.")
    @is_blacklist_admin()
    async def list(self, ctx: Context):
        blk_lst = f'The items in the karma blacklist are:\n\n'
        items = db_session.query(Blacklist).all()
        for item in items:
            blk_lst += f' • **{item.name}**\n'
        await ctx.send(blk_lst)

    @blacklist.command(help="Search for a blacklisted karma item.")
    async def search(self, ctx: Context, item: str):
        item_repl = item.replace('*','%')
        items = db_session.query(Blacklist).filter(Blacklist.name.ilike(f'%{item_repl}%')).all()        
        if len(items) == 0:
            await ctx.send(f'There were no items matching "{item}" in the blacklist. :sweat:')
        else:
            if len(items) == 1:
                blk_lst = f'The item matching "{item}" in the blacklist is:\n\n'
            else:
                blk_lst = f'The items matching "{item}" in the blacklist are:\n\n'

            # Don't want to spam too much on a search
            max_len = 10
            for it in items:
                if max_len > 0:
                    blk_lst += f' • **{it.name}**\n'
                else:
                    break
                max_len -= 1

            await ctx.send(blk_lst)

    @list.error
    @add.error
    @remove.error
    async def blacklist_error_handler(self, ctx: Context, error: BlacklistError):
        await ctx.send(error.message)

def setup(bot: Bot):
    bot.add_cog(Blklist(bot))

