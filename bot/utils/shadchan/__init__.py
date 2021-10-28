import asyncio
import inspect

from asyncio.events import AbstractEventLoop
from collections import namedtuple
from uuid import uuid4
from random import choice
from typing import Any, Callable, Dict, List
from dataclasses import dataclass
from discord.embeds import Embed
from discord import ui
from discord.enums import ButtonStyle
from discord.interactions import Interaction
from discord.member import Member
from discord.ext.commands.context import Context
from bot.utils.hearsay import Hearsay

SERVICES: Dict[str, "Pool"] = {}

MatchStatus = namedtuple('int', ["IDLE", "ONGOING"])(0x10DE, 0x36)
MatchModes = namedtuple('int', ["singleplayer", "gvg", "lan", "unknown"])(0x1, 0x2, 0x3, 0x4)


class Bridge:
    """
    A temporary context object that creates a unique space inside a dictionary
    with an init value, then supplies it to the needed function
    """
    def __init__(self, otk, board, init) -> None:
        self.otk = otk
        self.init = init
        self.board = board

    def __enter__(self):
        if self.otk not in self.board.keys() or bool(self.init) is True and not bool(self.board[self.otk]):
            self.board[self.otk] = self.init
        return self.board[self.otk]

    def __exit__(self, exc_type, exc_value, traceback):
        try:
            self.board.pop(self.otk)
        except KeyError:
            pass


@dataclass
class Player:
    user: Member
    ctx: Context
    callback: Callable


@dataclass
class MatchOptions:
    mode: MatchModes
    self_pair: bool = False
    parallel: bool = False


class MatchmakerUI(ui.View):
    def __init__(self):
        super().__init__(timeout=180)
        self.mode = None

    @ui.button(label="SINGLEPLAYER", emoji="🏠", style=ButtonStyle.blurple)
    async def singleplayer(self, button, i: Interaction):
        self.mode = MatchModes.singleplayer
        self.stop()

    @ui.button(label="MULTIPLAYER", emoji="🏟️", style=ButtonStyle.green)
    async def multiplayer(self, button, i: Interaction):
        self.mode = MatchModes.gvg
        self.stop()

    @ui.button(emoji="❌", style=ButtonStyle.grey)
    async def cancel(self, button, i: Interaction):
        await i.response.send_message("Cancelled")
        self.stop()


