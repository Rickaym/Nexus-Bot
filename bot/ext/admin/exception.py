import traceback
import logging
import sys

from discord import Embed, Color, errors, HTTPException, ui
from io import StringIO
from discord.components import SelectOption
from discord.ext import commands
from discord.file import File
from discord.interactions import Interaction
from bot.constants import Colour

log = logging.getLogger(__name__)
log.setLevel(logging.CRITICAL)
file_handler = logging.FileHandler('./bot/logs/errors.log')
file_handler.setFormatter(
    logging.Formatter("[%(asctime)s][%(name)s]: %(message)s"))
log.addHandler(file_handler)

class HandleException(ui.Select):
    def __init__(self, view: ui.View):
        options = (
            SelectOption(label="Report to admins", emoji="❗"),
            SelectOption(label="Delete", emoji="🗑️")
        )
        self._from_view = view
        self.report = False
        super().__init__(placeholder="Handle Exception", options=options)

    async def callback(self, i: Interaction):
        if "Report to admins" in i.data["values"]:
            await i.response.send_message("Done, thanks for reporting.")
            self.report = True
        self._from_view.stop()

class ExceptionHandler(commands.Cog):
    """Basic discord exception handler"""

    def __init__(self, bot):
        self.bot = bot
        self.color = Color.random()
        self.error_color = Colour.EXCEPTION

    async def raise_norm(self, ctx, error):
        report = ''.join(traceback.format_exception(
            type(error), error, error.__traceback__))

        print(f'Ignoring exception in command {ctx.command}:')
        log.critical(report)
        traceback.print_exception(
            type(error), error, error.__traceback__, file=sys.stderr)

        view = ui.View()
        select = HandleException(view)
        view.add_item(select)
        m = await ctx.send("<a:stresswarning:845304431289303071> Something went wrong...", view=view)
        await view.wait()
        await m.delete()
        if select.report:
            buf = StringIO(report)
            await self.bot.hotline_channel.send(file=File(buf, "report.log"), content=f"Reported by {ctx.author.name}#{ctx.author.discriminator} @here")

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

        elif isinstance(error, commands.CheckFailure):
            print(error)

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
        elif cog.qualified_name in ('Pictionary, GuessTheCharacter, Deception'):
            if isinstance(error, commands.BotMissingPermissions):
                embed = Embed(title='⚠️ Permission needed!', description=f"Due to the latest update on the new multi-answering system. The bot now requires the `manage_messages` permission. Find out more [here](https://github.com/Ricky-MY/The-Pictionary-Bot/blob/main/src/game_files/pictionary.py).", color=self.error_color )
                embed.add_field(name="Why?", value="The new rewarding system allows multiple people to score points according to how fast they answer. The bot is required to delete valid answers so that when one person gets the correct theme. It remains unexposed.")
                embed.add_field(name="How?", value=f"• Create a new role named `Pictionary`\n• Give the role access to the `manage_messages` permission\n• Give {self.bot.user.mention} the role!",inline= True)
                embed.set_image(url = 'https://i.gyazo.com/98f79a36e4145705917434c6942f7a99.png')
                embed.set_footer(text=f'{ctx.prefix}updates | to find out about latest updates (currently getting revamped -- might not work)')
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
