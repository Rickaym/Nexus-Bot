from anyio import create_task_group
from asyncio import wait_for
from asyncio.events import AbstractEventLoop
from asyncio.exceptions import TimeoutError
from inspect import iscoroutinefunction
from collections import namedtuple
from uuid import uuid4
from decorator import decorator
from random import choice
from typing import Any, Callable, Dict, List, Union
from dataclasses import dataclass, field
from discord.ext import commands
from discord.embeds import Embed
from discord.enums import ButtonStyle
from discord.interactions import Interaction
from discord.member import Member
from discord.ext.commands.context import Context
from time import time

from bot.utils.ui import BetterView, button
from bot.utils.hearsay import Hearsay

SERVICES: Dict[str, "Pool"] = {}

MatchStatus = namedtuple('int', ["IDLE", "ONGOING"])(0x10DE, 0x36)
MatchModes = namedtuple('int', ["singleplayer", "gvg", "lan", "unknown"])(0x1, 0x2, 0x3, 0x4)

AnyInt = Union[int, float, bytes]

class Bridge:
    """
    A temporary context object that creates a unique space inside a dictionary
    with an init value, then supplies it to the needed function
    """
    def __init__(self, otk: str, board: dict, init: Any) -> None:
        self.otk = otk
        self.init = init
        self.board = board

    def __enter__(self):
        if (self.otk not in self.board.keys() or bool(self.init) == True
            and bool(self.board[self.otk]) is False):
            self.board[self.otk] = self.init
        return self.board[self.otk]

    def __exit__(self, *args, **kwargs):
        try:
            self.board.pop(self.otk)
        except KeyError:
            pass


@dataclass
class Player:
    """
    A player representation inside the match instance.
    """
    user: Member
    ctx: Context
    callback: Callable


@dataclass
class MatchOptions:
    """
    Possible match options for a match instance.
    """
    mode: int
    parallel: bool = False
    channel_host: bool = True
    disabled_modes: List[int] = field(default_factory=lambda: [MatchModes.unknown])


class MatchmakerUI(BetterView):
    """
    Matches started on MatchModes.unknown are resolved on lineup,
    this ui provides a view to choose from, match options' disallowed
    modes affect this.
    """
    styles = {"singleplayer": ButtonStyle.blurple,
              "gvg": ButtonStyle.green,
              "lan": ButtonStyle.red}

    emojis = {"singleplayer": "🏠",
              "gvg": "🏟️",
              "lan": "<:channel:845286257344643103>"}

    def __init__(self, ctx: Context, options: MatchOptions):
        super().__init__(ctx)
        self.mode = None
        self.ctx = ctx
        for i, pk in enumerate(MatchModes._asdict().items()):
            key, val = pk
            if val != MatchModes.unknown:
                disabled = False
                if val in options.disabled_modes:
                    disabled = True
                self.add_item(ui.Button(label=key.upper(), style=self.styles[key], emoji=self.emojis[key], disabled=disabled, custom_id=f"{key}:{val}"))
        self.add_item(ui.Button(label="\u200b", style=ButtonStyle.gray, emoji='❌', custom_id="cancel"))

    async def interaction_check(self, interaction: Interaction) -> bool:
        if interaction.user.id != self.ctx.author.id or interaction.channel_id != self.ctx.channel.id:
            return False
        if interaction.data["custom_id"] != "cancel":
            self.mode = int(interaction.data["custom_id"].split(':')[-1])
            if self.mode != MatchModes.singleplayer:
                for item in self.children:
                    if item.custom_id == interaction.data["custom_id"]:
                        item.emoji = "<a:loading:835922241191280680>"
        await super().interaction_check(interaction, edit_later=True)
        return True


class MatchReadyUpUI(BetterView):
    """
    This ui provides a way to ready up on matchup before the
    game finally begins.
    """
    def __init__(self, ctx, loop):
        super().__init__(ctx, loop, 60)
        self.done = False
        self.timeouted = False

    @button(label="Ready", emoji="<a:done:903006503538143323>", style=ButtonStyle.blurple)
    async def ready(self, b, i):
        self.done = True

    async def on_timeout(self) -> None:
        self.timeouted = True
        self.stop()


