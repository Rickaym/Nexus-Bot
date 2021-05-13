import discord
import random
import asyncio

from discord.ext import commands
from discord import Member, Message, Embed
from discord.ext.commands.context import Context

from bot.constants import NUMBER_MAP

START_NUM = 1_000_000

SLOTS_ROLL_EMOJI = "<a:slots:822066633262366731>"
DICER_ROLL_EMOJI = '<a:numberroll:822150497863335957>'


class DeathRoll(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.embed = Embed(
            title="Death Roll",
            color=discord.Color.random(),
        )

        self.embed.set_author(name="Pictionary' Gamble",
                              icon_url="https://cdn0.iconfinder.com/data/icons/casinos-and-gambling/500/SingleCartoonCasinoAndGamblingYulia_6-512.png")
        self.embed.set_footer(
            text=f"To get support • {bot.command_prefix}help deathroll")

    def convert_to_emoji(self, number: int) -> str:
        """
        Takes in an integer and translates it into a series of discord emojis
        for better display.
        """
        sequence = ''
        number = str(number)
        for i in range(7-len(number)):
            sequence += f"🟦"

        for num in list(number):
            sequence += f"{NUMBER_MAP[num]}"
        return sequence

    async def animate_embed(self, message: Message, embed: Embed, p1: Member, p2: Member, results: list, status: str = "ongoing") -> Embed:
        """
        Animates the embed with moving emojis and static numbers
        in turns.
        """
        p1_place = self.convert_to_emoji(results[0])
        p2_place = self.convert_to_emoji(results[1])

        embed.set_field_at(
            0,
            name=p1.display_name +
            (' 🎉' if results[0] < results[1] and status == 'win' else ''),
            value=p1_place
        )
        embed.set_field_at(
            1,
            name=p2.display_name +
            (' 🎉' if results[1] < results[0] and status == 'win' else ''),
            value=p2_place
        )
        await message.edit(embed=embed)
        if status != "win":
            await asyncio.sleep(2)
            embed.set_field_at(
                0,
                name=p1.display_name,
                value=''.join([DICER_ROLL_EMOJI if i >= p1_place.count(
                    '🟦') else '🟦' for i in range(7)])
            )
            embed.set_field_at(
                1,
                name=p2.display_name,
                value=''.join([DICER_ROLL_EMOJI if i >= p2_place.count(
                    '🟦') else '🟦' for i in range(7)])
            )
            await message.edit(embed=embed)
        return embed

    @commands.command(name="deathroll", aliases=["dr"])
    @commands.guild_only()
    async def death_roll(self, ctx: Context, member: discord.Member):
        """
        A simple game of randomized subtraction where the first person to reach 1 from 1 mil wins
        """
        if member == ctx.author:
            return

        REST_TIME = 0.6
        msg = await ctx.reply(f"{member.display_name} please react to this message with 🤝 to accept the challenge.", mention_author=False)
        await msg.add_reaction('🤝')
        try:
            await self.bot.wait_for('reaction_add', timeout=60.0, check=lambda reaction, user: user == member and str(reaction.emoji) == '🤝')
        except asyncio.TimeoutError:
            await msg.edit(content="📲 Your opponent didn't respond in time.")
            return

        p1_num = START_NUM
        p2_num = START_NUM

        embed = self.embed.copy()
        embed.description = f"**🍯 BETA-Coming soon™️**\n\n> The first person to reach 1 wins, let's get it goin~!!"
        embed.add_field(name=ctx.author.display_name,
                        value=self.convert_to_emoji(p1_num))
        embed.add_field(name=member.display_name,
                        value=self.convert_to_emoji(p2_num))
        msg = await ctx.reply(embed=embed, mention_author=False)
        await asyncio.sleep(1)

        embed.description = f"**🍯 BETA-Coming soon™️**\n\n <:slowmode:835921659068022814> **`Let's start the rollingggggggg~`**"
        embed.set_field_at(
            0, name=ctx.author.display_name + 'insert', value=''.join([DICER_ROLL_EMOJI for i in range(6)]))
        embed.set_field_at(
            1, name=member.display_name + 'insert', value=''.join([DICER_ROLL_EMOJI for i in range(6)]))
        await msg.edit(embed=embed)
        await asyncio.sleep(1)

        while True:
            p1_num -= random.randint(p1_num//2, p1_num - 1)
            p2_num -= random.randint(p2_num//2, p2_num - 1)

            if p1_num == 1 or p2_num == 1:
                embed = await self.animate_embed(msg, embed, ctx.author, member, (p1_num, p2_num), "win")
                break
            else:
                embed = await self.animate_embed(msg, embed, ctx.author, member, (p1_num, p2_num))
            await asyncio.sleep(REST_TIME)

        embed.description = f"{ctx.author.display_name if p1_num == 1 else member.display_name} won the game! Congratulations."

        if p1_num == 1 and p2_num == 1:
            embed.description = "It's a tie! Your \"bets\" have been returned."
        await msg.edit(embed=embed)


def setup(bot):
    """Loads the DeathRoll cog"""
    bot.add_cog(DeathRoll(bot))
    print("DeathRoll.cog is loaded")
