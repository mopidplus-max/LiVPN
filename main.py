import mysql.connector
import secrets
from aiogram import Bot, Dispatcher, types, executor
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# Данные подключения
DB_CONFIG = {
    'host': 'server145.cpcontroller.top',
    'user': 'Livpnweb_Dplusmop',
    'password': '32156416Dana',
    'database': 'livpnweb_db'
}

TOKEN = '8239393918:AAGGPBoBE3KBK3KPuwYaH72AE6vdgsXthA8'
ADMIN_ID = 5017549785 
bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

def get_db():
    return mysql.connector.connect(**DB_CONFIG)

def main_menu(user_id):
    kbd = InlineKeyboardMarkup(row_width=1)
    kbd.add(
        InlineKeyboardButton("🔄 Сменить ссылку (токен)", callback_data="reset_token"),
        InlineKeyboardButton("❓ Поддержка", url="https://t.me/LiVPN_Support")
    )
    if user_id == ADMIN_ID:
        kbd.add(InlineKeyboardButton("⚙️ АДМИН-ПАНЕЛЬ", callback_data="admin_panel"))
    return kbd

@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    args = message.get_args()
    db = get_db()
    cursor = db.cursor(dictionary=True)
    if args:
        cursor.execute("UPDATE users SET telegram_id = %s WHERE token = %s", (message.from_user.id, args))
        db.commit()
        await message.answer("✅ Аккаунт привязан! VPN разморожен.", reply_markup=main_menu(message.from_user.id))
    else:
        cursor.execute("SELECT * FROM users WHERE telegram_id = %s", (message.from_user.id,))
        u = cursor.fetchone()
        if u:
            await message.answer(f"Привет, {u['username']}! 👋", reply_markup=main_menu(message.from_user.id))
        else:
            await message.answer("❌ Аккаунт не привязан. Получите ссылку на сайте.")
    db.close()

@dp.callback_query_handler(lambda c: c.data == "admin_panel")
async def admin_info(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID: return
    text = (
        "📊 **Управление LiVPN**\n\n"
        "🔹 **Чтобы добавить ключ:**\n"
        "Пришли сообщение в формате:\n"
        "`Название | vless://ссылка`\n\n"
        "🔹 **Чтобы продлить юзера:**\n"
        "Просто напиши число дней."
    )
    await callback.message.answer(text, parse_mode="Markdown")
    await callback.answer()

@dp.message_handler()
async def handle_messages(message: types.Message):
    db = get_db()
    cursor = db.cursor()

    # 1. Логика добавления VLESS ключей (только для админа)
    if message.from_user.id == ADMIN_ID and "|" in message.text and "vless://" in message.text:
        try:
            name, content = message.text.split("|", 1)
            cursor.execute("INSERT INTO vless_configs (name, content) VALUES (%s, %s)", (name.strip(), content.strip()))
            db.commit()
            await message.answer(f"✅ Ключ **{name.strip()}** успешно добавлен в базу!")
        except Exception as e:
            await message.answer(f"❌ Ошибка при добавлении: {e}")

    # 2. Логика продления подписки
    elif message.text.isdigit():
        days = int(message.text)
        cursor.execute("UPDATE users SET expiry_date = DATE_ADD(GREATEST(expiry_date, NOW()), INTERVAL %s DAY) WHERE telegram_id = %s", (days, message.from_user.id))
        db.commit()
        await message.answer(f"✅ Подписка продлена на {days} дн.!")
    
    db.close()

@dp.callback_query_handler(lambda c: c.data == "reset_token")
async def reset_token(callback: types.CallbackQuery):
    new_token = secrets.token_hex(8)
    db = get_db()
    cursor = db.cursor()
    cursor.execute("UPDATE users SET token = %s WHERE telegram_id = %s", (new_token, callback.from_user.id))
    db.commit()
    db.close()
    
    new_url = f"http://livpn.webspot.sbs/sub.php?token={new_token}"
    await callback.message.answer(f"⚠️ **Ссылка обновлена!**\n\nНовая ссылка:\n`{new_url}`", parse_mode="Markdown")
    await callback.answer()

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
