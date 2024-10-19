from discord.ext import commands
from discord.ext.commands import Bot, Context, clean_content

from discord import File as discord_file, Interaction, SelectOption
from discord.ui import View, Select, button, Button, select
from collections import defaultdict
from math import ceil

import chess.pgn
import chess.svg
from cairosvg import svg2png

from io import StringIO, BytesIO



LONG_HELP_TEXT = """
Make the bot repeat after you.
"""

SHORT_HELP_TEXT = """Make the bot repeat after you."""

piece_mappings = {"B":"Bishop", "K": "King", "P": "Pawn", "N":"Knight", "R": "Rook", "Q":"Queen",
                    "b":"Bishop", "k": "King", "p": "Pawn", "n":"Knight", "r": "Rook", "q":"Queen"
                }


########################## Select Target Position of Piece Class ###################################


class TargetSquareSelectHandler(Select):
    def __init__(self, legal_moves, piece):

        self.items_per_page = 25
        self.page = -1
        
        super().__init__(options=self.switch_page(legal_moves, piece), placeholder="Select a Square")

    # switch page if there are more than 25 legal moves
    def switch_page(self, legal_moves, piece):
        self.generate_legal_moves_by_piece(legal_moves, piece)
        self.page = (self.page + 1) % ceil(len(self.moves)/self.items_per_page)    
        start = self.page * self.items_per_page
        end = start + self.items_per_page if len(self.moves) > start + self.items_per_page else len(self.moves)
        return self.moves[start:end]

    # generate list of target squares given piece to move
    def generate_legal_moves_by_piece(self, legal_moves, piece):
        self.moves = [SelectOption(label=move,value=move) for move in legal_moves[piece]] 
        return self.moves
    
    # event handler when target square is selected
    async def callback(self, interaction: Interaction):
        await self.view.play_move(self.values[0], interaction)



############################### Selct Piece to Move Class ###################################



class PieceSelectionHandler(Select):
    def __init__(self, legal_moves):
        super().__init__(options=self.generate_select_pieces(legal_moves), max_values=1, placeholder="Select Piece")
    
    # generate options for the select menu given legal moves
    def generate_select_pieces(self, legal_moves):
        return [SelectOption(label=piece_mappings[move],value=move) for move in legal_moves.keys()]

    # piece selection from menu event handler 
    async def callback(self, interaction: Interaction):
        self.placeholder = piece_mappings[self.values[0]]
        await self.view.piece_select_event_respond(interaction, self.values[0])
        await interaction.response.defer()
        



############################### Over 25 Legal Moves Button Manager ###################################


        
class NextPageButtonWrapper(Button):

    def __init__(self,piece):
        self.piece = piece
        super().__init__(label=">", row=3)

    # press next page button (for >25 legal moves) event handler 
    async def callback(self, interaction: Interaction):
        await self.view.update_target_square_select_menu_values(self.piece)
        await interaction.response.edit_message(view=self.view)





############################### Main View Manager Class ###################################

