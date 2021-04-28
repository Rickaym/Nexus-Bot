import discord
import asyncio
import random

from discord.ext import commands


class MM(commands.Cog):

    def __init__(self, client):
        self.client = client

    def botAdminCheck(ctx):
        return ctx.message.author.id == 368671236370464769

    # Guilds Checker
    @commands.command()
    @commands.guild_only()
    @commands.check(botAdminCheck)
    async def mmstart(self, ctx, members: commands.Greedy[discord.Member] = None):
        list_role = ['Murder', 'Detective']
        roles = {}
        killed_people = []
        guild = ctx.guild
        channel = ctx.channel
        color = 0xa05a4e

        f = open('cogs/mm/lives.txt', 'w')
        f.write("")
        f.close()
        # Refresh database
        f = open('cogs/mm/murder.txt', 'w')
        f.write("")
        f.close()
        # Refresh database
        f = open('cogs/mm/actions.txt', 'w')
        f.write("")
        f.close()

        meeting_cd = 10   # Meeting duration
        voting_cd = 10    # Voting wait time
        cooldown = 20

        for i in (0, (len(members)-2)):
            # appending bystanding roles with regards to the total number of participants
            list_role.append('Bystanders')
        bystanders = len(list_role)-2
        new = True
        for role in ctx.guild.roles:
            if role.name == 'Participant':         # making a participant roles for permission purposes
                participant = role
                new = False
        if new:
            participant = await guild.create_role(name='Participant', hoist=False)

        lobby_init = await ctx.send(embed=discord.Embed(title='__**# Lobby**__', description=f'> Starting in 3 seconds...\n> \n> **__Roles__**\n> Murder \n> Detective \n> By Standers', color=color))
        await asyncio.sleep(3)  # lOBBY COOL DOWN
        for member in members:
            role = random.choice(list_role)
            roles[member] = role
            count = 0
            await member.add_roles(participant)

            for i in list_role:
                if i == role:
                    list_role.pop(count)
                count += 1

            try:
                await lobby_init.edit(embed=discord.Embed(title='__**# Lobby**__', description=f'> {member.mention} Please reply ready.\n> \n> **__Roles__**\n> Murder : 1\n> Detective : 1\n> By Standers : {bystanders}', color=color))
