import discord
import asyncio

from discord.ext import commands

PLAYER_MAP = {'🔴': 1, '🔵': 0}
PLAYER_1 = '🔴'
PLAYER_2 = '🔵'
BLANK = f'<:background_square:836677677175799928>'

BASE_LINE = [[f'{BLANK}', f'{BLANK}', f'{BLANK}', f'{BLANK}', f'{BLANK}', f'{BLANK}', f'{BLANK}'],
             [f'{BLANK}', f'{BLANK}', f'{BLANK}', f'{BLANK}',
                 f'{BLANK}', f'{BLANK}', f'{BLANK}'],
             [f'{BLANK}', f'{BLANK}', f'{BLANK}', f'{BLANK}',
                 f'{BLANK}', f'{BLANK}', f'{BLANK}'],
             [f'{BLANK}', f'{BLANK}', f'{BLANK}', f'{BLANK}',
                 f'{BLANK}', f'{BLANK}', f'{BLANK}'],
             [f'{BLANK}', f'{BLANK}', f'{BLANK}', f'{BLANK}',
                 f'{BLANK}', f'{BLANK}', f'{BLANK}'],
             [f'{BLANK}', f'{BLANK}', f'{BLANK}', f'{BLANK}', f'{BLANK}', f'{BLANK}', f'{BLANK}']]

HORIZON_LOC = {'A': 0, 'B': 1, 'C': 2, 'D': 3,
               'E': 4, 'F': 5, 'G': 6, 'H': 7, 'I': 8}


class ConnectFour(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.jobs = {}
        self.template = discord.Embed(title="Connect Four",
                                      color=discord.Colour.random())

    @commands.Cog.listener()
    async def on_message(self, message):
        if not message.guild:
            return
        if message.guild.id not in self.jobs.keys():
            return
        if message.channel.id not in [values[0] for values in self.jobs.values()]:
            return
        if message.author.id not in [values[1] for values in self.jobs.values()][0]:
            return

        guild_id = message.guild.id
        channel = message.channel
        author = message.author
        content = message.content
        game = self.jobs[guild_id]
        board = game[2]

        await message.delete()
        turn = self.get_turn(board)
        if (turn == PLAYER_1 and author.id != game[1][0]) or (turn == PLAYER_2 and author.id != game[1][1]):
            to_del = await channel.send("This is not your turn!")
            await asyncio.sleep(5)
            await to_del.delete()
            return

        x, y = self.extract_pos(content)
        if x is None and y is None:
            return
        if self.jobs[guild_id][2][y][x] == BLANK:
            self.jobs[guild_id][2][y][x] = turn
        else:
            to_del = await channel.send(f"Position {content} already occupied.")
            await asyncio.sleep(5)
            await to_del.delete()
            return
        board_message = await self.update_board(guild_id, turn)
        status, player = self.get_report(board)
        if status == "win":
            del self.jobs[guild_id]
            await board_message.reply(f"{player} {author.display_name} has won!")

    def get_report(self, board) -> str:
        board = tuple([tuple(line) for line in board])
        vertical_board = tuple(zip(*board))
        for line in board:
            if PLAYER_1 in line or PLAYER_2 in line:
                start_on = None
                horizon_count = 1
                for character in line:
                    if character == BLANK:
                        continue
                    if character == PLAYER_1 and start_on == PLAYER_1:
                        horizon_count += 1
                    elif character == PLAYER_1 and start_on == PLAYER_2:
                        horizon_count = 1

                    if character == PLAYER_2 and start_on == PLAYER_2:
                        horizon_count += 1
                    elif character == PLAYER_2 and start_on == PLAYER_1:
                        horizon_count = 1

                    if character == PLAYER_1:
                        start_on = PLAYER_1
                    elif character == PLAYER_2:
                        start_on = PLAYER_2

                    if horizon_count == 4:
                        return "win", start_on
        for verline in vertical_board:
            if PLAYER_1 in verline or PLAYER_2 in verline:
                vertical_count = 1
                ver_start_on = None
                for character in verline:
                    if character == BLANK:
                        continue
                    if character == PLAYER_1 and ver_start_on == PLAYER_1:
                        vertical_count += 1
                    elif character == PLAYER_1 and ver_start_on == PLAYER_2:
                        vertical_count = 1

                    if character == PLAYER_2 and ver_start_on == PLAYER_2:
                        vertical_count += 1
                    elif character == PLAYER_2 and ver_start_on == PLAYER_1:
                        vertical_count = 1

                    if character == PLAYER_1:
                        ver_start_on = PLAYER_1
                    elif character == PLAYER_2:
                        ver_start_on = PLAYER_2
                    if vertical_count == 4:
                        return "win", ver_start_on
        return None, None

    def get_turn(self, board: list) -> str:
        """
        Retrieve the information on whose turn it is for the current game
        based on the count of circles inserted.
        """
        board = sum(board, [])
        if board.count(PLAYER_1) > board.count(PLAYER_2):
            return PLAYER_2
        elif board.count(PLAYER_1) == 0 and board.count(PLAYER_2) == 0:
            return PLAYER_1
        else:
            return PLAYER_1

    async def update_board(self, guild_id: int, turn: str) -> discord.Message:
        """
        Gets the latest updates of the game and update the
        embed of the game.
        """
        message = self.jobs[guild_id][3]
        embed = self.template.copy()
        embed.description = f"<@{self.jobs[guild_id][1][PLAYER_MAP[turn]]}>'s turn\n" + str(
            '\n'.join([''.join(line) for line in self.jobs[guild_id][2]]))
        await message.edit(embed=embed)
        return message

    def extract_pos(self, content: str):
        """
        Extracts the x and y position from the content of the message that was sent.

        A numeric horizontal index is acquired by mapping the value onto a
        dictionary.
        """
        if len(content) != 2:
            return (None, None)
        try:
            int(content[0])
        except ValueError:
            return HORIZON_LOC[content[0].upper()], int(content[1]) - 1
        else:
            return HORIZON_LOC[content[1].upper()], int(content[0]) - 1

    @commands.command(name="connectfour", aliases=["connect4", "cnt4", "ct4", "ctfour"])
    @commands.guild_only()
    async def connnect_four(self, ctx, opponent: discord.Member):
        """
        Connect four is a game of vertical checkers with whoever succeeds to place down 4 straight ellipses wins.
        """
        if opponent.bot:
            await ctx.reply("You can't play with a bot!")
            return
        embed = self.template.copy()
        embed.description = f"<@{ctx.author.id}>'s turn\n" + str(
            '\n'.join([''.join(line) for line in BASE_LINE]))
        message = await ctx.reply(embed=embed, mention_author=False)
        self.jobs[ctx.guild.id] = [ctx.channel.id, [
            ctx.author.id, opponent.id], BASE_LINE, message]


def setup(bot):
    bot.add_cog(ConnectFour(bot))
    print('ConnectFour.cog is loaded')
