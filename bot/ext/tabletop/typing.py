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
from bot.utils.shadchan import MatchInstance, Pool
from string import printable

printable += "‘’“”,"

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
        self.font = ImageFont.truetype("arial.ttf", 32)

    def extract(self, max_chars=100):
        start_idx = randint(0, len(self.lines))
        excerpt = ""
        i = 0
        while True:
            excerpt += self.lines[start_idx+i]
            if len(excerpt) >= max_chars:
                break
            else:
                i += 1
        return excerpt.strip()

    @commands.group(name="typing", aliases=("type",), invoke_without_command=True)
    async def typing(self, ctx):
        """IGNORE"""
        pass

    def get_text_image(self, text) -> BytesIO:
        buf = BytesIO()
        h = self.font.getsize(text)[1]
        text = wrap(text, width=40)
        w = max([self.font.getsize(ln)[0] for ln in text])
        with Image.new("RGBA", (w, h*len(text)), (0, 0, 0, 0)) as img:
            draw = ImageDraw.Draw(img)
            draw.text((0, 0), '\n'.join(text), fill=(255, 255, 255, 255), font=self.font)
            img.save(buf, format="PNG")
        buf.seek(0)
        return buf

    async def start_race(self, commander, ctx, match: MatchInstance):
        text = await match.generalize(self.extract())

        embed = Embed(title="TYPING RACE", description="Match begins in 3 seconds.", color=Color.random())
        embed.set_footer(text=f"• Tip - {choice(self.tips)}")
        m = await ctx.channel.send(embed=embed)
        embed.set_image(url="attachment://text.png")
        embed.description = "God Speed."
        embed.add_field(name="\u200b", value="You: <a:loadin_color:902978712503472211>")
        embed.set_thumbnail(url="https://raw.githubusercontent.com/twitter/twemoji/master/assets/72x72/2328.png")
        embed.add_field(name="\u200b", value="Opponent: <a:loadin_color:902978712503472211>")
        await asyncio_sleep(3)
        await m.delete()
        await match.wait_other()
        m = await ctx.channel.send(file=File(self.get_text_image(text), filename="text.png"), embed=embed)

        async def update_finished(player):
            if commander.id == player.id:
                embed.set_field_at(0, name="\u200b", value="You: <a:done:903006503538143323>")
            else:
                embed.set_field_at(1, name="\u200b", value="Opponent: <a:done:903006503538143323>")
            await m.edit(embed=embed)

        match.on_emit("player_done", update_finished)
        st = time()
        delayed, other = await match.conclude_with_answer(st, by=lambda a, b: a > b)
        msg = await self.bot.wait_for("message", check=lambda m: m.author.id == commander.id and m.channel.id == ctx.channel.id)
        ft = time()-st
        if delayed:
            margin = st-other
            ft -= margin
        await ctx.send(f"You finished in {round(ft, 5)} {f'with a delay of {margin}!' if delayed else ''}")
        await match.emit("player_done", commander)
        await match.wait_other()

        res = await match.conclude(ft, by=lambda a, b: a < b)
        await ctx.send(f"You {'won' if res else 'lost'}...")
        await match.enable_chat(self.bot, 30)
        match.end()
        print(round(SequenceMatcher(None, text, msg.content).ratio(), 2))

    @typing.command(name="race")
    async def typing_race(self, ctx):
        """
        Starts a multiplayer speed typing race against a global opponent.
        """
        p = Pool.get(self.race_SID)
        ins = p.lineup(ctx.author, ctx, self.bot.loop, lambda *args: self.bot.loop.create_task(self.start_race(*args)))
        ins.register_signal("player_done")
        await ctx.reply("!")

def setup(bot):
    bot.add_cog(Typing(bot))