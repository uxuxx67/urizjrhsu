import asyncio
import requests
import json
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage

# ---------- КОНФИГ ----------
BOT_TOKEN = "8644938642:AAFcN3sfkt4Ppc6p9i0cu7uIGRsGDcmow6E"
ANYMODEL_API_KEY = "sk-dc9d4b7df36ba555-xudaww-f83d999e"  # СМЕНИ!
ANYMODEL_URL = "https://anymodel.org/v1/chat/completions"
ADMIN_ID = 297562307

# Новая модель: Gemini 3.1 Flash-Lite (самая свежая, дёшево и умнее 2.5 Flash)
MODEL = "gemini-3.1-flash-lite-preview"

# Альтернативы (если эта не запустится):
# MODEL = "gc/gemini-2.5-flash-lite"   # старая, но рабочая
# MODEL = "gc/gemini-2.5-flash"        # средняя

# ---------- БОТ ----------
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("доступ запрещён")
        return
    await message.answer("привет ыхыхх, я твой ии агент, пиши че над")

@dp.message(F.text)
async def handle_message(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return

    await bot.send_chat_action(message.chat.id, action="typing")

    try:
        response = requests.post(
            ANYMODEL_URL,
            headers={
                "Authorization": f"Bearer {ANYMODEL_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": MODEL,
                "messages": [{"role": "user", "content": message.text}],
                "max_tokens": 2048,
                "stream": False
            },
            timeout=60
        )

        try:
            data = response.json()
        except json.JSONDecodeError:
            await message.answer(
                f"сервер вернул не json\nстатус: {response.status_code}\nтекст: {response.text[:300]}"
            )
            return

        if response.status_code == 200:
            reply = data["choices"][0]["message"]["content"]
            await message.answer(reply)
        else:
            error_msg = data.get("error", {}).get("message", str(data))
            await message.answer(f"ошибка api ({response.status_code}): {error_msg}")

    except requests.exceptions.Timeout:
        await message.answer("превышено время ожидания")
    except requests.exceptions.ConnectionError:
        await message.answer("не удалось соединиться с api")
    except Exception as e:
        await message.answer(f"ошибка: {str(e)}")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