class MatchInstance:
    def __init__(self, pool, loop: AbstractEventLoop, player1: Member, ctx: Context, callback: Callable, mode: MatchModes) -> None:
        self.pool = pool
        self.loop = loop
        self.status = MatchStatus.IDLE
        self.options = MatchOptions(mode)
        self.id = choice(str(uuid4()).split('-'))

        self.p1 = Player(player1, ctx, callback)
        self.p2 = None

        self.signals = {}
        self._roughboard = {}

    def includes(self, user: Member):
        """
        Check whether if a user is included in this matchup.
        """
        return user.id != self.p1.user.id and not self.options.mode == MatchModes.singleplayer and user.id != self.p1.user.id

    def _register_signal(self, name):
        if name not in self.signals.keys():
            self.signals[name] = []

    def on_emit(self, signal_name, callback: Callable=None):
        """
        Assign an incoming signal to a callback.
        """
        self._register_signal(signal_name)
        if callback is None:
            def wrapper(callback: Callable):
                self.signals[signal_name].append(callback)
                return callback
            return wrapper
        else:
            self.signals[signal_name].append(callback)

    def emit(self, signal_name, *args, **kwargs):
        """
        Emits a signal and create tasks for the callbacks.
        """
        try:
            self.signals[signal_name]
        except KeyError:
            raise KeyError("You can't emit a signal that hasn't been waited for.")
        for cb in self.signals[signal_name]:
            if inspect.iscoroutinefunction(cb):
                self.loop.create_task(cb(*args, **kwargs))
            else:
                self.loop.create_task(self._invoke(cb, *args, **kwargs))

    async def emit_wait_for(self, signal_name, *args, **kwargs):
        """
        Emits a signal and waits until the callbacks for both parties are received.
        Meaning it will wait for the other side of callbacks as well.
        """
        try:
            self.signals[signal_name]
        except KeyError:
            raise KeyError("You can't emit a signal that hasn't been waited for.")

        for cb in self.signals[signal_name]:
            if inspect.iscoroutinefunction(cb):
                await cb(*args, **kwargs)
            else:
                await self.loop.run_in_executor(None, cb, *args, **kwargs)
        await self.wait_other()

    async def _puppet_async(self): ...

    def _ignore_on_sp(coro=True):
        """
        Decorated function will be silently ignored on call under a singleplayer
        context.
        """
        def wrapper(func: Callable):
            def wrapped(this: "MatchInstance", *args, **kwargs):
                if this.options.mode == MatchModes.singleplayer:
                    if coro:
                        return this._puppet_async()
                    else:
                        return None
                else:
                    return func(this, *args, **kwargs)
            return wrapped
        return wrapper

    async def _establish_msg_relay(self, bot, node):
        """
        Connect a match session player-to-player for realtime chatting.
        """
        if len(node) == 0:
            node.append("p1")
            target = self.p1
            send_to = self.p2
        else:
            target = self.p2
            send_to = self.p1

        while True:
            m = await bot.wait_for("message", check=lambda m: m.author.id == target.user.id and m.channel.id == target.ctx.channel.id)

            await send_to.ctx.channel.send(f"{Hearsay.resolve_name(m.author)}: {m.content}")

    def _generalize(self, value, node):
        node.append(value)
        while True:
            if len(node) >= 2:
                return node[0]

    async def generalize(self, value):
        """
        Provided any amounts of value in parallel, chooses the fastest posting
        value. It can be used to generalize a game setting that needs to be decided
        between two player ends.
        """
        if self.options.mode == MatchModes.singleplayer:
            return value
        else:
            with Bridge("__generalize__", self._roughboard, []) as node:
                return await asyncio.wait_for(self.loop.run_in_executor(None, self._generalize, value, node), 60, loop=self.loop)

    @_ignore_on_sp()
    async def enable_chat(self, bot, time: int):
        """
        Establish an echo bridge betwen two players in a multiplayer
        game for a given amount of time.
        """
        if self.options.mode == MatchModes.gvg:
            with Bridge("__estab__", self._roughboard, []) as node:
                try:
                    await asyncio.wait_for(self._establish_msg_relay(bot, node), time, loop=self.loop)
                except asyncio.exceptions.TimeoutError:
                    pass

    async def _invoke(self, callback, *args, **kwargs):
        """
        Simply an asynchronous wrapper for tasks.
        ONLY USE THIS WHEN CREATING TASKS - NOTHING ELSE.
        IT IS CAPABLE OF BLOCKING.
        """
        return callback(*args, **kwargs)

    def _engage(self):
        if self.p1 is not None:
            self.loop.create_task(self._invoke(self.p1.callback,
                                self.p1.user, self.p1.ctx, self))
        if self.options.mode != MatchModes.singleplayer:
            self.loop.create_task(self._invoke(self.p2.callback,
                                self.p2.user, self.p2.ctx, self))

    def pair(self, player=None, ctx=None, callback=None):
        """
        Pairs a match instance.
        """
        if self.status != MatchStatus.ONGOING:
            self.status = MatchStatus.ONGOING
            self.p2 = Player(player, ctx, callback)
            self._engage()

    def _conclude(self, score: Any, by: Callable, node: list):
        node.append(score)
        while True:
            if len(node) == 2:
                res = by(score, node[int(not node.index(score))])
                return res

    async def conclude(self, score, by):
        """
        Conclude a judgement between two players with a comparing function.
        """
        if self.options.mode == MatchModes.singleplayer:
            cond = True
        else:
            with Bridge("__con_answer__", self._roughboard, []) as node:
                cond = await asyncio.wait_for(self.loop.run_in_executor(None, self._conclude, score, by, node), 60, loop=self.loop)
        return cond

    async def conclude_with_answer(self, score, by):
        """
        Conclude a judgement between two players with a comparing function and returns the other
        player's submitted value.
        """
        if self.options.mode == MatchModes.singleplayer:
            cond = True
            other = score
        else:
            with Bridge("__con_with_answer__", self._roughboard, []) as node:
                cond = await asyncio.wait_for(self.loop.run_in_executor(None, self._conclude, score, by, node), 60, loop=self.loop)
                other = None
                if cond:
                    other = node[int(not node.index(score))]
        return cond, other

    def end(self):
        """
        Ends the match.
        """
        self.pool._conclude(self)

    def _catchup(self, node):
        node.append(None)
        while True:
            if len(node) >= 2:
                break

    @_ignore_on_sp()
    async def wait_other(self):
        """
        Synchronizes playing parties.
        """
        with Bridge("wait_other", self._roughboard, []) as node:
            await asyncio.wait_for(self.loop.run_in_executor(None, self._catchup, node), 60, loop=self.loop)


