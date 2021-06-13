from discord.ext.commands import (
    ArgumentParsingError,
    BadArgument,
    Command,
    CommandError,
    Group,
)

__all__ = ["Greedy1Command", "Greedy1Group"]


class Greedy1Command(Command):
    """Implementation of Command that fails to parse if Greedy[T] does not find any arguments."""

    async def _transform_greedy_pos(self, ctx, param, required, converter):
        view = ctx.view
        result = []
        while not view.eof:
            # for use with a manual undo
            previous = view.index

            view.skip_ws()
            try:
                argument = view.get_quoted_word()
                value = await self.do_conversion(ctx, converter, argument, param)
            except (CommandError, ArgumentParsingError):
                view.index = previous
                break
            else:
                result.append(value)

        if not result and not required:
            return param.default
        elif not result:
            raise BadArgument
        return result

    # Does not currently require overriding
    # async def _transform_greedy_var_pos(self, ctx, param, converter):
    #     view = ctx.view
    #     previous = view.index
    #     try:
    #         argument = view.get_quoted_word()
    #         value = await self.do_conversion(ctx, converter, argument, param)
    #     except (CommandError, ArgumentParsingError):
    #         view.index = previous
    #         raise RuntimeError() from None  # break loop
    #     else:
    #         return value


class Greedy1Group(Group):
    _transform_greedy_pos = Greedy1Command._transform_greedy_pos
