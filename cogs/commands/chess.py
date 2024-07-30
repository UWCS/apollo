from discord.ext import commands
from discord.ext.commands import Bot, Context, clean_content

# import chess
from discord.file import File
import chess.pgn
import chess.svg
from io import StringIO, BytesIO
from cairosvg import svg2png

from PIL import Image as PilImage
from PIL.PngImagePlugin import PngInfo




LONG_HELP_TEXT = """
Make the bot repeat after you.
"""

SHORT_HELP_TEXT = """Make the bot repeat after you."""


class Chess(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.hybrid_command(help=LONG_HELP_TEXT, brief=SHORT_HELP_TEXT)
    async def chess(self, ctx: Context, *, pgn: str):
        
        pgnIO = StringIO(pgn)
        
        game = chess.pgn.read_game(pgnIO)
        board = game.board()
        
        for move in game.mainline_moves():
            board.push(move)
        
        svg_board = chess.svg.board(board)
        bytesImage = BytesIO(svg2png(bytestring=svg_board))
        img = PilImage.open(bytesImage)

        # metadata = PngInfo()
        # metadata.add_text("MyNewString", pgn)
        bytesImg = BytesIO() 
        img.save(bytesImg, format='PNG')
        print(bytesImg)
        img_file= File(bytesImg, filename="chess.png")

        await ctx.send(file=img_file)

    # def load_game(self, pgn):

async def setup(bot: Bot):
    await bot.add_cog(Chess(bot))