class MatchInstance:
    def __init__(self, pool, loop: AbstractEventLoop, player1: Member, ctx: Context,
        callback: Callable, options: MatchOptions) -> None:
        self.pool = pool
        self.loop = loop
        self.status = MatchStatus.IDLE
        self.options = options
        self.id = choice(str(uuid4()).split('-'))

        self.p1 = Player(player1, ctx, callback)
        self.p2 = None

        self.signals: dict[str, list[Callable]] = {}
        self._roughboard = {}

    def includes(self, user: Member):
        """
        Check whether if a user is included in this matchup.
        """
        return user.id != self.p1.user.id and not self.options.mode == MatchModes.singleplayer and user.id != self.p1.user.id

    def _register_signal(self, name: str):
        if name not in self.signals.keys():
            self.signals[name] = []

    def on_emit(self, signal_name: str, callback: Callable=None):
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

    def emit(self, signal_name: str, *args, **kwargs):
        """
        Emits a signal and create tasks for the callbacks.
        """
        try:
            self.signals[signal_name]
        except KeyError:
            raise KeyError("You can't emit a signal that hasn't been waited for.")
        for cb in self.signals[signal_name]:
            if iscoroutinefunction(cb):
                self.loop.create_task(cb(*args, **kwargs))
            else:
                self.loop.create_task(self._invoke(cb, *args, **kwargs))

    async def emit_wait_for(self, signal_name: str, *args, **kwargs):
        """
        Emits a signal and waits until the callbacks for both parties are executed.
        Meaning it will wait for the other side of callbacks as well.

        This is not synonymous with wait_for.
        """
        try:
            self.signals[signal_name]
        except KeyError:
            raise KeyError("You can't emit a signal that hasn't been waited for.")
        await self.wait_other()
        for cb in self.signals[signal_name]:
            if iscoroutinefunction(cb):
                await cb(*args, **kwargs)
            else:
                await self.loop.run_in_executor(None, cb, *args, **kwargs)
        await self.wait_other()

    def _to_timeout(self, start: float, timeout: AnyInt):
        """
        Raises a timeout error if a given deadline is exceeded.
        For sync functions ran inside executors.
        """
        if time()-start >= timeout:
            raise TimeoutError

    def _suspend_until(self, node: list, timeout: AnyInt):
        s = time()
        while True:
            if len(node) == 1:
                return
            self._to_timeout(s, timeout)

    async def wait_for(self, signal_name: str, timeout: AnyInt):
        """
        Waits for a certain signal to be dispatched
        """
        endpoint = []
        @self.on_emit(signal_name)
        def dispatch(*args):
            endpoint.append(True)

        try:
            await self.loop.run_in_executor(None, self._suspend_until, endpoint, timeout)
        except TimeoutError as e:
            self.signals[signal_name].remove(dispatch)
            raise e
        else:
            self.signals[signal_name].remove(dispatch)

    async def _puppet_async(self): ...

    @decorator
    def _ignore_on_sp(func, *args, **kwargs):
        """
        Decorated function will be silently ignored on call under a singleplayer
        context.
        """
        this = args[0]
        if this.options.mode == MatchModes.singleplayer:
            if iscoroutinefunction(func):
                return this._puppet_async()
            else:
                return None
        else:
            return func(*args, **kwargs)

    async def _establish_msg_relay(self, bot: commands.Bot, node):
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

            await send_to.ctx.channel.send(f"{await Hearsay.resolve_name(m.author)}: {m.content}")

    def _generalize(self, value: Any, node: list, timeout: AnyInt):
        node.append(value)
        s = time()
        while True:
            if len(node) >= 2:
                return node[0]
            self._to_timeout(s, timeout)

    async def generalize(self, value: Any):
        """
        Provided any amounts of value in parallel, chooses the fastest posting
        value. It can be used to generalize a game setting that needs to be decided
        between two player ends.
        """
        if self.options.mode == MatchModes.singleplayer:
            return value
        else:
            with Bridge("__generalize__", self._roughboard, []) as node:
                return await self.loop.run_in_executor(None, self._generalize, value, node, 60)

    @_ignore_on_sp()
    async def enable_chat(self, bot, time: int):
        """
        Establish an echo bridge betwen two players in a multiplayer
        game for a given amount of time.
        """
        if self.options.mode == MatchModes.gvg:
            with Bridge("__estab__", self._roughboard, []) as node:
                try:
                    await wait_for(self._establish_msg_relay(bot, node), time, loop=self.loop)
                except TimeoutError:
                    pass

    async def _invoke(self, callback: Callable, *args, **kwargs):
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

    def pair(self, player: Member=None, ctx: Context=None, callback: Callable=None):
        """
        Pairs a match instance. Does necessary readyups beforehand.
        """
        if self.status != MatchStatus.ONGOING:
            self.status = MatchStatus.ONGOING
            self.p2 = Player(player, ctx, callback)
            self.loop.create_task(self._start_onready())

    async def _start_onready(self):
        conditions = []
        async def wait_dispatch(ctx, player):
            view = MatchReadyUpUI(ctx, self.loop)
            await ctx.send(embed=Embed(description="Match found, please ready up"), view=view)
            await view.wait()
            if view.timeouted:
                return conditions.append([player, False])
            return conditions.append([player, view.done])

        async with create_task_group() as tg:
            tg.start_soon(wait_dispatch, self.p1.ctx, self.p1.user)
            tg.start_soon(wait_dispatch, self.p2.ctx, self.p2.user)

        for p, done in conditions:
            if done is False:
                if p.id == self.p1.user.id:
                    self.end()
                    await self.p1.ctx.send("You didn't ready up in time.")
                else:
                    self.p2 = None
                    await self.p2.ctx.send("You didn't ready up in time.")
                break
        else:
            self._engage()

    def _conclude(self, value: Any, by: Callable, node: list, timeout: AnyInt):
        node.append(value)
        s = time()
        while True:
            if len(node) == 2:
                res = by(value, node[int(not node.index(value))])
                return res
            self._to_timeout(s, timeout)

    async def conclude(self, value: Any, by: Callable):
        """
        Conclude a judgement between two players with a comparing function.
        """
        if self.options.mode == MatchModes.singleplayer:
            cond = True
        else:
            with Bridge("__con_answer__", self._roughboard, []) as node:
                cond = await self.loop.run_in_executor(None, self._conclude, value, by, node, 60)
        return cond

    async def conclude_with_answer(self, value: Any, by: Callable):
        """
        Conclude a judgement between two players with a comparing function and returns the other
        player's submitted value.
        """
        if self.options.mode == MatchModes.singleplayer:
            cond = True
            other = value
        else:
            with Bridge("__con_with_answer__", self._roughboard, []) as node:
                cond = await self.loop.run_in_executor(None, self._conclude, value, by, node, 60)
                other = None
                if cond:
                    other = node[int(not node.index(value))]
        return cond, other

    def end(self):
        """
        Ends the match.
        """
        self.pool._conclude(self)

    def _catchup(self, node: list, timeout: AnyInt):
        if timeout is not None:
            s = time()
        node.append(None)
        while True:
            if len(node) >= 2:
                return
            if timeout is not None:
                self._to_timeout(s, timeout)

    @_ignore_on_sp()
    async def wait_other(self, timeout: AnyInt=None):
        """
        Synchronizes playing parties.
        """
        try:
            self._roughboard["otp"]
        except KeyError:
            otp = str(uuid4())
            self._roughboard["otp"] = otp
        else:
            otp = self._roughboard["otp"]
            self._roughboard.pop("otp")

        with Bridge(otp, self._roughboard, []) as node:
            await self.loop.run_in_executor(None, self._catchup, node, timeout)


