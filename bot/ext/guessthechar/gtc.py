import discord
import asyncio
import random

from discord.ext import commands

from bot.constants import Colour
from . import themes as TH

EMOJIS = ('🤩', '🤪', '🤭',
          '🤫', '🤨', '🤮', '🤯', '🧐', '🤬', '🧡',
          '🤟', '🤲', '🧠', '🧒', '🧑', '🧔', '🧓',
          '🧕', '🤱', '🧙', '🧚', '🧛', '🧜', '🧝',
          '🧞', '🧟', '🧖', '🧗', '🧘', '🦓',
          '🦒', '🦔', '🦕', '🦖', '🦗', '🥥',
          '🥦', '🥨', '🥩', '🥪', '🥣', '🥫',
          '🥟', '🥠', '🥡', '🥧', '🥤', '🥢', '🛸',
          '🛷', '🥌', '🧣', '🧤', '🧥', '🧦', '🧢')


class BadTheme(commands.CommandError):
    ...


class GuessTheCharacter(commands.Cog):

    """ =------------------------- GuessTheChar -------------------------=
        | This is the main cog that the game loop will be written in.    |
        |                                                                |
        | Main Commands - 'start'                                        |
        |    Parameters:                                                 |
        |        - normal                                                |
        |        - custom                                                |
        |            - rounds                                            |
        |                - members                                       |
        |                                                                |
        | start <normal/custom> <rounds> <members>                       |
        =----------------------------------------------------------------= """

    def __init__(self, bot):
        self.bot = bot

        self.basic_score = 7
        self.starting_score = 0

        self.channels = {}  # {guild_id: channel_id}

        self.to_ready_up = {}           # {messageID : {user_id : bool}}
        # {channelID : ['theme', [members], place]}
        self.to_complete_answers = {}

        self.scores = {}   # {channelID : {authorID :score, authorID2 :score}}
        self.scotd = {}    # Scores of the day for leaderboards
        self.latest_answers = {}

        self.ready_up_emoji = '👨'
        self.takedown_emoji = '<:takedown:806794390538027009>'

        self.color = Colour.SUN_YELLOW

    async def rapid_ready_up(self, ctx, message, members, guess_time, images, topic, branch):
        """
        A lobby system is used before a game instance; that is invoked by
        the rapid-ready-up function. The function cycles through a request process
        for 50 seconds, checking whether if all players have responded and commited
        to the lobby. A on_raw_reaction_add event is used as a reciever that completes a
        series of checklists.
        """
        self.to_ready_up[message.id] = {}
        self.scores[ctx.channel.id] = {}
        for member in members:
            self.to_ready_up[message.id][member.id] = False
            self.scores[ctx.channel.id][member.id] = self.starting_score

        players_text = ' ,'.join([member.mention for member in members])
        embed = message.embeds[0]
        embed.description = f'> Players: {players_text}\n> \n> All members please react with {self.ready_up_emoji} to ready up.\n> Vote with {self.takedown_emoji} to force stop(3/4 votes).\n\n> **Information**\n> Starting in 3 seconds...\n> Guess Time = {guess_time} seconds\n> Characters = {len(images)}\n> No of Participants = {len(members)}\n\n> **Game**\n> Theme : {topic}\n> Branch : {branch}'
        await message.edit(embed=embed)

        for emoji in [self.ready_up_emoji, self.takedown_emoji]:
            await message.add_reaction(emoji)

        for i in range(50):
            try:
                self.to_ready_up[message.id]
            except KeyError:
                raise asyncio.TimeoutError
            else:
                if False not in [self.to_ready_up[message.id][key] for key in self.to_ready_up[message.id].keys()]:
                    self.to_ready_up.pop(message.id)
                    return
                await asyncio.sleep(1)

        inactive_members = [f'<@{key}>' for key in self.to_ready_up[message.id].keys(
        ) if self.to_ready_up[message.id][key] == False]
        inactive_members = ', '.join(z := inactive_members)
        await message.edit(embed=discord.Embed(title="__**# Lobby**__", description=f"{inactive_members} {'are' if len(z) >= 2 else 'is'} inactive - Lobby failed to start.", color=discord.Color.dark_red()))
        self.to_ready_up.pop(message.id)
        self.channels.pop(ctx.guild.id)
        self.scores.pop(ctx.channel.id)
        raise asyncio.TimeoutError

    def get_word(self, word, branch=None):
        """
        We use the get_word function to forumulate an omitted word. This is done by
        replacing all the characters from the theme with underscores. Although there is
        a minimal chance that a character stays unomitted
        """
        theme = word[:]

        characters = list(theme)
        length = len(characters)
        blanked_word = [''] * len(characters)

        hint_amount = random.randint((length // 3), (length // 2))
        if branch != "seasons":
            for z, char in enumerate(characters):
                if char == ' ':
                    blanked_word[z] = ('  ')
                else:
                    if random.randint(0, 1) == 0 or hint_amount == 0:
                        blanked_word[z] = (' _ ')
                    else:
                        blanked_word[z] = (f' {char} ')
                        hint_amount -= 1
        elif branch.lower() == "seasons":
            for z, char in enumerate(characters):
                if not char.strip().isnumeric():
                    blanked_word[z] = (f' {char} ')
                elif char.strip().isnumeric():
                    blanked_word[z] = (' _ ')

        blank = blanked_word
        return blank, theme

    async def build_score(self, guild, channel, members):
        """
        We use the build_score function that takes in scores and members to
        build the final embed that contains the position and scores of every
        player. This is done by sorting them accordingly to their scores from highest
        to lowest and pairing them up with positions by index.
        """
        target = self.scores[channel.id]
        scores = sorted(target.items(),
                        key=lambda x: x[1], reverse=True)
        embed = discord.Embed(title='__**# Scoreboard**__', color=self.color)
        places = ['🥇', '🥈', '🥉', ':four:', ':five:',
                  ':six:', ':seven:', ':eight:', ':nine:', '🔟']
        for i in range(0, len(members)):
            embed.add_field(
                name='\u200b', value=f'{places[i]} : <@{scores[i][0]}> : {scores[i][1]} pts', inline=False)
        self.scores.pop(channel.id)
        return embed

    def member_validation(self, members, author, bot):
        """
        When the start command is invoked, the bot filters through the member list
        given. It ensures that there are no repeating players and that the bot is not included.
        """
        members = list(set(members))
        if author not in members:
            members.append(author)
        if self.bot.user in members:
            members.remove(bot)
        return list(members)

    async def get_answers_from_players(self, message, channel, theme, blank, members, answer_time):
        """
        Recieves and filter answers based on the theme.
        """
        members = members.copy()
        data = [
            theme, members, len(members)]
        self.to_complete_answers[channel.id] = data
        for i in range(answer_time // 3):
            await asyncio.sleep(3)
            data = self.to_complete_answers[channel.id]
            if len(data[1]) == 0:
                await channel.send("Great job! Everyone answered correctly.")
                self.to_complete_answers.pop(channel.id)
                return
            if (i >= (i // 2)) and (i % 5 == 0) and (i != 0) and (len(theme) > 5):
                blank = self.get_hint(blank, theme)
                embed = message.embeds[0]
                embed.description = f'Just say it out loud, no fancy commands needed!\n> Character : `{"".join(blank)}`'
                await message.edit(embed=embed)
        if len(z := data[1]) > 0:
            unanswered = [f'{i.mention}' for i in data[1]]
            text = ', '.join(unanswered)
            await channel.send(f"{text} {'have' if len(z) >= 2 else 'has'} failed to answer correctly. What a let down fellas :p. The character was {theme}.")
        try:
            self.to_complete_answers.pop(channel.id)
        except KeyError:
            pass

    def get_hint(self, blank, theme):
        blank_copy = blank[:]
        theme_copy = [f' {char} ' if char != ' ' else '  ' for char in theme]
        try:
            i = blank_copy.index(' _ ')
        except ValueError:
            pass
        else:
            if random.randint(0, 1) == 1 and not theme_copy[i].strip().isnumeric():
                blank_copy[i] = theme_copy[i]
        return blank_copy

    def get_images(self, topic, branch):
        topic = topic.lower().strip()
        branch = branch.lower().strip()
        all_topics = ["fortnite", "marvel",
                      "starwars", "harrypotter", "disney"]
        if topic not in all_topics:
            raise BadTheme
        elif topic in all_topics:
            if topic == "fortnite":
                if branch == "characters":
                    return list(TH.Fortnite.CHARACTERS.items())
                elif branch == "items":
                    return list(TH.Fortnite.ITEMS.items())
                elif branch == "seasons":
                    return list(TH.Fortnite.SEASONS.items())
            elif topic == "marvel":
                if branch == "easy":
                    return list(TH.Marvel.EASY.items())
                elif branch == "medium":
                    return list(TH.Marvel.MEDIUM.items())
                elif branch == "hard":
                    return list(TH.Marvel.HARD.items())
            elif topic == "starwars":
                if branch == "easy":
                    return list(TH.StarWars.EASY.items())
                elif branch == "medium":
                    return list(TH.StarWars.MEDIUM.items())
                elif branch == "hard":
                    return list(TH.StarWars.HARD.items())
            elif topic == "harrypotter":
                if branch == "easy":
                    return list(TH.HarryPotter.EASY.items())
                elif branch == "medium":
                    return list(TH.HarryPotter.MEDIUM.items())
                elif branch == "hard":
                    return list(TH.HarryPotter.HARD.items())
            elif topic == "disney":
                if branch == "easy":
                    return list(TH.WaltDisney.EASY.items())
                elif branch == "medium":
                    return list(TH.WaltDisney.MEDIUM.items())
                elif branch == "hard":
                    return list(TH.WaltDisney.HARD.items())
            raise BadTheme

    @commands.Cog.listener()
    async def on_message(self, message):
        author = message.author
        if author == self.bot:
            return
        channel = message.channel
        if channel.id in self.to_complete_answers.keys():
            data = self.to_complete_answers[channel.id]
            if author in data[1]:
                if message.content.lower() == data[0].lower():
                    score = self.basic_score * data[2]
                    self.scores[channel.id][author.id] += score
                    self.to_complete_answers[channel.id][2] -= 1
                    self.to_complete_answers[channel.id][1].remove(author)
                    await message.delete()
                    await channel.send(f"{author.mention} has answered correctly and scored {score}!")
                else:
                    await message.add_reaction('🤣')

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        """
        Works hand in hand with rapid_ready_up to form a await_for like process
        that waits for emojis to be reacted without a halt within the command process.
        Making it work like a well oiled machine.
        """
        if payload.user_id == self.bot.user.id:
            return
        if payload.channel_id in [self.channels[key] for key in self.channels.keys()]:
            guild = discord.utils.find(
                lambda g: g.id == payload.guild_id, self.bot.guilds)
            channel = guild.get_channel(payload.channel_id)
            message = await channel.fetch_message(payload.message_id)
            if payload.user_id in [i for i in self.to_ready_up[message.id].keys()] and not self.to_ready_up[message.id][payload.user_id]:
                emoji = str(payload.emoji)
                member = await guild.fetch_member(payload.user_id)
                if emoji == self.ready_up_emoji:
                    self.to_ready_up[message.id][payload.user_id] = True
                    await channel.send(f'{member.display_name} is now ready!')
                if emoji == self.takedown_emoji:
                    if (target_reaction := [reaction for reaction in message.reactions if f'{reaction.emoji}' == self.takedown_emoji][0]).count == len([i for i in self.to_ready_up[message.id].keys()]):
                        user_list = await target_reaction.users().flatten()
                        sd_people = ', '.join(
                            v := [i.mention for i in [user for user in user_list if user != self.bot.user] if i.id in self.to_ready_up[message.id].keys()])

                        await message.edit(embed=discord.Embed(title='__**# Force Stop**__', description=f"{sd_people} {'have' if len(v) >= 2 else 'has'} voted to force stop the match.", color=discord.Color.dark_red()))
                        self.to_ready_up.pop(message.id)
                        self.scores.pop(payload.channel_id)
                        self.channels.pop(guild.id)

    @commands.group(name="guessthechar", aliases=("gtc", "guessthecharacter"), invoke_without_command=True)
    @commands.bot_has_permissions(manage_messages=True)
    @commands.guild_only()
    async def guessthecharacter(self, ctx):
        embed = discord.Embed(color=discord.Colour.random())
        embed.set_author(
            name="Guess The Character Manual", icon_url="https://raw.githubusercontent.com/twitter/twemoji/master/assets/72x72/1f4d6.png")
        embed.description = f"Guess what character it is by looking at the images!\n\n__**Command**__\n> `{ctx.prefix}guessthecharacter start <topic> <branch> <members...>`\n\n__**Information**__\n**1.** In a game with default settings, participants will get a duration of 60 seconds to guess the character displayed. \n\n**2.** Faliure to answer will grant you no points. The first person to answer will get the points of `total participants * 7`, which depletes by 7 points as it goes down."
        embed.set_footer(
            text=f"All topics and branches • {ctx.prefix}guessthecharacter themes")
        await ctx.reply(embed=embed, mention_author=False)

    @guessthecharacter.command(name="themes", aliases=("theme",))
    @commands.guild_only()
    async def guessthecharacter_themes(self, ctx):
        embed = discord.Embed(
            description="Below is a list of all available topics and their respective brances. Make sure to avoid using spaces on topics or branches with two words.", color=discord.Colour.random())
        embed.set_author(
            name="Themes", icon_url="https://raw.githubusercontent.com/twitter/twemoji/master/assets/72x72/1f451.png")
        fields = (("`Marvel`", "> - Easy\n> - Medium\n> - Hard"),
                  ("`StarWars`", "> - Easy\n> - Medium\n> - Hard"),
                  ("`Fortnite`", "> - Characters\n> - Items\n> - Seasons"),
                  ("`Walt Disney`", "> - Easy\n> - Medium\n> - Hard"),
                  ("`Harry Potter`", "> - Easy\n> - Medium\n> - Hard"))
        for field in fields:
            embed.add_field(name=field[0], value=field[1])
        embed.set_footer(text=f"Index of all commands • {ctx.prefix}help")
        await ctx.reply(embed=embed, mention_author=False)

    @guessthecharacter.command(name="start")
    @commands.guild_only()
    async def guessthecharacter_start(self, ctx, topic, branch, members: commands.Greedy[discord.Member] = None, guess_time=60):
       # Pre-member validation
        if members is None:
            await ctx.send("⚠️ You didn't specify any participants, please try again.")
            return
        elif members is not None:
            members = self.member_validation(members, ctx.author, ctx.guild.me)

        elif len(members) < 2:
            await ctx.send("⚠️ You need more than 2 members to start a game.")
            return
        elif len(members) > 30:
            await ctx.send("⚠️ You have way too many members to start a game!")
            return

        # Prevention of hosting two game instances in the same channel
        if ctx.channel.id in [self.channels[key] for key in self.channels.keys()]:
            await ctx.send("⚠️ Unable to start a new game since there is an on-going game in this channel.")
            return

        self.channels[ctx.guild.id] = ctx.channel.id
        channel = ctx.channel
        guild = ctx.guild
        try:
            images = self.get_images(topic, branch)
            random.shuffle(images)
        except BadTheme:
            await ctx.reply("❗ You passed in an invalid topic or a branch. Do `!themes` to see the topics available.")
            self.channels.pop(ctx.guild.id)
            return
        GUESSING_TIME = guess_time
        lobby_init = await ctx.send(embed=(discord.Embed(title='__**# Lobby**__', description=f'> **Information**\n> Starting in 3 seconds...\n> Guess Time = {guess_time} seconds\n> Characters = {len(images)}\n> No of Participants = {len(members)}\n\n> **Game**\n> Theme : {topic}\n> Branch : {branch}', color=self.color)).set_thumbnail(url="https://cdn.discordapp.com/icons/709035048313159720/3c6bfd11a92e3f0f6029310b4daa9280.webp?size=256"))
        await asyncio.sleep(3)

        # Rapid ready-up protocol
        try:
            await self.rapid_ready_up(ctx, lobby_init, members, GUESSING_TIME, images, topic, branch)
        except asyncio.TimeoutError:
            return

        main_embed = await channel.send(embed=discord.Embed(title="All players ready.", description="Game will shortly begin in 5 seconds", color=self.color))
        await asyncio.sleep(5)
        await main_embed.edit(embed=discord.Embed(title="GAME HAS STARTED", description='Picture : 1', color=self.color))
        for n, group in enumerate(images):
            # Group = (image, theme)
            url = group[1]
            theme = group[0]
            if n != 0:
                await channel.send(embed=discord.Embed(title="Game Update", description=f'Picture : {n+1}', color=self.color))
            blank, theme = self.get_word(theme, branch)
            embed = discord.Embed(title="Use the format 'Chapter x Season y'" if branch.lower() == 'seasons' else "Start Guessing",
                                  description=f'Just say it out loud, no fancy commands needed!\n> Character : `{"".join(blank)}`', color=discord.Color.random()).set_author(name=f"{random.choice(EMOJIS)} Guess the character!")
            embed.set_image(url=url)
            message = await channel.send(embed=embed)
            await self.get_answers_from_players(message, channel, theme, blank, members, GUESSING_TIME)
        embed = await self.build_score(guild, channel, members)
        await channel.send(embed=embed)
        self.channels.pop(ctx.guild.id)


def setup(bot):
    bot.add_cog(GuessTheCharacter(bot))
    print("[PRIORITY] Guess The Character game is now loaded")
