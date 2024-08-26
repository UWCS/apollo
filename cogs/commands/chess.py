from discord.ext import commands
from discord.ext.commands import Bot, Context, clean_content

from discord import File as discord_file, Interaction, SelectOption
from discord.ui import View, Select, button, Button, select 
from collections import defaultdict

import chess.pgn
import chess.svg

from io import StringIO, BytesIO
from cairosvg import svg2png



LONG_HELP_TEXT = """
Make the bot repeat after you.
"""

SHORT_HELP_TEXT = """Make the bot repeat after you."""

piece_mappings = {"B":"Bishop", "K": "King", "P": "Pawn", "N":"Knight", "R": "Rook", "Q":"Queen"}



# class RankSelection(Select):
#     def __init__(self, legal_moves):
#         moves = [SelectOption(label=piece_mappings[str(move)],value=move) for move in legal_moves]
#         super().__init__(options=moves, placeholder="Select Piece", max_values=1)

#     async def select_piece(self):


class FileSelection(Select):
    def __init__(self,legal_moves, piece):
        
        moves = [SelectOption(label=move,value=move) for move in legal_moves[piece]]
        super().__init__(options=moves, placeholder="Select Piece", max_values=1)
    



class PieceSelection(Select):
    def __init__(self,legal_moves):
        self.legal_moves = legal_moves 
        moves = [SelectOption(label=piece_mappings[move],value=move) for move in legal_moves.keys()]
        super().__init__(options=moves, placeholder="Select Piece", max_values=1)

    async def callback(self, interaction: Interaction):
        self.placeholder = piece_mappings[self.values[0]]
        await self.view.respond_piece(interaction, self.values[0], self.legal_moves)
        await interaction.response.defer()
        
        
        
        




class ButtonInteractions(View): 
    
    def __init__(self, board):
        super().__init__()
        self.board = board
        self.forward_stack = []

    async def reload_board(self, interaction: Interaction):
        svg_board = chess.svg.board(self.board)
        bytesImage = BytesIO(svg2png(bytestring=svg_board))

        exporter = chess.pgn.StringExporter(headers=True, variations=True, comments=True)
        pgn = chess.pgn.Game.from_board(self.board).accept(exporter)

        img = discord_file(bytesImage, filename="board.png", description=pgn)
        await self.message.edit(view=self)
        await interaction.response.edit_message(attachments=[img])

    async def respond_piece(self, interaction: Interaction, select_items: Select, legal_moves):
        self.children[2].disabled = True
        file_selection = FileSelection(legal_moves, select_items)
        self.add_item(file_selection)
        await interaction.message.edit(view=self)

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
        self.reload_board(interaction)
    

        

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
        
        self.reload_board(interaction)




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
        # [str(move)[0:2], str(move)[2:]]
        legal_moves = defaultdict(list)
        for move in board.legal_moves:
            square = chess.parse_square(str(move)[:2])
            piece = board.piece_at(square=square)
            legal_moves[str(piece)].append(str(move))
        view = ButtonInteractions(board)
        view.add_item(PieceSelection(legal_moves))
        svg_board = chess.svg.board(board)
        bytesImage = BytesIO(svg2png(bytestring=svg_board))
        img = discord_file(bytesImage, filename="board.png", description=pgn)
        message = await ctx.send(file=img, view=view)
        view.message = message
        await view.wait()

    # def load_game(self, pgn):

async def setup(bot: Bot):
    await bot.add_cog(Chess(bot))
