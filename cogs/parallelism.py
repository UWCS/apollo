from __future__ import annotations

import asyncio
import concurrent.futures

from discord.ext.commands import Bot, Cog


class Parallelism(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        self._thread_pool = None
        self._process_pool = None

    @staticmethod
    async def get(cls, bot: Bot) -> Parallelism:
        await bot.wait_until_ready()
        return bot.get_cog(cls.__name__)

    @property
    def thread_pool(self):
        if self._thread_pool is None:
            self._thread_pool = concurrent.futures.ThreadPoolExecutor()
        return self._thread_pool

    @thread_pool.deleter
    def thread_pool(self):
        self.thread_pool.shutdown()
        self._thread_pool = None

    @property
    def process_pool(self):
        if self._process_pool is None:
            self._process_pool = concurrent.futures.ProcessPoolExecutor()
        return self._process_pool

    @process_pool.deleter
    def process_pool(self):
        self.process_pool.shutdown()
        self._process_pool = None

    def execute_on_thread(self, func, /, *args, **kwargs):
        return self.thread_pool.submit(func, *args, **kwargs)

    def execute_on_process(self, func, /, *args, **kwargs):
        return self.process_pool.submit(func, *args, **kwargs)

    def run_coro_after_threaded(self, func, after, loop, /, *args, **kwargs):
        def work():
            result = func(*args, **kwargs)
            asyncio.run_coroutine_threadsafe(after(result), loop)

        return self.execute_on_thread(work, *args, **kwargs)

    def send_to_ctx_after_threaded(self, func, ctx, loop, /, *args, **kwargs):
        return self.run_coro_after_threaded(func, ctx.send, loop, *args, **kwargs)


def setup(bot: Bot):
    bot.add_cog(Parallelism(bot))
