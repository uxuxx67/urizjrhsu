import asyncio
import requests
import json
import base64
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.storage.memory import MemoryStorage

# ---------- КОНФИГ ----------
BOT_TOKEN = "8644938642:AAFcN3sfkt4Ppc6p9i0cu7uIGRsGDcmow6E"
ANYMODEL_API_KEY = "sk-dc9d4b7df36ba555-xudaww-f83d999e"  # СМЕНИ!
ANYMODEL_URL = "https://anymodel.org/v1/chat/completions"
ADMIN_ID = 297562307

# Модели
MODELS = {
    "gpt-5.6-sol": "gpt-5.6-sol",
    "gpt-5.6-luna": "gpt-5.6-luna",
    "gemini 2.5 flash": "gc/gemini-2.5-flash",
    "gemini-3.1-pro-preview": "gemini-3.1-pro-preview",
    "claude-sonnet-4-6": "claude-sonnet-4-6",
    "claude-opus-4-8": "claude-opus-4-8",
    "claude-haiku-4-5-20251001": "claude-haiku-4-5-20251001"
}

# ---------- БОТ ----------
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Храним модель и историю
user_data = {}  # {user_id: {"model": model_id, "history": [{"role": "user", "content": "..."}, ...]}}

# ---------- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ----------
def split_text(text, limit=4096):
    parts = []
    while len(text) > limit:
        split_at = text[:limit].rfind('\n')
        if split_at == -1:
            split_at = text[:limit].rfind(' ')
        if split_at == -1:
            split_at = limit
        parts.append(text[:split_at])
        text = text[split_at:].lstrip()
    if text:
        parts.append(text)
    return parts

async def send_long_message(chat_id, text):
    parts = split_text(text)
    for i, part in enumerate(parts):
        if len(parts) > 1:
            await bot.send_message(chat_id, f"часть {i+1}/{len(parts)}:\n\n{part}")
        else:
            await bot.send_message(chat_id, part)

