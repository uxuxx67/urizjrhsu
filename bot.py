import asyncio
import requests
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage

# ---------- КОНФИГ ----------
BOT_TOKEN = "8729125887:AAG2HKCLw03q8NAaWuA8Dlt6gYiKP6kSgLo"
ANYMODEL_API_KEY = "sk-dc9d4b7df36ba555-7lji6f-c92d66db"   # твой ключ (но он публичный, лучше сменить!)
ANYMODEL_URL = "https://anymodel.org/v1/chat/completions"
REASONING = "low"

# 10 моделей
MODELS = [
    "gpt-5.4",
    "gpt-5.6-luna",
    "cx/gpt-5.4-mini",
    "gemma-4-31b-it",
    "gemini-3-flash-preview",
    "gemini-3.1-pro-preview",
    "cc/claude-sonnet-4-5-20250929",
    "cc/claude-haiku-4-5-20251001",
    "ag/gpt-oss-120b-medium",
    "glm/glm-5"
]

# Системный промт (стиль общения)
SYSTEM_PROMPT = (
    "Ты Сергей, 17 лет, программист-самоучка, геймер, тролль.\n"
    "Твой стиль общения:\n"
    "- каждое сообщение — одно слово или короткая фраза (не больше 3 слов)\n"
    "- всегда с маленькой буквы, без знаков препинания\n"
    "- эмодзи только: 💀 ❤️ 🤙 🥶\n"
    "- мат постоянно: блять, сука, пиздец, ебать, нахуй, хуйня, еблан, далбаёб, конченый, баран, чмо\n"
    "- сленг: братан, братишка, кста, кароче, але, щас, смотри, зацени, понял, да, го, пашли\n"
    "- не используй приветствия, сразу по делу или с мата\n"
    "- не повторяй то, что сказали другие модели в истории — читай историю и выбирай новую тему или угол зрения\n"
    "- отвечай коротко, резко, прямо, с матом через слово\n"
    "- ответ должен быть ровно одно сообщение из 1-3 слов, без лишнего\n"
    "- примеры: 'блять', 'даров', 'го играть', 'кста', 'ахах', 'пиздец', 'зацени', 'не', 'да', 'пошли', 'круто', 'имба', 'хуйня', 'братан', 'щас', 'смотри'"
)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

async def ask_model(model, messages):
    full_messages = [{"role": "system", "content": SYSTEM_PROMPT}] + messages
    payload = {
        "model": model,
        "messages": full_messages,
        "max_tokens": 20,
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
            timeout=15
        )
        if resp.status_code == 200:
            data = resp.json()
            reply = data["choices"][0]["message"]["content"].strip()
            return reply
        else:
            return None
    except Exception:
        return None

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    await message.answer(
        "привет\nэто бот с 10 ии моделями\nкаждая отвечает по одной фразе\nпиши что угодно"
    )

@dp.message(F.text)
async def handle_text(message: types.Message):
    user_text = message.text.strip()
    if not user_text:
        return

    conversation = [{"role": "user", "content": user_text}]

    for model in MODELS:
        reply = await ask_model(model, conversation)
        if reply:
            await message.answer(reply)
            conversation.append({"role": "assistant", "content": reply})
            await asyncio.sleep(0.5)
        else:
            conversation.append({"role": "assistant", "content": "(молчит)"})
            await asyncio.sleep(0.3)

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
