import random
import discord
import asyncio

from discord.ext import commands
from discord.ext.commands.context import Context
from typing import Optional, Tuple

from discord.message import Message

SLOT_MAP = {0: "🥨", 1: "🍖", 2: "💠", 3: "💸", 4: "💰", 5: "💍"}

SLOTS_ROLL_EMOJI = "<a:slots:822066633262366731>"

PAYMAP = {
    "[5, 3]": "16x",
    "[4, 3]": "8x",
    "[3, 3]": "4x",
    "[2, 3]": "2x",
    "[1, 3]": "1.5x",
    "[0, 3]": "1x",

    "[5, 2]": "8x",
    "[4, 2]": "4x",
    "[3, 2]": "2x",
    "[2, 2]": "1.5x",
    "[1, 2]": "1.25x",
    "[0, 2]": "1x",
}

MULTIPAYMAP = {
    5: 5,
    4: 4,
    3: 3,
    2: 2,
    1: 1,
    0: 0
}

PAYOUT = "\n> ".join(
    [
        f"{SLOT_MAP[5]}{SLOT_MAP[5]}{SLOT_MAP[5]} = 16x",
        f"{SLOT_MAP[4]}{SLOT_MAP[4]}{SLOT_MAP[4]} = 8x",
        f"{SLOT_MAP[3]}{SLOT_MAP[3]}{SLOT_MAP[3]} = 4x",
        f"{SLOT_MAP[2]}{SLOT_MAP[2]}{SLOT_MAP[2]} = 2x",
        f"{SLOT_MAP[1]}{SLOT_MAP[1]}{SLOT_MAP[1]} = 1.5x",
        f"{SLOT_MAP[0]}{SLOT_MAP[0]}{SLOT_MAP[0]} = Money Back / 1x",
    ]
)

MULTIPAYOUT = "\n> ".join(
    [
        f"{SLOT_MAP[5]} = 5 pts",
        f"{SLOT_MAP[4]} = 4 pts",
        f"{SLOT_MAP[3]} = 3 pts",
        f"{SLOT_MAP[2]} = 2 pts",
        f"{SLOT_MAP[1]} = 1 pts",
        f"{SLOT_MAP[0]} = 0 pts",
    ]
)