class Pool:
    def __init__(self, service_name):
        self.nm = service_name
        self.puddle: List[MatchInstance] = []

    def _get_sp_match_count(self):
        return len([m for m in self.puddle if m.options.mode == MatchModes.singleplayer and m.status == MatchStatus.ONGOING])

    async def _get_matchmode(self, ctx: Context):
        view = MatchmakerUI()

        embed = Embed(color=0x1cc7d4)
        embed.set_author(name="SHADCHAN ➖ WELCOME TO THE MATCHMAKER")
        embed.add_field(name="Gamemode",
                        value=f"🧖 **[SINGLEPLAYER](https://google.com/ \"CAMPAIGN MODE\")**\n<:onl:903016826450112542> {self._get_sp_match_count()} Ongoing"
                               "\n➖ Start Campaign by pressing single player"
                               "\n<:channel:845286257344643103> This channel is open to games.")
        embed.add_field(name="\u200b",
                        value=f"⚔️ **[MULTIPLAYER](https://google.com/ \"PVP MODE\")**\n<:onl:903016826450112542> {self._get_sp_match_count()} Ongoing"
                               "\n➖ 1v1 Global Server Scope"
                               "\n⚔️ You will be matched against a random player.")
        m = await ctx.send(embed=embed, view=view)
        await view.wait()
        for i in view.children:
            i.disabled = True
        if view.mode is not None:
            embed.set_author(name=f"SHADCHAN ➖ STARTING {'SINGLEPLAYER' if view.mode == MatchModes.singleplayer else 'MULTIPLAYER'}")
            await m.edit(embed=embed, view=view, delete_after=2)
        return view.mode

    async def lineup(self, player: Member, ctx: Context, loop: AbstractEventLoop, on_matchup: Callable, mode: MatchModes) -> MatchInstance:
        if mode == MatchModes.unknown:
            mode = await self._get_matchmode(ctx)
        if mode is None:
            return
        match = self._reharse(player, ctx, loop, on_matchup, mode)
        return match

    def _get_match(self, player):
        for match in self.puddle:
            if match.status != MatchStatus.ONGOING and match.p1.user.id != player.id:
                return match

    def _reharse(self, player, ctx, loop, callback, mode):
        if mode == MatchModes.singleplayer:
            new_match = MatchInstance(self, loop, player, ctx, callback, mode)
            self.puddle.append(new_match)
            new_match.pair()
            return new_match
        elif mode == MatchModes.gvg:
            pending_match = self._get_match(player)
            if pending_match is not None:
                pending_match.pair(player, ctx, callback)
                return pending_match
            else:
                new_match = MatchInstance(self, loop, player, ctx, callback, mode)
                self.puddle.append(new_match)
                return new_match

    def _conclude(self, match: MatchInstance):
        try:
            self.puddle.remove(match)
        except ValueError:
            pass

    @staticmethod
    def get(nm: str) -> "Pool":
        if not nm in SERVICES.keys():
            SERVICES[nm] = Pool(nm)
        return SERVICES[nm]


class MimeData:
    def __init__(self, val) -> None:
        self.value = val

    def __repr__(self) -> str:
        return str(self.value)

    def __eq__(self, o):
        return self.value == o

    def __ne__(self, o: object) -> bool:
        return not self.__eq__(o)
