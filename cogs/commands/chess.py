from collections import defaultdict
from datetime import datetime
from io import BytesIO, StringIO
from math import ceil

import chess.pgn
import chess.svg
from cairosvg import svg2png
from discord import File as discord_file
from discord import Interaction, SelectOption
from discord.ext import commands
from discord.ext.commands import Bot, Context
from discord.ui import Button, Select, View, button

SHORT_HELP_TEXT = """Apollo is now a chess board."""

piece_mappings = {"B":"Bishop", "K": "King", "P": "Pawn", "N":"Knight", "R": "Rook", "Q":"Queen",
                    "b":"Bishop", "k": "King", "p": "Pawn", "n":"Knight", "r": "Rook", "q":"Queen"
                }

# format message to print game details
def header_message_format(pgn, last_move, turn, game_header=None, end=""):

    game = chess.pgn.read_game(StringIO(pgn))
    if not game_header:
        game_header = game.headers
    color = "White" if turn else "Black"
    
    # if game is not over, use default format
    if end == "":
        header_template = """ 

# **Event:** {event_name}     
**Date**: {date}
**White:** {white}          **Black**: {black}
**Last Move**: {last_move}
**{color} to move** 
        """ 
        return header_template.format(event_name=game_header["Event"], date=game_header["Date"], white=game_header["White"], black=game_header["Black"], last_move=last_move, color=color)
    else:
        # if game is over, set checkmate or draw accordingly
        anti_color = "Black" if turn else "White"
        if end == "C":
            state = "checkmated"
        elif end == "D":
            state = "drew"
        header_template = """ 

# **Event:** {event_name}     
**Date**: {date}
**White:** {white}          **Black**: {black}
**Last Move**: {last_move}
**{anti_color} {state} {color}** 
        """ 
        return header_template.format(event_name=game_header["Event"], date=game_header["Date"], white=game_header["White"], black=game_header["Black"], last_move=last_move, color=color, state=state, anti_color=anti_color)




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
    def __init__(self, board, game, analysis_mode : bool):

        super().__init__()
        
        # setting initial/default values and objects
        self._board = board
        self._legal_moves = self.calculate_legal_moves()

        self._prev_move_btn = self.children[0]
        self._next_move_btn = self.children[1]
        self._target_square_select_menu = None                     # Square Selections
        self._switch_page_btn = None                               # For >25 moves
        self._forward_stack = []
        self._next_move_btn.disabled = True
        self._game_headers = game.headers
        self._last_move = None
        self._analysis_mode = analysis_mode
        # disable prev/next move if analysis mode is not enabled
        if not analysis_mode:
            self._prev_move_btn.disabled = True
        elif not board.move_stack:
                self._prev_move_btn.disabled = True

        # generate/add the piece selection menu to the view
        self._piece_select_menu = PieceSelectionHandler(self._legal_moves) # Piece Selection
        self.add_item(self._piece_select_menu)
    
    # get list of all legal moves given a board state
    def calculate_legal_moves(self):
        
        legal_moves = defaultdict(list)
        for move in self._board.legal_moves: # for each move played in the game
            square = chess.parse_square(str(move)[:2]) # get starting square
            piece = self._board.piece_at(square=square) # get piece at starting square

            # map piece to value of standard algebraic notation of move 
            legal_moves[str(piece)].append(str(self._board.san(move))) 

        return legal_moves

    # referesh image of board
    async def reload_board(self, interaction: Interaction):

        # get the svg representation of board, convert to png, and store image in byte form
        svg_board = chess.svg.board(self._board)
        bytesImage = BytesIO(svg2png(bytestring=svg_board))

        # get pgn from board
        exporter = chess.pgn.StringExporter(headers=True, variations=True, comments=True)
        game = chess.pgn.Game.from_board(self._board)
        game.headers=self._game_headers

        # set white/black player names if not set
        game.headers["Black"] = interaction.user.display_name if game.headers["Black"] == "?" and self._board.turn else game.headers["Black"]
        game.headers["White"] = interaction.user.display_name if game.headers["White"] == "?" and self._board.turn else game.headers["White"]
        pgn = game.accept(exporter)
        
        # generate discord image file of board with implicit description being the game's pgn
        img = discord_file(bytesImage, filename="board.png", description=pgn[:1024])
        self.message.attachments = [img]
        for i in range(len(pgn)//1024):
            self.message.attachments.append(discord_file("1pximage.png", filename="1.png", description=pgn[1024*i:1024*(i+1)]))

        end = ""

        # check if game ended
        if not self._board.is_checkmate() and not self._board.is_stalemate() and not self._board.is_insufficient_material():


            # update the legal moves
            self._legal_moves = self.calculate_legal_moves()
            # update and enable piece selection menu with new legal moves
            self._piece_select_menu.options = self._piece_select_menu.generate_select_pieces(self._legal_moves)
            self._piece_select_menu.disabled = False
            self._piece_select_menu.placeholder = "Select Piece"

        else:
            self._piece_select_menu.disabled = True
            self._piece_select_menu.placeholder = "Select Piece"
            if self._board.is_checkmate():
                end = "C"
            else:
                end = "D"


        # disable target square select menu if enabled
        if self._target_square_select_menu:
            self._target_square_select_menu.page = -1
            self._target_square_select_menu.disabled = True
        
        # disable page switching button (for >25 moves)
        if self._switch_page_btn: 
            self._switch_page_btn.disabled = True
        
        if not self._analysis_mode:
            self._next_move_btn.disabled = self._forward_stack == []
            self._prev_move_btn.disabled = self._board.move_stack == []
        

        # update view on discord
        await self.message.edit(content= header_message_format(pgn, self._last_move, self._board.turn, self._game_headers, end),view=self)
        await interaction.response.edit_message(attachments=self.message.attachments)

    # play a move given its standard algebraic notation (SAN)
    async def play_move(self, move, interaction : Interaction):
        self._last_move = move
        self._board.push(self._board.parse_san(move))
        self._forward_stack.clear()
        await self.reload_board(interaction)


    # switches page of target select menu page when >25 legal moves  
    async def update_target_square_select_menu_values(self, piece):
        self._target_square_select_menu.options = self._target_square_select_menu.switch_page(self._legal_moves, piece)


    # response to user selecting a piece to move
    async def piece_select_event_respond(self, interaction: Interaction, piece: Select):
        
        self._piece_select_menu.disabled = True # disable piece selection menu
        
        # if target square select menu was not generated, generate it
        if not self._target_square_select_menu:
            self._target_square_select_menu = TargetSquareSelectHandler(self._legal_moves, piece)
            self.add_item(self._target_square_select_menu)
        else: # otherwise update it with new values
            await self.update_target_square_select_menu_values(piece)
        
        # enable the target square selection menu
        self._target_square_select_menu.disabled = False

        # if there are too many legal squares a piece can move to, 
        # enable/generate button to support cycling through list of target squares  
        if len(self._legal_moves[piece]) > 25:
            if not self._switch_page_btn:
                self._switch_page_btn = NextPageButtonWrapper(piece)
                self.add_item(self._switch_page_btn)
            self._switch_page_btn.disabled = False
        elif self._switch_page_btn:
            self._switch_page_btn.disabled = True


        # update view
        await interaction.message.edit(view=self)




    # take back a move  
    @button(label="<-")
    async def next_move_btn_handler(self, interaction: Interaction, button : Button):

        # if the board's move stack is empty, disable the button
        if not self._board.move_stack:
            button.disabled = True

            # enable "go forward a move" button accordingly
            if self._forward_stack: 
                self._next_move_btn.disabled = False
            else:
                self._next_move_btn.disabled = True

            await self.message.edit(view=self)
            await interaction.response.edit_message()
            return

        # when move stack is not empty

        self._forward_stack.append(self._board.peek()) # add move to forward stack
        self._board.pop() # pop last move from board's move stack
        self._next_move_btn.disabled = False # enable next move button
        if self._board.move_stack:
            move = self._board.pop()
            self._last_move = self._board.san(move)
            self._board.push_san(self._last_move)
        # disable button if there are no more previous moves
        if not self._board.move_stack:
                self._prev_move_btn.disabled = True

        # refresh board
        await self.reload_board(interaction)
    

    # go forward a move
    @button(label="->")
    async def prev_move_btn_handler(self, interaction: Interaction, button : Button):

        # if the forward move stack is empty, disable the button
        if not self._forward_stack:
            button.disabled = True

            # enable "take back a move" button accordingly
            if self._board.move_stack:
                self._prev_move_btn.disabled = False
            else:
                self._prev_move_btn.disabled = True

            await self.message.edit(view=self)
            await interaction.response.edit_message()
            return

        # when move stack is not empty

        # play the move 
        self._last_move = self._board.san(self._forward_stack[-1])
        self._board.push(self._forward_stack.pop())
        # enable "take back a move" button
        self._prev_move_btn.disabled = False
        
        # if forward_stack doesn't contain any moves, disable "go forward a move" button
        if not self._forward_stack:
                self._next_move_btn.disabled = True
        
        # referesh boards
        await self.reload_board(interaction)



################################## Main Command Class ###################################


class Chess(commands.Cog):


    def __init__(self, bot: Bot):
        self.bot = bot
    
    CHESS_HELP = """
!chess -- loads empty board (analysis mode enabled by default)
!chess load <pgn> -- loads board given PGN
!chess analysis -- creates a game analysis (can go back and forth between moves)
"""

    @commands.hybrid_group(help=CHESS_HELP, brief=SHORT_HELP_TEXT)
    async def chess(self, ctx: Context, analysis_mode: bool = True):
        # default command
        if not ctx.invoked_subcommand:
            
            await self.initialise_board(ctx, None, True, None)

    LOAD_HELP = "!chess load <pgn>"
    # load chessboard from pgn subcommand
    @chess.command(help=LOAD_HELP, brief=SHORT_HELP_TEXT)
    async def load(self, ctx : Context, *, pgn: str, analysis_mode: bool = True):
        
        game = chess.pgn.read_game(StringIO(pgn))
        await self.initialise_board(ctx, game, True, pgn)
    
    ANALYSIS_HELP = "!chess analysis <pgn> OR reply to previous board message and send !chess analysis"
    # run analysis mode on a board given a pgn, reply from an existing board in chat, or empty board 
    @chess.command(help=ANALYSIS_HELP, brief=SHORT_HELP_TEXT)
    async def analysis(self, ctx: Context, *, pgn = None):
        if not pgn:
            # if reply exists check that it contains an png attachment
            if ctx.message.reference:
                reply = await ctx.channel.fetch_message(ctx.message.reference.message_id)
                if reply.attachments and reply.attachments[0].content_type == "image/png":
                    # get pgn from attachment description and generate board
                    pgn = ""
                    for a in reply.attachments:
                        if a.description:
                            pgn += a.description

                    game = chess.pgn.read_game(StringIO(pgn))

                    await self.initialise_board(ctx, game, True, pgn)
                else:
                    await ctx.send("Error: Message must contain a png image with board generated by bot!")

            else: # if no reply and no pgn, just generate an empty board
                await self.initialise_board(ctx, None, True, pgn)
        else:

            game = chess.pgn.read_game(StringIO(pgn))
            await self.initialise_board(ctx, game, True, pgn)


    # generate the board object and send the initial response
    async def initialise_board(self, ctx: Context, game, analysis_mode, pgn):
        last_move = ""
        if game:
            board = game.board()
            for move in game.mainline_moves():
                    last_move = board.san(move)
                    board.push(move)
        else:
            # Make headers nicer

            game = chess.pgn.Game()
            game.headers["Date"] =  datetime.now().strftime("%Y.%m.%d")
            game.headers["Event"] = ctx.author.display_name +"'s Event"
            game.headers["White"] = ctx.author.display_name
            
            
            # get pgn from board
            board = chess.Board()
            exporter = chess.pgn.StringExporter(headers=True, variations=True, comments=True)
            pgn = game.accept(exporter)
        
        
        # initialise the view manager with the board
        view = MainViewManager(board, game, analysis_mode)

        # generate image of board
        svg_board = chess.svg.board(board)
        bytesImage = BytesIO(svg2png(bytestring=svg_board))
        img = [discord_file(bytesImage, filename="board.png", description=pgn[:1024])]
        for i in range(len(pgn)//1024):
            img.append(discord_file("1pximage.png", filename="1.png", description=pgn[1024*i:1024*(i+1)]))
            
        message = await ctx.send( header_message_format(pgn, last_move, board.turn), files=img, view=view)
        
        # store the message in the view manager to edit later

        view.message = message
        await view.wait()


async def setup(bot: Bot):
    await bot.add_cog(Chess(bot))


