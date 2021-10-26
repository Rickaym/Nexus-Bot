import random
import discord
from discord.channel import CategoryChannel
import yaml
import logging
import datetime
import asyncio

from typing import Dict, List, Optional, Tuple, Union
from discord.activity import Game
from discord import Member
from discord.ext import commands
from discord.ext.commands import Context, Greedy
from discord.raw_models import RawReactionActionEvent
from discord.permissions import PermissionOverwrite

from .Deception.ext import LAN_Game_Instance, Player, Rank, WAN_Game_Instance, default_ranks, all_ranks, FACTION_COLORS
from .Deception import utils
from bot.utils.checks import is_admin

NUMBER_MAP = {0: ':zero:', 1: ':one:', 2: ':two:', 3: ':three:',
              4: ':four:', 5: ':five:', 6: ':six:',
              7: ':seven:', 8: ':eight:', 9: ':nine:'}

"""
TODO:
   [1]. Ability to use skills in their own channels         ☑️
   [2]. Day and night cycle and adding values onto them     ☑️
   [3]. Voting someone out
   [4]. Make decisions on how long for the talking meeting
   [5]. A Will system somehow??
   [6]. Create winning situations etc..
   [7]. Loading a game out of templates                     ☑️
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


class Deception(commands.Cog):
    """
    What is a lie?...
    I.. can you really trust anyone - especially those subject to the will of their self interest?..
    """
    def __init__(self, bot):
        self.bot = bot

        with open('bot/ext/deception/Deception/preset.yaml', 'r') as file:
            self.preset = yaml.load(file, Loader=yaml.SafeLoader)

        self.games: Dict[int, LAN_Game_Instance] = {}

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

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: RawReactionActionEvent):
        if payload.user_id == self.bot.user.id or payload.emoji.name not in utils.printable_emojis.values():
            return

        if int(payload.guild_id) not in self.games.keys():
            return

        log.info(
            f"Carrying out a skill panel task for guild {payload.guild_id}")
        game = self.games[int(payload.guild_id)]

        # the reaction is done by one of the people that owns a skill panel
        if payload.member not in game.info['skill_panel'].keys():
            return

        message = game.info['skill_panel'][payload.member]

        # apparently the reacting user is reacting to something else
        if payload.message_id != message.id:
            return

        actor = utils.get(Player, game, id=payload.user_id)
        victim = utils.get_options(message.embeds[0].description, game)[
            payload.emoji.name]

        actor.skill(victim)
        await game.info['channels'][payload.user_id].send(actor.rank.skill.msg)

    @commands.command(name="kill", aliases=("investigate", "sheriff"))
    async def use_skill(self, ctx: Context):
        """
        Use skill.
        """
        # Check if there is an ongoing game in the guild
        try:
            self.games[ctx.guild.id]
        except KeyError:
            return

        # Target game
        game = self.games[ctx.guild.id]
        if (p := game.get_player(ctx.author)).rank.skill.__name__ == "passive" or game.night != game.day:
            return
        possible_targets = {
            i: m.member for (i, m) in enumerate(game.all_participants.values())
            if m != game.get_player(ctx.author)}

        await ctx.reply(f"Choose your targets from: {''.join(m.display_name for m in list(possible_targets.values()))}")
        while True:
            msg = await self.bot.wait_for('message', check=lambda m: m.author == ctx.author and m.channel == ctx.channel and (m.content).isnumeric() and int(m.content)-1 in [m for m in list(possible_targets.keys())])
            choice = int(msg.content)-1

            # Player doesn't have a passive ability or if its day time
            p.skill(game.get_player(possible_targets[choice]))
            await ctx.reply(p.rank.skill.msg)

    @commands.group(name="deception", aliases=("decep", "d"), invoke_without_command=True)
    async def deception(self, ctx: Context):
        """IGNORE"""
        await self.bot.call_command("help", ctx, module="deception")

    @deception.command(name="start", aliases=("lobby", "join", "load"))
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
            return
        if ctx.invoked_with == "load" and is_admin(ctx):
            # Finds category ID at the last place of the args without specifically asking for it
            category_id = int(ctx.args[-1])
            log.info(
                f"Loading a templated local lobby of id ({identifier}) author is {ctx.author.name}#{ctx.author.discriminator} with category id {category_id}"
            )
            await self.start_local_lobby(ctx, ranks, participants, identifier, mode="load", load_id=category_id)
        else:
            log.info(
                f"Starting a new local lobby of id ({identifier}) author is {ctx.author.name}#{ctx.author.discriminator}")
            await self.start_local_lobby(ctx, ranks, participants, identifier, mode="start")

    @deception.command(name="info")
    async def deception_help(self, ctx: Context, rank_name: str):
        """
        Get more details of a specific rank.
        """
        ranks = [r.name.lower() for r in all_ranks]
        if rank_name.lower() in ranks:
            rank = utils.get(object=Rank, name=rank_name, id=rank_name)
            desc = utils.get_info(rank)

            embed = discord.Embed(color=FACTION_COLORS[desc.fac]).set_author(
                name=f"⦿ {rank.name} - Info board")
            embed.description = f"```diff\n{desc.tips}\n```"

            embed.add_field(
                name="Attributes", value=f"Faction - {desc.fac}\n\n🛡️ : {rank.defense}\n⚔️ : {rank.attack}\n✊ : {rank.skill.__name__}")
            embed.add_field(
                name=f"📋 About {rank.name}", value=f"{desc.guide}\n\n{desc.guide_long}")
            embed.set_thumbnail(url=desc.image)

            await ctx.reply(embed=embed)
        else:
            ...

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

    @staticmethod
    def make_embed(player: Player):
        rank = player.rank
        info = utils.get_info(rank)
        name = player.member.display_name

        choosable_list = '\n\n'
        index = 0
        for other in player.game.all_participants.values():
            if other != player:
                choosable_list += f'{NUMBER_MAP[i]} {other.member.display_name}'
                index += 1

        embed = discord.Embed(colour=FACTION_COLORS[info.fac])
        embed.description = info.skill_message % name + choosable_list
        return embed

    async def make_player_channel(self, ctx: Context, game: Union[LAN_Game_Instance, WAN_Game_Instance], member: Member, load: bool):
        if ctx.guild.owner != member:
            overwrite = {member: PermissionOverwrite(read_messages=True, send_messages=True),
                         ctx.guild.default_role: PermissionOverwrite(read_messages=False),
                         ctx.guild.me: PermissionOverwrite(read_messages=True, send_messages=True)}
        else:
            overwrite = {ctx.guild.default_role: PermissionOverwrite(read_messages=False),
                         ctx.guild.me: PermissionOverwrite(read_messages=True, send_messages=True)}

        if not load:
            channel = await game.category.create_text_channel(
                self.preset['names']['member'] % member.display_name, overwrites=overwrite)
        else:
            channel = discord.utils.get(
                game.category.channels, name=self.preset['names']['member'] % member.display_name)

            # make a new channel if it can't be found
            if not channel:
                channel = await game.category.create_text_channel(
                    self.preset['names']['member'] % member.display_name, overwrites=overwrite)
            else:
                await channel.edit(overwrites=overwrite)

        player = game.get_player(member)
        await channel.send(
            f"You got the role {player.rank.name}.\n\n{utils.get_info(player).guide}")
        return channel

    async def start_local_lobby(self, ctx: Context, ranks: tuple, participants: List[Member], id: int, mode: Union[str('load'), str('start')], load_id: int = Optional[int]):
        await ctx.reply("Game is starting soon...")

        # Build player role
        role = discord.utils.get(
            ctx.guild.roles, name=self.preset['names']['role_name'])

        # Instantiate local game
        game = LAN_Game_Instance(
            ctx, participants, ranks, role, id)

        # Declares it as a class variable to handle skill commands separately
        self.games[ctx.guild.id] = game

        # Make a game role if it doesn't exist
        if not role:
            role = await ctx.guild.create_role(name=self.preset['names']['role_name'], colour=discord.Colour.random())

        # We allow everyone with the target role to see the channels
        # the bot itself and remove @everyone
        basic_overwrite = {role: PermissionOverwrite(read_messages=True),
                           ctx.guild.me: PermissionOverwrite(read_messages=True),
                           ctx.guild.default_role: PermissionOverwrite(read_messages=False)}

        if mode == "start":
            # create game category and inquiry channel
            game.category = await ctx.guild.create_category(
                random.choice(TOWNSHIPS), overwrites=basic_overwrite)

            game.inquiry_channel = await game.category.create_text_channel(
                self.preset['names']['inquiry'], overwrites=basic_overwrite)

            # Creating a channel for each member
            positions = {}
            for member in participants:
                channel = await self.make_player_channel(ctx, game, member, load=False)
                await member.add_roles(role)
                positions[member.id] = channel
        else:
            # try to find the category for the game to load
            game.category = discord.utils.get(ctx.guild.categories, id=load_id)
            if not game.category:
                await ctx.reply("Cannot find the category to load the game.")
                log.info(
                    f"Failed to find category in ({id}) game of author {ctx.author.name}#{ctx.author.discriminator} with category id {load_id}"
                )
                return

            for target in basic_overwrite.keys():
                await game.category.set_permissions(target, overwrite=basic_overwrite[target])

            # find the inquiry channel
            game.inquiry_channel = discord.utils.get(
                game.category.channels, name=self.preset['names']['inquiry'])
            # silently ignores failure to find an inquiry channel and proceeds to make a new one
            if not game.inquiry_channel:
                log.info(
                    f"Failed to find inquiry channel in ({id}) game of author {ctx.author.name}#{ctx.author.discriminator}."
                )
                game.inquiry_channel = await game.category.create_text_channel(
                    self.preset['names']['inquiry'], overwrites=basic_overwrite)

            player_channels = [
                ch for ch in game.category.channels if ch.name != self.preset['names']['inquiry']]

            positions = {}
            for member in participants:
                if self.preset['names']['member'] % member.display_name not in player_channels:
                    channel = await self.make_player_channel(ctx, game, member, load=True)
                    await member.add_roles(role)
                    positions[member.id] = channel

        # Provides the game class with channel intel
        game.assign_channels(positions)

        # Game loop starts
        while game.is_ongoing:
            game.day += 1
            await game.inquiry_channel.send(f"Day {game.day}\n Members = {' ,'.join(user.display_name for user in participants if game.get_player(user).alive)}")
            # await game.open_inquiry(10)
            await game.inquiry_channel.send("... the sun has set on us. Goodnight sleep tight.")
            if game.day == 1:
                skill_panel = await utils.announce(game, self.make_embed)
                game.info['skill_panel'] = skill_panel
            game.night += 1
            await asyncio.sleep(20)

    @commands.command(name="delall")
    @commands.is_owner()
    async def del_all_channels_from_category(self, ctx: Context, id: Greedy[int]):
        """IGNORE"""
        for i in id:
            category = discord.utils.get(ctx.guild.categories, id=int(i))
            for channel in category.channels:
                await channel.delete()
                await asyncio.sleep(1)
            await category.delete()


def setup(bot):
    print("[PRIORITY] Deception game is now loaded")
    bot.add_cog(Deception(bot))
