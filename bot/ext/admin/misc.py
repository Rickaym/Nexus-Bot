import discord

from io import StringIO
from discord.embeds import Embed
from discord.errors import Forbidden
from discord.ext.commands import Context
from discord.ext import commands
from datetime import datetime
from discord.message import Message
from random import randint, choice
from discord.raw_models import RawReactionActionEvent

from bot.utils.hearsay import Hearsay
from bot.utils.prefixes import PrefixHandler, get_real_prefix
from bot.constants import (SUPPORT_INVITE, Colour, BADGED_MODULES,
                          SILENT_MODULES, BETA_MODULES, Defaults)

HELP_ICONS = {"gamble": 'š°', "pictionary":'šļø',
                "speedgames": 'š”', "tabletop": "š",
                "deception": 'š£ļø', "default": "š§©"}

class Misc(commands.Cog):
    """
    Miscellaneous commands for administrators and inquisitive users.
    """
    help_for = ["admin", "gamble", "pictionary", "deception", "tabletop"]

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.db = "bot/assets/prefixes.db"

    def get_general_help_embed(self, ctx):
        embed = Embed(description="Revamped Pictionary bot unpacked with loads and loads of features!\n*press the dark squares..*", color=0x1cc7d4)
        embed.set_author(name="PICTIONARY ā TO BE NEXUS")
        modules = {}
        for ext in self.bot.EXTENSIONS:
            fn, cog = ext.replace("bot.ext.", '', -1).split('.')
            try:
                modules[fn].append(cog)
            except KeyError:
                modules[fn] = [cog]
        field_group = []
        report = ""
        for fn in self.help_for:
            cog = modules[fn]
            report += f"{HELP_ICONS.get(fn, HELP_ICONS['default'])} **[{fn.title()}](https://github.com/Rickaym/Nexus-Bot/tree/main/bot/ext/{fn}/README.md \"{ctx.prefix}help {fn}\")**" + (' š§' if fn.lower() in BETA_MODULES else '')
            for pce in cog:
                if pce.lower() not in [m.lower() for m in SILENT_MODULES]:
                    report += f"\nā¢ {pce}{(f' ' + BADGED_MODULES.get(pce, '')).replace(',', ' ', -1)}"
            report += '\n'
            if report.count('\n') >= 5:
                field_group.append(["\u200b", report.strip() + '\n'])
                report = ""
            report += '\n'

        if report.strip():
            field_group.append(["\u200b", report.strip() + '\n'])
        field_group.sort(key=lambda i: i[1].count('\n'), reverse=True)
        # sadly this needs to be removed for mobile
        # optimization
        if False:
            # decorative lines
            for grp in field_group:
                while grp[1].count('\n') <= 9:
                    decor = list("\nā¬ā¬ā¬ā¬ā¬")
                    decor[randint(1, 5)] = choice((f"||[{choice(('š„', 'š«', 'š§', 'šØ', 'ā¬', 'šŖ', 'š©', 'š¦', 'šļø'))}](https://youtu.be/9UHstqfSNJc \"You're safe.. but not for long!\")||", "||[š£](https://youtu.be/dQw4w9WgXcQ \"BOOM You're dead!\")||"))
                    grp[1] += ''.join(decor)

        # irritate the progression
        tmp = field_group[1]
        field_group[1] = field_group[-1]
        field_group[-1] = tmp
        for i, f in enumerate(field_group):
            if f[1]:
                embed.add_field(name="Games" if i == 0 else f[0], value=f[1])
        embed.add_field(name="šļø News", value=f"```diff\n+ Try out the new multi-player speed typing competition with {ctx.prefix}typing race. Enjoy the thrill. More games will be introduced to multiplayer.\n\n\n- Support at {ctx.prefix}support```")
        embed.add_field(name="š A New Chapter .. .", value="```ā£āāāāāāāāāāš  āāāļø   "
                                                        "\nāāāāāāāā ššš      "
                                                        "\nāāļøāāāāāšššš     "
                                                        "\nāāāāāāāāšššš     "
                                                        "\nāāāāļøāāāāā£ššš      "
                                                        "\nāāāāāāāāāāā š        "
                                                        "\nāļøāāāš­š®-š©ļøāāļø       ```", inline=True)
        #embed.set_footer(text=f"ā¢ Get support with {ctx.prefix}support")
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
        for cmd in sorted(cog.__cog_commands__, key=lambda cmd: len(f"ā {cmd.qualified_name} {cmd.signature}")):
            if str(cmd.callback.__doc__).strip().lower() != "ignore":
                notate = f"ā {cmd.qualified_name} {cmd.signature}"
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

    @commands.command(name="support")
    async def support(self, ctx: Context):
        admin_count = len(self.bot.support_guild.members)
        embed = Embed(description=f"<:onl:903016826450112542> {admin_count} Admin{'s' if admin_count else ''} "
                                  f"ā¢ Seek support by joining **[here](https://discord.gg/{SUPPORT_INVITE})** "
                                   "\n<:ofl:903017154486599690> HotLine ā¢ Contact through **`~report`** in the bot dms."
                                   , color=0x2F3136)
        embed.set_thumbnail(url=self.bot.support_guild.icon_url)
        embed.set_author(name="SEEK, AND YE SHALL FIND")
        embed.set_footer(text="If there are low amount of admins, please be patient.")
        await ctx.send(embed=embed)

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

    @commands.Cog.listener("on_message")
    async def my_prefix(self, message):
        if  message.content.strip() in (f"<@{self.bot.user.id}>", f"<@!{self.bot.user.id}>", self.bot.user.mention):
            await self.prefix(message)

    @commands.Cog.listener("on_message")
    async def report_hotline(self, message: Message):
        if (self.bot.hotline_channel is not None
            and message.channel.id == self.bot.hotline_channel.id and message.author.id in Defaults.ADMINS):
            if message.reference:
                ref = message.reference.cached_message or (await self.bot.hotline_channel.fetch_message(message.reference.message_id))
                if len(ref.embeds) != 0 and ref.embeds[0].author.name.isnumeric():
                    usr = await self.bot.fetch_user(int(ref.embeds[0].author.name))
                    if usr is None:
                        return await message.reply("Target user wasn't found when attempted fetching.")
                    try:
                        m = await usr.send(f"{await Hearsay.resolve_name(message.author)}: {message.content}")
                    except Forbidden:
                        return await message.reply("Couldn't message the target user.")
                    else:
                        e = await message.reply(f"{usr.id}-{m.id}")
                        await e.add_reaction('šļø')

    @commands.Cog.listener("on_raw_reaction_add")
    async def delete_hotline(self, payload: RawReactionActionEvent):
        """TODO: Implement"""
        return
        if (payload.channel_id == self.bot.hotline_channel.id and payload.member.id in Defaults.ADMINS
            and (msg:=self.bot.hotline_channel.get_message(payload.message_id)).author.id == self.bot.user.id
            and str(payload.emoji) == 'šļø'):
            usr, m_id = msg.content.split('-')
            usr = await self.bot.fetch_user(int(usr))
            usr.get_message

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

    @commands.command(name="report")
    @commands.dm_only()
    async def report(self, ctx: Context, *, incident: str):
        """
        Report for abuse or get hotline support - only through DMs.
        """
        await self.bot.hotline_channel.send(embed=Embed(description=incident, timestamp=datetime.utcnow()).set_footer(text=f"{ctx.author.name}#{ctx.author.discriminator}").set_author(name=str(ctx.author.id)))

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
