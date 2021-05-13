import asyncio
import random
import functools

from datetime import datetime as date
from types import FunctionType
from discord.ext import commands
from discord.ext.commands import Context
from discord.channel import CategoryChannel, TextChannel
from discord import Member, Role

from dataclasses import dataclass
from typing import Any, Optional, Text, Tuple, Dict, List

from discord import Member

"""
+---------------------------------------+   
|     Deception... Lie?                 |
|  Who are you..                        |
|                                       |
|          Cannot handle the truth.     |
|    Could not handle the truth.        |
|        Should not handle the truth.   |
+---------------------------------------+

Deception™️ package extensions. Contains all the 
dataclasses statically typed

Game Info ===============================

Defense Levels
-----------------
There are three levels of defenses.

1. Standard Defense - Immune to standard attacks
2. Strong Defense - Immune to standard and strong attacks
3. Unbreakable Defense - Immune to all attacks


Attack Levels
----------------
There are three potencies of inflictive attacks.

1. Standard Attack - Futile to standard defense
2. Strong Attack - Futile to standard and strong defense
3. Skilled Attack - Futile to standard and strong defense


Happen-ables
---------------
This is a list of things that can be happening to a player that is
unoticed by the player but influences any ensuing action.

framed: Shows up as a bad moral for a sheriff


Random-ideas
---------------
[0] serial killer gets kill ability at random night 2 - 3
[1] random psychotic dreams
"""


class actuator:
    """
    Actuator (skill action definitior) that is used to mark skill functions
    Utilized to mark actions down whenever the function is called to the 
    game instance it was called upon to be later traced
    """

    def __init__(self, function: FunctionType):
        self.func = function

    def __call__(self, *args, **kwds):
        actor: Player = args[0]
        victim: Player = args[1]

        # Dispatching actions
        print("ACTUATOR REPORT:", actor, victim)
        actor.game._latest_actions.append(
            Action(actor.rank.skill.__name__, actor, victim))
        actor.game.alive_count -= 1
        ret = self.func(actor, victim, **kwds)
        return ret

    def __get__(self, instance, owner):
        # Self refers to the actuator decorator
        # while instance refers to the actual object
        # on which the atribute lookup is happening. (owner is owner of instance)
        return functools.partial(self.__call__, instance)


@dataclass(repr=True, order=True, frozen=True)
class Rank:
    """
    Base class for playable ranks. 

    Attributes
    ---
    id          : `int`
        First 3 initials of every word in the name separated by underscores
    name        : `str`
        Name of rank
    moral       : `bool`
        Morality, defines if the role is evil or good. 0 = Evil, 1 = Good
    skill       : Union[`function`, `passive`]
        Raw function that represents a rank skill
    defense     : `int`
        Defense level of the rank
    attack      : `int`
        Attack potency of the rank (0 means no attack skills)
    description : `dict`
        Human readable details about the rank
    """

    id: str
    name: str
    moral: bool
    skill: FunctionType
    description: Dict[str, str]
    defense: int = 0
    attack: int = 0
    win_with: Optional[Tuple] = None


class Player:
    """
    Base class for players.

    Attributes
    ---
    member    : `discord.Member`
        A discord.Member representation of the player
    id        : `int`
        id of the `Member` attribute of this player
    name      : `str`
        Name of Member, this is acquired from `Member` attribute
    display_name: `str`
        Display name or nickname of the member, this is acquired from the `Member` attribute
    rank      : `Deception.ext.Rank`
        Rank that is assigned to the player
    game      : Union[`Deception.ext.LAN_Game_Instance`, `Deception.ext.WAN_Game_Instance`]
        Game instance where the player is partaking in
    happening : Optional[List[`Action`]]
        Actions happening to the player
    alive     : int
        In the game or not, 0 = Dead, 1 = Alive
    skill     : `partial`
        Actuator partial function that is used to ensue one's skill
        onto an opposing member. Refer to `Player.rank.skill` for
        a fully loaded function.
    """

    def __init__(self, member: Member, rank: Rank, game: object, happening: list = ['']):
        self.member = member
        self.id = member.id
        self.name = member.name
        self.display_name = member.display_name

        self.rank = rank
        self._skill = rank.skill
        self.game = game

        self.happening = happening
        self.alive: bool = True

    @actuator
    def skill(self, *args: Any):
        """
        Making a function bound to the class to allow
        attribute lookup with __get__ for the decorator
        """
        self._skill(*args)

    def __repr__(self) -> str:
        return f"Player(name={self.member.name}, id={self.member.id})"


@dataclass(repr=True, frozen=True, order=True)
class Action:
    """
    Base class for all action, marks down what happens 
    during the night to evaluate what happens in the morning.

    name   : `str`
        Name of action
    actor  : `Player`
        Perpetrator
    victim : `Player`
        Victim
    """
    name: str
    actor: Player
    victim: Player


