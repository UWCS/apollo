from discord.ext import commands
from discord.ext.commands import Bot, Context, clean_content

from discord import File as discord_file, Interaction, SelectOption
from discord.ui import View, Select, button, Button, select
from collections import defaultdict
from math import ceil

import chess.pgn
import chess.svg

from io import StringIO, BytesIO
from cairosvg import svg2png



LONG_HELP_TEXT = """
Make the bot repeat after you.
"""

SHORT_HELP_TEXT = """Make the bot repeat after you."""

piece_mappings = {"B":"Bishop", "K": "King", "P": "Pawn", "N":"Knight", "R": "Rook", "Q":"Queen",
                    "b":"Bishop", "k": "King", "p": "Pawn", "n":"Knight", "r": "Rook", "q":"Queen"
                }




class FileSelection(Select):
    def __init__(self, legal_moves, piece):

        self.items_per_page = 25
        
        self.page = -1
        
        
        super().__init__(options=self.switch_page(legal_moves, piece), placeholder="Select a Square")
    
    def switch_page(self, legal_moves, piece):
        self.generate_legal_moves_by_piece(legal_moves, piece)
        self.page = (self.page + 1) % ceil(len(self.moves)/self.items_per_page)    
        start = self.page * self.items_per_page
        end = start + self.items_per_page if len(self.moves) > start + self.items_per_page else len(self.moves)
        return self.moves[start:end]

    def generate_legal_moves_by_piece(self, legal_moves, piece):
        self.moves = [SelectOption(label=move,value=move) for move in legal_moves[piece]] 
        return self.moves
    
    async def callback(self, interaction: Interaction):
        await self.view.play_move(self.values[0], interaction)



class PieceSelection(Select):
    def __init__(self, legal_moves):
        super().__init__(options=self.generate_select_pieces(legal_moves), max_values=1, placeholder="Select Piece")
    
    def generate_select_pieces(self, legal_moves):
        return [SelectOption(label=piece_mappings[move],value=move) for move in legal_moves.keys()]


    async def callback(self, interaction: Interaction):
        self.placeholder = piece_mappings[self.values[0]]
        await self.view.select_piece_respond(interaction, self.values[0])
        await interaction.response.defer()
        
        
class MoveSelectionNext(Button):

    def __init__(self,piece):
        self.piece = piece
        super().__init__(label=">", row=3)

    async def callback(self, interaction: Interaction):
        
        await self.view.refresh_select_menu(self.piece)
        await interaction.response.edit_message(view=self.view)


class ButtonInteractions(View): 
    
    def __init__(self, board):
        super().__init__()
        
        self.board = board
        self.legal_moves = self.calculate_legal_moves()

        self.prev_move_btn = self.children[0]
        self.next_move_btn = self.children[1]
        self.select_piece_menu = PieceSelection(self.legal_moves)
        self.select_move_menu = None
        self.switch_page_btn = None

        self.add_item(self.select_piece_menu)

        
        self.forward_stack = []

    def calculate_legal_moves(self):
        
        legal_moves = defaultdict(list)
        for move in self.board.legal_moves:
            square = chess.parse_square(str(move)[:2])
            piece = self.board.piece_at(square=square)
            legal_moves[str(piece)].append(str(self.board.san(move)))
        return legal_moves

    async def reload_board(self, interaction: Interaction):

        svg_board = chess.svg.board(self.board)
        bytesImage = BytesIO(svg2png(bytestring=svg_board))

        exporter = chess.pgn.StringExporter(headers=True, variations=True, comments=True)
        pgn = chess.pgn.Game.from_board(self.board).accept(exporter)


        img = discord_file(bytesImage, filename="board.png", description=pgn)
        
        self.legal_moves = self.calculate_legal_moves()
        self.select_piece_menu.options = self.select_piece_menu.generate_select_pieces(self.legal_moves)
        self.select_piece_menu.disabled = False
        self.select_piece_menu.placeholder = "Select Piece"

        if self.select_move_menu:
            self.select_move_menu.page = -1
            self.select_move_menu.disabled = True
        if self.switch_page_btn: 
            self.switch_page_btn.disabled = True
        

        await self.message.edit(view=self)
        await interaction.response.edit_message(attachments=[img])


    async def play_move(self, move, interaction : Interaction):
        self.board.push(self.board.parse_san(move))
        await self.reload_board(interaction)

    async def refresh_select_menu(self, piece):
        self.select_move_menu.options = self.select_move_menu.switch_page(self.legal_moves, piece)

    async def select_piece_respond(self, interaction: Interaction, piece: Select):
        
        self.select_piece_menu.disabled = True
        
        if not self.select_move_menu:
            self.select_move_menu = FileSelection(self.legal_moves, piece)
            self.add_item(self.select_move_menu)
        else:
            await self.refresh_select_menu(piece)
        
        self.select_move_menu.disabled = False

        if len(self.legal_moves[piece]) > 25:
            if not self.switch_page_btn:
                self.switch_page_btn = MoveSelectionNext(piece)
                self.add_item(self.switch_page_btn)
            self.switch_page_btn.disabled = False
        else:
            self.switch_page_btn = None
        await interaction.message.edit(view=self)


    @button(label="<-")
    async def left(self, interaction: Interaction, button : Button):
        if not self.board.move_stack:
            button.disabled = True
            if self.forward_stack:
                self.next_move_btn.disabled = False
            else:
                self.next_move_btn.disabled = True
            await self.message.edit(view=self)
            await interaction.response.edit_message()
            return
        self.forward_stack.append(self.board.peek())
        self.board.pop()
        self.next_move_btn.disabled = False
        await self.reload_board(interaction)
    

        

    @button(label="->")
    async def right(self, interaction: Interaction, button : Button):
        if not self.forward_stack:
            button.disabled = True;
            if self.board.move_stack:
                self.prev_move_btn.disabled = False
            else:
                self.prev_move_btn.disabled = True
            await self.message.edit(view=self)
            await interaction.response.edit_message()
            return

        self.board.push(self.forward_stack.pop())
        self.prev_move_btn.disabled = False
        
        await self.reload_board(interaction)




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
