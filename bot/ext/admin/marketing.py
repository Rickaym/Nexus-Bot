import dbl
import discord
import aiohttp

from dotenv import load_dotenv
from os import getenv
from discord.ext import commands


class Marketing(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        load_dotenv()

        self.DBLTOKEN = getenv("DBLTOKEN")
        self.DISBOTSGG = getenv("DISBOTSGG")
        self.MOTIONDEV = getenv("MOTIONDEV")
        self.DBLAPIKEY = getenv("DBLAPIKEY")

        self.dblpy = dbl.DBLClient(self.bot, self.DBLTOKEN)

        self.bot.loop.create_task(self.post_server.callback(self))

    # The decorator below will work only on discord.py 1.1.0+
    # In case your discord.py version is below that, you can use self.bot.loop.create_task(self.update_stats())

    @commands.command(name="postserver", aliases=["ps"])
    async def post_server(self, ctx=None):
        """
        Updating server counts command, this function runs every 30 minutes to
        automatically update your server count.
        """
        await self.bot.wait_until_ready()
        if self.bot.user.id == 807283060164919316:
            return
        guild_count = len(self.bot.guilds)
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://discord.bots.gg/api/v1/bots/768442873561481216/stats",
                json={"guildCount": guild_count},
                headers={
                    "Content-type": "application/json",
                    "Authorization": self.DISBOTSGG,
                },
            ) as r:
                if ctx:
                    await ctx.send(f"DiscordBotsGG: {r.status} {await r.text()}")
            async with session.post(
                "https://www.motiondevelopment.top/api/bots/768442873561481216/stats",
                json={"guilds": guild_count},
                headers={"content-type": "application/json", "key": self.MOTIONDEV},
            ) as r:
                if ctx:
                    await ctx.send(f"MotionDev: {r.status} {await r.text()}")
            async with session.post(
                "https://discordbotlist.com/api/v1/bots/768442873561481216/stats",
                json={
                    "guilds": guild_count,
                    "users": sum([g.member_count for g in self.bot.guilds]),
                },
                headers={
                    "content-type": "application/json",
                    "Authorization": self.DBLAPIKEY,
                },
            ) as r:
                if ctx:
                    await ctx.send(f"DiscordBotList: {r.status} {await r.text()}")
        try:
            await self.dblpy.post_guild_count()
        except Exception as e:
            print("Failed to post server count\n{}: {}".format(type(e).__name__, e))
        await self.bot.update_status()

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        await self.post_server.callback(self)

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        await self.post_server.callback(self)


def setup(bot):
    bot.add_cog(Marketing(bot))
    print("Marketing is loaded")
