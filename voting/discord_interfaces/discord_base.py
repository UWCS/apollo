import discord
from typing import List, Tuple, NamedTuple, Iterable

from sqlalchemy.exc import SQLAlchemyError

from models import db_session
from models.votes import DiscordVote, DiscordVoteChoice, DiscordVoteMessage, VoteType
from utils import get_database_user, get_database_user_from_id
from voting.emoji_list import default_emojis
from voting.vote_types.base_vote import base_vote
from discord import AllowedMentions
from discord.ext.commands import Bot, Context, clean_content

DENSE_ARRANGE = True
Choice = NamedTuple("Choice", [('emoji', str), ('prompt', str)])
DCMessage = NamedTuple("DCMessage", [('msg', discord.Message), ('choices', List[Choice])])

class DiscordBase:
    def __init__(self):
        self.vote_type = base_vote

    async def create_vote(self, ctx: Context, args: List[str], vote_limit=None, seats=None):
        title, emoji_choices = self.parse_choices(args)
        choices = [c.prompt for c in emoji_choices]

        try:
            # Create DB entry for vote
            owner = get_database_user_from_id(ctx.author.id)  # Questionable
            vote_obj, choices_obj = self.vote_type.create_vote(title, owner.id, choices, VoteType.basic, vote_limit, seats)
            new_dc_vote = DiscordVote(vote=vote_obj)
            db_session.add(new_dc_vote)

            # Post messages
            messages: List[DCMessage] = []
            msg_index = 0
            for chunk in self.chunk_choices(emoji_choices):
                # Send msg
                embed = self.create_embed(title, chunk)
                msg = await ctx.send(embed=embed, allowed_mentions=AllowedMentions.none())
                messages.append(DCMessage(msg, [c for i, c in chunk]))

                # Add msg to DB
                start_ind, _ = chunk[0]
                end_ind, _ = chunk[-1]
                new_dc_msg = DiscordVoteMessage(message_id=msg.id, channel_id=msg.channel.id, vote=vote_obj, discord_vote=new_dc_vote,
                                                choices_start_index=start_ind, numb_choices=end_ind-start_ind, part=msg_index)
                db_session.add(new_dc_msg)
                msg_index += 1

                # Add choices to DB
                for db_ch, (i, ch) in zip(choices_obj[start_ind:end_ind], chunk):
                    if db_ch.choice_index != i: raise Exception(f"DB and bot disagree on choice index")
                    new_dc_choice = DiscordVoteChoice(choice=db_ch, emoji=ch.emoji, msg=new_dc_msg)
                    db_session.add(new_dc_choice)

            db_session.commit()
        except SQLAlchemyError:
            db_session.rollback()
            await ctx.send("Error creating vote")
            raise

        # Add reactions to message, takes a while, so do last
        for msg, choices in messages:
            for c in choices:
                await msg.add_reaction(c.emoji)

        await ctx.message.add_reaction("✅")


    def get_title(self, title): return f"Basic Vote: {title}"
    def get_description(self): return "Votes: Visible"

    def parse_choices(self, choices: List[str]) -> Tuple[str, List[Choice]]:
        if len(choices) > 256: raise Exception(f"More than 256 choices given")
        if len(choices) == 0: raise Exception(f"No choices given")

        # Truncate each choice to 256 chars
        for i, c in enumerate(choices):
            if len(c) > 250: choices[i] = c[:250] + "..."

        # Title is first argument
        title = choices[0]
        choices = choices[1:]

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
        embed = discord.Embed(title=self.get_title(title), description=self.get_description())
        for i, ch in chunk:
            if len(ch.prompt) > 250: ch.prompt = ch.prompt[:250]
            embed.add_field(name=ch.emoji + " " + ch.prompt, value="_ _",
                            inline=(DENSE_ARRANGE and len(ch.prompt) < 25))
        return embed


    def create_msg(self, msg, choices):
        dc_choices = []
        for i, choice in enumerate(choices):
            new_dc_choice = DiscordVoteChoice(choice=choice.prompt, emoji=choice.emoji)
            db_session.add(new_dc_choice)
            dc_choices.append(new_dc_choice)

    def react_add(self, msg, user, emoji):
        raise NotImplemented()


    def react_remove(self, msg, user, emoji):
        raise NotImplemented()


    def record_vote(self, vote, user, option):
        raise NotImplemented()

    def make_results(self, vote):
        raise NotImplemented()

    def remove(self, vote):
        raise NotImplemented()






discord_base = DiscordBase()
