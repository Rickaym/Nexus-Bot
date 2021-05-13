import discord
import asyncio

from discord.ext import commands
from bot.utils.prefixes import PrefixHandler, get_real_prefix

class Misc(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot = bot
        self.db = "bot/assets/prefixes.db"

    @commands.command(name="help")
    async def help_command(self, ctx):
        cmds = '''```md
Gamble
----------
<A> $deathroll <member> - Game of deathroll against someone
<B> $slots - Normal slots
<C> $roll <member> - Dice roll against someone
<D> $roulette help - Roulette

Games
----------
<E> $gtc - guess the character game help
<F> $pictionary - pictionary game help
<G> $deception - IN ALPHA deception game help
```'''.replace('$', ctx.prefix)
        await ctx.reply(f"Hey there! The help menu hasn't been completed yet, here are a few commands to try. The bot's official name will be changed to **`Nexus`** OR **`Games`** soon along with the revamp. Expect great things!; {cmds}")

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        async with PrefixHandler(self.db) as cont:
            await cont.update_value("prefixes", {guild.id: "~"})

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        async with PrefixHandler(self.db) as ctx:
            await ctx.delete_value("prefixes", guild.id)

    @commands.Cog.listener()
    async def on_message(self, message):
        if '<@!769198596339269643>' == message.content:
            await self.prefix(message)

    # Prefix finding Command
    @commands.group(invoke_without_command=True)
    @commands.guild_only()
    async def prefix(self, ctx):
        prefix = await get_real_prefix(ctx.guild.id)
        embed = discord.Embed(
            title=f"Preset", description=f"CURRENT SERVER PREFIX : \n1. '`{prefix}`' \n2.{ctx.guild.me.mention}\nExecute `{prefix}prefix change <new_prefix>` command to change prefixes!", colour=discord.Color.random())
        await ctx.channel.send(embed=embed)

    @prefix.command()
    @commands.guild_only()
    async def change(self, ctx, prefix):
        async with PrefixHandler(self.db) as cont:
            await cont.update_value("prefixes", {ctx.guild.id: prefix})
        embed = discord.Embed(
            title=f"Success!", description=f'PREFIX SUCCESSFULLY CHANGED INTO : `{prefix}`\nExecute `{prefix}prefix` command to check the local prefix anytime!', colour=discord.Color.random())
        await ctx.send(embed=embed)

def setup(bot):
    bot.add_cog(Misc(bot))
