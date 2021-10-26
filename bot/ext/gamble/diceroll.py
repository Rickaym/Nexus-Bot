import discord
import random
import asyncio

from discord import Member
from discord.ext import commands
from discord.message import Message
from discord.ext.commands.context import Context

from bot.constants import NUMBER_MAP

DICER_ROLL_EMOJI = '<a:numberroll:822150497863335957>'


class DiceRoll(commands.Cog):
    def __init__(self, bot: discord.Client):
        self.bot = bot
        self.jobs = {}
        self.embed = discord.Embed(
            title="Roll",
            color=discord.Colour.random(),
        )
        self.embed.set_author(name=f"Nexus' Gamble",
                              icon_url="https://cdn0.iconfinder.com/data/icons/casinos-and-gambling/500/SingleCartoonCasinoAndGamblingYulia_6-512.png")
        self.embed.set_thumbnail(
            url="https://raw.githubusercontent.com/twitter/twemoji/master/assets/72x72/1f3b0.png"
        )
        self.embed.set_footer(
            text="Type ~wallet to check how much gold you have.")

    async def update_embed(self, id, turn: str, message: str, value: str):
        """
        Updates the embed with rolling animations and stopping animations
        using intervals of numbers.
        """
        embed = self.jobs[id]
        embed.add_field(
            name=turn, value=f"{DICER_ROLL_EMOJI}{DICER_ROLL_EMOJI}{DICER_ROLL_EMOJI}")
        await asyncio.sleep(2.5)

        value = str(value)
        value = '0' + value if len(value) == 2 else '00' + \
            value if len(value) == 1 else value
        for i in range(3):
            embed.set_field_at(
                index=len(embed.fields)-1,
                name=turn,
                value=f"{NUMBER_MAP[value[0]]}{DICER_ROLL_EMOJI if i < 1 else f'{NUMBER_MAP[value[1]]}'}{DICER_ROLL_EMOJI if i < 2 else f'{NUMBER_MAP[value[2]]}'}",
            )
            await message.edit(embed=self.jobs[id])
            await asyncio.sleep(1)

    async def animate_embed(self, ctx: Context, id: int, p1: Member, p2: Member, results: list) -> Message:
        """
        Animate the embed twice, once for player 1 and once for player 2
        """
        embed = self.jobs[id]
        embed.description = f"Alright, let's start rolling the numbers for **`{p1.display_name}`**, best of luck."
        message = await ctx.reply(embed=embed, mention_author=False)
        await self.update_embed(p1.id, p1.display_name, message, results[0])
        embed.description = f"Alright, let's start rolling the numbers for **`{p2.display_name}`**, best of luck."
        await self.update_embed(p1.id, p2.display_name, message, results[1])
        return message

    @commands.command(name="roll", aliases=["rolls"])
    @commands.guild_only()
    async def dice_roll(self, ctx: Context, member: Member):
        """
        A chance game that two players can partake in where each gets a random number from 0-100. The player with the higher number wins the game.
        """
        if member == ctx.author:
            return

        msg = await ctx.reply(f"{member.display_name} please react to this message with 🤝 to accept the challenge.", mention_author=False)
        await msg.add_reaction('🤝')
        try:
            await self.bot.wait_for('reaction_add', timeout=60.0, check=lambda reaction, user: user == member and str(reaction.emoji) == '🤝')
        except asyncio.TimeoutError:
            await msg.edit(content="📲 Your opponent didn't respond in time.")
            return

        author_id = ctx.author.id
        self.jobs[author_id] = self.embed.copy()
        embed = self.jobs[author_id]
        embed.title = f"**🍯 BETA-Coming soon™️**"

        p1_num, p2_num = random.randint(0, 100), random.randint(0, 100)
        message = await self.animate_embed(ctx, author_id, ctx.author, member, (p1_num, p2_num))
        if p1_num == p2_num:
            embed.description = f"It's a tie! No one wins or loses money."
            await message.edit(embed=embed)
            del self.jobs[ctx.author.id]
            return
        else:
            winner = ctx.author if p1_num > p2_num else member
            embed.description = f"{winner.display_name} has won the gamble by a margin of {p1_num-p2_num if p1_num > p2_num else p2_num-p1_num}."
        await message.edit(embed=embed)
        del self.jobs[ctx.author.id]


def setup(bot):
    """Loads the diceroll cog"""
    bot.add_cog(DiceRoll(bot))
    print("DiceRoll.cog is loaded")