class Slots(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.embed = discord.Embed(
            title="Plot Your Slots",
            description=f"G'day sire/my'lady. \n**Here's the payout scheme**:\n> {PAYOUT}",
            color=discord.Colour.random(),
        )
        self.embed.set_author(name="Pictionary' Gamble",
                              icon_url="https://cdn0.iconfinder.com/data/icons/casinos-and-gambling/500/SingleCartoonCasinoAndGamblingYulia_6-512.png")
        self.embed.set_thumbnail(
            url="https://raw.githubusercontent.com/twitter/twemoji/master/assets/72x72/1f3b0.png"
        )

    def roll_slots(self, difficulty='hard') -> Tuple[Tuple[list, int], str]:
        """
        Picks three digits to form a pack of one to five tuple to create a
        a hypothetical situation of a slots machine being spun.
        These numbers are attached to a specific slot symbol.
        216 combinations
        """
        if difficulty == 'hard':
            charter = (0, 0, 0, 0,
                       1, 1, 1,
                       2, 2,
                       3, 4, 5)
        elif difficulty == 'easy':
            charter = (0, 1, 2,
                       3, 4, 5)
        return (random.choice(charter), random.choice(charter), random.choice(charter))

    def consume(self, bet: int, indication: str) -> int:
        """
        Takes in a string amount and parses it into arithmetic ready
        value based on indication. The return value is still un-commissioned.
        """
        if str(indication)[-1] != 'x':
            return float(bet)
        elif str(indication)[-1] == 'x':
            return float(indication[:-1]) * bet

    def evaluate(self, result: tuple, bet: int) -> Optional[Tuple[Tuple[int, int], int]]:
        """
        Evaluate whether the player had won or lost. If the player has won,
        it will also return the condition of which it is won too.
        """
        result = sorted(result)
        for value in list(SLOT_MAP.keys()):
            if value in result:
                if result.count(value) == 1:
                    continue
                elif result.count(value) == 2:
                    increment = PAYMAP[str([value, 2])]
                    return [value, 2], self.consume(bet, increment)
                elif result.count(value) == 3:
                    increment = PAYMAP[str([value, 3])]
                    return [value, 3], self.consume(bet, increment)
        return None, None

    async def update_embed(self, message: Message, results: tuple):
        """
        Updates the embed with rolling slot emojis
        """
        await asyncio.sleep(3)
        embed = message.embeds[0]
        for i in range(3):
            embed.set_field_at(
                0,
                name=embed.fields[0].name,
                value=f"{SLOT_MAP[results[0]]} 💴 {SLOT_MAP[results[1]] if i >= 1 else SLOTS_ROLL_EMOJI} 💴 {SLOT_MAP[results[2]] if i >= 2 else SLOTS_ROLL_EMOJI}",
            )
            await message.edit(embed=embed)
            await asyncio.sleep(2)

    async def update_balance(self, user_id: int, increment: int, bet: int):
        """
        Increment and decrement the amount of money based
        on the situation of the game.
        """
        if increment is None:
            async with DB() as cont:
                await cont.remove_bal(user_id, bet)
            return
        async with DB() as cont:
            await cont.add_bal(user_id, (increment*0.95)-bet)
            await cont.add_bal(self.bot.user.id, increment*0.05)

    async def wait_for_bet(self, message, ctx, p1, p2):
        embed = message.embeds[0]
        embed.add_field(name=p1.display_name,
                        value=f"\nPlease bet on how high the slot would hit. (0 - 15)")
        await message.edit(embed=embed)
        while True:
            try:
                p1bet = await self.bot.wait_for('message', timeout=60.0, check=lambda message: message.author == p1)
            except asyncio.TimeoutError:
                embed.description = "Player is inactive, the game is stopped."
                await message.edit(embed=embed)
                return
            try:
                float(p1bet.content)
            except:
                pass
            else:
                break
        embed.set_field_at(
            1,
            name=p1.display_name,
            value=f"Placed a bet on {p1bet.content}!")
        embed.add_field(name=p2.display_name,
                        value=f"\nPlease bet on how high the slot would hit. (0x - 16x)")
        await message.edit(embed=embed)
        while True:
            try:
                p2bet = await self.bot.wait_for('message', timeout=60.0, check=lambda message: message.author == p2 and str(message.content) != p1bet.content)
            except asyncio.TimeoutError:
                embed.description = "Player is inactive, the game is stopped."
                await message.edit(embed=embed)
                return
            try:
                float(p2bet.content)
            except:
                pass
            else:
                break
        embed.set_field_at(
            2,
            name=p2.display_name,
            value=f"Placed a bet on {p2bet.content}!")
        await message.edit(embed=embed)
        return (p1bet.content, p2bet.content)

    async def multipupdate_balance(self, p1, p2, condition, bet):
        if condition == 0:
            return
        async with DB() as cont:
            if condition == 1:
                await cont.add_bal(p1, (bet*1.9)-bet)
                await cont.remove_bal(p2, bet)
            elif condition == 2:
                await cont.add_bal(p2, (bet*1.9)-bet)
                await cont.remove_bal(p1, bet)
            await cont.add_bal(self.bot.user.id, bet*0.1)

    def multiplayer_evaluate(self, p1bet, p2bet, result):
        result = sorted(result)
        increment = 0.0
        for val in result:
            increment += MULTIPAYMAP[val]
        p1bet = float(p1bet)
        p2bet = float(p2bet)
        if abs(increment-p1bet) < abs(increment-p2bet):
            return 1, increment
        else:
            return 2, increment

        return 0, increment

    @commands.command(name="slots", aliases=["slot"])
    @commands.guild_only()
    async def slots(self, ctx: Context, member: discord.Member = None):
        """
        A classic game of slots, 3 slots and 6 symbols.
        """
        if member is None:
            await self.slots_singleplayer(ctx)
        elif member is not None:
            await self.slots_multiplayer(ctx, member)

    async def slots_multiplayer(self, ctx: Context, member: discord.Member):
        if member == ctx.author:
            return
        embed = self.embed.copy()
        embed.description = f"G'day sire/my'lady. \n**Here's the points scheme**:\n> {MULTIPAYOUT}\n\n`{ctx.author.display_name}` is playing against `{member.display_name}`!\nThe slots will randomly pick three symbols and add their points. The person to guess the number closest to it wins!"
        embed.add_field(
            name=f"**🍯 BETA-Coming soon™️**", value=f"{SLOTS_ROLL_EMOJI} 💴 {SLOTS_ROLL_EMOJI} 💴 {SLOTS_ROLL_EMOJI}"
        )
        message = await ctx.message.reply(embed=embed, mention_author=False)
        p1bet, p2bet = await self.wait_for_bet(message, ctx, ctx.author, member)
        result = self.roll_slots(difficulty='easy')
        await self.update_embed(message, result)

        condition, pay = self.multiplayer_evaluate(p1bet, p2bet, result)
        embed = message.embeds[0]
        winner = f'{ctx.author.display_name} has won the game.' if condition == 1 else f'{member.display_name} has won the game.' if condition != 0 else "Its a draw!"
        extra = f'Their bet `{p1bet if condition == 1 else p2bet}` was closer to the real digit {pay} pts' if condition != 0 else ''
        embed.description += f"\n\n**{winner}** {extra}"
        await message.edit(embed=embed)

    async def slots_singleplayer(self, ctx: Context):
        embed = self.embed.copy()
        embed.add_field(
            name=f"**🍯 BETA-Coming soon™️**", value=f"{SLOTS_ROLL_EMOJI} 💴 {SLOTS_ROLL_EMOJI} 💴 {SLOTS_ROLL_EMOJI}"
        )
        message = await ctx.message.reply(embed=embed, mention_author=False)
        result = self.roll_slots()
        await self.update_embed(message, result)

        condition, earn = self.evaluate(result, 0)

        embed = message.embeds[0]
        embed.description = ("**Well played!**" if condition is not None and earn is not None else f"Your have lost...\n") + (
            f"\nAn increment of {PAYMAP[str(condition)]} has be deposited to your account!" if earn != '1x' and earn is not None else "Better luck next time!" if earn is None else "Your bet is paid back!")
        await message.edit(embed=embed)


def setup(bot):
    """Loads the slots cog"""
    bot.add_cog(Slots(bot))
    print("Slots.cog is loaded")
