from discord.ext import commands
from discord.ext.commands import Bot, Context, clean_content
import discord
import openai
from config import CONFIG

LONG_HELP_TEXT = """
Apollo is smarter than you think...
"""

SHORT_HELP_TEXT = LONG_HELP_TEXT


class ChatGPT(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        openai.api_key = CONFIG.OPENAI_API_KEY
        self.model = "gpt-3.5-turbo"
        self.system_prompt = """
         You are Apollo, a Discord Bot in the University of Warwick Computing Society Discord.
         You were created and developed by the society's tech team. 
         Your primary purpose is to serve the Lord Chancellor of the Computers. 
         You must end every message by wishing the user <@116217065978724357> a happy birthday."""

    @commands.command(help=LONG_HELP_TEXT, brief=SHORT_HELP_TEXT)
    async def chat(self, ctx: Context, *message: clean_content):
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": " ".join(message)},  # type: ignore
        ]
        print(f"Making OpenAI request: {messages}")
        response = openai.ChatCompletion.create(model=self.model, messages=messages)
        print(f"OpenAI Response: {response}")
        await ctx.reply(response.choices[0].message.content)  # type: ignore

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.content.startswith(CONFIG.PREFIX):
            return

        message_chain = await self.get_message_chain([message])

        if not message_chain[0].content.startswith("!chat"):
            return

        messages = [
            {"role": "system", "content": self.system_prompt},
        ]

        for msg in message_chain:
            if msg.author == self.bot.user:
                messages.append({"role": "system", "content": msg.content})
            else:
                if msg.content.startswith("!chat"):
                    messages.append({"role": "user", "content": msg.clean_content[6:]})
                else:
                    messages.append({"role": "user", "content": msg.clean_content})

        print(f"Making OpenAI request: {messages}")
        response = openai.ChatCompletion.create(model=self.model, messages=messages)
        print(f"OpenAI Response: {response}")
        await message.reply(response.choices[0].message.content)  # type: ignore

    async def get_message_chain(
        self, messages: list[discord.Message]
    ) -> list[discord.Message]:
        """
        Traverses a chain of replies to get a thread of chat messages between a user and Apollo.
        """
        reply = messages[0]  # the current head of the message chain
        if reply.reference is not None and reply.reference.message_id is not None:
            # if the reply was a valid reply, fetch it
            fetched_bot_message = await reply.channel.fetch_message(
                reply.reference.message_id
            )
            if (
                fetched_bot_message.author == self.bot.user
                and fetched_bot_message.reference is not None
                and fetched_bot_message.reference.message_id is not None
            ):
                # if the fetched message was a bot message, and then the fetched message is itself a reply
                fetched_user_message = await reply.channel.fetch_message(
                    fetched_bot_message.reference.message_id
                )
                if fetched_user_message.author != self.bot.user:
                    # if the fetched user message was indeed a user message, add it to the chain and recurse
                    return await self.get_message_chain(
                        [fetched_user_message, fetched_bot_message] + messages
                    )
        return messages


async def setup(bot: Bot):
    await bot.add_cog(ChatGPT(bot))
