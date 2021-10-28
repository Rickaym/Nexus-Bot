import asyncio

from asyncio.events import AbstractEventLoop
import inspect
from typing import Any, Callable, Dict, List
from discord.member import Member
from discord.ext.commands.context import Context

SERVICES: Dict[str, "Pool"] = {}

class MatchStatus:
    IDLE = 0x1
    ONGOING = 0x2


class Bridge:
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


class MatchInstance:
    def __init__(self, pool, loop: AbstractEventLoop, player1: Member, ctx: Context, callback: Callable) -> None:
        self.pool = pool
        self.loop = loop
        self.status = MatchStatus.IDLE

        self.context = {
            "p1": {"member": player1,
                   "ctx": ctx,
                   "callback": callback},
            "p2": {"member": None,
                   "ctx": None,
                   "callback": None},
            }
        self.signals = {}
        self.handshook = None
        self._roughboard = {}

    def register_signal(self, name):
        if name not in self.signals.keys():
            self.signals[name] = []

    def on_emit(self, signal_name, callback):
        self.signals[signal_name].append(callback)

    async def emit(self, signal_name, *args, **kwargs):
        for cb in self.signals[signal_name]:
            if inspect.iscoroutinefunction(cb):
                self.loop.create_task(cb(*args, **kwargs))
            else:
                self.loop.create_task(self._invoke(cb, *args, **kwargs))

    async def _puppet_async(self): ...

    def _ignore_on_sp(coro=True):
        """
        Decorated function will be silently ignored on call under a singleplayer
        context.
        """
        def wrapper(func: Callable):
            def wrapped(this: "MatchInstance", *args, **kwargs):
                if this.context["p2"]["member"] is None:
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
            target = "p1"
            send_to = "p2"
        else:
            target = "p2"
            send_to = "p1"

        while True:
            m = await bot.wait_for("message", check=lambda m: m.author.id == self.context[target]["member"].id and m.channel.id == self.context[target]["ctx"].channel.id)

            await self.context[send_to]["ctx"].send(f"{m.author.name}#{m.author.discriminator}: {m.content}")

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
        if self.context["p2"]["member"] is None:
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
        with Bridge("__estab__", self._roughboard, []) as node:
            try:
                await asyncio.wait_for(self._establish_msg_relay(bot, node), time, loop=self.loop)
            except asyncio.exceptions.TimeoutError:
                pass

    async def _invoke(self, callback, *args, **kwargs):
        """
        Simple asynchronous wrapper for a synchronous function.
        """
        return callback(*args, **kwargs)

    def _engage(self):
        for p in self.context.keys():
            if self.context[p]["member"] is not None:
                self.loop.create_task(self._invoke(self.context[p]["callback"],
                                    self.context[p]["member"], self.context[p]["ctx"], self))

    def pair(self, player=None, ctx=None, callback=None):
        """
        Pairs a match instance.
        """
        if self.status != MatchStatus.ONGOING:
            self.status = MatchStatus.ONGOING
            self.context["p2"] = {"member": player,
                                  "ctx": ctx,
                                  "callback": callback}
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
        if self.context["p2"]["member"] is None:
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
        if self.context["p2"]["member"] is None:
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

    def _handshake(self):
        while True:
            if self.handshook is True:
                break
            if self.handshook is None:
                self.handshook = False
            elif self.handshook is False:
                self.handshook = True

    @_ignore_on_sp()
    async def wait_other(self):
        """
        Synchronizes playing parties.
        """
        await asyncio.wait_for(self.loop.run_in_executor(None, self._handshake), 60, loop=self.loop)
        self.handshook = None


class Pool:
    def __init__(self, service_name):
        self.nm = service_name
        self.puddle: List[MatchInstance] = []

    def lineup(self, player: Member, ctx: Context, loop: AbstractEventLoop, on_matchup: Callable) -> MatchInstance:
        match = self._reharse(player, ctx, loop, on_matchup)
        return match

    def _reharse(self, player, ctx, loop, callback):
        for match in self.puddle:
            if match.status != MatchStatus.ONGOING:
                match.pair(player, ctx, callback)
                return match
        else:
            new_match = MatchInstance(self, loop, player, ctx, callback)
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
