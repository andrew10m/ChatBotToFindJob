import aiosqlite
import logging
from config import DATABASE_URL

logger = logging.getLogger(__name__)

async def init_db():
    """Инициализирует базу данных, создавая таблицы, если они не существуют."""
    try:
        async with aiosqlite.connect(DATABASE_URL) as db:
            db.row_factory = aiosqlite.Row
            # Явно указываем кодировку utf-8 при чтении файла схемы
            with open('db/schema.sql', 'r', encoding='utf-8') as f:
                await db.executescript(f.read())
            await db.commit()
        logger.info("Database initialized successfully.")
    except aiosqlite.Error as e:
        logger.error(f"Database error during initialization: {e}") # Более общее сообщение
    except FileNotFoundError:
        logger.error("schema.sql not found. Make sure it's in the 'db' directory relative to where the script is run.")
    except Exception as e: # Ловим другие возможные исключения, включая проблемы с кодировкой при чтении
        logger.error(f"An unexpected error occurred during DB initialization: {e}")


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
    try:
        async with aiosqlite.connect(DATABASE_URL) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(query, params or ()) as cursor: # Используем курсор как контекстный менеджер
                if last_row_id:
                    await db.commit()
                    return cursor.lastrowid
                if fetch_one:
                    return await cursor.fetchone()
                if fetch_all:
                    return await cursor.fetchall()
                await db.commit()
                return True # Для INSERT/UPDATE/DELETE без fetch/last_row_id
    except aiosqlite.Error as e:
        logger.error(f"Database query execution error: {e} (Query: {query}, Params: {params})")
        return None
    except Exception as e:
        logger.error(f"An unexpected error during query execution: {e} (Query: {query}, Params: {params})")
        return None


if __name__ == '__main__':
    import asyncio
    asyncio.run(init_db())
