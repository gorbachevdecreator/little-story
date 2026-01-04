import asyncio
import os
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from dotenv import load_dotenv

# 1. Загружаем переменные из файла .env
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

# Проверка, что токен есть
if not TOKEN:
    print("ОШИБКА: Токен не найден! Проверь файл .env")
    exit()

# 2. Настройка логирования (чтобы видеть ошибки в консоли)
logging.basicConfig(level=logging.INFO)

# 3. Создаем объекты бота и диспетчера
bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- ОБРАБОТЧИКИ СОБЫТИЙ (HANDLERS) ---

# Реакция на команду /start
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_name = message.from_user.first_name
    
    # Текст приветствия
    text = (
        f"Привет, {user_name}! 👋\n\n"
        "Я — бот проекта Little Story.\n"
        "Скоро здесь появится кнопка для запуска визуальных новелл."
    )
    
    # Отправляем ответ
    await message.answer(text)

# --- ЗАПУСК БОТА ---
async def main():
    print("Бот запущен и готов к работе...")
    # Удаляем вебхуки (на всякий случай, если они были) и запускаем опрос
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот остановлен.")