class MainViewManager(View): 
    

    # initiliase the view manager for a specific board
    def __init__(self, board, analysis_mode : bool):

        super().__init__()
        
        # setting initial/default values and objects
        self.__board = board
        self.__legal_moves = self.calculate_legal_moves()

        self.__prev_move_btn = self.children[0]
        self.__next_move_btn = self.children[1]
        self.__target_square_select_menu = None                     # Square Selections
        self.__switch_page_btn = None                               # For >25 moves
        self.__forward_stack = []
        self.__next_move_btn.disabled = True

        # disable prev/next move if analysis mode is not enabled
        if not analysis_mode:
            self.__prev_move_btn.disabled = True
        elif not board.move_stack:
                self.__prev_move_btn.disabled = True

        # generate/add the piece selection menu to the view
        self.__piece_select_menu = PieceSelectionHandler(self.__legal_moves) # Piece Selection
        self.add_item(self.__piece_select_menu)
    
    # get list of all legal moves given a board state
    def calculate_legal_moves(self):
        
        legal_moves = defaultdict(list)
        for move in self.__board.legal_moves: # for each move played in the game
            square = chess.parse_square(str(move)[:2]) # get starting square
            piece = self.__board.piece_at(square=square) # get piece at starting square

            # map piece to value of standard algebraic notation of move 
            legal_moves[str(piece)].append(str(self.__board.san(move))) 

        return legal_moves

    # referesh image of board
    async def reload_board(self, interaction: Interaction):

        # get the svg representation of board, convert to png, and store image in byte form
        svg_board = chess.svg.board(self.__board)
        bytesImage = BytesIO(svg2png(bytestring=svg_board))

        # get pgn from board
        exporter = chess.pgn.StringExporter(headers=True, variations=True, comments=True)
        pgn = chess.pgn.Game.from_board(self.__board).accept(exporter)

        # generate discord image file of board with implicit description being the game's pgn 
        img = discord_file(bytesImage, filename="board.png", description=pgn)
        
        # update the legal moves
        self.__legal_moves = self.calculate_legal_moves()
        # update and enable piece selection menu with new legal moves
        self.__piece_select_menu.options = self.__piece_select_menu.generate_select_pieces(self.__legal_moves)
        self.__piece_select_menu.disabled = False
        self.__piece_select_menu.placeholder = "Select Piece"

        # disable target square select menu if enabled
        if self.__target_square_select_menu:
            self.__target_square_select_menu.page = -1
            self.__target_square_select_menu.disabled = True
        
        # disable page switching button (for >25 moves)
        if self.__switch_page_btn: 
            self.__switch_page_btn.disabled = True
        
        # update view on discord
        await self.message.edit(view=self)
        await interaction.response.edit_message(attachments=[img])

    # play a move given standard algebraic notation
    async def play_move(self, move, interaction : Interaction):
        self.__board.push(self.__board.parse_san(move))
        await self.reload_board(interaction)


    # switches page of target select menu page when >25 legal moves  
    async def update_target_square_select_menu_values(self, piece):
        self.__target_square_select_menu.options = self.__target_square_select_menu.switch_page(self.__legal_moves, piece)


    # response to user selecting a piece to move
    async def piece_select_event_respond(self, interaction: Interaction, piece: Select):
        
        self.__piece_select_menu.disabled = True # disable piece selection menu
        
        # if target square select menu was not generated, generate it
        if not self.__target_square_select_menu:
            self.__target_square_select_menu = TargetSquareSelectHandler(self.__legal_moves, piece)
            self.add_item(self.__target_square_select_menu)
        else: # otherwise update it with new values
            await self.update_target_square_select_menu_values(piece)
        
        # enable the target square selection menu
        self.__target_square_select_menu.disabled = False

        # if there are too many legal squares a piece can move to, 
        # enable/generate button to support cycling through list of target squares  
        if len(self.__legal_moves[piece]) > 25:
            if not self.__switch_page_btn:
                self.__switch_page_btn = NextPageButtonWrapper(piece)
                self.add_item(self.__switch_page_btn)
            self.__switch_page_btn.disabled = False
        else:
            self.__switch_page_btn.disabled = None

        # update view
        await interaction.message.edit(view=self)


    # take back a move  
    @button(label="<-")
    async def next_move_btn_handler(self, interaction: Interaction, button : Button):

        # if the board's move stack is empty, disable the button
        if not self.__board.move_stack:
            button.disabled = True

            # enable "go forward a move" button accordingly
            if self.__forward_stack: 
                self.__next_move_btn.disabled = False
            else:
                self.__next_move_btn.disabled = True

            await self.message.edit(view=self)
            await interaction.response.edit_message()
            return

        # when move stack is not empty

        self.__forward_stack.append(self.__board.peek()) # add move to forward stack
        self.__board.pop() # pop last move from board's move stack
        self.__next_move_btn.disabled = False # enable next move button
        
        # disable button if there are no more previous moves
        if not self.__board.move_stack:
                self.__prev_move_btn.disabled = True

        # refresh board
        await self.reload_board(interaction)
    

    # go forward a move
    @button(label="->")
    async def prev_move_btn_handler(self, interaction: Interaction, button : Button):

        # if the forward move stack is empty, disable the button
        if not self.__forward_stack:
            button.disabled = True;

            # enable "take back a move" button accordingly
            if self.__board.move_stack:
                self.__prev_move_btn.disabled = False
            else:
                self.__prev_move_btn.disabled = True

            await self.message.edit(view=self)
            await interaction.response.edit_message()
            return

        # when move stack is not empty

        # play the move 
        self.__board.push(self.__forward_stack.pop())
        # enable "take back a move" button
        self.__prev_move_btn.disabled = False
        
        # if forward_stack doesn't contain any moves, disable "go forward a move" button
        if not self.__forward_stack:
                self.__next_move_btn.disabled = True
        
        # referesh boards
        await self.reload_board(interaction)



################################## Main Command Class ###################################


class Chess(commands.Cog):


    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.hybrid_group(help=LONG_HELP_TEXT, brief=SHORT_HELP_TEXT)
    async def chess(self, ctx: Context, analysis_mode: bool = True):
        # default command
        if not ctx.invoked_subcommand:
            
            await self.initialise_board(ctx, None, analysis_mode)


    # load chessboard from pgn subcommand
    @chess.command(help="")
    async def load(self, ctx : Context, *, pgn: str, analysis_mode: bool = True):
        
        game = chess.pgn.read_game(StringIO(pgn))
        board = game.board()
        
        for move in game.mainline_moves():
            board.push(move)
        
        await self.initialise_board(ctx, board, analysis_mode)
    

    # run analysis mode on a board given a pgn, reply from an existing board in chat, or empty board 
    @chess.command(help="")
    async def analysis(self, ctx: Context, pgn = None):
        if not pgn:
            if ctx.message.reference:
                reply = await ctx.channel.fetch_message(ctx.message.reference.message_id)
                if reply.attachments and reply.attachments[0].content_type == "image/png":
                    pgn = reply.attachments[0].description

                    
                    game = chess.pgn.read_game(StringIO(pgn))
                    if not game:
                        await ctx.reply("Cannot read game!")
                    
                    board = game.board()
                    
                    for move in game.mainline_moves():
                        board.push(move)

                    await self.initialise_board(ctx, board, True)
            else:
                await self.initialise_board(ctx, None, True)
        else:

            game = chess.pgn.read_game(StringIO(pgn))
            board = game.board()
            
            for move in game.mainline_moves():
                board.push(move)
            await self.initialise_board(ctx, board, True)





    async def initialise_board(self, ctx: Context, board, analysis_mode):
        
        board = board if board else chess.Board()
        
        # get pgn from board
        exporter = chess.pgn.StringExporter(headers=True, variations=True, comments=True)
        pgn = chess.pgn.Game.from_board(board).accept(exporter)

        # initialise the view manager with the board
        view = MainViewManager(board, analysis_mode)

        # generate image of board
        svg_board = chess.svg.board(board)
        bytesImage = BytesIO(svg2png(bytestring=svg_board))
        img = discord_file(bytesImage, filename="board.png", description=pgn)
        message = await ctx.send(file=img, view=view)
        
        # store the message sent in the view manager to edit later
        view.message = message
        await view.wait()


async def setup(bot: Bot):
    await bot.add_cog(Chess(bot))


