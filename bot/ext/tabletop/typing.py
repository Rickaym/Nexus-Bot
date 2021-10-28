import bot.utils.shadchan as shadchan
from io import BytesIO
from textwrap import wrap
from typing import Tuple
from discord import File
from discord.ext import commands
from discord.colour import Color
from os import listdir
from time import time
from random import choice
from asyncio import sleep as asyncio_sleep
from discord.embeds import Embed
from random import randint

from PIL import Image, ImageDraw, ImageFont
from difflib import SequenceMatcher
from string import printable


class Typing(commands.Cog):
    """
    Typing related games for single and multiplayer modes.
    """
    race_SID = "race_SID_____"
    tips = ["Always start with the correct finger position on based on your keyboard configuration."]

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

        self.lines = None
        self.font = None
        self.bot.loop.create_task(self.init())

    async def init(self):
        with open("bot/assets/lord-of-the-rings.txt", "r", encoding="utf-8") as f:
            self.lines = [ln for ln in f.readlines() if all([c in printable for c in ln])]
        self.font = ImageFont.truetype("arial.ttf", 28)

    def extract(self, max_chars=160):
        start_idx = randint(0, len(self.lines))
        excerpt = ""
        i = 0
        while True:
            excerpt += self.lines[start_idx+i]
            if len(excerpt) >= max_chars:
                break
            else:
                i += 1
        if len(excerpt) > max_chars+100:
            _tmp = excerpt
            excerpt = ""
            for wrd in _tmp.split(' '):
                excerpt += f"{wrd} "
                if len(excerpt) > max_chars:
                    break
        return excerpt.strip()

    @commands.group(name="typing", aliases=("type",), invoke_without_command=True)
    async def typing(self, ctx):
        """IGNORE"""
        pass

    def get_text_image(self, text) -> BytesIO:
        buf = BytesIO()
        h = self.font.getsize(text)[1]
        text = wrap(text, width=25)
        w = max([self.font.getsize(ln)[0] for ln in text])
        with Image.new("RGBA", (w, h*len(text)), (0, 0, 0, 0)) as img:
            draw = ImageDraw.Draw(img)
            draw.text((0, 0), '\n'.join(text), fill=(255, 255, 255, 255), font=self.font)
            img.save(buf, format="PNG")
        buf.seek(0)
        return buf

    def get_badge(self, won, score):
        victory_badges = {'☁️':"2601", '🌥️':"1f325", '🌦️': "1f326", '🌤️': "1f324", "🌈": "1f308"}
        defeat_badges = {'💩': "1f4a9", '🌧️': "1f327", '🌨️': "1f328", '🌩️': "1f329"}
        model_score = 645

        if won:
            use = tuple(victory_badges.values())
        else:
            use = tuple(defeat_badges.values())

        idx = round(score * (len(use)/model_score))
        if idx >= len(use):
            idx = -1
        elif idx < 0:
            idx = 0

        return f"https://raw.githubusercontent.com/twitter/twemoji/master/assets/72x72/{use[idx]}.png"

    def get_performance(self, score, type):
        """
        Returns a + or a - for determining whether if the given score is performant.
        """
        if type == "wpm":
            return '+' if score > 70 else '-'
        elif type == "acc":
            return '+' if score > 90 else '-'
        elif type == "pts":
            return '+' if score > 450 else '-'
        else:
            return '-'

    async def start_race(self, commander, ctx, match: shadchan.MatchInstance):
        text = await match.generalize(self.extract())
        color = Color.random()
        embed = Embed(description="Match begins in 3 seconds.", color=color)
        embed.set_footer(text=f"• Tip - {choice(self.tips)}")
        embed.set_author(name="TYPING RACE ➖ ONGOING")
        m = await ctx.channel.send(embed=embed)

        embed.description = "God Speed."
        embed.set_image(url="attachment://text.png")
        embed.set_thumbnail(url="https://raw.githubusercontent.com/twitter/twemoji/master/assets/72x72/2328.png")
        embed.add_field(name="Progress", value="You: <a:loadin_color:902978712503472211>")
        if match.options.mode != shadchan.MatchModes.singleplayer:
            embed.add_field(name="\u200b", value=f"Opponent: <a:loadin_color:902978712503472211>")
        await asyncio_sleep(3)
        await m.delete()
        await match.wait_other()
        m = await ctx.channel.send(file=File(self.get_text_image(text), filename="text.png"), embed=embed)

        @match.on_emit("player_done")
        async def update_finished(player):
            if commander.id == player.id:
                embed.set_field_at(0, name=embed.fields[0].name, value="You: <a:done:903006503538143323>")
            else:
                embed.set_field_at(1, name=embed.fields[1].name, value="Opponent: <a:done:903006503538143323>")
            await m.edit(embed=embed)

        st = time()
        delayed, other = await match.conclude_with_answer(st, by=lambda a, b: a > b)
        msg = await self.bot.wait_for("message", check=lambda m: m.author.id == commander.id and m.channel.id == ctx.channel.id)
        taken = time()-st
        if delayed:
            margin = st-other
            taken -= margin
        match.emit("player_done", commander)
        await match.wait_other()

        wpm = round((len(msg.content)/5) / (taken/60))
        acc = round(SequenceMatcher(None, text, msg.content).ratio(), 2)
        score = 5*wpm+45*acc
        percent_acc = round(acc*100, 1)
        res = await match.conclude(score, by=lambda a, b: a > b)

        scoreboard = Embed(color=color)
        scoreboard.add_field(name="Scoreboard", value="\u200b")
        scoreboard.add_field(name="\u200b", value="\u200b")

        @match.on_emit("post_performance")
        def post_performance(player, wpm, taken, percent_acc, score):
            if player.id == commander.id:
                display = "Your"
            else:
                display = "Opponent"
            idx = 0 if display == "Your" else 1
            scoreboard.set_field_at(idx,
                                name=scoreboard.fields[idx].name,
                                value=(f"**[{display} Performance](https://google.com)**\n```diff\n+ 🕐 {round(taken)} seconds"
                                    f"\n{self.get_performance(wpm, 'wpm')} 👌 {wpm} words per minute"
                                    f"\n{self.get_performance(percent_acc, 'acc')} 📏 {percent_acc}% accuracy"
                                    f"\n{self.get_performance(score, 'pts')} 🧊 {score} pts```"),
                                inline=scoreboard.fields[idx].inline)
        await match.wait_other()
        await match.emit_wait_for("post_performance", commander, wpm, taken, percent_acc, score)
        scoreboard.set_author(name=f"TYPING RACE ➖ {'VICTORY' if res else 'DEFEAT'}!")
        scoreboard.set_thumbnail(url=self.get_badge(res, score))
        scoreboard.set_footer(text=f"You scored {5*wpm}pts for speed and {round(45*acc)} pts for accuracy.")
        await ctx.send(embed=scoreboard)
        await match.enable_chat(self.bot, 30)
        match.end()

    @typing.command(name="race")
    async def typing_race(self, ctx):
        """
        Starts a multiplayer speed typing race against a global opponent.
        """
        p = shadchan.Pool.get(self.race_SID)
        match = await p.lineup(ctx.author, ctx, self.bot.loop, lambda *args: self.bot.loop.create_task(self.start_race(*args)), shadchan.MatchModes.unknown)

def setup(bot):
    bot.add_cog(Typing(bot))