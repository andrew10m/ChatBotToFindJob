import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN
from handlers import common_handlers #, employer_handlers, job_seeker_handlers, admin_handlers
from db.database import init_db

async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    )
    logger = logging.getLogger(__name__)
    logger.info("Starting bot...")

    await init_db() # Инициализация БД

    bot = Bot(token=BOT_TOKEN)
    storage = MemoryStorage() # В будущем можно заменить на Redis
    dp = Dispatcher(storage=storage)

    # Регистрация обработчиков
    dp.include_router(common_handlers.router)
    # dp.include_router(employer_handlers.router)
    # dp.include_router(job_seeker_handlers.router)
    # dp.include_router(admin_handlers.router)

    # Удаление старых вебхуков и запуск polling
    await bot.delete_webhook(drop_pending_updates=True)
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