# msg = await self.client.wait_for('message', check=lambda message : message.content.lower() == 'ready' and message.channel == channel and message.author == member, timeout = 30)
            except asyncio.TimeoutError:
                await lobby_init.edit(embed=discord.Embed(title='__**# Lobby**__', description=f'{member.mention} is inactive - Lobby failed to start.', color=discord.Color.dark_red()))
                return
        to_be_edited = await ctx.send('> Game is starting in `5` seconds....')
        await asyncio.sleep(5)
        await to_be_edited.delete()

        ids = 1  # 1 Chill pill center, 2 MIS

        if ids == 1:
            m_channel_id = 774215902433509386
            d_channel_id = 774215942048710687        # THE CHILL PILL CENTER
            meeting = 774215983610200064
        elif ids == 2:
            m_channel_id = 774201930892705822		# MIS
            d_channel_id = 774201944431656972
            meeting = 774201910852976640

        meeting_ch = ctx.guild.get_channel(meeting)
        m_channel = ctx.guild.get_channel(m_channel_id)
        d_channel = ctx.guild.get_channel(d_channel_id)
        await meeting_ch.purge(limit=200)
        await d_channel.purge(limit=200)
        await m_channel.purge(limit=200)

        # Disable everyones permissions to see any gaming channels
        await meeting_ch.set_permissions(ctx.guild.default_role, read_messages=False, send_messages=False)
        await d_channel.set_permissions(ctx.guild.default_role, read_messages=False, send_messages=False)
        await m_channel.set_permissions(ctx.guild.default_role, read_messages=False,  send_messages=False)

        ######## GAME STARTS ########

        await meeting_ch.send('> @everyone Meeting starts in 10 seconds!')
        await meeting_ch.set_permissions(participant, read_messages=True, send_messages=False)
        f = open('cogs/mm/lives.txt', 'a')
        for member in members:
            if roles[member] == 'Murder':
                murder = member
                await m_channel.set_permissions(murder, read_messages=True, send_messages=False)
                b = open('cogs/mm/murder.txt', 'w')
                b.write(f'{member.id}')
                b.close()
                f.write(f'{member.id}\n')

            elif roles[member] == 'Detective':
                detective = member
                await d_channel.set_permissions(detective, read_messages=True, send_messages=False)
                f = open('cogs/mm/lives.txt', 'a')
                f.write(f'{member.id}\n')
            elif roles[member] == 'Bystanders':
                f = open('cogs/mm/lives.txt', 'a')
                f.write(f'{member.id}\n')
        f.close()

        await m_channel.send(embed=discord.Embed(description=f'{murder.mention} you have been chosen as the murder!, you will have a choice to kill someone every night!', color=0x800000))
        await d_channel.send(embed=discord.Embed(description=f'{detective.mention} you have been chosen as the detective!, you will have a choice to inspect someone every night!', color=0x6050dc))

        ######## Identify certain bystanders for the detective ########

        embed = discord.Embed(
            title='Bystanders', description="Detective, we have identified some bystanders for you, we really hope it helps!", color=0x6050dc)
        count = 0
        for member in members:
            if count != random.randint(0, 3):
                if roles[member] == 'Bystanders':
                    embed.add_field(
                        name=f'{member.display_name}', value='is a confirmed bystander!')
            else:
                pass
            count += 1
        await d_channel.send(embed=embed)

        ####### First ever setup meeting starts #######

        # 10 sec before meeting begins
        await asyncio.sleep(10)
        f = open('cogs/mm/lives.txt', 'r')
        alive_list = f.read().split('\n')							# Retrieve member data
        f.close()
        alive_list = [int(i) for i in alive_list if i != ""]
        initial_list = alive_list.copy()

        # Filter out murder from the member data set
        without_mrd = [int(i) for i in alive_list if int(i) != int(murder.id)]
        text = await meeting_ch.send(embed=discord.Embed(description='> Meeting has started! Introduce yourselves! You all have 50 seconds to talk. Prove your innocence.\n@everyone', color=color))
        await meeting_ch.set_permissions(participant, read_messages=True, send_messages=True)
        # 50 sec meeting cool down
        await asyncio.sleep(meeting_cd)
        await meeting_ch.send(embed=discord.Embed(description='Meeting has ended.', color=color))
        await meeting_ch.set_permissions(participant, read_messages=True, send_messages=False)
        await d_channel.set_permissions(detective, read_messages=True, send_messages=True)
        await m_channel.set_permissions(murder, read_messages=True, send_messages=True)
        f = open('cogs/mm/murder.txt', 'r')
        f_murder = f.read().split('\n')							# Retrieve member data
        f.close()
        f_murder = [int(i) for i in f_murder if i != ""]
        murder = f_murder[0]
        list2 = alive_list.copy()
        while (len(without_mrd)) > 1:
            await asyncio.sleep(cooldown)
            f = open('cogs/mm/actions.txt', 'r')
            actions = f.read().split('~')
            actions = [i for i in actions if i != ""]
            f.close()
            killed = [i for i in actions if (list(i)[0]) == 'K']
            if killed:
                victim = ctx.guild.get_member(int(killed[0][1:]))
                await meeting_ch.send(f'{victim.mention} got killed last night!')
                await meeting_ch.set_permissions(victim, read_messages=True, send_messages=False)
                await victim.remove_roles(participant)
                alive_list = [i for i in actions if i != int(killed[0][1:])]
                killed_people.append(victim)

            if not len(f_murder) > 0:
                await meeting_ch.send(embed=discord.Embed(description='Hip Hip Hooray! The murder is gone for good.', color=color))
                break

            if len(list2) <= 2:
                await meeting_ch.send(f'{ctx.author.mention} <@{murder}> the town murder has killed enough bystanders and won! ')
                break

            murder = ctx.guild.get_member(murder)
            await meeting_ch.set_permissions(participant, read_messages=True, send_messages=False)
            await d_channel.set_permissions(detective, read_messages=True, send_messages=False)
            await m_channel.set_permissions(murder, read_messages=True, send_messages=False)

            f = open('cogs/mm/lives.txt', 'r')
            alive_list = f.read().split('\n')
            f.close()
            alive_list = [int(i) for i in alive_list if i != ""]
#			list2 = alive_list.copy()
            await asyncio.sleep(9)
