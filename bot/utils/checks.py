from discord.ext.commands.context import Context
from bot.constants import Defaults


def is_role_admin(ctx: Context):
    """
    Checks if the target author is a qualified admin
    by the basis of marked roles.
    """
    roles = [role.id for role in ctx.message.author.roles]
    chances = [(ID in roles) for ID in Defaults.ADMIN_ROLES]
    return any(chances)


def is_admin(ctx: Context):
    """
    Checks if the target author is a qualified admin
    by the basis of marked IDs
    """
    return ctx.author.id in Defaults.ADMINS
