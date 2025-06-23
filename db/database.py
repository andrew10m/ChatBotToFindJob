import aiosqlite
import logging
from config import DATABASE_URL

logger = logging.getLogger(__name__)

async def init_db():
    """Инициализирует базу данных, создавая таблицы, если они не существуют."""
    try:
        # Используем aiosqlite.connect() напрямую как асинхронный контекстный менеджер
        async with aiosqlite.connect(DATABASE_URL) as db:
            db.row_factory = aiosqlite.Row # Устанавливаем row_factory здесь
            # Убедимся, что директория db существует относительно текущего рабочего каталога
            # или используем абсолютный путь к schema.sql если это необходимо.
            # Для простоты, предполагаем, что скрипт запускается из корня проекта.
            with open('db/schema.sql', 'r') as f:
                await db.executescript(f.read())
            await db.commit()
        logger.info("Database initialized successfully.")
    except aiosqlite.Error as e:
        logger.error(f"Database initialization error: {e}")
    except FileNotFoundError:
        logger.error("schema.sql not found. Make sure it's in the 'db' directory relative to where the script is run.")
    except Exception as e:
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
    # Используем aiosqlite.connect() напрямую как асинхронный контекстный менеджер
    async with aiosqlite.connect(DATABASE_URL) as db:
        db.row_factory = aiosqlite.Row # Устанавливаем row_factory здесь
        try:
            cursor = await db.execute(query, params or ())
            if last_row_id:
                # Для aiosqlite, commit нужен перед тем как lastrowid станет доступным для некоторых операций.
                await db.commit()
                result = cursor.lastrowid
                await cursor.close()
                return result
            if fetch_one:
                result = await cursor.fetchone()
                await cursor.close()
                return result
            if fetch_all:
                result = await cursor.fetchall()
                await cursor.close()
                return result
            # Для INSERT (без last_row_id), UPDATE, DELETE
            await db.commit()
            await cursor.close()
            # Для операций, не возвращающих данные и не last_row_id, можно вернуть True для индикации успеха
            return True
        except aiosqlite.Error as e:
            logger.error(f"Query execution error: {e} (Query: {query}, Params: {params})")
            # Можно пробросить ошибку дальше или вернуть None/False
            return None # или False, или raise e
        except Exception as e:
            logger.error(f"An unexpected error occurred during query execution: {e} (Query: {query}, Params: {params})")
            return None


if __name__ == '__main__':
    # Для ручной инициализации БД
    import asyncio
    asyncio.run(init_db())
