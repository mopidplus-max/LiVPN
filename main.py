import os
import threading
import http.server
import socketserver
import mysql.connector
import secrets
from aiogram import Bot, Dispatcher, types, executor
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage

# --- СЕРВЕР ДЛЯ RENDER (Устранение ошибки No open ports) ---
def run_dummy_server():
    port = int(os.environ.get("PORT", 8080))
    handler = http.server.SimpleHTTPRequestHandler
    socketserver.TCPServer.allow_reuse_address = True
    try:
        with socketserver.TCPServer(("", port), handler) as httpd:
            httpd.serve_forever()
    except Exception:
        pass

threading.Thread(target=run_dummy_server, daemon=True).start()

# --- КОНФИГУРАЦИЯ БАЗЫ ДАННЫХ ---
DB_CONFIG = {
    'host': 'server145.cpcontroller.top',
    'user': 'Livpnweb_tgbot',           # Проверьте точность в cPanel!
    'password': '32156416DabbingPid',    # Ваш новый пароль
    'database': 'livpnweb_db',
    'connect_timeout': 15
}

TOKEN = '8239393918:AAGGPBoBE3KBK3KPuwYaH72AE6vdgsXthA8'
ADMIN_ID = 5017549785 
bot = Bot(token=TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

def get_db():
    return mysql.connector.connect(**DB_CONFIG)

# --- ГЛАВНОЕ МЕНЮ ---
def main_menu(user_id):
    kbd = InlineKeyboardMarkup(row_width=1)
    kbd.add(
        InlineKeyboardButton("🔄 Обновить ссылку", callback_data="reset_token"),
        InlineKeyboardButton("❓ Поддержка", url="https://t.me/LiVPN_Support")
    )
    if user_id == ADMIN_ID:
        kbd.add(InlineKeyboardButton("⚙️ АДМИН-ПАНЕЛЬ", callback_data="admin_panel"))
    return kbd

@dp.message_handler(commands=['start'], state="*")
async def start(message: types.Message, state: FSMContext):
    await state.finish()
    args = message.get_args()
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)
        if args:
            cursor.execute("UPDATE users SET telegram_id = %s WHERE token = %s", (message.from_user.id, args))
            db.commit()
            await message.answer("✅ Аккаунт успешно привязан!", reply_markup=main_menu(message.from_user.id))
        else:
            cursor.execute("SELECT * FROM users WHERE telegram_id = %s", (message.from_user.id,))
            u = cursor.fetchone()
            if u:
                await message.answer(f"Привет, {u['username']}! Бот готов к работе.", reply_markup=main_menu(message.from_user.id))
            else:
                await message.answer("❌ Вы еще не зарегистрированы. Получите ссылку на сайте.")
        db.close()
    except Exception as e:
        await message.answer(f"❌ Ошибка подключения: {e}")

# --- АДМИН-ЛОГИКА ---
@dp.callback_query_handler(lambda c: c.data == "admin_panel", state="*")
async def admin_panel(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID: return
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT id, name FROM vless_configs")
        configs = cursor.fetchall()
        db.close()
        kbd = InlineKeyboardMarkup(row_width=1)
        for cfg in configs:
            kbd.add(InlineKeyboardButton(f"🌐 {cfg['name']}", callback_data=f"manage_{cfg['id']}"))
        kbd.add(InlineKeyboardButton("⬅️ Назад", callback_data="back_to_main"))
        await callback.message.edit_text("⚙️ Список серверов:", reply_markup=kbd)
    except Exception as e:
        await callback.answer(f"Ошибка БД: {e}", show_alert=True)

@dp.callback_query_handler(lambda c: c.data == "back_to_main", state="*")
async def back_to_main(callback: types.CallbackQuery):
    await callback.message.edit_text("Привет! Чем могу помочь?", reply_markup=main_menu(callback.from_user.id))

@dp.callback_query_handler(lambda c: c.data == "reset_token", state="*")
async def reset_token(callback: types.CallbackQuery):
    new_t = secrets.token_hex(8)
    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute("UPDATE users SET token = %s WHERE telegram_id = %s", (new_t, callback.from_user.id))
        db.commit()
        db.close()
        await callback.message.answer(f"✅ Токен обновлен!\nНовая ссылка: `http://livpn.webspot.sbs/sub.php?token={new_t}`", parse_mode="Markdown")
        await callback.answer()
    except Exception as e:
        await callback.answer(f"Ошибка: {e}", show_alert=True)

if __name__ == '__main__':
    # drop_pending_updates=True поможет избежать ошибки TerminatedByOtherGetUpdates
    executor.start_polling(dp, skip_updates=True)
