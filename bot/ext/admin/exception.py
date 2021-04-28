import traceback
import logging
import sys

from discord import Embed, Color, errors, HTTPException
from discord.ext import commands

from bot.constants import Colour

log = logging.getLogger(__name__)
log.setLevel(logging.CRITICAL)
file_handler = logging.FileHandler('./bot/logs/errors.log')
file_handler.setFormatter(
    logging.Formatter("[%(asctime)s][%(name)s]: %(message)s"))
log.addHandler(file_handler)


class ExceptionHandler(commands.Cog):
    """Basic discord exception handler"""

    def __init__(self, bot):
        self.bot = bot
        self.color = Color.random()
        self.error_color = Colour.EXCEPTION

    async def raise_norm(self, ctx, error):
        print(f'Ignoring exception in command {ctx.command}:')
        report = ''.join(traceback.format_exception(
            type(error), error, error.__traceback__))

        log.critical(report)
        traceback.print_exception(
            type(error), error, error.__traceback__, file=sys.stderr)

    def get_usage(self, ctx):
        return f'{ctx.prefix}{ctx.command.qualified_name} {ctx.command.signature}'

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if hasattr(ctx.command, 'on_error'):
            return

        cog = ctx.cog
        if cog:
            if cog._get_overridden_method(cog.cog_command_error) is not None:
                return

        ignored = (commands.CommandNotFound)
        error = getattr(error, 'original', error)
        if isinstance(error, ignored):
            return

        elif isinstance(error, commands.DisabledCommand):
            await ctx.send(f'⚠️ {ctx.command} has been disabled.')

        elif isinstance(error, commands.NoPrivateMessage):
            try:
                await ctx.author.send(f'⚠️ {str(ctx.command).upper()} cannot be used in Private Messages.')
            except HTTPException:
                pass

        elif isinstance(error, errors.Forbidden):
            embed = Embed(title='⚠️ Unable to proceed...',
                          description=f"Required permission is missing.", color=self.error_color)
            embed.set_footer(text=self.get_usage(ctx))
            await ctx.send(embed=embed)

        elif isinstance(error, commands.MissingRequiredArgument):
            embed = Embed(title='⚠️ Unable to proceed...',
                          description=f"{error.param} is a required parameter.", color=self.error_color)
            embed.set_footer(text=self.get_usage(ctx))
            await ctx.send(embed=embed)

        elif isinstance(error, commands.BadArgument):
            embed = Embed(title='⚠️ Unable to proceed...',
                          description=f"Incorrect details passed in.", color=self.error_color)
            embed.set_footer(text=self.get_usage(ctx))
            await ctx.send(embed=embed)

        elif cog.qualified_name == 'Admin':
            if isinstance(error, commands.ExtensionNotFound):
                await ctx.send("⚠️ Extension is not found.")
            elif isinstance(error, commands.ExtensionNotLoaded):
                await ctx.send("⚠️ Extension is not loaded.")
            elif isinstance(error, commands.ExtensionAlreadyLoaded):
                await ctx.send("⚠️ Extension has been already loaded.")
            elif isinstance(error, commands.errors.CheckFailure):
                pass
            else:
                await self.raise_norm(ctx, error)
        else:
            await self.raise_norm(ctx, error)


def setup(bot):
    bot.add_cog(ExceptionHandler(bot))
    print('Exception handler is loaded')
