from discord.embeds import Embed
from discord.enums import ButtonStyle
from discord.ext.commands.context import Context
from discord.interactions import Interaction
from discord.member import Member
from bot.utils.hearsay import Hearsay
import bot.utils.shadchan as shadchan
from bot.utils.ui import BetterView, button
from discord.ext import commands


class YesNoUi(BetterView):
    def __init__(self, ctx):
        super().__init__(ctx)
        self.choice = False

    @button(label="Yes", emoji="🙇", style=ButtonStyle.green)
    async def yes(self, buttion, i):
        self.choice = True

    @button(label="No", emoji="✖️", style=ButtonStyle.red)
    async def no(self, buttion, i):
        self.choice = False


class SOSUi(BetterView):
    SPLIT = 0x1
    STEAL = 0x2

    def __init__(self, ctx):
        super().__init__(ctx)
        self.decision = None

    @button(label="Split", emoji="🍴", style=ButtonStyle.green)
    async def splits(self, button, i: Interaction):
        self.decision = self.SPLIT

    @button(label="Steal", emoji="💰", style=ButtonStyle.blurple)
    async def steals(self, button, i: Interaction):
        self.decision = self.STEAL


class SplitOrSteal(commands.Cog):
    sos_SID = "splitorsteal_SID_____"

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def start_splitorsteal(
        self, commander: Member, ctx: Context, match: shadchan.MatchInstance
    ):
        embed = Embed(color=0xFFD700)
        embed.set_author(name="SPLIT OR STEAL ➖ CONVINCE OR BETRAY")
        players = []

        @match.on_emit("register_player")
        async def register_player(player):
            players.append(
                await Hearsay.resolve_name(
                    player, "**[%name](https://google.com/)** %badges\n"
                )
            )

        await match.emit_wait_for("register_player", commander)

        embed.add_field(name="Game Details", value="".join(players))
        await ctx.send(embed=embed)
        rep = 0
        while rep <= 5:
            await match.enable_chat(self.bot, 60)
            view = YesNoUi(ctx)
            await ctx.send(
                embed=Embed(
                    description="*Would you like to continue this conversion for 60 more seconds?*",
                    color=0x2F3136,
                ),
                view=view,
            )
            await view.wait()
            await match.wait_other()
            cond = await match.conclude(view.choice, lambda a, b: a and b)
            if cond:
                await ctx.send(
                    embed=Embed(
                        description="*Both players chose to continue the conversation.*",
                        color=0x2F3136,
                    )
                )
                rep += 1
            else:
                await ctx.send(
                    embed=Embed(
                        description="*One or both of the players chose to stop the conversation here.*",
                        color=0x2F3136,
                    )
                )
                break
        view = SOSUi(ctx)
        embed = Embed(color=0x2F3136)
        await ctx.send(
            embed=Embed(description="*What do you do?*", color=0x2F3136), view=view
        )
        await view.wait()

        @match.on_emit("decision")
        def opponent_decision(other, decision):
            if other.id != commander.id:
                if decision == SOSUi.SPLIT and view.decision == SOSUi.SPLIT:
                    embed.description = "Good work, you both chose to split the prize."
                elif decision == SOSUi.SPLIT and view.decision == SOSUi.STEAL:
                    embed.description = "Your opponent chose split, leaving you with all the fetched prize!"
                elif decision == SOSUi.STEAL and view.decision == SOSUi.SPLIT:
                    embed.description = "RIP, you chose split and your opponent chose steal, resulting you with a large sum of 0 prize split."
                if decision == SOSUi.STEAL and view.decision == SOSUi.STEAL:
                    embed.description = "LOL both of you chose steal, resulting in no prize being distributed."

        await match.emit_wait_for("decision", commander, view.decision)
        await ctx.send(embed=embed)
        match.end()

    @commands.command(name="splitorsteal", aliases=("sos",))
    async def splitorsteal(self, ctx):
        p = shadchan.Pool.get(self.sos_SID)
        opts = shadchan.MatchOptions(
            shadchan.MatchModes.unknown,
            disabled_modes=[shadchan.MatchModes.singleplayer, shadchan.MatchModes.lan],
        )
        await p.lineup(
            ctx.author,
            ctx,
            self.bot.loop,
            lambda *args: self.bot.loop.create_task(self.start_splitorsteal(*args)),
            opts,
        )


def setup(bot):
    bot.add_cog(SplitOrSteal(bot))
