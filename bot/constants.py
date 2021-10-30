from yaml import load, SafeLoader

CONFIG_PATH = 'config.yaml'

with open(CONFIG_PATH, 'r', encoding="utf-8") as file:
    _CONFIGURATION = load(file, Loader=SafeLoader)

_DIRECTIONS = _CONFIGURATION['directory']


class Directory:
    PREFIXES_PTH = _DIRECTIONS['prefixes_db']  # Prefixes database


style = _CONFIGURATION['style']
dir = _CONFIGURATION['directory']
bot = _CONFIGURATION['bot']
help_decor = _CONFIGURATION["help_decorations"]

# NUMBER MAP
NUMBER_MAP = {'0': ':zero:', '1': ':one:', '2': ':two:', '3': ':three:',
              '4': ':four:', '5': ':five:', '6': ':six:',
              '7': ':seven:', '8': ':eight:', '9': ':nine:'}


class Colour:
    EXCEPTION = style['exception']
    LIGHT_BLUE = style['light_blue']
    SUN_YELLOW = style['sun_yellow']
    BRIGHT_GREEN = style['bright_green']
    BABY_PINK = style['baby_pink']
    COLORS = style['light_blue']
    EXCEPTION = style['exception']

SILENT_MODULES = help_decor["silent_modules"]
BETA_MODULES = help_decor["beta_modules"]
BADGED_MODULES = help_decor["badged_modules"]
PRIVILEGED_GUILDS = bot["privileged_guilds"]
SUPPORT_GUILD = bot["support_guild"]
SUPPORT_INVITE = bot["support_invite"]
HOTLINE_CHANNEL = bot["hotline_channel"]

class Defaults:
    PREFIX = bot['prefix']
    ADMINS = bot['admins']
    ADMIN_ROLES = bot['admin_roles']