#			refined_set = set(initial_list) - set(list2)
#			if len(list(refined_set)) > 0:
#				initial_list = [i for i in list(initial_list) if i != list(refined_set)[0]]         # Restart the main member volume
#				for i in range(0,len(list(refined_set))):
#					await meeting_ch.send(f'<@{list(refined_set)[i]}> got killed last night.')
#			else:
#				pass

            text = await meeting_ch.send(embed=discord.Embed(description='Meeting has started! Introduce yourselves! You all have 50 seconds to talk. Prove your innocence.\n@everyone', color=color))
            await meeting_ch.set_permissions(participant, read_messages=True, send_messages=True)
            await asyncio.sleep(meeting_cd)

            ############### VOTING ###############

            embed = discord.Embed(
                title="Vote out the most suspicious person (Needs majority to get voted out)(If you wish to skip, avoid voting anyone)!", color=color)
            emojis = ['\u0031\ufe0f\u20e3', '\u0032\ufe0f\u20e3', '\u0033\ufe0f\u20e3', '\u0034\ufe0f\u20e3',
                      '\u0035\ufe0f\u20e3', '\u0036\ufe0f\u20e3', '\u0037\ufe0f\u20e3', '\u0038\ufe0f\u20e3', '\u0039\ufe0f\u20e3', '🔟']

            count = 0
            for member in list2:
                # Makes a votable embed list with every member
                embed.add_field(
                    name=f'\u200b', value=f'{emojis[count]} <@{member}>')
                count += 1

            message = await meeting_ch.send(embed=embed)
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
                c            final = await meeting_ch.fetch_message(message.id)
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
                await meeting_ch.send('No one has voted! ')

            ############################################ VOTING ############################################
            color = 0x6050dc
            embed = discord.Embed(
                title="Vote out the most suspicious person (Needs majority to get voted out)(If you wish to skip, avoid voting anyone)!", color=color)
            emojis = ['\u0031\ufe0f\u20e3', '\u0032\ufe0f\u20e3', '\u0033\ufe0f\u20e3', '\u0034\ufe0f\u20e3',
                      '\u0035\ufe0f\u20e3', '\u0036\ufe0f\u20e3', '\u0037\ufe0f\u20e3', '\u0038\ufe0f\u20e3', '\u0039\ufe0f\u20e3', '🔟']
            list2 = []
            count = 0
            for member in list2:
                # Makes a votable embed list with every member
                embed.add_field(
                    name=f'\u200b', value=f'{emojis[count]} <@{member}>')
                count += 1

            message = await meeting_ch.send(embed=embed)
            for i in range(0, len(list2)):
                # Adds reactions to the embed with regards to the all members alive
                await message.add_reaction(f'{emojis[i]}')
            await asyncio.sleep(10)

            final = await meeting_ch.fetch_message(message.id)
            # Fetch aftervoting results
            reactions = final.reactions
            highest = 0

            tie = False
            for reaction in reactions:
                if (counter := int(reaction.count)) > highest:
                    voted_emoji = reaction.emoji
                    highest = counter
                elif (counter := int(reaction.count)) == highest:                     # Checks the votes
                    tie = True
            if highest <= 1:
                tie = False

            index = 0
            for emoji in emojis:
                if emoji == voted_emoji:                 # Gets the position of the highly voted emoji to retrieve the member
                    break
                index += 1

            low = False
            if not tie and highest > 1:        # If the majority votes one highest person
                # The selected person
                await meeting_ch.send(f'<@{list2[index]}> has the majority vote!')
                on_alive_list = list2.copy()

                c = 0
                for i in on_alive_list:                 # Makes a new list and removes the id of the person who got voted out
                    if i == list2[index]:
                        on_alive_list.pop(c)
                    c += 1

                f = open('cogs/mm/lives.txt', 'w')
                for i in on_alive_list:
                    f.write(f'{i}\n')
                f.close()
            elif tie and not low:
                await meeting_ch.send('There has been a tie!')
            elif highest == 1:
                await meeting_ch.send('No one has voted!')
            else:
                await meeting_ch.send('There were no votes or are way too low!')
                low = True

            ########################################

            await meeting_ch.send(embed=discord.Embed(description='Meeting has ended.', color=color))
            await meeting_ch.set_permissions(participant, read_messages=True, send_messages=False)
            await d_channel.set_permissions(detective, read_messages=True, send_messages=True)
            await m_channel.set_permissions(murder, read_messages=True, send_messages=True)
            without_mrd = [int(i) for i in alive_list if int(i) != int(murder)]
        for member in members:
            await member.remove_roles(participant)
        for member in killed_people:
            await meeting_ch.set_permissions(member, read_messages=False, send_messages=False)

    @commands.command()
    @commands.cooldown(rate=1, per=10)
    @commands.guild_only()
    async def kill(self, ctx):
        ids = 1  # 1 Chill pill center, 2 MIS

        if ids == 1:
            m_channel_id = 774215902433509386
            d_channel_id = 774215942048710687        # THE CHILL PILL CENTER
            meeting = 774215983610200064
        elif ids == 2:
            m_channel_id = 774201930892705822		# MIS
            d_channel_id = 774201944431656972
            meeting = 774201910852976640

        meeting_ch = ctx.guild.get_channel(meeting)
        color = 0x800000

        if ctx.channel.id == m_channel_id:
            f = open('cogs/mm/murder.txt', 'r')
            murder = f.read().split('\n')
            f.close()
            f = open('cogs/mm/lives.txt', 'r')
            alive_list = f.read().split('\n')
            f.close()
            alive_list = [i for i in alive_list if i != "" and murder[0]]
            embed = discord.Embed(
                title=f"POPULATION - {len(alive_list)}", color=color)
            count = 1
            for i in alive_list:
                embed.add_field(
                    name=f'\u200b', value=f'**{count}** <@{i}>', inline=False)
                count += 1
            embed.set_footer(
                text='Please reply with the index of the person to kill!')
            try:
                text = await ctx.send(embed=embed)
                msg = await self.client.wait_for('message', check=lambda message: message.channel.id == m_channel_id and message.author == ctx.author, timeout=30)
            except asyncio.TimeoutError:
                await ctx.send('Kill timed out')
            else:
                index = int(msg.content) - 1
                await text.edit(embed=discord.Embed(description=f'Killed <@{alive_list[index]}>!', color=color))
                f = open('cogs/mm/actions.txt', 'w')
                f.write(f'~K{alive_list[index]}~')
                f.close()

    @kill.error
    async def kill_erorr_handler(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send("Kill is on cooldown!")

    @commands.command()
    @commands.cooldown(rate=1, per=10)
    @commands.guild_only()
    async def inspect(self, ctx):
        ids = 1  # 1 Chill pill center, 2 MIS
        if ids == 1:
            m_channel_id = 774215902433509386
            d_channel_id = 774215942048710687        # THE CHILL PILL CENTER
            meeting = 774215983610200064
        elif ids == 2:
            m_channel_id = 774201930892705822		# MIS
            d_channel_id = 774201944431656972
            meeting = 774201910852976640

#		if ctx.channel.id == d_channel_id:
#			color = 0x6050dc
#			f = open('cogs/mm/lives.txt', 'r')
#			alive_list = f.read().split('\n')
#			f.close()
#			alive_list = [int(i) for i in alive_list if i != ""]
#
#			f = open('cogs/mm/murder.txt', 'r')
#			murder = f.read()
#			f.close()
#
#			embed = discord.Embed(title=f"POPULATION - {len(alive_list)}", color = color)
#			count = 1
#			for i in alive_list:
#				embed.add_field(name = f'\u200b', value =f'**{count}** <@{i}>', inline = False)
#				count += 1
#			embed.set_footer(text='Please reply with the index of the person you would like to interrogate!')
#			try:
#				await ctx.send(embed=embed)
#				msg = await self.client.wait_for('message', check=lambda message : message.channel.id == d_channel_id , timeout =60)
#			except asyncio.TimeoutError:
#				await ctx.send('Inspect timed out')
#			else:
#				index = int(msg.content) - 1
#				choice = random.randint(0,5)
#				if choice > 3:
#					if alive_list[index] == murder:
#						await ctx.send(embed = discord.Embed(title="RESULTS", color = color, description=f"<@{alive_list[index]}> is highly suspicious, better watch out for them."))
#					else:
#						await ctx.send(embed = discord.Embed(title="RESULTS", color = color, description= f"<@{alive_list[index]}> is clear you can trust in them!"))
#				elif choice <= 3:
#					await ctx.send(embed=discord.Embed(title="RESULTS", color = color,description= f"<@{alive_list[index]}> is unclear, you may inspect this person tomorrow again!"))

    @inspect.error
    async def inspect_erorr_handler(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            for role in ctx.guild.roles:
                if role.name == 'Participant':
                    participant = role
            await ctx.send("Inspection is on cooldown!")

    @commands.command()
    async def voting(self, ctx, members: commands.Greedy[discord.Member] = None):
        m_channel_id = ctx.channel.id
        color = 0x800000
        if ctx.channel.id == m_channel_id:
            f = open('cogs/mm/murder.txt', 'r')
            murder = f.read().split('\n')
            f.close()
            murder = [i for i in murder if i != ""]
            f = open('cogs/mm/lives.txt', 'r')
            alive_list = f.read().split('\n')
            f.close()
            alive_list = [i for i in alive_list if i != "" and murder[0]]
            embed = discord.Embed(
                title=f"POPULATION - {len(alive_list)}", color=color)
            count = 1
            for i in alive_list:
                embed.add_field(
                    name=f'\u200b', value=f'**{count}** <@{i}>', inline=False)
                count += 1
            embed.set_footer(
                text='Please reply with the index of the person to kill!')
            try:
                text = await ctx.send(embed=embed)
                msg = await self.client.wait_for('message', check=lambda message: message.channel.id == m_channel_id and message.author == ctx.author, timeout=30)
            except asyncio.TimeoutError:
                await ctx.send('Kill timed out')
            else:
                index = int(msg.content) - 1
                await text.edit(embed=discord.Embed(description=f'Killed <@{alive_list[index]}>!', color=color))
                f = open('cogs/mm/actions.txt', 'w')
                f.write(f'~K{alive_list[index]}~')
                f.close()


def setup(client):
    client.add_cog(MM(client))
    print('MM.cog is loaded')
