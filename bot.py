import asyncio
import sqlite3
import datetime
import json
import requests
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.storage.memory import MemoryStorage

# ---------- конфиг ----------
BOT_TOKEN = "8644938642:AAFcN3sfkt4Ppc6p9i0cu7uIGRsGDcmow6E"
ANYMODEL_API_KEY = "sk-dc9d4b7df36ba555-xudaww-f83d999e"  # смени!
ANYMODEL_URL = "https://anymodel.org/v1/chat/completions"
ADMIN_ID = 297562307

# модели (без gpt-5.3-codex)
MODELS = {
    "gpt-5.6-sol": "gpt-5.6-sol",
    "gpt-5.6-luna": "gpt-5.6-luna",
    "gpt-5.6-terra": "gpt-5.6-terra",
    "gpt-5.5": "gpt-5.5",
    "gpt-5.4-mini": "gpt-5.4-mini",
    "gpt-5.4": "gpt-5.4"
}
DEFAULT_MODEL = "gpt-5.4"

COST = 333.33333333333
INITIAL = 1000
ADMIN_INITIAL = 7381848292
MAX_MSG_LEN = 4096

# ---------- база ----------
def init_db():
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            balance REAL DEFAULT 1000,
            model TEXT DEFAULT 'gpt-5.4',
            last_reset DATE DEFAULT NULL,
            username TEXT DEFAULT NULL
        )
    """)
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("SELECT balance, model, last_reset, username FROM users WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return {"balance": row[0], "model": row[1], "last_reset": row[2], "username": row[3]}
    return None

def create_user(user_id, username=None):
    balance = ADMIN_INITIAL if user_id == ADMIN_ID else INITIAL
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("INSERT INTO users (user_id, balance, model, last_reset, username) VALUES (?, ?, ?, ?, ?)",
              (user_id, balance, DEFAULT_MODEL, None, username))
    conn.commit()
    conn.close()

def update_balance(user_id, amount):
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
    conn.commit()
    conn.close()

def set_model(user_id, model):
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("UPDATE users SET model = ? WHERE user_id = ?", (model, user_id))
    conn.commit()
    conn.close()

def reset_if_needed(user_id):
    user = get_user(user_id)
    if not user:
        return
    today = datetime.date.today().isoformat()
    if user["last_reset"] != today:
        start = ADMIN_INITIAL if user_id == ADMIN_ID else INITIAL
        conn = sqlite3.connect("bot.db")
        c = conn.cursor()
        c.execute("UPDATE users SET balance = ?, last_reset = ? WHERE user_id = ?", (start, today, user_id))
        conn.commit()
        conn.close()

# ---------- бот ----------
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

user_history = {}  # {user_id: [{"role": "user", "content": ...}, ...]}

def model_keyboard():
    buttons = []
    for name in MODELS.keys():
        buttons.append([InlineKeyboardButton(text=name, callback_data=f"model_{name}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# ---------- обработчики ----------
@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username or "пользователь"
    user = get_user(user_id)
    if not user:
        create_user(user_id, username)
        user = get_user(user_id)
    else:
        # обновим имя
        if user["username"] != username:
            conn = sqlite3.connect("bot.db")
            c = conn.cursor()
            c.execute("UPDATE users SET username = ? WHERE user_id = ?", (username, user_id))
            conn.commit()
            conn.close()
    reset_if_needed(user_id)
    user_history[user_id] = []
    await show_menu(message)

async def show_menu(message: types.Message, edit=False):
    user_id = message.from_user.id
    user = get_user(user_id)
    if not user:
        await message.answer("ошибка, начните с /start")
        return
    balance = user["balance"]
    model = user["model"]
    username = user["username"] or "пользователь"
    text = (
        f"привет, {username}, это бот для легкого тестирования всех gpt моделей.\n\n"
        f"твои токены: {balance:.2f}\n"
        f"токены сбрасываются раз в сутки.\n\n"
        f"текущая модель: {model}\n"
        f"выбери другую модель, чтобы начать новый диалог."
    )
    if edit:
        await message.edit_text(text, reply_markup=model_keyboard())
    else:
        await message.answer(text, reply_markup=model_keyboard())

@dp.callback_query(F.data.startswith("model_"))
async def select_model(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    model_name = callback.data.split("model_", 1)[1]
    model_id = MODELS.get(model_name)
    if not model_id:
        await callback.answer("неизвестная модель", show_alert=True)
        return
    # проверяем, зарегистрирован ли пользователь
    user = get_user(user_id)
    if not user:
        # создаём автоматически при выборе модели
        create_user(user_id, callback.from_user.username)
        user = get_user(user_id)
    reset_if_needed(user_id)
    set_model(user_id, model_id)
    user_history[user_id] = []
    await callback.message.answer(f"сменена модель на: {model_name}")
    await show_menu(callback.message, edit=True)
    await callback.answer()

@dp.message(F.text)
async def handle_text(message: types.Message):
    user_id = message.from_user.id
    # проверка регистрации
    user = get_user(user_id)
    if not user:
        await message.answer("сначала /start")
        return

    reset_if_needed(user_id)
    user = get_user(user_id)  # обновляем данные после сброса
    balance = user["balance"]
    model = user["model"]

    if balance < COST:
        await message.answer(f"недостаточно токенов. нужно: {COST:.2f}, у вас: {balance:.2f}")
        return

    if user_id not in user_history:
        user_history[user_id] = []
    history = user_history[user_id]
    history.append({"role": "user", "content": message.text})

    await bot.send_chat_action(message.chat.id, action="typing")
    try:
        resp = requests.post(
            ANYMODEL_URL,
            headers={"Authorization": f"Bearer {ANYMODEL_API_KEY}", "Content-Type": "application/json"},
            json={"model": model, "messages": history, "max_tokens": 4096, "stream": False},
            timeout=120
        )
        data = None
        try:
            data = resp.json()
        except json.JSONDecodeError:
            await message.answer(f"сервер вернул не json: {resp.text[:200]}")
            return
        if resp.status_code == 200 and data and "choices" in data:
            reply = data["choices"][0]["message"]["content"]
            if len(reply) > MAX_MSG_LEN:
                await message.answer("сообщение слишком длинное, напишите другой вопрос,")
                return
            update_balance(user_id, -COST)
            history.append({"role": "assistant", "content": reply})
            await message.answer(reply)
        else:
            err = data.get("error", {}).get("message", str(data)) if data else "неизвестная ошибка"
            await message.answer(f"ошибка api ({resp.status_code}): {err}")
    except Exception as e:
        await message.answer(f"ошибка: {str(e)}")

async def main():
    init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
