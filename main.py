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

# --- ИСПРАВЛЕННЫЙ ФИКЦИВНЫЙ СЕРВЕР ---
def run_dummy_server():
    port = int(os.environ.get("PORT", 8080))
    handler = http.server.SimpleHTTPRequestHandler
    socketserver.TCPServer.allow_reuse_address = True
    try:
        with socketserver.TCPServer(("", port), handler) as httpd:
            print(f"✅ Dummy server on port {port}")
            httpd.serve_forever()
    except OSError:
        print("⚠️ Порт уже занят, пропускаем запуск сервера...")

threading.Thread(target=run_dummy_server, daemon=True).start()

# --- КОНФИГ И СОСТОЯНИЯ ---
class EditState(StatesGroup):
    edit_name = State()
    edit_vless = State()

DB_CONFIG = {
    'host': 'server145.cpcontroller.top',
    'user': 'Livpnweb_Dplusmop',
    'password': '32156416Dana',
    'database': 'livpnweb_db',
    'connect_timeout': 10
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
        InlineKeyboardButton("🔄 Сменить ссылку", callback_data="reset_token"),
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
            await message.answer("✅ Аккаунт привязан! VPN разморожен.", reply_markup=main_menu(message.from_user.id))
        else:
            cursor.execute("SELECT * FROM users WHERE telegram_id = %s", (message.from_user.id,))
            u = cursor.fetchone()
            if u:
                await message.answer(f"Привет, {u['username']}!", reply_markup=main_menu(message.from_user.id))
            else:
                await message.answer("❌ Аккаунт не привязан. Сделайте это на сайте.")
        db.close()
    except Exception as e:
        await message.answer(f"❌ Ошибка базы: {e}\nУбедитесь, что IP Render разрешен в Remote MySQL.")

# --- АДМИНКА ---
@dp.callback_query_handler(lambda c: c.data == "admin_panel", state="*")
async def admin_panel(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID: return
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT id, name FROM vless_configs")
    configs = cursor.fetchall()
    db.close()
    kbd = InlineKeyboardMarkup(row_width=1)
    for cfg in configs:
        kbd.add(InlineKeyboardButton(f"🌐 {cfg['name']}", callback_data=f"manage_{cfg['id']}"))
    kbd.add(InlineKeyboardButton("⬅️ Назад", callback_data="back_to_main"))
    await callback.message.edit_text("⚙️ Управление VLESS:", reply_markup=kbd)

@dp.callback_query_handler(lambda c: c.data.startswith("manage_"), state="*")
async def manage_config(callback: types.CallbackQuery):
    cfg_id = callback.data.split("_")[1]
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM vless_configs WHERE id = %s", (cfg_id,))
    cfg = cursor.fetchone()
    db.close()
    kbd = InlineKeyboardMarkup(row_width=1)
    kbd.add(
        InlineKeyboardButton("📝 Название", callback_data=f"editname_{cfg_id}"),
        InlineKeyboardButton("🔗 VLESS ключ", callback_data=f"editvless_{cfg_id}"),
        InlineKeyboardButton("🗑️ УДАЛИТЬ", callback_data=f"delconf_{cfg_id}"),
        InlineKeyboardButton("⬅️ Назад", callback_data="admin_panel")
    )
    await callback.message.edit_text(f"🛠️ {cfg['name']}\n`{cfg['content'][:50]}...`", reply_markup=kbd, parse_mode="Markdown")

@dp.callback_query_handler(lambda c: c.data.startswith("delconf_"), state="*")
async def delete_config(callback: types.CallbackQuery):
    cfg_id = callback.data.split("_")[1]
    db = get_db()
    cursor = db.cursor()
    cursor.execute("DELETE FROM vless_configs WHERE id = %s", (cfg_id,))
    db.commit()
    db.close()
    await callback.answer("✅ Удалено")
    await admin_panel(callback)

# --- РЕДАКТИРОВАНИЕ ---
@dp.callback_query_handler(lambda c: c.data.startswith("editname_"), state="*")
async def edit_name_start(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(cfg_id=callback.data.split("_")[1])
    await EditState.edit_name.set()
    await callback.message.answer("Введите новое название:")
    await callback.answer()

@dp.message_handler(state=EditState.edit_name)
async def edit_name_save(message: types.Message, state: FSMContext):
    data = await state.get_data()
    db = get_db()
    cursor = db.cursor()
    cursor.execute("UPDATE vless_configs SET name = %s WHERE id = %s", (message.text, data['cfg_id']))
    db.commit()
    db.close()
    await state.finish()
    await message.answer(f"✅ Готово: {message.text}")

@dp.callback_query_handler(lambda c: c.data.startswith("editvless_"), state="*")
async def edit_vless_start(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(cfg_id=callback.data.split("_")[1])
    await EditState.edit_vless.set()
    await callback.message.answer("Пришлите новый VLESS:")
    await callback.answer()

@dp.message_handler(state=EditState.edit_vless)
async def edit_vless_save(message: types.Message, state: FSMContext):
    data = await state.get_data()
    db = get_db()
    cursor = db.cursor()
    cursor.execute("UPDATE vless_configs SET content = %s WHERE id = %s", (message.text, data['cfg_id']))
    db.commit()
    db.close()
    await state.finish()
    await message.answer("✅ Ключ обновлен!")

@dp.callback_query_handler(lambda c: c.data == "reset_token", state="*")
async def reset_token(callback: types.CallbackQuery):
    new_t = secrets.token_hex(8)
    db = get_db()
    cursor = db.cursor()
    cursor.execute("UPDATE users SET token = %s WHERE telegram_id = %s", (new_t, callback.from_user.id))
    db.commit()
    db.close()
    await callback.message.answer(f"⚠️ Новый токен: `{new_t}`", parse_mode="Markdown")
    await callback.answer()

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
