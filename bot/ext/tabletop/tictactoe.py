from discord import ui
from discord.embeds import Embed
from discord.enums import ButtonStyle
from discord.ext import commands
from discord.interactions import Interaction
from asyncio.exceptions import TimeoutError
from discord.ui.button import Button
from bot.utils.shadchan import MatchInstance, MatchModes, Pool, MatchOptions
from bot.utils.hearsay import Hearsay
from string import ascii_uppercase

class TicTacToeUi(ui.View):
    """
    A1 B1 C1
    A2 B2 C2
    A3 B3 C3
    """
    def __init__(self, player, match: MatchInstance, symbol, loop):
        super().__init__(timeout=180)
        self.player = player
        self.match = match
        self.symbol = symbol
        self.loop = loop
        self.started = False
        self.won = False
        self.board = [[], [], []]
        for c_id in ("A1", "B1", "C1", "A2", "B2", "C2", "A3", "B3", "C3"):
            i = Button(label="\u200b", style=ButtonStyle.gray,
                                 custom_id=c_id, row=int(c_id[1]))
            self.board[ascii_uppercase.index(c_id[0])].append(i)
            self.add_item(i)

    async def interaction_check(self, i: Interaction) -> bool:
        if not self.started or i.user.id != self.player.id:
            return False

        custom_id = i.data["custom_id"]
        for item in self.children:
            item.disabled = True
            if item.custom_id == custom_id:
                item.emoji = self.symbol
                item.style = ButtonStyle.blurple
        won, line = self.get_gamestate(custom_id, self.symbol)
        if won:
            self.won = True
            for z in line:
                z.style = ButtonStyle.green
            self.stop()
        self.loop.create_task(i.message.edit(view=self))
        self.match.emit("press_button", custom_id, self.player, self.symbol, self.won, line)
        return True

    async def enemy_press(self, custom_id, message, symbol, enemy_won, line):
        if enemy_won is True:
            self.stop()

        for item in self.children:
            if item.custom_id == custom_id:
                item.disabled = True
                item.emoji = symbol
                item.style = ButtonStyle.blurple
            if enemy_won is True:
                if item.custom_id in [i.custom_id for i in line]:
                    item.style = ButtonStyle.danger
                item.disabled = True
            else:
                if item.style == ButtonStyle.gray:
                    item.disabled = False

        self.loop.create_task(message.edit(view=self))

    def get_gamestate(self, custom_id, symbol):
        """
        A1 B1 C1
        A2 B2 C2
        A3 B3 C3
        """
        line = []
        col, row = ascii_uppercase.index(custom_id[0]), int(custom_id[1])-1
        for i in range(3):
            if str(self.board[col][i].emoji) != symbol:
                break
            else:
                line.append(self.board[col][i])
            if i == 2:
                return True, line

        line = []
        for i in range(3):
            if str(self.board[i][row].emoji) != symbol:
                break
            else:
                line.append(self.board[i][row])
            if i == 2:
                return True, line

        line = []
        if col == row:
            for i in range(3):
                if str(self.board[i][i].emoji) != symbol:
                    break
                else:
                    line.append(self.board[i][i])
                if i == 2:
                    return True, line

        line = []
        if col+row == 2:
            for i in range(3):
                if str(self.board[i][2-i].emoji) != symbol:
                    break
                else:
                    line.append(self.board[i][2-i])
                if i == 2:
                    return True, line
        return False, None


class TicTacToe(commands.Cog):
    ttt_SID = "tic_tac_toe___"
    symbol_AID = "tttemoji"

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def start_tictactoe(self, commander, ctx, match: MatchInstance):
        game = TicTacToeUi(commander, match, (await Hearsay.resolve_asset(commander, self.symbol_AID)) or "⭕", self.bot.loop)
        msg = await ctx.send(embed=Embed(description=f"*You are {game.symbol}! First person to click starts.*", color=0x2F3136), view=game)

        @match.on_emit("press_button")
        async def press_button(custom_id, player, symbol, won, line):
            if player.id != commander.id:
                if symbol == game.symbol:
                    symbol = '❌'
                await game.enemy_press(custom_id, msg, symbol, won, line)

        game.started = True
        for i in range(9):
            # press_button is dispatched from inside the ui
            try:
                await match.wait_for("press_button", 20)
            except TimeoutError:
                await ctx.send("Timed out! A turn has been skipped.")
                break
            res = await match.conclude(game.won, lambda a, b: a or b)
            if res is True:
                if game.won is True:
                    await ctx.send(embed=Embed(description=f"*You've won!*", color=0x2F3136))
                else:
                    await ctx.send(embed=Embed(description=f"*You've lost!*", color=0x2F3136))
                break
        if not res:
            await ctx.send(embed=Embed(description=f"*It's a tie.*", color=0x2F3136))
        await match.enable_chat(self.bot, 45)
        return match.end()

    @commands.command(name="view")
    async def vvv(self, ctx):
        v = TicTacToeUi(ctx.author)
        await ctx.send("test", view=v)
        v.started = True
        await v.wait()

    @commands.command(name="tictactoe", aliases=("ttt",))
    async def tictactoe(self, ctx):
        await Pool.get(self.ttt_SID).lineup(ctx.author, ctx, self.bot.loop,
                lambda *args: self.bot.loop.create_task(self.start_tictactoe(*args)),
                MatchOptions(MatchModes.gvg))


def setup(bot):
    bot.add_cog(TicTacToe(bot))
    print("Loaded TicTactoe.cog")