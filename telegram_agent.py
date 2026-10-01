import os
import asyncio
from datetime import datetime
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

# Import deterministic Python tools
from tools.mock_tools import get_current_time, list_unread_emails, check_calendar_events
from tools.web_tools import search_web, read_webpage
from tools.resume_tools import get_my_resume_summary, analyze_job_fit

# 1. Load Environment Variables
load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ALLOWED_USER_ID = int(os.getenv("TELEGRAM_ALLOWED_USER_ID", "0"))

# 2. Local LLM Client
client = OpenAI(
    base_url=Config.LLM_BASE_URL,
    api_key=Config.LLM_API_KEY
)

# In-memory conversation history (keeps track of chat + any tool outputs injected)
conversation_history = [
    {"role": "system", "content": "You are a helpful, concise personal AI assistant. Keep responses clear and direct."}
]

def is_authorized(update: Update) -> bool:
    return update.effective_user and update.effective_user.id == ALLOWED_USER_ID

def update_system_context(info_text: str):
    """Appends factual context to the primary system prompt at index 0 (safe for Jinja template)."""
    conversation_history[0]["content"] += f"\n\n[Context Update]:\n{info_text}"

async def ask_llm(user_prompt: str, context_info: str = "") -> str:
    """Helper to query the local LLM without violating Jinja role alternation rules."""
    messages = list(conversation_history)
    
    if context_info:
        full_content = f"[Retrieved Information]:\n{context_info}\n\n[Request]:\n{user_prompt}"
    else:
        full_content = user_prompt

    messages.append({"role": "user", "content": full_content})

    loop = asyncio.get_running_loop()
    response = await loop.run_in_executor(
        None,
        lambda: client.chat.completions.create(
            model=Config.LLM_MODEL,
            messages=messages,
            max_tokens=300,
            temperature=0.4,
            extra_body={"reasoning_budget": 0}
        )
    )
    reply = response.choices[0].message.content or "(No response)"
    conversation_history.append({"role": "user", "content": user_prompt})
    conversation_history.append({"role": "assistant", "content": reply})
    return reply

# /start command
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    await update.message.reply_text(
        "👋 **Deterministic Local AI Assistant**\n\n"
        "⚡ **Direct Tool Commands (Instant / ~15s):**\n"
        "• `/time` -> Current system date & time\n"
        "• `/search <query>` -> Live DuckDuckGo search + AI summary\n"
        "• `/read <url>` -> Extract & summarize webpage\n"
        "• `/emails` -> Check unread emails\n"
        "• `/calendar [YYYY-MM-DD]` -> Check events\n"
        "• `/resume` -> View your local resume summary\n"
        "• `/fit <Role> | <Skills>` -> Calculate job fit percentage\n"
        "• `/clear` -> Reset chat history\n\n"
        "💬 Or simply send any message to chat directly!",
        parse_mode="Markdown"
    )

# /clear command
async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    global conversation_history
    conversation_history = [
        {"role": "system", "content": "You are a helpful, concise personal AI assistant. Keep responses clear and direct."}
    ]
    await update.message.reply_text("🧹 Conversation history cleared.")

# /time tool
async def time_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    t = get_current_time()
    msg = f"🕒 **Current Local Time:**\n• Date: `{t['date']}` ({t['day']})\n• Time: `{t['time']}`"
    # Inject into context so subsequent chats know the time
    update_system_context(f"Current system date/time is {t['datetime']} ({t['day']}).")
    await update.message.reply_text(msg, parse_mode="Markdown")

# /search tool
async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    if not context.args:
        await update.message.reply_text("Usage: `/search <query>`\nExample: `/search bangalore weather today`", parse_mode="Markdown")
        return

    query = " ".join(context.args)
    status_msg = await update.message.reply_text(f"🔍 Searching DuckDuckGo for: `{query}`...", parse_mode="Markdown")
    
    # 1. Python executes search instantly
    results = search_web(query, max_results=3)
    
    if not results or "error" in results[0]:
        await status_msg.edit_text(f"⚠️ Search error: {results[0].get('error', 'No results found')}")
        return

    # Format text preview
    snippets_text = ""
    for idx, r in enumerate(results, 1):
        snippets_text += f"{idx}. {r.get('title')}\nURL: {r.get('url')}\nSummary: {r.get('snippet')}\n\n"

    await status_msg.edit_text(f"🔍 Found results for `{query}`. Synthesizing answer...", parse_mode="Markdown")
    
    # 2. Local LLM summarizes search results (takes ~15-20s without heavy schemas)
    prompt = f"Based on the following search results, concisely answer: '{query}'"
    answer = await ask_llm(prompt, context_info=snippets_text)
    
    final_output = f"🔍 **Search Results for:** _{query}_\n\n{answer}\n\n**Sources:**\n"
    for r in results:
        final_output += f"• [{r.get('title')}]({r.get('url')})\n"
        
    await status_msg.edit_text(final_output[:4000], parse_mode="Markdown", disable_web_page_preview=True)

# /read tool
async def read_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    if not context.args:
        await update.message.reply_text("Usage: `/read <url>`\nExample: `/read https://example.com/article`", parse_mode="Markdown")
        return

    url = context.args[0]
    status_msg = await update.message.reply_text(f"📖 Scraping & extracting text from:\n`{url}`...", parse_mode="Markdown")
    
    data = read_webpage(url)
    if "error" in data:
        await status_msg.edit_text(f"⚠️ Error reading webpage: {data['error']}")
        return

    await status_msg.edit_text("📖 Page extracted. Summarizing key insights...", parse_mode="Markdown")
    prompt = f"Summarize the key takeaways from this article in 3-4 bullet points."
    answer = await ask_llm(prompt, context_info=f"Webpage content ({url}):\n{data['text']}")
    
    await status_msg.edit_text(f"📖 **Summary for:** {url}\n\n{answer}")