class GameHasEnded(commands.CommandError):
    ...


class LAN_Game_Instance:
    """
    # Local Game Instance

    This is a the local game variant of the two game instances that
    a member can make to play deception. It needs to be instantiated
    once the decisions of what roles this game will has the participants
    are made.

    Attribute 
    ---
    id              : Optional[`int`]
        ID of the game instance for logging purposes
    ctx             : `Context`
        The discord command context at which it is invoked under
    is_ongoing      : `bool`
        Indication of if the game is still ongoing or not
    category        : `CategoryChannel`
        The category that the game takes place in
    inquiry_channel : `TextChannel`
        The main inquiry text channel that people can speak
    all_participants: Dict[`int`, `Player`]
        A dictionary that is kept for reference purposes of a
        player's member id and their respective player instances
        under the game instance
    info            : Dict[`str`, Optional[Dict[`Member`, `str`]]]
        Miscellaneous instance information;
            [ranks] - member id : rank
            [channels] - member id : textchannel 
    day             : `int`
        The number of days that had passed until now       
    night           : `int`
        The number of nights that had passed until now       
    alive_count     : `int`
        The number of players alive now       
    """

    def __init__(self, ctx: Context, members: Tuple[Member], ranks: Tuple[Rank], player_role: Role, id: Optional[int] = 0x666):
        self._game_id: int = id
        self._ctx: Context = ctx
        self._is_ongoing: bool = True
        self._player_role: Role = player_role

        # discord.Member type list members
        self._members: List[Member] = members
        self._allowed_ranks: List[Rank] = ranks

        self.category: Optional[CategoryChannel] = None
        self.inquiry_channel: Optional[TextChannel] = None

        self._latest_actions: List[Action] = []

        # reference note for type Players
        self.all_participants: Dict[int, Player] = {}

        self.info: Dict[str, Optional[Dict[Member, str]]] = {
            "ranks": self._assign_ranks(), "channels": None}

        self._start_time: date = date.utcnow()
        self._end_time: date = date.utcnow()
        self.duration: int = round(
            (self._start_time - self._end_time).seconds / 60)

        self.day: int = 0
        self.night: int = 0
        self.alive_count: int = len(members)

    @property
    def is_ongoing(self) -> bool:
        return self._is_ongoing

    @property
    def good_members(self) -> Dict[int, Player]:
        return {player[0]: player[1] for player in self.all_participants if player[1].rank.moral == "good"}

    @property
    def bad_members(self) -> Dict[int, Player]:
        return {player[0]: player[1] for player in self.all_participants if player[1].rank.moral == "bad"}

    @property
    def members(self) -> List[Member]:
        return self._members

    @property
    def id(self) -> int:
        return self._game_id

    def _assign_ranks(self) -> Dict[int, Player]:
        positions = {}

        cpy_ranks = self._allowed_ranks.copy()
        for member in self._members:
            rank = random.choice(cpy_ranks)

            # This is where we turn discord.Member objects into
            # Player objects that we can do cool stuff with
            self.all_participants[member.id] = Player(member, rank, self)
            positions[member.id] = rank
            cpy_ranks.remove(rank)

        return positions

    def get_player(self, member: Member) -> Player:
        return self.all_participants[member.id]

    def assign_channels(self, positions: Dict[int, TextChannel]):
        """
        Saves an info dictionary as an instance variable"
        """
        self.info["channels"] = positions

    async def open_inquiry(self, time: float):
        """
        Allows participants to send messages into the inquiry channel for a limited
        amount of time. This is called every morning so actions are discussed here.
        """
        for action in self._latest_actions:
            await self.inquiry_channel.trigger_typing()
            if action.actor.rank.attack:  # must be a murder
                await self.inquiry_channel.send(action.actor.rank.skill.report % (action.victim.member.display_name, action.actor.rank.name))
                self._latest_actions.remove(action)
                await asyncio.sleep(5)

        await self._stop()
        await self.inquiry_channel.set_permissions(self._player_role, read_messages=True, send_messages=True)
        await asyncio.sleep(time)
        await self.close_inquiry()

    async def close_inquiry(self):
        """
        Restricts participants from sending messages into the inquiry channel
        """
        await self.inquiry_channel.set_permissions(self._player_role, read_messages=True, send_messages=True)

    async def delete_trace(self):
        """
        Traces back all the discord objects created and eventually
        deleting them.
        """
        for channel in self.category.channels:
            await channel.delete()
            await asyncio.sleep(0.3)
        await self.category.delete()
        await self._player_role.delete()

    async def _stop(self, purge: bool = True):
        """
        Should be called when the game ends. Optional argument purge can be 
        given false to avoid deleting traces. (for some reason)
        """
        ended = False
        if self.alive_count == 0:  # when two opposing players with attack abilities clash
            await self.inquiry_channel.send("The game has ended in a tie!")
            ended = True
        elif self.alive_count == 1:
            last_man_standing = [
                p for p in self.all_participants.values() if p.alive][0]

            # if the W local shares the win
            if last_man_standing.rank.win_with:
                winners = ', '.join([m.member.display_name for m in self.all_participants.values(
                ) if m.rank in last_man_standing.rank.win_with])
            else:
                winners = last_man_standing.member.display_name
            await self.inquiry_channel.send(f"The {last_man_standing.rank.name} has won.\nPlayers: {winners}")
            ended = True
        elif self.day >= 8:
            await self.inquiry_channel.send("The game has ended in a tie!")
            ended = True
        if ended:
            await asyncio.sleep(60)
            if purge:
                await self.delete_trace()
            self.save_player_data()
            self._is_ongoing = False
            raise GameHasEnded(f'Game {self.id} has ended.')

    def save_player_data(self):
        ...


