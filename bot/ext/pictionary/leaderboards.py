import discord
import json

from discord.ext import commands

from bot.utils.paginator import Paginator
from bot.utils.prefixes import get_real_prefix
from bot.utils.checks import is_admin
from bot.constants import Colour

from .src.database import DB

BLACKLIST_PATH = "bot/ext/pictionary/src/blacklisted.json"


class Leaderboards(commands.Cog):
    """
    Daily leaderboards are updated every 2 hours.
    All time leaderboards are updated every day.
    """

    def __init__(self, bot):
        self.bot = bot
        self.color = Colour.SUN_YELLOW

        self.awards = ['🌟🥇🌟', '🥈', '🥉', ':four:', ':five:',
                       ':six:', ':seven:', ':eight:', ':nine:', '🔟',
                       '11th', '12th', '13th', '14th', '15th', '16th',
                       '17th', '18th', '19th', '20th', '21th', '22th',
                       '23th', '24th', '25th', '26th', '27th', '28th',
                       '29th', '30th']
        self.books = []
        self.buttons = ['⬅️', '➡️', '🗑️']

        with open(BLACKLIST_PATH, "r") as file:
            self.blacklisted = json.load(file)

    @commands.group(name="blacklist", aliases=["bl"], invoke_without_command=True)
    @commands.guild_only()
    @commands.check(is_admin)
    async def blacklist(self, ctx, score, type):
        """IGNORE"""
        async with DB() as cont:
            values = await cont.get_value("daily_boards" if type.lower() == "daily" else "all_time_leaderboards")
        culprits = [(record[0], self.bot.get_user(int(record[0])).display_name, record[1])
                    for record in values if int(record[1]) == int(score)]
        await ctx.channel.send(f"Possible culprits:{culprits}\nPlease insert the ID")
        msg = await self.bot.wait_for('message', check=lambda x: x.author == ctx.author)
        with open(BLACKLIST_PATH, "w") as file:
            self.blacklisted["IDs"].append(int(msg.content))
            json.dump(self.blacklisted, file)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        """
        Instantiate the subclass Leaderboards from the framework directory
        that handles fetching data
        """
        if str(payload.emoji) not in self.buttons or payload.member == self.bot:
            return
        if self.books:
            for book in self.books:
                if book.state == '0':
                    self.books.remove(book)
                elif book.state == '1':
                    await book.check_action(payload)

    @commands.group(name="leaderboard", aliases=["leaderboards", "lb", "top", "board"], invoke_without_command=True)
    @commands.guild_only()
    async def leaderboards(self, ctx):
        """IGNORE"""
        await self.global_leader_board(ctx)

    @leaderboards.command(name="daily", aliases=["dailys", "d", "today"])
    async def daily_leader_board(self, ctx):
        """
        Fetches data from the daily boards table and
        visualize the data
        """
        async with DB() as cont:
            values = await cont.get_value("daily_boards")
        prefix = ctx.prefix
        generator = [(x[0], x[1]) for x in sorted(values, key=lambda x: x[1],
                                                  reverse=True) if x[0] not in self.blacklisted["IDs"]][:50]
        entry = Paginator(self.buttons, 60)
        if values:
            values = {user_id: score for (user_id, score) in generator}
            fields = []
            for i, key in enumerate(values.keys()):
                fields.append(
                    ('\u200b', f"{self.awards[i]} • {self.bot.get_user(key).display_name} : {values[key]} pts • { (self.awards[i] if i <= 2 else '')}", False))
                if len(values.keys()) > 10 and (i % 9 == 0 or i+1 == len(values.keys())) and i != 0:
                    entry.add_page(title="__**# DAILY LEADERBOARDS**__", thumbnail_url="https://cdn.discordapp.com/attachments/806122193301274634/812964996446945280/trohpy.png",
                                   fields=fields, color=self.color, footer=f"• File a report using {prefix}report <report> for abuse and bugs")
                    fields = []
            if len(values.keys()) < 10:
                entry.add_page(title="__**# DAILY LEADERBOARDS**__", thumbnail_url="https://cdn.discordapp.com/attachments/806122193301274634/812964996446945280/trohpy.png",
                               fields=fields, color=self.color, footer=f"• File a report using {prefix}report <report> for abuse and bugs")
            await entry.send_pages(ctx.channel, ctx.author)
            self.books.append(entry)
        elif not values:
            embed = discord.Embed(
                title='__**# DAILY LEADERBOARDS**__', color=self.color)
            embed.description = f"Commands : `{prefix}pictionary start <rounds> <participants>`"
            embed.set_image(
                url="https://cdn.discordapp.com/attachments/806122193301274634/812964996446945280/trohpy.png")
            embed.add_field(name="LEADERBOARDS ARE CURRENTLY DISABLED!",
                            value="Go now and participate in the daily leaderboards by winning some pictionary games once it is enabled! The leaderboard updates every 2 hours. Everyone can see this leaderboard!")
            await ctx.send(embed=embed)

    @leaderboards.command(name="global", aliases=["alltimes", "alltime", "at"])
    async def global_leader_board(self, ctx):
        """
        Fetches data from the all time boards table and
        visualize the data
        """
        async with DB() as cont:
            values = await cont.get_value("all_time_leaderboards")
        prefix = ctx.prefix

        if values:
            values.sort(key=lambda x: x[1], reverse=True)

            # Get the first 50 users with all members that returned none or blacklisted
            # are filtered out
            values = [(x[0], x[1]) for x in values
                      if x[0] not in self.blacklisted["IDs"] and
                      ctx.guild.get_member(x[0])][:50]
        if values:
            entry = Paginator(self.buttons, 60)
            fields = []
            for i, key in enumerate(values.keys()):
                fields.append(
                    ('\u200b', f"{self.awards[i]} • {values[key].display_name} : {values[key]} pts • { (self.awards[i] if i <= 2 else '')}", False))
                if len(values.keys()) > 10 and (i % 9 == 0 or i+1 == len(values.keys())) and i != 0:
                    entry.add_page(title="__**# ALL-TIMES LEADERBOARDS**__", thumbnail_url="https://cdn.discordapp.com/attachments/806122193301274634/812964996446945280/trohpy.png",
                                   fields=fields, color=self.color, footer=f"• File a report using {prefix}report <report> for abuse and bugs")
                    fields = []
            if len(values.keys()) < 10:
                entry.add_page(title="__**# ALL-TIMES LEADERBOARDS**__", thumbnail_url="https://cdn.discordapp.com/attachments/806122193301274634/812964996446945280/trohpy.png",
                               fields=fields, color=self.color, footer=f"• File a report using {prefix}report <report> for abuse and bugs")
            await entry.send_pages(ctx.channel, ctx.author)
            self.books.append(entry)
        elif not values:
            embed = discord.Embed(
                title='__**# ALL-TIMES LEADERBOARDS**__', color=self.color)
            embed.description = f"Commands : `{prefix}pictionary start <rounds> <participants>`"
            embed.set_image(
                url="https://cdn.discordapp.com/attachments/806122193301274634/812964996446945280/trohpy.png")
            embed.add_field(name="LEADERBOARDS ARE CURRENTLY DISABLED!",
                            value="Go now and participate in the ALL-TIMES leaderboards by winning some pictionary games once it is enabled! The leaderboard updates every 24 hours. Everyone can see this leaderboard!")
            await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Leaderboards(bot))
    print('Leaderboards.cog is loaded')
