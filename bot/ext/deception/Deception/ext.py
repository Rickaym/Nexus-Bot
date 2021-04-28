import asyncio
import random
import functools

from datetime import datetime as date
from types import FunctionType
from discord.ext.commands import Context
from discord.channel import CategoryChannel, TextChannel
from discord import Member, Role

from dataclasses import dataclass, field
from typing import Any, Optional, Tuple, Dict, List

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
    def __init__(self, function: FunctionType):
        """
        Actuator or action decorator that is used to mark skill functions
        Utilized to mark actions down whenever the function is called
        """
        self.func = function

    def __call__(self, *args, **kwds):
        actor: Player = args[0]
        victim: Player = args[1]

        # Dispatching actions
        actor.game._latest_actions.append(
            Action(actor.rank.skill.__name__, actor, victim))

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

    id          : First 3 initials of every word in the name separated by underscores
    name        : Name of rank
    moral       : Morality, defines if the role is evil or good. 0 = Evil, 1 = Good
    skill       : A function argument that is executed if the player with the role acts onto someone
    defense     : Defense level of the rank
    attack      : Attack potency of the rank (0 means no attack skills)
    description : Descriptive detail about the rank
    """

    id: str
    name: str
    moral: bool
    defense: int
    skill: FunctionType
    attack: int
    description: str


class Player:
    def __init__(self, member: Member, rank: Rank, game: object, happening: list = ['']):
        """
        Base class for players.

        member    : A discord.Member representation of the player
        rank      : Rank of the playerF
        game      : Game instance where the player is partaking in

        happening : Optional list of activies or happen-ables. 
        alive     : In the game or not, 0 = Dead, 1 = Alive
        """
        self.member = member
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

    name   : Name of action
    actor  : Perpetrator
    victim : Victim
    """
    name: str
    actor: Player
    victim: Player


class Local_Game_Instance:
    def __init__(self, ctx: Context, members: Tuple[Member], ranks: Tuple[Rank], player_role: Role, id: Optional[int] = 0x666):
        """
        Local Game Instance ----------------------------------------------

        This is a the local game variant of the two game instances that
        a member can make to play deception. It needs to be instantiated
        once the decisions of what roles this game will has the participants
        are made.

        Params:
            ctx         : Discord context it is invoked under
            members     : all participants
            ranks       : allowed ranks
            player_role : A role all players of this current game has for permission purposes
            id          : game id

        """
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

        self.info: dict = {
            "ranks": self._assign_ranks(), "channels": None}

        self.start_time: date = date.utcnow()
        self.end_time: date = date.utcnow()
        self.duration: int = round(
            (self.start_time - self.end_time).seconds / 60)

        self.day: int = 0
        self.night: int = 0

    @property
    def is_ongoing(self) -> bool:
        return self._is_ongoing

    @property
    def good_members(self) -> Dict[Member, Player]:
        return {player[0]: player[1] for player in self.all_participants if player[1].rank.moral == "good"}

    @property
    def bad_members(self) -> Dict[Member, Player]:
        return {player[0]: player[1] for player in self.all_participants if player[1].rank.moral == "bad"}

    @property
    def members(self) -> List[Member]:
        return self._members

    @property
    def id(self) -> int:
        return self._game_id

    def _assign_ranks(self) -> Dict[Member, str]:
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

    def assign_channels(self, positions: dict):
        """Saves an info dictionary as an instance variable"""
        self.info["channels"] = positions

    async def open_inquiry(self, time: float):
        """Allows participants to send messages into the inquiry channel for a limited
        amount of time"""
        await self.inquiry_channel.set_permissions(self._player_role, read_messages=True, send_messages=True)
        await asyncio.sleep(time)
        await self.close_inquiry()

    async def close_inquiry(self):
        """Restricts participants from sending messages into the inquiry channel"""
        await self.inquiry_channel.set_permissions(self._player_role, read_messages=True, send_messages=True)

    def stop(self):
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
    defense=...,
    attack=...,
    description=...)

serial_killer = Rank(
    id="ser_kil",
    name="SerialKiller",
    moral=False,
    skill=potency_3_attack,
    defense=3,
    attack=3,
    description="You are a psychopathic killer")

officer = Rank(
    id="off",
    name="Officer",
    moral=True,
    skill=_sheriff,
    defense=0,
    attack=0,
    description="You are an active town sheriff that everyone respects.")


default_ranks = [serial_killer, officer]


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
