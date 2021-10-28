from dotenv import load_dotenv
from os import getenv
from discord.ext.commands.context import Context
from discord.embeds import Embed
from discord import Intents, Status, Activity, ActivityType
from discord.ext import commands

from bot.constants import Defaults, BETA_MODULES, PRIVILEGED_GUILDS, Colour, SUPPORT_GUILD, HOTLINE_CHANNEL
from bot.utils.extensions import EXTENSIONS
from bot.utils.prefixes import get_prefix

intents = Intents.default()
intents.reactions = True
intents.members = False # WILL BREAK THINGS

# Bot constructor
bot = commands.Bot(command_prefix=get_prefix,
                   intents=intents,
                   status=Status.online)

bot.EXTENSIONS = EXTENSIONS

# On ready event
bot.remove_command('help')

@bot.event
async def on_ready():
    header = f"{bot.user.name} is onready"
    desc = f"\n|{header:^28}|\n"
    help = f"|{f'Default Prefix: {Defaults.PREFIX}':^28}|\n"
    placeholder = len(desc)
    baseline = '+'+''.join(["-" for i in range(placeholder-4)])+'+'
    print("\n"+baseline+desc+help+baseline)

for ext in EXTENSIONS:
    bot.load_extension(ext)

async def call_command(signature, *args, **kwargs):
    cmd = bot.get_command(signature)
    that = bot.cogs[cmd.cog_name]
    await cmd.callback(that, *args, **kwargs)

bot.call_command = call_command

@bot.check
async def is_beta(ctx: Context):
    cond = ctx.guild is not None and ctx.guild.id in PRIVILEGED_GUILDS or not ctx.command.cog_name.lower() in BETA_MODULES
    if not cond:
        await ctx.reply(embed=Embed(title="Slow Down...!", description="This module is in beta-testing! Please join any of the privileged servers to test the module.", color=Colour.EXCEPTION))

    return cond

async def update_status():
    await bot.wait_until_ready()
    await bot.change_presence(status=Status.online, activity=Activity(type=ActivityType.listening, name=f'~help | {len(bot.guilds)} guilds'))

async def load_support():
    bot.hotline_channel = None
    await bot.wait_until_ready()
    bot.support_guild = bot.get_guild(SUPPORT_GUILD)
    bot.hotline_channel = bot.support_guild.get_channel(HOTLINE_CHANNEL)

bot.update_status = update_status

bot.loop.create_task(bot.update_status())
bot.loop.create_task(load_support())


load_dotenv()
TOKEN = getenv('TOKEN')
bot.run(TOKEN)
