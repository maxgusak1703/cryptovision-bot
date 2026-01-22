import asyncio
import sys
import os
from aiogram import Bot, Dispatcher
from bot.handlers import router
from app.config import settings
from bot.middlewares import DbSessionMiddleware

async def main():
    bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)
    dp.update.middleware(DbSessionMiddleware())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())