import asyncio
import requests
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage

# ---------- КОНФИГ ----------
BOT_TOKEN = "8729125887:AAG2HKCLw03q8NAaWuA8Dlt6gYiKP6kSgLo"
ANYMODEL_API_KEY = "sk-dc9d4b7df36ba555-7lji6f-c92d66db"  # ОБЯЗАТЕЛЬНО ЗАМЕНИТЕ!
ANYMODEL_URL = "https://anymodel.org/v1/chat/completions"
MODEL = "gpt-5.6-sol"
REASONING = "high"
ALLOWED_USER_ID = 297562307  # ТОЛЬКО ЭТОТ ПОЛЬЗОВАТЕЛЬ СМОЖЕТ ИСПОЛЬЗОВАТЬ

SYSTEM_PROMPT = (
    "Ты — полезный ИИ-ассистент. Отвечай максимально подробно, развёрнуто, "
    "предоставляй всю возможную информацию по вопросу. Не отвечай коротко, "
    "старайся найти и выдать максимум данных."
)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

user_history = {}

def get_history(user_id):
    if user_id not in user_history:
        user_history[user_id] = []
    return user_history[user_id]

def split_text(text, limit=4096):
    parts = []
    while len(text) > limit:
        idx = text[:limit].rfind('\n')
        if idx == -1:
            idx = text[:limit].rfind(' ')
        if idx == -1:
            idx = limit
        parts.append(text[:idx])
        text = text[idx:].lstrip()
    if text:
        parts.append(text)
    return parts

async def send_long_message(chat_id, text):
    parts = split_text(text)
    for i, part in enumerate(parts):
        if len(parts) > 1:
            await bot.send_message(chat_id, f"Часть {i+1}/{len(parts)}:\n\n{part}")
        else:
            await bot.send_message(chat_id, part)

async def ask_model(messages):
    full_messages = [{"role": "system", "content": SYSTEM_PROMPT}] + messages
    payload = {
        "model": MODEL,
        "messages": full_messages,
        "max_tokens": 4096,
        "reasoning_effort": REASONING,
        "stream": False
    }
    try:
        resp = requests.post(
            ANYMODEL_URL,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {ANYMODEL_API_KEY}"
            },
            json=payload,
            timeout=120
        )
        if resp.status_code == 200:
            data = resp.json()
            return data["choices"][0]["message"]["content"]
        else:
            return None
    except Exception:
        return None

def is_allowed(user_id):
    return user_id == ALLOWED_USER_ID

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    if not is_allowed(message.from_user.id):
        await message.answer("Доступ запрещён")
        return
    user_id = message.from_user.id
    user_history[user_id] = []
    await message.answer(
        "Привет! Я — мощный ИИ-ассистент на базе GPT-5.6 Sol с максимальным уровнем reasoning.\n"
        "Я отвечаю максимально подробно и развёрнуто на любые вопросы.\n"
        "Просто пиши, и я выдам всю возможную информацию.\n"
        "Для сброса диалога используй /start."
    )

@dp.message(F.text)
async def handle_text(message: types.Message):
    if not is_allowed(message.from_user.id):
        await message.answer("Доступ запрещён")
        return
    user_id = message.from_user.id
    user_text = message.text.strip()
    if not user_text:
        return

    history = get_history(user_id)
    history.append({"role": "user", "content": user_text})

    await bot.send_chat_action(message.chat.id, action="typing")

    reply = await ask_model(history)
    if reply:
        history.append({"role": "assistant", "content": reply})
        await send_long_message(message.chat.id, reply)
    else:
        await message.answer("Извините, произошла ошибка при обращении к модели. Попробуйте позже.")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