class Pool:
    def __init__(self, service_name: str):
        self.nm = service_name
        self.puddle: List[MatchInstance] = []

    def _get_sp_match_count(self):
        return len([m for m in self.puddle if m.options.mode == MatchModes.singleplayer and m.status == MatchStatus.ONGOING])

    async def _get_matchmode(self, ctx: Context, options: MatchOptions):
        view = MatchmakerUI(ctx, options)

        embed = Embed(color=0x1cc7d4)
        embed.set_author(name="SHADCHAN ➖ MATCHMAKING PORTAL")
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
        embed.clear_fields()
        if view.mode == MatchModes.gvg:
            embed.add_field(name="🔍 Finding a match..", value="Rock on! You will be alerted when a match is found.")
        await m.edit(embed=embed, view=view)
        return view.mode

    async def lineup(self, player: Member, ctx: Context, loop: AbstractEventLoop,
        on_matchup: Callable, options: MatchOptions) -> MatchInstance:
        if options.channel_host is True:
            occupation = list(filter(lambda p: (p.p1.ctx.channel.id == ctx.channel.id or
                                                (p.options.mode != MatchModes.singleplayer
                                                and p.p2 is not None
                                                and p.p2.ctx.channel.id == ctx.channel.id)),
                                    self.puddle))
            if len(occupation) != 0:
                return await ctx.reply("*There is an ongoing game in this channel.*")
        if options.parallel is False:
            occupation = list(filter(lambda p: (p.p1.user.id == ctx.author.id or
                                                (p.options.mode != MatchModes.singleplayer
                                                and p.p2 is not None
                                                and p.p2.user.id == ctx.author.id)),
                                    self.puddle))
            if len(occupation) != 0:
                return await ctx.reply("*You can't play two games or instances in parallel.*")

        if options.mode == MatchModes.unknown:
            options.mode = await self._get_matchmode(ctx, options)
        if options.mode is None:
            return
        return self._reharse(player, ctx, loop, on_matchup, options)

    def _reharse(self, player: Member, ctx: Context, loop: AbstractEventLoop,
        callback: Callable, options: MatchOptions):
        if options.mode == MatchModes.singleplayer:
            new_match = MatchInstance(self, loop, player, ctx, callback, options)
            self.puddle.append(new_match)
            new_match.pair()
        elif options.mode == MatchModes.gvg:
            pending_match = self._get_match(player)
            if pending_match is not None:
                pending_match.pair(player, ctx, callback)
            else:
                new_match = MatchInstance(self, loop, player, ctx, callback, options)
                self.puddle.append(new_match)

    async def _get_ready(self, ctx, player):
        await ctx.send("Match Found please ready up")


    def _get_match(self, player):
        for match in self.puddle:
            if match.status != MatchStatus.ONGOING and match.p1.user.id != player.id:
                return match

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
