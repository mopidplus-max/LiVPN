import os
import mysql.connector
from aiogram import Bot, Dispatcher, types, executor

# Настройки БД (замени на свои данные)
DB_CONFIG = {
    'host': 'твой_хост',
    'user': 'твой_юзер',
    'password': 'твой_пароль',
    'database': 'твой_бд_нейм'
}

BOT_TOKEN = '8239393918:AAGGPBoBE3KBK3KPuwYaH72AE6vdgsXthA8'
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

def get_db():
    return mysql.connector.connect(**DB_CONFIG)

@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    args = message.get_args()
    db = get_db()
    cursor = db.cursor(dictionary=True)

    if args:  # Привязка через сайт
        cursor.execute("UPDATE users SET telegram_id = %s WHERE token = %s", (message.from_user.id, args))
        db.commit()
        await message.answer("✅ Аккаунт привязан! Теперь VPN на сайте разморожен.")
    else:
        cursor.execute("SELECT * FROM users WHERE telegram_id = %s", (message.from_user.id,))
        user = cursor.fetchone()
        if user:
            await message.answer(f"Привет, {user['username']}! 👋\nТвоя подписка до: {user['expiry_date']}\n\nЧтобы продлить, просто напиши количество дней.")
        else:
            await message.answer("❌ Аккаунт не привязан. Используйте кнопку на сайте LiVPN.")
    db.close()

@dp.message_handler()
async def prolong(message: types.Message):
    if message.text.isdigit():
        days = int(message.text)
        db = get_db()
        cursor = db.cursor()
        # Продлеваем от текущей даты или даты окончания
        cursor.execute("UPDATE users SET expiry_date = DATE_ADD(GREATEST(expiry_date, NOW()), INTERVAL %s DAY) WHERE telegram_id = %s", (days, message.from_user.id))
        db.commit()
        await message.answer(f"✅ Подписка продлена на {days} дн.!")
        db.close()

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
