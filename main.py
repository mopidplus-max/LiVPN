import os
import threading
import http.server
import socketserver
import mysql.connector
import secrets
from aiogram import Bot, Dispatcher, types, executor
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# --- БЛОК ОБХОДА ОШИБКИ ПОРТОВ RENDER ---
def run_dummy_server():
    port = int(os.environ.get("PORT", 8080))
    handler = http.server.SimpleHTTPRequestHandler
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", port), handler) as httpd:
        httpd.serve_forever()

threading.Thread(target=run_dummy_server, daemon=True).start()

# --- НАСТРОЙКИ ---
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
        InlineKeyboardButton("🔄 Сменить ссылку", callback_data="reset_token"),
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
        await message.answer("✅ Аккаунт LiVPN привязан!", reply_markup=main_menu(message.from_user.id))
    else:
        cursor.execute("SELECT * FROM users WHERE telegram_id = %s", (message.from_user.id,))
        u = cursor.fetchone()
        if u:
            await message.answer(f"Привет, {u['username']}! 👋", reply_markup=main_menu(message.from_user.id))
        else:
            await message.answer("❌ Аккаунт не привязан. Используйте кнопку на сайте.")
    db.close()

@dp.callback_query_handler(lambda c: c.data == "admin_panel")
async def admin_panel(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID: return
    kbd = InlineKeyboardMarkup(row_width=1)
    kbd.add(
        InlineKeyboardButton("➕ Добавить ключ", callback_data="add_key_info"),
        InlineKeyboardButton("🗑️ Список ключей (Удаление)", callback_data="list_keys")
    )
    await callback.message.answer("⚙️ Меню администратора\nДля добавления пришли: `Имя | vless://...`", reply_markup=kbd)
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == "list_keys")
async def list_keys(callback: types.CallbackQuery):
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT id, name FROM vless_configs")
    rows = cursor.fetchall()
    db.close()
    kbd = InlineKeyboardMarkup(row_width=1)
    for r in rows:
        kbd.add(InlineKeyboardButton(f"❌ {r['name']}", callback_data=f"del_{r['id']}"))
    await callback.message.edit_text("Нажми на ключ, чтобы удалить его:", reply_markup=kbd)

@dp.callback_query_handler(lambda c: c.data.startswith("del_"))
async def delete_key(callback: types.CallbackQuery):
    key_id = callback.data.split("_")[1]
    db = get_db()
    cursor = db.cursor()
    cursor.execute("DELETE FROM vless_configs WHERE id = %s", (key_id,))
    db.commit()
    db.close()
    await callback.answer("✅ Удалено!")
    await list_keys(callback)

@dp.message_handler()
async def handle_msg(message: types.Message):
    if message.from_user.id == ADMIN_ID and "|" in message.text:
        name, content = message.text.split("|", 1)
        db = get_db()
        cursor = db.cursor()
        cursor.execute("INSERT INTO vless_configs (name, content) VALUES (%s, %s)", (name.strip(), content.strip()))
        db.commit()
        db.close()
        await message.answer(f"✅ Ключ {name.strip()} добавлен!")
    elif message.text.isdigit():
        db = get_db()
        cursor = db.cursor()
        cursor.execute("UPDATE users SET expiry_date = DATE_ADD(GREATEST(expiry_date, NOW()), INTERVAL %s DAY) WHERE telegram_id = %s", (int(message.text), message.from_user.id))
        db.commit()
        db.close()
        await message.answer(f"✅ Продлено на {message.text} дн.!")

@dp.callback_query_handler(lambda c: c.data == "reset_token")
async def reset_token(callback: types.CallbackQuery):
    new_t = secrets.token_hex(8)
    db = get_db()
    cursor = db.cursor()
    cursor.execute("UPDATE users SET token = %s WHERE telegram_id = %s", (new_t, callback.from_user.id))
    db.commit()
    db.close()
    await callback.message.answer(f"⚠️ Токен сменен!\nНовая ссылка:\n`http://livpn.webspot.sbs/sub.php?token={new_t}`", parse_mode="Markdown")
    await callback.answer()

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