# ---------- КЛАВИАТУРА ----------
def model_keyboard():
    buttons = []
    for name in MODELS.keys():
        buttons.append([InlineKeyboardButton(text=name, callback_data=f"model_{name}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# ---------- ХЭНДЛЕРЫ ----------
@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("доступ запрещён")
        return
    user_data[message.from_user.id] = {"model": None, "history": []}
    await message.answer(
        "привет ыхыхх, я твой ии агент\nвыбери модель:",
        reply_markup=model_keyboard()
    )

@dp.callback_query(F.data.startswith("model_"))
async def select_model(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if user_id != ADMIN_ID:
        await callback.answer("доступ запрещён", show_alert=True)
        return
    model_name = callback.data.split("model_", 1)[1]
    model_id = MODELS.get(model_name)
    if not model_id:
        await callback.answer("неизвестная модель", show_alert=True)
        return
    user_data[user_id] = {"model": model_id, "history": []}
    await callback.message.edit_text(
        f"выбрана модель: {model_name}\nтеперь пиши свои запросы в чат"
    )
    await callback.answer()

# ---------- ОБРАБОТЧИК ТЕКСТА ----------
@dp.message(F.text)
async def handle_text(message: types.Message):
    user_id = message.from_user.id
    if user_id != ADMIN_ID:
        return
    ud = user_data.get(user_id)
    if not ud or not ud["model"]:
        await message.answer("сначала выбери модель через /start")
        return

    model_id = ud["model"]
    history = ud["history"]
    history.append({"role": "user", "content": message.text})

    await bot.send_chat_action(message.chat.id, action="typing")

    try:
        response = requests.post(
            ANYMODEL_URL,
            headers={
                "Authorization": f"Bearer {ANYMODEL_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": model_id,
                "messages": history,
                "max_tokens": 4096,
                "stream": False
            },
            timeout=120
        )

        data = None
        try:
            data = response.json()
        except json.JSONDecodeError:
            await message.answer(f"сервер вернул не json: {response.text[:200]}")
            return

        if response.status_code == 200 and data and "choices" in data:
            reply = data["choices"][0]["message"]["content"]
            history.append({"role": "assistant", "content": reply})
            await send_long_message(message.chat.id, reply)
        else:
            error_msg = data.get("error", {}).get("message", str(data)) if data else "неизвестная ошибка"
            await message.answer(f"ошибка api ({response.status_code}): {error_msg}")

    except Exception as e:
        await message.answer(f"ошибка: {str(e)}")

# ---------- ОБРАБОТЧИК ФОТО ----------
@dp.message(F.photo)
async def handle_photo(message: types.Message):
    user_id = message.from_user.id
    if user_id != ADMIN_ID:
        return
    ud = user_data.get(user_id)
    if not ud or not ud["model"]:
        await message.answer("сначала выбери модель через /start")
        return

    model_id = ud["model"]
    history = ud["history"]

    await bot.send_chat_action(message.chat.id, action="upload_photo")

    try:
        photo = message.photo[-1]
        file = await bot.get_file(photo.file_id)
        file_bytes = await bot.download_file(file.file_path)
        image_base64 = base64.b64encode(file_bytes.getvalue()).decode('utf-8')

        # Формируем текущее сообщение с картинкой
        current_content = []
        if message.caption:
            current_content.append({"type": "text", "text": message.caption})
        current_content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}
        })

        # Отправляем историю + текущее сообщение с картинкой
        messages_for_api = history.copy()
        messages_for_api.append({"role": "user", "content": current_content})

        response = requests.post(
            ANYMODEL_URL,
            headers={
                "Authorization": f"Bearer {ANYMODEL_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": model_id,
                "messages": messages_for_api,
                "max_tokens": 4096,
                "stream": False
            },
            timeout=120
        )

        data = None
        try:
            data = response.json()
        except json.JSONDecodeError:
            await message.answer(f"сервер вернул не json: {response.text[:200]}")
            return

        if response.status_code == 200 and data and "choices" in data:
            reply = data["choices"][0]["message"]["content"]
            # Сохраняем в историю текстовое представление (без картинки)
            if message.caption:
                history.append({"role": "user", "content": f"[фото] {message.caption}"})
            else:
                history.append({"role": "user", "content": "[фото]"})
            history.append({"role": "assistant", "content": reply})
            await send_long_message(message.chat.id, reply)
        else:
            error_msg = data.get("error", {}).get("message", str(data)) if data else "неизвестная ошибка"
            await message.answer(f"ошибка api: {error_msg}")

    except Exception as e:
        await message.answer(f"ошибка обработки фото: {str(e)}")

# ---------- ОБРАБОТЧИК ДОКУМЕНТОВ ----------
@dp.message(F.document)
async def handle_document(message: types.Message):
    user_id = message.from_user.id
    if user_id != ADMIN_ID:
        return
    ud = user_data.get(user_id)
    if not ud or not ud["model"]:
        await message.answer("сначала выбери модель через /start")
        return

    model_id = ud["model"]
    history = ud["history"]

    await bot.send_chat_action(message.chat.id, action="upload_document")

    try:
        doc = message.document
        file = await bot.get_file(doc.file_id)
        file_bytes = await bot.download_file(file.file_path)

        try:
            text_content = file_bytes.getvalue().decode('utf-8')
            caption = message.caption or "проанализируй этот файл"
            full_text = f"{caption}\n\n```\n{text_content[:5000]}\n```"
        except:
            full_text = message.caption or f"получен файл: {doc.file_name}"

        history.append({"role": "user", "content": full_text})

        response = requests.post(
            ANYMODEL_URL,
            headers={
                "Authorization": f"Bearer {ANYMODEL_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": model_id,
                "messages": history,
                "max_tokens": 4096,
                "stream": False
            },
            timeout=120
        )

        data = None
        try:
            data = response.json()
        except json.JSONDecodeError:
            await message.answer(f"сервер вернул не json: {response.text[:200]}")
            return

        if response.status_code == 200 and data and "choices" in data:
            reply = data["choices"][0]["message"]["content"]
            history.append({"role": "assistant", "content": reply})
            await send_long_message(message.chat.id, reply)
        else:
            error_msg = data.get("error", {}).get("message", str(data)) if data else "неизвестная ошибка"
            await message.answer(f"ошибка api: {error_msg}")

    except Exception as e:
        await message.answer(f"ошибка обработки документа: {str(e)}")

@dp.message(F.voice | F.audio)
async def handle_audio(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    await message.answer("пока не умею обрабатывать аудио, но скоро научусь")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
