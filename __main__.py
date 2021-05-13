from os import getenv
from dotenv import load_dotenv
from discord import Intents, Status, Game
from discord.ext import commands

from bot.constants import Defaults
from bot.utils.extensions import EXTENSIONS
from bot.utils.prefixes import get_prefix

intents = Intents.default()
intents.reactions = True
intents.members = False # WILL BREAK THINGS

# Bot constructor
bot = commands.Bot(command_prefix=get_prefix,
                   intents=intents,
                   status=Status.offline, activity=Game("Loading.."))

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


load_dotenv()
TOKEN = getenv('TOKEN')
bot.run(TOKEN)
