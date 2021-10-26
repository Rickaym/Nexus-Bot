import discord

from io import StringIO
from discord.embeds import Embed
from discord.ext.commands import Context
from discord.ext import commands
from discord.ext.commands.core import is_owner

from bot.constants import Colour, SILENT_MODULES, BETA_MODULES
from bot.utils.prefixes import PrefixHandler, get_real_prefix

HELP_ICONS = {"gamble": '🎰', "pictionary":'🖌️',
                "speedgames": '🎡', "tabletop": "🏓",
                "deception": '🗣️', "default": "🧩"}

class Misc(commands.Cog):
    """
    Miscellaneous commands for administrators and inquisitive users.
    """
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.db = "bot/assets/prefixes.db"

    def get_general_help_embed(self, ctx):
        embed = Embed(color=0x1cc7d4)
        embed.set_author(name="NEXUS ➖ THE FORCE TO BE RECKONED WITH!")
        modules = {}
        for ext in self.bot.EXTENSIONS:
            fn, cog = ext.replace("bot.ext.", '', -1).split('.')
            try:
                modules[fn].append(cog)
            except KeyError:
                modules[fn] = [cog]
        field_group = []
        report = ""
        for fn, cog in modules.items():
            report += f"{HELP_ICONS.get(fn, HELP_ICONS['default'])} **[{fn.title()}](https://github.com/Rickaym/Nexus-Bot/tree/main/bot/ext/{fn}/README.md \"{ctx.prefix}help {fn}\")**" + (' 🇧' if fn.lower() in BETA_MODULES else '')
            for pce in cog:
                if pce.lower() not in [m.lower() for m in SILENT_MODULES]:
                    report += f"\n➖ {pce}"
            report += f"\n"
            if report.count('\n') >= 5:
                field_group.append(("Games" if len(embed.fields) == 0 else "\u200b", report))
                report = ""
        if report:
            field_group.append(("\u200b", report))
        field_group.sort(key=lambda i: len(i[1]), reverse=True)
        for f in field_group:
            embed.add_field(name=f[0], value=f[1])
        embed.add_field(name="🗞️ News", value=f"```diff\n+ Hey guys! After some down time, nexus has finally been released and the matchmaking process has been extended. You can now play most singleplayer games cross-server with players around the world!\n- Support at {ctx.prefix}support```")
        embed.add_field(name="A New Chapter .. .", value="```⁣          🎈    ☁️   "
                                                        "\n         🎈🎈🎈      "
                                                        "\n ☁️     🎈🎈🎈🎈     "
                                                        "\n        🎈🎈🎈🎈     "
                                                        "\n   ☁️    ⁣🎈🎈🎈      "
                                                        "\n            🎈        "
                                                        "\n☁️   🇭🇮-🛩️ ☁️       ```", inline=True)
        return embed

    def parse_doc(self, ctx, doc):
        """
        Normal module docs are permitted to contain special symbols that represent a
        component of the bot. They must be parsed and returned.
        """
        return doc.replace("%prefix", ctx.prefix, -1) if doc else doc

    def get_module_help_embed(self, ctx, module):
        cog_map = tuple(filter(lambda c: c[0].lower() == module.lower(), self.bot.cogs.items()))
        if len(cog_map) == 0:
            return Embed(title=f"I couldn't find the module named {module}!", description="Try again...", color=Colour.EXCEPTION)

        cog_name, cog = cog_map[0]
        if hasattr(cog, "help_embed"):
            return cog.help_embed(ctx)
        embed = Embed(color=Colour.BABY_PINK)
        embed.set_author(name=module.title(), icon_url="https://raw.githubusercontent.com/twitter/twemoji/master/assets/72x72/1f3f7.png")
        embed.description = self.parse_doc(ctx, cog.__doc__) or f"There was once a module called {module}..."
        for cmd in sorted(cog.__cog_commands__, key=lambda cmd: len(f"➕ {cmd.qualified_name} {cmd.signature}")):
            if str(cmd.callback.__doc__).strip().lower() != "ignore":
                notate = f"➕ {cmd.qualified_name} {cmd.signature}"
                embed.add_field(name=notate, value=self.parse_doc(ctx, cmd.callback.__doc__), inline=False if len(notate) > 46 else True)
        if cog_name.lower() in BETA_MODULES:
            embed.add_field(name="\u200b", value="\n```diff\n- This is a beta module! You may only use them in the development server.```", inline=False)
        return embed

    @commands.command(name="help")
    async def help_command(self, ctx: Context, *, module: str = ''):
        """
        Get helping details about a target module or the general bot.
        """
        if not module:
            embed = self.get_general_help_embed(ctx)
        else:
            embed = self.get_module_help_embed(ctx, module)
        await ctx.reply(embed=embed)

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        async with PrefixHandler(self.db) as cont:
            await cont.update_value("prefixes", {guild.id: "~"})

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        async with PrefixHandler(self.db) as ctx:
            await ctx.delete_value("prefixes", guild.id)

    @commands.command(name="guilds")
    @commands.guild_only()
    @commands.is_owner()
    async def guilds(self, ctx):
        """IGNORE"""
        guilds = [i.name for i in self.bot.guilds]
        text = '\n'.join(guilds)

        report = StringIO()
        report.write(text)
        report.seek(0)

        truncated_records = (text.replace('\n', ', '))[:100]
        embed = discord.Embed(
            title="Guilds Joined", description=f"{truncated_records}... Find more in the txt file below.", colour=discord.Color.random())
        embed.set_footer(text=f'Total of {len(guilds)} guild(s)')
        await ctx.send(embed=embed, file=discord.File(report, filename="records.txt"))
        await self.bot.change_presence(status=discord.Status.online, activity=discord.Activity(type=discord.ActivityType.listening, name=f'~help | {len(self.bot.guilds)} guilds'))

    @commands.Cog.listener()
    async def on_message(self, message):
        if  message.content.strip() in (f"<@{self.bot.user.id}>", f"<@!{self.bot.user.id}>", self.bot.user.mention):
            await self.prefix(message)

    # Prefix finding Command
    @commands.group(invoke_without_command=True)
    @commands.guild_only()
    async def prefix(self, ctx):
        """
        Find out what the prefix of the current server is.
        """
        prefix = await get_real_prefix(ctx.guild.id)
        embed = discord.Embed(
            title=f"Preset", description=f"CURRENT SERVER PREFIX : \n1. '`{prefix}`' \n2.{ctx.guild.me.mention}\nExecute `{prefix}prefix change <new_prefix>` command to change prefixes!", colour=discord.Color.random())
        await ctx.channel.send(embed=embed)

    @prefix.command()
    @commands.guild_only()
    @commands.has_guild_permissions(manage_guild=True)
    async def change(self, ctx, prefix):
        """
        Change the prefix of the current server.
        """
        async with PrefixHandler(self.db) as cont:
            await cont.update_value("prefixes", {ctx.guild.id: prefix})
        embed = discord.Embed(
            title=f"Success!", description=f'PREFIX SUCCESSFULLY CHANGED INTO : `{prefix}`\nExecute `{prefix}prefix` command to check the local prefix anytime!', colour=discord.Color.random())
        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Misc(bot))