# /emails tool
async def emails_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    emails = list_unread_emails(max_results=5)
    out = "📬 **Unread Emails:**\n\n"
    for e in emails:
        out += f"• **From:** {e['sender']}\n  **Subject:** {e['subject']}\n  **Snippet:** {e['snippet']}\n\n"
    
    update_system_context(f"User unread emails:\n{out}")
    await update.message.reply_text(out, parse_mode="Markdown")

# /calendar tool
async def calendar_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    date_str = context.args[0] if context.args else datetime.now().strftime("%Y-%m-%d")
    events = check_calendar_events(date_str)
    
    if not events:
        out = f"📅 No events scheduled for `{date_str}`."
    else:
        out = f"📅 **Schedule for {date_str}:**\n\n"
        for ev in events:
            out += f"• **{ev['title']}**\n  Time: {ev['start']} to {ev['end']}\n  Location: {ev.get('location', 'N/A')}\n\n"
            
    update_system_context(f"User schedule for {date_str}:\n{out}")
    await update.message.reply_text(out, parse_mode="Markdown")

# /resume tool
async def resume_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    res = get_my_resume_summary()
    if "error" in res:
        await update.message.reply_text(f"⚠️ {res['error']}")
        return

    skills = ", ".join(res.get("skills_detected", []))
    roles = ", ".join(res.get("target_roles", []))
    out = (
        f"📄 **Your Resume Profile:**\n"
        f"• **Education:** {res['education']}\n"
        f"• **Target Roles:** {roles}\n"
        f"• **Skills Detected ({len(res.get('skills_detected', []))}):** `{skills}`\n"
    )
    update_system_context(f"User Resume Context:\n{res['resume_preview']}")
    await update.message.reply_text(out, parse_mode="Markdown")

# /fit tool
async def fit_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    full_arg = " ".join(context.args)
    if not full_arg or "|" not in full_arg:
        await update.message.reply_text("Usage: `/fit <Job Title> | <Required Skills>`\nExample: `/fit Junior AI Engineer | Python, PyTorch, Docker, AWS`", parse_mode="Markdown")
        return

    parts = full_arg.split("|", 1)
    title = parts[0].strip()
    skills = parts[1].strip()

    data = analyze_job_fit(job_title=title, required_skills=skills)
    
    msg = (
        f"🎯 **Job Fit Analysis for:** `{data['job_title']}`\n\n"
        f"• **Match Score:** `{data['match_percentage']}%` ({data['assessment']})\n"
        f"• **Recommended:** `{'✅ Yes' if data['is_recommended'] else '❌ No'}`\n\n"
        f"✅ **Matching Skills:** `{', '.join(data['matching_skills']) or 'None'}`\n"
        f"⚠️ **Missing Skills:** `{', '.join(data['missing_skills']) or 'None'}`\n"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

# /agent command (Unified router that accepts `/agent <tool_name>` or `/agent <query>`)
async def agent_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    if not context.args:
        await start_command(update, context)
        return

    subcommand = context.args[0].lower()
    sub_args = context.args[1:]

    # Map subcommands to direct tools
    if subcommand in ("time", "clock", "date"):
        await time_command(update, context)
    elif subcommand in ("search", "web", "google"):
        context.args = sub_args
        await search_command(update, context)
    elif subcommand in ("read", "scrape", "url"):
        context.args = sub_args
        await read_command(update, context)
    elif subcommand in ("emails", "email", "mail"):
        await emails_command(update, context)
    elif subcommand in ("calendar", "cal", "schedule"):
        context.args = sub_args
        await calendar_command(update, context)
    elif subcommand in ("resume", "profile", "cv"):
        await resume_command(update, context)
    elif subcommand in ("fit", "match"):
        context.args = sub_args
        await fit_command(update, context)
    else:
        # Fallback: treat as a general search & answer query!
        context.args = context.args
        await search_command(update, context)

# Direct chat message handler
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return

    user_text = update.message.text
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)

    try:
        reply = await ask_llm(user_text)
        await update.message.reply_text(reply)
    except Exception as e:
        await update.message.reply_text(f"⚠️ Error: {str(e)}")

def main():
    if not BOT_TOKEN or not ALLOWED_USER_ID:
        print("[Error] Please configure TELEGRAM_BOT_TOKEN and TELEGRAM_ALLOWED_USER_ID in .env!")
        return

    print("=" * 60)
    print("  Deterministic Telegram Local AI Assistant")
    print(f"  Target LLM: {Config.LLM_MODEL} @ {Config.LLM_BASE_URL}")
    print(f"  Authorized User ID: {ALLOWED_USER_ID}")
    print("=" * 60)

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Register deterministic commands
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", start_command))
    app.add_handler(CommandHandler("clear", clear_command))
    app.add_handler(CommandHandler("time", time_command))
    app.add_handler(CommandHandler("search", search_command))
    app.add_handler(CommandHandler("read", read_command))
    app.add_handler(CommandHandler("emails", emails_command))
    app.add_handler(CommandHandler("calendar", calendar_command))
    app.add_handler(CommandHandler("resume", resume_command))
    app.add_handler(CommandHandler("fit", fit_command))
    app.add_handler(CommandHandler("agent", agent_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("🤖 Bot is live! Listening for deterministic commands...")
    app.run_polling()

if __name__ == "__main__":
    main()