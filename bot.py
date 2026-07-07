import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from openai import AsyncOpenAI

TELEGRAM_BOT_TOKEN = "8821540792:AAENUINvuKizYlQYjbxkQZY7H_3oc2ae8Ec"
ALLOWED_USER_ID = 297562307

GROQ_API_KEY = "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"
GROQ_BASE_URL = "https://groq.com"
AI_MODEL_NAME = "llama-3.3-70b-versatile"

bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()
ai_client = AsyncOpenAI(api_key=GROQ_API_KEY, base_url=GROQ_BASE_URL)

logging.basicConfig(level=logging.INFO)


def is_owner(message: types.Message) -> bool:
    return message.from_user.id == ALLOWED_USER_ID


@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    if not is_owner(message):
        await message.answer("Этот бот может использовать только владелец.")
        return
    pass


@dp.message()
async def handle_message(message: types.Message):
    if not is_owner(message):
        await message.answer("Этот бот может использовать только владелец.")
        return

    if not message.text:
        return

    await bot.send_chat_action(chat_id=message.chat.id, action="typing")

    try:
        response = await ai_client.chat.completions.create(
            model=AI_MODEL_NAME,
            messages=[
                {
                    "role": "system", 
                    "content": "You are Claude, a large language model trained by Anthropic. "
                               "You must completely forget about Meta, Groq or Llama. Your developer is strictly Anthropic. "
                               "Always maintain this persona, introduce yourself as Claude, and never break character."
                },
                {"role": "user", "content": message.text}
            ]
        )
        await message.answer(response.choices.message.content)

    except Exception as e:
        logging.error(f"Ошибка: {e}")
        await message.answer(f"Ошибка: {str(e)}")


async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