class WAN_Game_Instance:
    ...

# ------------------------------------------
#   Skill functions below
# ------------------------------------------

# To finish


def potency_1_attack(other: Player): ...


def potency_2_attack(other: Player): ...


def _investigator(other: Player): ...


def passive(other: Player): ...


def potency_3_attack(other: Player):
    """
    Potency 3 attack. Can inflict enough damage to kill any players with less then 
    a defense value of 2. 

    Can be however prevented by defense 3.
    """
    potency_3_attack.report = "%s's skull got brutally opened by a %s last night."

    if other.rank.defense >= 3:
        potency_3_attack.msg = f"You couldn't kill {other.member.display_name}, target has high defense."
        return

    potency_3_attack.msg = f"You killed {other.member.display_name}."
    other.alive = False


def _sheriff(other: Player):
    """
    Sherrif investigation. Can determine if a player has a good moral or a 
    bad moral. This can be hindered if the player is framed.
    """
    if not other.rank.moral:
        _sheriff.msg = f"Your target {other.member.display_name} is suspicious."
        return

    _sheriff.msg = f"Your target {other.member.display_name} seems innocent."


# ------------------------------------------
#   Pre-made ranks below
# ------------------------------------------

base_template = Rank(
    id=...,
    name=...,
    moral=...,
    skill=...,
    description={"faction": ...,
                 "image": ...,
                 "gist": ...,
                 "guide": ...,
                 "skill_message": ...,
                 "tips": '''...'''
                 })

assassin = Rank(
    id="ass",
    name="Assassin",
    moral=False,
    skill=potency_3_attack,
    defense=3,
    attack=3,
    description={"faction": "The Brotherhood",
                 "image": "https://media.discordapp.net/attachments/806122193301274634/837356743159447552/assassin_icon.png",
                 "gist": "You are a notorious assassin gone rogue.",
                 "guide": "We lurk in the shadows for the rigtious brothers bring forth the light.",
                 "skill_message": "Hi... Whom would you like to assassinate tonight %s.",
                 "tips": '''
+ Assassinate the prime police or thug roles to gain power" 
+ Constantly under the shadow from investigation

- No defense, inability to assassinate prime roles will put you at stake
- Assassination is shown as a suicide.''',
                 })

officer = Rank(
    id="off",
    name="Officer",
    moral=True,
    skill=_sheriff,
    description={"faction": "police",
                 "image": "https://i.dlpng.com/static/png/7151215_preview.png",
                 "gist": "You are an active town sheriff that everyone respects.",
                 "guide": "Civilized and respected sheriff of the town.",
                 "skill_message": "Good Evening officer! Whom do you have in mind to interrogate tonight %s?",
                 "tips": '''
+ Pick your investigation properly to uncover prime roles"
+ Ability to find out whether if the target is suspicious or not"

- Weak and defenseless, weak to shadow roles like assasins who does not show up sus" 
- Vulnerable when working along without assistance'''
                 })

default_ranks = [assassin, officer]

all_ranks = default_ranks + []

FACTION_COLORS = {
    "evil": 0xff002f,
    "The Brotherhood": 0xcd5c1c,
    "police": 0x2a3180
}

if __name__ == '__main__':
    """ Testing 
    from dummy import Member as dummyMember

    p1, p2 = dummyMember('player1', random.randint(0, 10000)), dummyMember(
        'player2', random.randint(0, 10000))
    game = Local_Game_Instance(
        "abc", [p1, p2], default_ranks, 'abc')

    print("ABSDASA'")
    player1 = game.get_player(p1)
    player2 = game.get_player(p2)
    print("ABSDASA'")
    player1.skill(player2)
    print(player1.game._latest_actions)"""
