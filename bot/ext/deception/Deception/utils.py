from types import FunctionType
from discord import Embed
from discord.abc import Messageable
from discord.member import Member
from discord.message import Message

from .ext import LAN_Game_Instance, Player, Rank, WAN_Game_Instance, all_ranks

from typing import Dict, Union

emojis = [':one:', ':two:', ':three:', ':four:',
          ':five:', ':six:', ':seven:', ':eight:', ':nine:']


printable_emojis = {':one:': '1️⃣', ':two:': '2️⃣', ':three:': '3️⃣',
                    ':four:': '4️⃣', ':five:': '5️⃣', ':six:': '6️⃣',
                    ':seven:': '7️⃣', ':eight:': '8️⃣', ':nine:': '9️⃣'}


def get(object: object, instance: Union[WAN_Game_Instance, LAN_Game_Instance] = None, name: str = '', id: str = '') -> Union[Player, Rank]:
    """
    Gets the class object of whichever type is given by basis of
    name and or id. ID is more valued than name.

    MAY be deprecated
    """
    if not name and not id:
        raise TypeError("get() requires either the name or id as an argument")

    LOOKUP_TABLE = {
        Rank: instance._allowed_ranks if instance else all_ranks,
        Player: instance.all_participants.values(),
        Member: [p.member for p in instance.all_participants.values()]
    }

    # get the iterable to search the object in using
    # a lookup table
    reference = LOOKUP_TABLE[object]

    if id:
        for r in reference:
            if r.id == id:
                return r
    if name:
        name = name.lower().strip()
        for r in reference:
            if r.name.lower() == name:
                return r
            elif r.display_name.lower() == name:
                return r


def get_info(target: object):
    """
    Information parser, this is used to get processed
    data in an accessible form without the need to 
    understand the architecture of the game
    """

    if isinstance(target, Player):
        desc = target.rank.description

    elif isinstance(target, Rank):
        desc = target.description

    get_info.fac = desc['faction']
    get_info.image = desc['image']
    get_info.guide = desc['gist']
    get_info.tips = desc['tips']
    get_info.guide_long = ['guide']
    get_info.skill_message = desc['skill_message']

    return get_info


async def add_appropriate_reactions(target: Message, message: str):
    for e in emojis:
        if e in message:
            await target.add_reaction(printable_emojis[e])


async def announce(game: Union[LAN_Game_Instance, WAN_Game_Instance], embed: Union[Embed, FunctionType]) -> Dict[Member, Message]:
    """
    Send a message or an embed to all the private channels of 
    a game instance

    To be deprecated
    """

    if isinstance(embed, Embed):
        content = embed
    elif isinstance(embed, FunctionType):
        # Pass in each and every player object to make an embed generator
        content = [embed(e[1]) for e in game.all_participants.items()]

    channels = list(game.info['channels'].values())
    players = list(game.info['channels'].keys())

    # prepare return value; Player: Message dict
    m = {}
    for i, channel in enumerate(channels):
        msg = await channel.send(embed=content if type(content) == Embed else content[i])
        await add_appropriate_reactions(msg, msg.embeds[0].description)
        m[get(Member, game, id=players[channels.index(channel)])] = msg
    return m


def get_emoji_choice(game, content: str) -> str:
    edits = [content.replace(i, '') for i in emojis]
    for i in edits:
        if i != content:
            return get(Player, game, name=i)


def get_options(contents: str, game: Union[LAN_Game_Instance, WAN_Game_Instance]) -> Dict[str, str]:
    """
    This is a method to be used by the skill panel interactions.

    Parses a random message and condenses it down to a useful dict by dissecting
    the message into options. Then converting the display_name choices into 
    player objects.
    """

    # contents look something like xyz\n\n:one: (name)\n:two: (name2)

    selection = contents.split('\n\n')[1:]

    # convert choices into player objects

    selectables = {printable_emojis[emojis[i]]: get_emoji_choice(
        game, k.strip()) for i, k in enumerate((''.join(selection)).split('\n'))}

    return selectables
