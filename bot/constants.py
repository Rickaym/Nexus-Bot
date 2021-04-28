from yaml import load, SafeLoader

CONFIG_PATH = 'config.yaml'

with open(CONFIG_PATH, 'r') as file:
    _CONFIGURATION = load(file, Loader=SafeLoader)

_DIRECTIONS = _CONFIGURATION['directory']


class Directory:
    PREFIXES_PTH = _DIRECTIONS['prefixes_db']  # Prefixes database


style = _CONFIGURATION['style']
dir = _CONFIGURATION['directory']
bot = _CONFIGURATION['bot']

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


class Defaults:
    PREFIX = bot['prefix']
    ADMINS = bot['admins']
    ADMIN_ROLES = bot['admin_roles']
