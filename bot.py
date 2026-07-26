import os

from dotenv import load_dotenv
from openai import OpenAI
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# Load .env file
load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Connect OpenAI SDK to OpenRouter
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hello! 👋\n\n"
        "I am your AI assistant powered by OpenRouter.\n"
        "Send me any question!"
    )


async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text

    try:
        completion = client.chat.completions.create(
            model="openrouter/free",
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful AI assistant."
                },
                {
                    "role": "user",
                    "content": user_message
                }
            ]
        )

        ai_reply = completion.choices[0].message.content

        await update.message.reply_text(ai_reply)

    except Exception as e:
        print("OpenRouter Error:", e)

        await update.message.reply_text(
            "Sorry, I couldn't generate a response."
        )


def main():

    if not TELEGRAM_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN missing from .env")

    if not OPENROUTER_API_KEY:
        raise ValueError("OPENROUTER_API_KEY missing from .env")

    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            chat
        )
    )

    print("================================")
    print(" Telegram AI Bot is running 🤖")
    print(" OpenRouter connected")
    print("================================")

    app.run_polling()


if __name__ == "__main__":
    main()