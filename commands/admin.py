from discord.ext import commands
from discord.ext.commands import Context, Bot

from config import CONFIG
from models import db_session, Blacklist, User

class Admin:
    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.command(help="Add a word to the karma blacklist.")
    @commands.has_role(CONFIG['BOT_ADMIN_ROLE'])
    async def blacklist_add(self, ctx: Context, item: str):
        authorid = db_session.query(User).filter(User.user_uid==ctx.message.author.id).first().id
        
        if not db_session.query(Blacklist).filter(Blacklist.name==item).all():
            blacklist = Blacklist(name=item, added_by=authorid)
            db_session.add(blacklist)
            db_session.commit()
            await ctx.send(f'Added {item} to blacklist.')
        else:
            await ctx.send(f'{item} already in blacklist.')

def setup(bot: Bot):
    bot.add_cog(Admin(bot))
