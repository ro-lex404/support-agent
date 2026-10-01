import os
import asyncio
from dotenv import load_dotenv
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from openai import OpenAI
from config import Config

# 1. Load Environment Variables
load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ALLOWED_USER_ID = int(os.getenv("TELEGRAM_ALLOWED_USER_ID", "0"))

# 2. Local LLM Client
client = OpenAI(
    base_url=Config.LLM_BASE_URL,
    api_key=Config.LLM_API_KEY
)

# In-memory conversation history
conversation_history = [
    {"role": "system", "content": "You are a concise, helpful personal AI assistant. Keep responses direct and to the point."}
]

# Security Guard: Rejects anyone who isn't you
def is_authorized(update: Update) -> bool:
    return update.effective_user and update.effective_user.id == ALLOWED_USER_ID

# /start command
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        await update.message.reply_text("⛔ Unauthorized access.")
        return
    await update.message.reply_text(
        "👋 Connected to your local 4B model running offline on your laptop!\n\n"
        "Commands:\n"
        "/clear - Reset conversation history\n"
        "/help  - Show instructions"
    )

# /clear command
async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    global conversation_history
    conversation_history = [
        {"role": "system", "content": "You are a concise, helpful personal AI assistant. Keep responses direct and to the point."}
    ]
    await update.message.reply_text("🧹 Conversation history cleared.")

# Message handler
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        await update.message.reply_text("⛔ Unauthorized.")
        return

    user_text = update.message.text
    conversation_history.append({"role": "user", "content": user_text})

    # Show "typing..." on your phone
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)

    # Run inference in a background thread so the Telegram loop doesn't freeze
    loop = asyncio.get_running_loop()
    try:
        response = await loop.run_in_executor(
            None,
            lambda: client.chat.completions.create(
                model=Config.LLM_MODEL,
                messages=conversation_history,
                max_tokens=300,
                temperature=0.4
            )
        )
        reply = response.choices[0].message.content or "(No response generated)"
        conversation_history.append({"role": "assistant", "content": reply})

        await update.message.reply_text(reply)

    except Exception as e:
        await update.message.reply_text(f"⚠️ Error: {str(e)}")

def main():
    if not BOT_TOKEN or not ALLOWED_USER_ID:
        print("[Error] Please configure TELEGRAM_BOT_TOKEN and TELEGRAM_ALLOWED_USER_ID in your .env file!")
        return

    print("=" * 60)
    print("  Telegram Local AI Bot Bridge")
    print(f"  Forwarding to: {Config.LLM_MODEL} @ {Config.LLM_BASE_URL}")
    print(f"  Authorized User ID: {ALLOWED_USER_ID}")
    print("=" * 60)

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("clear", clear_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("🤖 Bot is live! Send a message from your phone...")
    app.run_polling()

if __name__ == "__main__":
    main()