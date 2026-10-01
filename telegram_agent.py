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
from core.agent import Agent
from core.prompts import get_system_prompt
from tools.base import registry

# Import all tools to register them
import tools.mock_tools
import tools.web_tools
import tools.resume_tools

# 1. Load Environment Variables
load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ALLOWED_USER_ID = int(os.getenv("TELEGRAM_ALLOWED_USER_ID", "0"))

# 2. Local LLM Client
client = OpenAI(
    base_url=Config.LLM_BASE_URL,
    api_key=Config.LLM_API_KEY
)

# 3. Autonomous Agent Instance
agent = Agent(
    client=client,
    model=Config.LLM_MODEL,
    system_prompt=get_system_prompt(
        custom_instructions="You are an autonomous assistant. Answer concisely and use tools when up-to-date data, emails, web search, or schedule checks are requested."
    ),
    registry=registry,
    max_iterations=Config.MAX_ITERATIONS,
    max_tokens=400,
    verbose=True
)

# In-memory direct conversation history
conversation_history = [
    {"role": "system", "content": "You are a concise, helpful personal AI assistant. Keep responses direct and to the point."}
]

# Security Guard: Rejects anyone who isn't you
def is_authorized(update: Update) -> bool:
    return update.effective_user and update.effective_user.id == ALLOWED_USER_ID

# /start command
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    await update.message.reply_text(
        "👋 Connected to your local 4B model running on your laptop!\n\n"
        "Modes:\n"
        "💬 Send any text -> Fast direct chat (~15s)\n"
        "⚡ /agent <task> -> Autonomous multi-step agent with tools (web search, emails, calendar)\n"
        "🧹 /clear -> Reset chat history\n\n"
        "Try: `/agent Search the web for latest open source LLM news today`",
        parse_mode="Markdown"
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

# /agent command (Autonomous tool-calling loop with live progress updates)
async def agent_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return

    if not context.args:
        await update.message.reply_text(
            "⚠️ Please specify a task!\nExample:\n`/agent Search the web for latest AI news`\nor\n`/agent Check my unread emails and calendar for conflicts`",
            parse_mode="Markdown"
        )
        return

    task = " ".join(context.args)
    status_msg = await update.message.reply_text(
        f"⚙️ *[Agent Initialized]*\nTask: _{task}_\n\nAnalyzing and selecting tools...",
        parse_mode="Markdown"
    )

    loop = asyncio.get_running_loop()

    # Thread-safe callback to edit the status message live on Telegram
    def on_step(status_text: str):
        try:
            asyncio.run_coroutine_threadsafe(
                status_msg.edit_text(
                    f"⚙️ *[Agent Running]*\nTask: _{task}_\n\n{status_text}",
                    parse_mode="Markdown"
                ),
                loop
            )
        except Exception:
            pass

    try:
        final_answer = await loop.run_in_executor(
            None,
            lambda: agent.run(task, on_step=on_step)
        )
        
        # Replace the status message with the final response
        if len(final_answer) > 4000:
            await status_msg.edit_text(final_answer[:4000])
        else:
            await status_msg.edit_text(final_answer)

    except Exception as e:
        await status_msg.edit_text(f"⚠️ Agent Error: {str(e)}")

# Direct chat message handler (fast mode)
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return

    user_text = update.message.text
    conversation_history.append({"role": "user", "content": user_text})

    # Show "typing..." on your phone
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)

    loop = asyncio.get_running_loop()
    try:
        response = await loop.run_in_executor(
            None,
            lambda: client.chat.completions.create(
                model=Config.LLM_MODEL,
                messages=conversation_history,
                max_tokens=300,
                temperature=0.4,
                extra_body={"reasoning_budget": 0}
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
    print("  Telegram Local AI Bot Bridge (Chat + Autonomous Agent)")
    print(f"  Forwarding to: {Config.LLM_MODEL} @ {Config.LLM_BASE_URL}")
    print(f"  Registered Tools: {[s['function']['name'] for s in registry.get_schemas()]}")
    print(f"  Authorized User ID: {ALLOWED_USER_ID}")
    print("=" * 60)

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("clear", clear_command))
    app.add_handler(CommandHandler("agent", agent_command))
    app.add_handler(CommandHandler("act", agent_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("🤖 Bot is live! Send a message or /agent <task> from your phone...")
    app.run_polling()

if __name__ == "__main__":
    main()