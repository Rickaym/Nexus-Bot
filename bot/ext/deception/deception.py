import random
import discord
from discord.activity import Game
import yaml
import logging
import datetime
import asyncio

from typing import Dict, List, Tuple
from discord import Member
from discord.ext import commands
from discord.ext.commands import Context, Greedy

from discord.permissions import PermissionOverwrite

from .Deception.ext import Local_Game_Instance, default_ranks

"""
TODO:
   [1]. Ability to use skills in their own channels
   [2]. Day and night cycle and adding values onto them
   [3]. Voting someone out
   [4]. Make decisions on how long for the talking meeting
   [5]. A Will system somehow??
   [6]. Create winning situations etc..
"""

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)
file_handler = logging.FileHandler('./bot/logs/deception.log')
file_handler.setFormatter(logging.Formatter(
    "[%(asctime)s][%(levelname)s]: %(message)s"))
log.addHandler(file_handler)

TOWNSHIPS = (
    "Amesbury",
    "Andover",
    "Beverly",
    "Billerica",
    "Boxford",
    "Gloucester",
    "Haverhill",
    "Ipswich",
    "Lynn",
    "Malden",
    "Marblehead",
    "Peabody",
    "Reading",
    "Rowley",
    "Salem Towne",
    "Salem Village",
    "Salisbury",
    "Topsfield",
    "Wenham"
)

NUMBER_MAP = {'0': ':zero:', '1': ':one:', '2': ':two:', '3': ':three:',
              '4': ':four:', '5': ':five:', '6': ':six:',
              '7': ':seven:', '8': ':eight:', '9': ':nine:'}


