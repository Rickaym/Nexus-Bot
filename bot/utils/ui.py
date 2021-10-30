import asyncio

from asyncio.events import AbstractEventLoop
from discord.enums import ButtonStyle
from discord.interactions import Interaction
from discord.ui import *


class BetterView(View):
    """
    A subclass of view that is prepackaged with a check based on the context,
    and a one-time fade out implementation for buttons - the chosen button will
    remain in color whilst the rest will be grayed out. All the buttons are disabled
    after the first click.
    """

    def __init__(self, ctx, loop: AbstractEventLoop = None, timeout=600):
        super().__init__(timeout=timeout)
        self.ctx = ctx
        self.loop = loop or asyncio.get_running_loop()

    async def interaction_check(
        self, interaction: Interaction, edit_later=False
    ) -> bool:
        """
        Impose one-time fadeout presets if the interaction is valid.

        edit_later: If false will edit itself immediately, else it will not. This will save
                    a few requests if there is deemed to be an edit right after a valid interaction
                    is recieved.
        """
        if (
            interaction.channel.id != self.ctx.channel.id
            or interaction.user.id != self.ctx.author.id
        ):
            return False

        for i in self.children:
            i.disabled = True
            if i.custom_id != interaction.data["custom_id"]:
                i.style = ButtonStyle.gray
        if edit_later is False:
            self.loop.create_task(interaction.message.edit(view=self))
        self.stop()
        return True

    async def on_timeout(self) -> None:
        self.stop()
        raise TimeoutError(f"{self} timed out after {self.timeout}")
