import discord
import sqlite3
import aiosqlite

from discord.ext import commands

from bot.constants import Defaults
from bot.constants import Colour, Directory


def get_prefix(bot, message):
    if message.guild is None:
        return "~"
    elif message.guild is not None:
        with sync_handle_prefixes("bot/assets/minor.db") as cont:
            return commands.when_mentioned_or(cont.get_value("prefixes", message.guild.id))(bot, message)


async def get_real_prefix(guild_id):
    directory = "bot/assets/minor.db"
    async with PrefixHandler(directory) as cont:
        return await cont.get_value("prefixes", guild_id)


class sync_handle_prefixes:
    def __init__(self, full_path) -> None:
        self.path = full_path
        self.base_prefix = Defaults.PREFIX

    def __enter__(self) -> None:
        self.db = sqlite3.connect(self.path)
        return self

    def __exit__(self, type, value, traceback) -> bool:
        self.db.commit()
        self.db.close()
        if traceback is not None:
            print(f"{type}, {value}, {traceback}")
        else:
            return True

    def get_value(self, table, guild_id):
        query = f"SELECT prefix FROM {table} WHERE guildID = ?"
        val = (guild_id,)
        cursor = self.db.execute(query, val)
        prefix = cursor.fetchone()
        if prefix is not None:
            return prefix[0]
        elif prefix is None:
            self.set_value("prefixes", guild_id)
            return self.base_prefix

    def set_value(self, table, guild_id):
        query = f"INSERT INTO {table}(guildID, prefix) VALUES(?, ?)"
        val = (guild_id, self.base_prefix)
        self.db.execute(query, val)


class PrefixHandler:
    def __init__(self, full_path) -> None:
        self.path = full_path
        self.base_prefix = Defaults.PREFIX

    async def __aenter__(self) -> None:
        self.db = await aiosqlite.connect(self.path)
        return self

    async def __aexit__(self, type, value, traceback) -> bool:
        await self.db.commit()
        await self.db.close()
        if traceback is not None:
            print(f"{type}, {value}, {traceback}")
        else:
            return True

    async def update_value(self, table, dict):
        query = f"SELECT prefix FROM {table} WHERE guildID = ?"
        guild_id = (*dict,)
        async with self.db.execute(query, guild_id) as cursor:
            value = await cursor.fetchone()
            if value is not None:
                await self.delete_value(table, guild_id[0])
        query = f"INSERT INTO {table}(guildID, prefix) VALUES(?, ?)"
        new_values = (guild_id[0], dict[guild_id[0]])
        await self.db.execute(query, new_values)

    async def delete_value(self, table, guild_id):
        query = f"DELETE FROM {table} WHERE guildID = ?"
        await self.db.execute(query, (guild_id,))

    async def get_value(self, table, guildID):
        query = f"SELECT prefix FROM {table} WHERE guildID = ?"
        val = (guildID,)
        async with self.db.execute(query, val) as cursor:
            prefix = await cursor.fetchone()
            if prefix is None:
                await self.update_value(table, {guildID: self.base_prefix})
                return self.base_prefix
            elif prefix is not None:
                return prefix[0]


class Prefixes(commands.Cog):
    '''Basic class to handle custom prefixes'''

    def __init__(self, bot):
        self.bot = bot
        self.color = Colour.BABY_PINK
        self.minor_dir = Directory.MODULES

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        async with PrefixHandler(self.minor_dir) as cont:
            await cont.update_value("prefixes", {guild.id: "~"})

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        async with PrefixHandler(self.minor_dir) as ctx:
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
            title=f"Preset", description=f"CURRENT SERVER PREFIX : \n1. '`{prefix}`' \n2.{ctx.guild.me.mention}\nExecute `{prefix}prefix change <new_prefix>` command to change prefixes!", colour=self.color)
        await ctx.channel.send(embed=embed)

    @prefix.command()
    @commands.guild_only()
    async def change(self, ctx, prefix):
        async with PrefixHandler(self.minor_dir) as cont:
            await cont.update_value("prefixes", {ctx.guild.id: prefix})
        embed = discord.Embed(
            title=f"Success!", description=f'PREFIX SUCCESSFULLY CHANGED INTO : `{prefix}`\nExecute `{prefix}prefix` command to check the local prefix anytime!', colour=self.color)
        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Prefixes(bot))
    print('Prefixes.cog is loaded')


'''
return
async for entry in guild.audit_logs(action=discord.AuditLogAction.bot_add):
    if entry.target == self.bot.user:
        embed = discord.Embed(
            title="__# Notice__", description="Hey there buddy! I've noticed that you invited me into your server, here are some commands you can do to start-up!", color=self.color)
        fields = (('\nBrief Guide:', f'`~help`', True),
                    ('\nIn-depth Guide:', f'`~help guide`', True),
                    ('\nVisual tutorial:', f'`~help tutorial`', True),
                    ('\nPrefix Commands:', f'`~prefix` (Shows Current Prefix)\n`~prefix change <new_prefix>`(Changes Current Prefix)', False))
        for name, value, inline in fields:
            embed.add_field(name=name, value=value, inline=inline)
        embed.set_footer(
            text='Have a wonderful time playing pictionary!')
        inviter = entry.user
        await inviter.send(embed=embed)
        return'''
