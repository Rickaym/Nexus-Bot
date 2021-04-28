import aiosqlite

from bot.constants import Defaults


class DB:
    def __init__(self) -> None:
        self.base_prefix = Defaults.PREFIX

    async def __aenter__(self) -> None:
        self.db = await aiosqlite.connect("bot/ext/pictionary/src/player_data.db")
        return self

    async def __aexit__(self, type, value, traceback) -> bool:
        await self.db.commit()
        await self.db.close()
        if traceback is not None:
            print(f"{type}, {value}, {traceback}")
        else:
            return True

    async def update_value(self, table, scoreboard):
        if not scoreboard:
            return
        query = f"SELECT userID, score FROM {table}"
        async with self.db.execute(query) as cursor:
            # ((userID, score), (userID, score))
            latest_scoreboard = await cursor.fetchall()
        for user_id in scoreboard.keys():
            if user_id in [record[0] for record in latest_scoreboard]:
                query = f"UPDATE {table} SET score = score + {scoreboard[user_id]} WHERE userID = {user_id}"
                await self.db.execute(query)
            else:
                query = f"INSERT INTO {table}(userID, score) VALUES(?, ?)"
                val = (user_id, scoreboard[user_id])
                await self.db.execute(query, val)

    async def truncate(self, table):
        query = f"DELETE FROM {table};"
        await self.db.execute(query)

    async def delete_value(self, table, param):
        userID = [*dict][0]
        query = f"DELETE FROM {table} WHERE userID = ?"
        await self.db.execute(query, param)

    async def get_value(self, table):
        query = f"SELECT userID, score FROM {table}"
        async with self.db.execute(query) as cursor:
            return await cursor.fetchall()
