from discord.ext import commands
from discord.ext.commands import Bot, Context, clean_content

from discord import File as discord_file
from discord.ui import View as button_view
from discord.ui import button as button, Button as Button
from discord import Interaction

import chess.pgn
import chess.svg

from io import StringIO, BytesIO
from cairosvg import svg2png



LONG_HELP_TEXT = """
Make the bot repeat after you.
"""

SHORT_HELP_TEXT = """Make the bot repeat after you."""


class ButtonInteractions(button_view): 
    
    def __init__(self, board):
        super().__init__()
        self.board = board
        self.forward_stack = []
    @button(label="<-")
    async def left(self, interaction: Interaction, button : Button):
        if not self.board.move_stack:
            button.disabled = True
            if self.forward_stack:
                self.children[1].disabled = False
            else:
                self.children[1].disabled = True
            await self.message.edit(view=self)
            await interaction.response.edit_message()
            return
        self.forward_stack.append(self.board.peek())
        self.board.pop()
        self.children[1].disabled = False
        svg_board = chess.svg.board(self.board)
        bytesImage = BytesIO(svg2png(bytestring=svg_board))
        exporter = chess.pgn.StringExporter(headers=True, variations=True, comments=True)
        pgn = chess.pgn.Game.from_board(self.board).accept(exporter)
        img = discord_file(bytesImage, filename="board.png", description=pgn)
        await self.message.edit(view=self)
        await interaction.response.edit_message(attachments=[img])


    @button(label="->")
    async def right(self, interaction: Interaction, button : Button):
        if not self.forward_stack:
            self.children[1].disabled = True;
            if self.board.move_stack:
                self.children[0].disabled = False
            else:
                self.children[0].disabled = True
            await self.message.edit(view=self)
            await interaction.response.edit_message()
            return

        self.board.push(self.forward_stack.pop())
        self.children[0].disabled = False
        svg_board = chess.svg.board(self.board)
        bytesImage = BytesIO(svg2png(bytestring=svg_board))
        exporter = chess.pgn.StringExporter(headers=True, variations=True, comments=True)
        pgn = chess.pgn.Game.from_board(self.board).accept(exporter)
        img = discord_file(bytesImage, filename="board.png", description=pgn)
        await self.message.edit(view=self)
        await interaction.response.edit_message(attachments=[img])


class Chess(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot


    @commands.hybrid_command(help=LONG_HELP_TEXT, brief=SHORT_HELP_TEXT)
    async def read(self, ctx: Context):
        message = await ctx.channel.fetch_message(ctx.message.reference.message_id)
        print(message.attachments[0].description)



    @commands.hybrid_command(help=LONG_HELP_TEXT, brief=SHORT_HELP_TEXT)
    async def chess(self, ctx: Context, *, pgn: str):

        pgnIO = StringIO(pgn)
        
        game = chess.pgn.read_game(pgnIO)
        board = game.board()
        
        for move in game.mainline_moves():
            board.push(move)
        
        view = ButtonInteractions(board)
        svg_board = chess.svg.board(board)
        bytesImage = BytesIO(svg2png(bytestring=svg_board))
        img = discord_file(bytesImage, filename="board.png", description=pgn)
        message = await ctx.send(file=img, view=view)
        view.message = message
        await view.wait()

    # def load_game(self, pgn):

async def setup(bot: Bot):
    await bot.add_cog(Chess(bot))
