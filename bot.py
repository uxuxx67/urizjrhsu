import asyncio
import requests
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.storage.memory import MemoryStorage

# ---------- КОНФИГ ----------
BOT_TOKEN = "8644938642:AAFcN3sfkt4Ppc6p9i0cu7uIGRsGDcmow6E"
ANYMODEL_API_KEY = "sk-dc9d4b7df36ba555-xudaww-f83d999e"  # ОБЯЗАТЕЛЬНО СМЕНИТЕ ПОСЛЕ ПЕРВОГО ЗАПУСКА!
ANYMODEL_URL = "https://anymodel.org/v1/chat/completions"
ADMIN_ID = 297562307  # только этот пользователь может пользоваться ботом

# Доступные модели (правильные идентификаторы для AnyModel)
MODELS = {
    "gemma 4 31b": "gc/gemma-4-31b",
    "gemini 2.5 flash": "gc/gemini-2.5-flash",
    "gemini 2.5 flash lite": "gc/gemini-2.5-flash-lite",
}

# ---------- БОТ ----------
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Храним выбранную модель для пользователя (только для админа)
user_model = {}  # {user_id: model_id}

# ---------- КЛАВИАТУРЫ ----------
def model_keyboard():
    buttons = []
    for name in MODELS.keys():
        buttons.append([InlineKeyboardButton(text=name, callback_data=f"model_{name}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# ---------- ХЭНДЛЕРЫ ----------
@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    user_id = message.from_user.id
    if user_id != ADMIN_ID:
        await message.answer("доступ запрещён")
        return

    user_model[user_id] = None
    await message.answer(
        "привет ыхыхх, я твой ии агент, пиши че над\n\nвыбери модель:",
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

    user_model[user_id] = model_id
    await callback.message.edit_text(
        f"выбрана модель: {model_name}\nтеперь пиши свои запросы в чат"
    )
    await callback.answer()

@dp.message(F.text)
async def handle_message(message: types.Message):
    user_id = message.from_user.id
    if user_id != ADMIN_ID:
        return  # игнорируем всех, кроме админа

    model_id = user_model.get(user_id)
    if not model_id:
        await message.answer("сначала выбери модель через /start")
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
                "model": model_id,
                "messages": [{"role": "user", "content": message.text}],
                "max_tokens": 2048
            },
            timeout=45
        )

        if response.status_code == 200:
            data = response.json()
            reply = data["choices"][0]["message"]["content"]
            await message.answer(reply)
        else:
            error_text = f"ошибка api ({response.status_code})"
            try:
                err_data = response.json()
                if "error" in err_data:
                    error_text += f": {err_data['error']}"
                elif "message" in err_data:
                    error_text += f": {err_data['message']}"
            except:
                error_text += f": {response.text[:200]}"
            await message.answer(error_text)

    except requests.exceptions.Timeout:
        await message.answer("превышено время ожидания ответа от api")
    except requests.exceptions.ConnectionError:
        await message.answer("не удалось соединиться с api")
    except requests.exceptions.RequestException as e:
        await message.answer(f"ошибка сети: {str(e)}")
    except KeyError as e:
        await message.answer(f"неожиданный ответ api: отсутствует поле {e}")
    except Exception as e:
        await message.answer(f"непредвиденная ошибка: {str(e)}")

# ---------- ЗАПУСК ----------
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
