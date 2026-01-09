import asyncio
import sys
import os
from aiogram import Bot, Dispatcher
from bot.handlers import router
from app.config import settings

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

async def main():
    bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())