class Deception(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        # Equation for creating a unique identifier

        with open('bot/ext/deception/Deception/preset.yaml', 'r') as file:
            self.preset = yaml.load(file, Loader=yaml.SafeLoader)

        self.games: Dict[int, Local_Game_Instance] = {}

    def validate_members(self, members: List[Member], author: Member) -> Tuple[Member]:
        """
        When the start command is invoked, the bot filters through the member list
        given. It ensures that there are no repeating players and that the bot is not included.
        """
        members = list(set(members))

        # We add the author if they themselves aren't in the list
        if author not in members:
            members.append(author)

        # Removes all bots that may be infested in this list
        for member in members:
            if member.bot:
                members.remove(member)

        return tuple(members)

    @commands.command(name="kill", aliases=("investigate", "sheriff"))
    async def use_skill(self, ctx: Context):
        # Check if there is an ongoing game in the guild
        try:
            self.games[ctx.guild.id]
        except KeyError:
            return

        # Target game
        game = self.games[ctx.guild.id]
        print(game.night, game.day)
        if (p := game.get_player(ctx.author).rank).skill.__name__ == "passive" or game.night != game.day:
            return
        possible_targets = {
            i: m.member.display_name for (i, m) in enumerate(game.all_participants.values())
            if m != game.get_player(ctx.author)}

        await ctx.reply(f"Choose your targets from: {''.join(m for m in list(possible_targets.values()))}")
        while True:
            msg = await self.bot.wait_for('message', check=lambda m: m.author == ctx.author and m.channel == ctx.channel and (m.content).isnumeric() and int(m.content)+1 in [m for m in list(possible_targets.keys())])
            choice = int(msg.content)+1
            # Player doesn't have a passive ability or if its day time
            p.skill(game.get_player(possible_targets[choice]))
            await ctx.reply(p.skill.msg)

    @commands.group(name="deception", aliases=("decep", "d"), invoke_without_command=True)
    async def deception(self, ctx: Context):
        ...

    @deception.command(name="start", aliases=("lobby", "join"))
    @commands.guild_only()
    async def start_new_lobby(self, ctx: Context, members: Greedy[Member] = None):
        """
        Joins a public lobby or starts a private lobby.

        Params: members[list of members]
        """
        # Validate the provided member list
        participants = self.validate_members(members, ctx.author)
        ranks = default_ranks

        if len(participants) > len(ranks):
            await ctx.reply("You have way too many people!")
            return

        # Unique identifier for the game
        identifier = random.choice(
            participants).id * random.randint(1, 64) + datetime.datetime.utcnow().minute
        if not members:
            # multiplayer protocol
            ...
        else:
            log.info(
                f"Starting a new local lobby of id ({identifier}) author is {ctx.author.name}#{ctx.author.discriminator}")
            await self.start_local_lobby(ctx, ranks, participants, identifier)

    async def voting(self, members: Member, game: Game):
        embed = discord.Embed(
            title="Vote out the most suspicious person (Needs majority to get voted out)(If you wish to skip, avoid voting anyone)!", color=discord.Colour.random())

        embed.description = "\n".join(
            f'{NUMBER_MAP[str(i)]} : {m.display_name}' for i, m in enumerate(members))

        game.inquiry_channel.send(embed=embed)
        """
        for i in range(0, len(list2)):
            # Adds reactions to the embed with regards to the all members alive
            await message.add_reaction(f'{emojis[i]}')
        await asyncio.sleep(voting_cd)

        embed = discord.Embed(
            title="Vote out the most suspicious person (Needs majority to get voted out)(If you wish to skip, avoid voting anyone)!", color=color)
        emojis = ['\u0031\ufe0f\u20e3', '\u0032\ufe0f\u20e3', '\u0033\ufe0f\u20e3', '\u0034\ufe0f\u20e3',
                  '\u0035\ufe0f\u20e3', '\u0036\ufe0f\u20e3', '\u0037\ufe0f\u20e3', '\u0038\ufe0f\u20e3', '\u0039\ufe0f\u20e3', '🔟']

        count = 0
        for member in list2:
            # Makes a votable embed list with every member
            embed.add_field(
                name=f'\u200b', value=f'{emojis[count]} <@{member}>')
            final = await meeting_ch.fetch_message(message.id)
        # Fetch aftervoting results
        reactions = final.reactions
        highest = 0

        tie = False
        for reaction in reactions:
            if (counter := int(reaction.count)) > highest:
                voted_emoji = reaction.emoji
                highest = counter
                tie = False
            elif (counter := int(reaction.count)) == highest:                     # Checks the votes
                tie = True
        if highest <= 1:
            tie = False

        index = 0
        for emoji in emojis:
            if emoji == voted_emoji:                 # Gets the position of the highly voted emoji to retrieve the member
                break
            index += 1

        # If the majority votes one highest person
        if highest >= (len(list2) / 2) and not tie:
            # The selected person
            await meeting_ch.send(f'<@{list2[index]}> has been voted out!')
            on_alive_list = list2.copy()
            c = 0
            for i in on_alive_list:
                if int(i) == list2[index]:
                    on_alive_list.pop(c)
                c += 1
            f = open('cogs/mm/lives.txt', 'w')
            for i in on_alive_list:
                f.write(f'{i}\n')
            f.close()
        if tie:
            await meeting_ch.send('There has been a tie!')
        elif highest == 1:
            await meeting_ch.send('No one has voted! ')"""

    async def start_local_lobby(self, ctx: Context, ranks: tuple, participants: List[Member], id: int):
        await ctx.reply("Game is starting soon...")

        # Build player role
        role = discord.utils.get(
            ctx.guild.roles, name=self.preset['names']['role_name'])
        # Need to make a new one doesn't exist
        if not role:
            role = await ctx.guild.create_role(name=self.preset['names']['role_name'], colour=discord.Colour.random())

        # Instantiate local game
        game = Local_Game_Instance(
            ctx, participants, ranks, role, id)

        # We allow everyone with the target role to see the channels
        # the bot itself and remove @everyone
        basic_overwrite = {role: PermissionOverwrite(read_messages=True),
                           ctx.guild.me: PermissionOverwrite(read_messages=True),
                           ctx.guild.default_role: PermissionOverwrite(read_messages=False)}

        game.category = await ctx.guild.create_category(
            random.choice(TOWNSHIPS), overwrites=basic_overwrite)

        game.inquiry_channel = await game.category.create_text_channel(
            self.preset['names']['inquiry'], overwrites=basic_overwrite)

        # Creating a channel for each member
        positions = {}
        for member in participants:
            if ctx.guild.owner != member:
                overwrite = {member: PermissionOverwrite(read_messages=True, send_messages=True),
                             ctx.guild.default_role: PermissionOverwrite(read_messages=False),
                             ctx.guild.me: PermissionOverwrite(read_messages=True, send_messages=True)}
            else:
                overwrite = {ctx.guild.default_role: PermissionOverwrite(read_messages=False),
                             ctx.guild.me: PermissionOverwrite(read_messages=True, send_messages=True)}

            channel = await game.category.create_text_channel(
                self.preset['names']['member'] % member.display_name, overwrites=overwrite)
            await member.add_roles(role)
            await channel.send(
                f"You got the role {game.get_player(member).rank.name}.\n\n{game.get_player(member).rank.description}")

            positions[member.id] = channel

        # Provides the game class with channel intel
        game.assign_channels(positions)

        # Declares it as a class variable to handle skill commands
        # separately
        self.games[ctx.guild.id] = game
        # Game loop starts
        while game.is_ongoing:
            game.day += 1
            await game.inquiry_channel.send(f"Day {game.day}\n Members = {' ,'.join(user.display_name for user in participants)}")
            await game.open_inquiry(5)
            await game.inquiry_channel.send("... the sun has set on us. Goodnight sleep tight.")
            game.night += 1
            await asyncio.sleep(20)
            if game.day >= 8:
                game._is_ongoing = False
                game.stop()

    @commands.command(name="delall")
    @commands.is_owner()
    @commands.guild_only()
    async def del_all_channels_from_category(self, ctx: Context, id: Greedy[int]):
        print(id)
        for i in id:
            category = discord.utils.get(ctx.guild.categories, id=int(i))
            for channel in category.channels:
                await channel.delete()
                await asyncio.sleep(1)
            await category.delete()


def setup(bot):
    print("[PRIORITY] Deception game is now loaded")
    bot.add_cog(Deception(bot))
