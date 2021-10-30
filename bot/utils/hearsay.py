from aiosqlite import connect as aiosqlite_connect


class Hearsay:
    db_path = "bot/assets/hearsay.db"
    tablename = "assets"
    """
    A module responsible of controlling tied user assets and cosmetics.
    Includes but is not limited to, echo names, tictactoe emojis, nicknames
    and so on."""

    @staticmethod
    async def resolve_name(user, format_=None):
        async with aiosqlite_connect(Hearsay.db_path) as db:
            query = f"SELECT nickname, badges FROM {Hearsay.tablename} WHERE user_id = {user.id}"
            async with db.execute(query) as cur:
                res = await cur.fetchone()
        if res is not None:
            nickname, badges = res
            badges = badges.replace(',', ' ', -1)
            if format_ is None:
                return f"*{nickname}* {badges}"
            else:
                return format_.replace("%name", nickname).replace("%badges", badges)
        else:
            return (f"{user.name}#{user.discriminator}" if format_ is None else
                    format_.replace("%name", f"{user.name}#{user.discriminator}").replace("%badges", ""))

    @staticmethod
    async def resolve_asset(user, asset_id):
        async with aiosqlite_connect(Hearsay.db_path) as db:
            async with db.execute(f"SELECT {asset_id} FROM {Hearsay.tablename} WHERE user_id = {user.id}") as cur:
                try:
                    return (await cur.fetchone())[0]
                except (IndexError, TypeError):
                    return None
