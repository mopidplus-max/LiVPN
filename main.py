import mysql.connector
import secrets
from aiogram import Bot, Dispatcher, types, executor
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

DB_CONFIG = {
    'host': 'server145.cpcontroller.top',
    'user': 'Livpnweb_Dplusmop',
    'password': '32156416Dana',
    'database': 'livpnweb_db'
}

TOKEN = '8239393918:AAGGPBoBE3KBK3KPuwYaH72AE6vdgsXthA8'
ADMIN_ID = 5017549785 # Твой ID для админки
bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

def get_db():
    return mysql.connector.connect(**DB_CONFIG)

# Главное меню пользователя
def main_menu():
    kbd = InlineKeyboardMarkup(row_width=1)
    kbd.add(
        InlineKeyboardButton("🔄 Сменить токен (ссылку)", callback_data="reset_token"),
        InlineKeyboardButton("📊 Статус подписки", callback_data="status"),
        InlineKeyboardButton("❓ Поддержка", url="https://t.me/LiVPN_Support")
    )
    return kbd

@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    args = message.get_args()
    db = get_db()
    cursor = db.cursor(dictionary=True)

    if args: # Привязка
        cursor.execute("UPDATE users SET telegram_id = %s WHERE token = %s", (message.from_user.id, args))
        db.commit()
        await message.answer("✅ Аккаунт привязан! VPN разморожен.", reply_markup=main_menu())
    else:
        cursor.execute("SELECT * FROM users WHERE telegram_id = %s", (message.from_user.id,))
        u = cursor.fetchone()
        if u:
            msg = f"Привет, {u['username']}! 👋\n"
            if message.from_user.id == ADMIN_ID:
                msg += "\n⭐ Вы вошли как ГЛАВНЫЙ АДМИНИСТРАТОР."
                kbd = main_menu()
                kbd.add(InlineKeyboardButton("⚙️ АДМИН-ПАНЕЛЬ", callback_data="admin_panel"))
                await message.answer(msg, reply_markup=kbd)
            else:
                await message.answer(msg, reply_markup=main_menu())
        else:
            await message.answer("❌ Аккаунт не привязан. Получите ссылку на сайте.")
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
    await callback.message.answer(f"⚠️ **Ссылка успешно сменена!**\nСтарая ссылка больше не работает.\n\nНовая ссылка:\n`{new_url}`\n\nОбновите её в приложении.", parse_mode="Markdown")
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == "admin_panel")
async def admin_panel(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID: return
    kbd = InlineKeyboardMarkup(row_width=1)
    kbd.add(
        InlineKeyboardButton("👥 Список пользователей", callback_data="adm_users"),
        InlineKeyboardButton("🌐 Управление серверами", callback_data="adm_servers")
    )
    await callback.message.edit_text("⚙️ **ПАНЕЛЬ УПРАВЛЕНИЯ LIVPN**", reply_markup=kbd, parse_mode="Markdown")

# Логика продления через текст остается
@dp.message_handler()
async def handle_text(message: types.Message):
    if message.text.isdigit():
        days = int(message.text)
        db = get_db()
        cursor = db.cursor()
        cursor.execute("UPDATE users SET expiry_date = DATE_ADD(GREATEST(expiry_date, NOW()), INTERVAL %s DAY) WHERE telegram_id = %s", (days, message.from_user.id))
        db.commit()
        await message.answer(f"✅ Подписка продлена на {days} дн.!")
        db.close()

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
