import aiosqlite
import logging
from config import DATABASE_URL

logger = logging.getLogger(__name__)

async def get_db_connection():
    """Устанавливает соединение с базой данных SQLite."""
    try:
        conn = await aiosqlite.connect(DATABASE_URL)
        conn.row_factory = aiosqlite.Row # Для доступа к столбцам по именам
        return conn
    except aiosqlite.Error as e:
        logger.error(f"Database connection error: {e}")
        raise

async def init_db():
    """Инициализирует базу данных, создавая таблицы, если они не существуют."""
    try:
        async with await get_db_connection() as db:
            with open('db/schema.sql', 'r') as f:
                await db.executescript(f.read())
            await db.commit()
        logger.info("Database initialized successfully.")
    except aiosqlite.Error as e:
        logger.error(f"Database initialization error: {e}")
    except FileNotFoundError:
        logger.error("schema.sql not found. Make sure it's in the 'db' directory.")

async def execute_query(query: str, params: tuple = None, fetch_one: bool = False, fetch_all: bool = False, last_row_id: bool = False):
    """
    Выполняет SQL-запрос.

    :param query: SQL-запрос.
    :param params: Кортеж параметров для запроса.
    :param fetch_one: Вернуть одну запись.
    :param fetch_all: Вернуть все записи.
    :param last_row_id: Вернуть ID последней вставленной строки.
    :return: Результат запроса или ID последней строки.
    """
    async with await get_db_connection() as db:
        try:
            cursor = await db.execute(query, params or ())
            if last_row_id:
                await db.commit()
                return cursor.lastrowid
            if fetch_one:
                result = await cursor.fetchone()
                await cursor.close()
                return result
            if fetch_all:
                result = await cursor.fetchall()
                await cursor.close()
                return result
            await db.commit()
            await cursor.close()
        except aiosqlite.Error as e:
            logger.error(f"Query execution error: {e} (Query: {query}, Params: {params})")
            # В некоторых случаях можно пробрасывать ошибку дальше или возвращать None/False
            # в зависимости от логики приложения
            return None # или raise e

# Примеры использования (будут расширены в queries.py)
# async def add_user(user_id: int, role: str, username: str = None, contact_info: str = None):
#     query = "INSERT INTO users (user_id, role, username, contact_info) VALUES (?, ?, ?, ?)"
#     await execute_query(query, (user_id, role, username, contact_info))

# async def get_user(user_id: int):
#     query = "SELECT * FROM users WHERE user_id = ?"
#     return await execute_query(query, (user_id,), fetch_one=True)

if __name__ == '__main__':
    # Для ручной инициализации БД
    import asyncio
    asyncio.run(init_db())
