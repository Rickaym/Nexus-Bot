import random

from typing import Any, Tuple, Union

from discord import Embed, Color
from discord.ext import commands
from discord.ext.commands.context import Context

from bot.constants import Colour
from bot.constants import NUMBER_MAP

GREEN = (0)
BLACK = (2, 4, 6, 8, 10, 11, 13, 15, 17, 20, 22, 24, 26, 28, 29, 31, 33, 35)
RED = (1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36)

COLORS = {"red": '🟥',
          "green": '🟩',
          "black": '⬛'}

PAY_MAP = {"red": '2x', 'number': '35x',
           "green": '35x', 'high': '2x',
           "black": '2x', 'low': '2x'}


class Roulette(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.embed = Embed(
            title="Roulette",
            color=Color.random(),
        )
        self.embed.set_author(name="Pictionary' Gamble",
                              icon_url="https://cdn0.iconfinder.com/data/icons/casinos-and-gambling/500/SingleCartoonCasinoAndGamblingYulia_6-512.png")

    def create_poster(self, number: int, color: str) -> str:
        """
        Generates and returns a roulette result from the number and
        color in the form of a discord emoji poster.
        """
        emoji = COLORS[color.lower()]
        poster = f"{emoji}{emoji}{emoji}{emoji if number >= 10 else ''}\n{emoji}{''.join([NUMBER_MAP[str(digit)] for digit in str(number)])}{emoji}\n{emoji}{emoji}{emoji}{emoji if number >= 10 else ''}"
        return poster

    def roll_roulette(self) -> Tuple[int, str]:
        """
        Picks a number and it's respective color as a roulette table.
        """
        number = random.choice((0, *BLACK, *RED))
        color = "red" if number in RED else "black" if number in BLACK else "green"
        return number, color

    def evaluate(self, number: int, color: str, bet_type: Any) -> Union[str, int]:
        """
        Evaluate whether the player had won or lost. If the player has won,
        it will also return the condition of which it is won.
        """
        try:
            int(bet_type)
        except ValueError:
            integer = False
            if (status := bet_type.lower()) in ('high', 'low'):
                if status == 'high':
                    condition = number > 18
                elif status == 'low':
                    condition = number <= 18
            elif (status := bet_type.lower()) in ('red', 'green', 'black'):
                condition = status == color
        else:
            condition = number == int(bet_type)
            integer = True
        if condition and integer:
            return PAY_MAP['number']
        elif condition and not integer:
            return PAY_MAP[bet_type]
        elif not condition:
            return 0

    async def update_balances(self, user_id: int, increment: str, bet: int, embed: Embed) -> Embed:
        """
        Increment and decrement balances respective to the condition of the game
        """
        if increment == 0:
            async with DB() as cont:
                await cont.remove_bal(user_id, bet)
                embed.description += f"\n**{format(round(bet), ',')} gold lost**"
        elif increment != 0:
            increment = self.consume(bet, increment)
            async with DB() as cont:
                await cont.add_bal(user_id, (increment*0.95)-bet)
                await cont.add_bal(self.bot.user.id, increment*0.05)
                embed.description += f"\n**🎉 {format(round(increment*0.95), ',')} gold won**"
        return embed

    def consume(self, bet: int, indication: str) -> int:
        """
        Takes in a string amount and parses it into arithmetic ready
        value based on indication. The return value is un-commissioned.
        """
        if str(indication)[-1] != 'x':
            return float(bet)
        elif str(indication)[-1] == 'x':
            return float(indication[:-1]) * bet

    @commands.group(name="roulette", aliases=["roul"], invoke_without_command=True)
    @commands.guild_only()
    async def roulette(self, ctx: Context, bet_type: str):
        """
        A game of roulette where a random ball is spun to lay on a random color and a respective number.
        """
        extras = ''
        try:
            int(bet_type)
        except ValueError as e:
            pass
        else:
            if int(bet_type) not in (0, *BLACK, *RED):
                embed = self.embed.copy()
                embed.description = f"Your number bet is invalid, it has to be one of `{sorted((0, *BLACK, *RED))}`"
                await ctx.reply(embed=embed, mention_author=False)
                return
            elif int(bet_type) in (0, *BLACK, *RED):
                extras = f"of color {COLORS['red' if int(bet_type) in RED else ('black' if int(bet_type) in BLACK else 'green')]}"

        embed = self.embed.copy()
        number, color = self.roll_roulette()
        embed.description = f"Your bet is {COLORS[bet_type] if bet_type.lower() in ('green', 'red', 'black') else ''.join([NUMBER_MAP[str(digit)] for digit in str(bet_type)]) if bet_type.lower() not in ('high', 'low') else bet_type} {extras}"
        poster = self.create_poster(number, color)
        embed.add_field(name="Bet Colors:",
                        value="> 🟥: `2x`\n> ⬛: `2x`\n> 🟩: `35x`")
        embed.add_field(
            name="Bet Numbers:", value="> :one: - :three::six:: `35x`\n> Even/Odd: `2x`\n> High/Low: `2x`")
        embed.add_field(name="Result:", value=poster, inline=False)
        embed.set_footer(text=f"Do {ctx.prefix}roulette help for help")
        await ctx.reply(embed=embed, mention_author=False)

    @roulette.command(name="help", aliases=["support"])
    @commands.guild_only()
    async def show_help_menu(self, ctx: Context):
        """
        A roulette rules and support embed board
        """
        embed = self.embed.copy()
        embed.description = "A game of roulette! Here are rules for the starter.\n\nJust like any other gambling game, you will win if the ball lands on your bet. Remember that 1 - 18 are low numbers and 19 - 36 are high numbers for probability betting. I.e. if you had your bet on red and if the ball lands on any red squares you win."
        embed.add_field(name="Bet Colors:",
                        value="> 🟥: `2x`\n> ⬛: `2x`\n> 🟩: `35x`")
        embed.add_field(
            name="Bet Numbers:", value="> :one: - :three::six:: `35x`\n> Even/Odd: `2x`\n> High/Low: `2x`")
        embed.add_field(
            name="Examples:", value=f"To start a bet, you have to decide the bet type and the bet.\n\n**`{ctx.prefix}roulette red 1000`**\n**`{ctx.prefix}roulette 23 1000`**", inline=False)
        embed.set_footer(
            text=f"Do {ctx.prefix}roulette <bet_type> to start playing")

        #embed.set_thumbnail(url=ROULETTE_BOARD)
        await ctx.reply(embed=embed, mention_author=False)


def setup(bot):
    """Loads the Roulette cog"""
    bot.add_cog(Roulette(bot))
    print("Roulette.cog is loaded")
