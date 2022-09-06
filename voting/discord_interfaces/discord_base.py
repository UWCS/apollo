import discord
from typing import List, Tuple, NamedTuple, Iterable, Dict

from discord.ui import View, Button
from sqlalchemy.exc import SQLAlchemyError

from models import db_session, User
from models.votes import DiscordVote, DiscordVoteChoice, DiscordVoteMessage, VoteType, UserVote
from utils import get_database_user_from_id
from voting.emoji_list import default_emojis

from voting.vote_types.base_vote import base_vote
from discord import AllowedMentions, InteractionMessage, ButtonStyle
from discord.ext.commands import Context

DENSE_ARRANGE = True
Choice = NamedTuple("Choice", [('emoji', str), ('prompt', str)])
DCMessage = NamedTuple("DCMessage", [('msg', discord.Message), ('choices', List[Choice])])

# Records last ephemeral message to each user, so can edit for future votes
class VoteButton(Button):
    def __init__(self, interface, dvc: DiscordVoteChoice, msg_title):
        super().__init__(label=dvc.choice.choice, emoji=dvc.emoji)
        self.dvc = dvc
        self.vote = dvc.msg.vote
        self.msg_title = msg_title
        self.interface = interface

    async def callback(self, interaction: discord.Interaction):
        db_user = db_session.query(User).filter(User.user_uid == interaction.user.id).one_or_none()
        msg = self.interface.vote_type.vote_for(self.vote, db_user, self.dvc.choice)
        await self.interface.send_choice_feedback(interaction, (db_user, self.vote.id), msg, self.msg_title)

class CloseButton(Button):
    def __init__(self, interface, vote_id):
        super().__init__(label="End", emoji="✖️", style=ButtonStyle.danger)
        self.interface = interface
        self.vote_id = vote_id

    async def callback(self, interaction: discord.Interaction):
        self.interface.vote_type.end(self.vote_id)
        await interaction.message.edit(view=None)
        await self.interface.end_vote(interaction, self.vote_id)

class DiscordBase:
    def __init__(self, vote_type=base_vote, btn_class=VoteButton):
        self.vote_type = vote_type
        self.BtnClass = btn_class
        self.users_last_vote_update_message: Dict[Tuple[int, int], InteractionMessage] = {}

    async def create_vote(self, ctx: Context, args: List[str], vote_limit=None, seats=None):
        title, emoji_choices = self.parse_choices(args)
        choices = [c.prompt for c in emoji_choices]

        try:
            # Create DB entry for vote
            # TODO Get DB user from DC user properly
            owner = get_database_user_from_id(ctx.author.id)  # Questionable
            vote_obj, choices_obj = self.vote_type.create_vote(title, owner.id, choices, VoteType.basic, vote_limit, seats)
            new_dc_vote = DiscordVote(vote=vote_obj)
            db_session.add(new_dc_vote)

            # Post messages
            messages: List[DCMessage] = []
            msg_index = 0
            for chunk in self.chunk_choices(emoji_choices):
                msg_title = self.get_title(title, msg_index)
                # Send msg
                embed = self.create_embed(title, chunk)
                msg = await ctx.send(content=msg_title, embed=embed, allowed_mentions=AllowedMentions.none())
                messages.append(DCMessage(msg, [c for i, c in chunk]))

                # Add msg to DB
                start_ind, _ = chunk[0]
                end_ind, _ = chunk[-1]
                end_ind += 1
                new_dc_msg = DiscordVoteMessage(message_id=msg.id, channel_id=msg.channel.id, vote=vote_obj,
                                                choices_start_index=start_ind, numb_choices=end_ind - start_ind, part=msg_index)
                db_session.add(new_dc_msg)
                msg_index += 1

                # Add choices to DB and add buttons
                view = View(timeout=None)
                for db_ch, (i, ch) in zip(choices_obj[start_ind:end_ind], chunk):
                    print("\t", db_ch, (i, ch))
                    if db_ch.choice_index != i: raise Exception(f"DB and bot disagree on choice index")
                    new_dc_choice = DiscordVoteChoice(choice=db_ch, emoji=ch.emoji, msg=new_dc_msg)
                    db_session.add(new_dc_choice)

                    view.add_item(self.BtnClass(self, new_dc_choice, msg_title))

                if start_ind == 0:
                    view.add_item(CloseButton(self, vote_obj.id))
                await msg.edit(view=view)

            db_session.commit()
        except SQLAlchemyError:
            db_session.rollback()
            await ctx.send("Error creating vote")
            raise


    def get_title(self, title, msg_index):
        if msg_index == 0: return f"**Basic Vote: {title}**"
        else: return f"**Basic Vote: {title} pt. {msg_index+1}**"

    def get_description(self): return "Votes: Visible"

    def parse_choices(self, args: List[str]) -> Tuple[str, List[Choice]]:
        """Parse title and choices out of args"""
        if len(args) > 256: raise Exception(f"More than 256 choices given")
        if len(args) == 0: raise Exception(f"No choices given")

        # Truncate each choice to 256 chars
        for i, c in enumerate(args):
            if len(c) > 250: args[i] = c[:250] + "..."

        # Title is first argument
        title = args[0]
        choices = args[1:]

        # Pair choices with emojis -- thumbs up/down if single option given
        if len(choices) <= 1:
            c = choices[0] if choices else ""
            return title, [Choice("👍", c), Choice("👎", c)]
        else:
            return title, [Choice(e, c) for e, c in zip(default_emojis, choices)]


    def chunk_choices(self, choices: List[Choice], per_msg=20, len_per_msg=5900) -> Iterable[List[Tuple[int, Choice]]]:
        """Splits options such that they'll fit onto a message. Each msg can have 20 reacts and each embed can have max 6000 chars for the whole thing"""
        chunk, msg_len = [], 0
        for i, choice in enumerate(choices):
            line_len = len(choice.emoji) + len(choice.prompt) + 4
            if len(chunk)+1 > per_msg or msg_len + line_len > len_per_msg:
                yield chunk
                chunk, msg_len = [], 0
            chunk.append((i, choice))
            msg_len += line_len
        if chunk: yield chunk

    def create_embed(self, title: str, chunk: List[Tuple[int, Choice]]):
        """Construct embed from list of choices"""
        embed = discord.Embed(title=self.get_description())
        for i, ch in chunk:
            if len(ch.prompt) > 250: ch.prompt = ch.prompt[:250]
            embed.add_field(name=ch.emoji + " " + ch.prompt, value="_ _",
                            inline=(DENSE_ARRANGE and len(ch.prompt) < 25))
        return embed


    async def send_choice_feedback(self, interaction: discord.Interaction, key, msg, msg_title):
        # Check if existing feedback message and attempt to send to it
        if old_msg := self.users_last_vote_update_message.get(key):
            try:
                await old_msg.edit(content=msg)
                # Hack to give interaction a response without changing anything
                await interaction.response.edit_message(content=f"**{msg_title}**")
                return
            except (discord.errors.NotFound, discord.errors.HTTPException):
                pass
        # If no existing message, send it and update record for user
        await interaction.response.send_message(msg, ephemeral=True)
        new_msg = await interaction.original_response()
        self.users_last_vote_update_message[key] = new_msg


    async def end_vote(self, interaction: discord.Interaction, vote_id):
        votes = self.vote_type.get_votes_for(vote_id)
        await interaction.response.send_message(votes)
        self.vote_type.end(vote_id)

    async def make_results(self, vote):
        raise NotImplemented()