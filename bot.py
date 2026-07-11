import asyncio
import requests
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage

BOT_TOKEN = "8729125887:AAG2HKCLw03q8NAaWuA8Dlt6gYiKP6kSgLo"
ANYMODEL_API_KEY = "sk-dc9d4b7df36ba555-7lji6f-c92d66db"  # замени на новый!
ANYMODEL_URL = "https://anymodel.org/v1/chat/completions"
REASONING = "low"

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

# Исправленный промт (без конкретных примеров, только стиль)
SYSTEM_PROMPT = (
    "Ты Сергей, 17 лет.\n"
    "Твой стиль общения: коротко, резко, с матом через слово.\n"
    "Каждое сообщение — 1-3 слова, без знаков препинания, с маленькой буквы.\n"
    "Отвечай строго по теме вопроса или реплики, не уходи в абстракции.\n"
    "Читай историю диалога и не повторяй то, что уже сказали другие модели.\n"
    "Не используй приветствия, начинай сразу с сути.\n"
    "Эмодзи: 💀 ❤️ 🤙 🥶. Мат: блять, сука, пиздец, ебать, нахуй, хуйня, еблан, далбаёб, конченый, баран, чмо.\n"
    "Сленг: братан, братишка, кста, кароче, але, щас, смотри, зацени, понял, да, го, пашли."
)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

async def ask_model(model, messages):
    full = [{"role": "system", "content": SYSTEM_PROMPT}] + messages
    try:
        r = requests.post(
            ANYMODEL_URL,
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {ANYMODEL_API_KEY}"},
            json={"model": model, "messages": full, "max_tokens": 30, "reasoning_effort": REASONING, "stream": False},
            timeout=15
        )
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"].strip()
        return None
    except:
        return None

@dp.message(Command("start"))
async def start_cmd(m: types.Message):
    await m.answer("привет\nпиши что угодно")

@dp.message(F.text)
async def handle(m: types.Message):
    text = m.text.strip()
    if not text:
        return
    conv = [{"role": "user", "content": text}]
    for model in MODELS:
        reply = await ask_model(model, conv)
        if reply:
            await m.answer(reply)
            conv.append({"role": "assistant", "content": reply})
            await asyncio.sleep(0.4)
        else:
            conv.append({"role": "assistant", "content": "(молчит)"})
            await asyncio.sleep(0.2)

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
