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

# 2. Local LLM Client with generous timeout (15 mins) to prevent connection drops on low-power CPU
client = OpenAI(
    base_url=Config.LLM_BASE_URL,
    api_key=Config.LLM_API_KEY,
    timeout=900.0
)

# 3. Context & Sliding Window Management
# On a dual-core CPU (~0.96 tokens/sec prefill), we strictly constrain prompt size to under 150 tokens.
MAX_HISTORY_TURNS = 2  # Retains system prompt + last 2 turns (max 4 user/assistant messages)

BASE_SYSTEM_PROMPT = (
    "You are a helpful, factual, and concise personal AI assistant. "
    "Provide direct, high-value answers without filler or repetition. "
    "Keep answers strictly relevant to the question."
)

conversation_history = [
    {"role": "system", "content": BASE_SYSTEM_PROMPT}
]

def is_authorized(update: Update) -> bool:
    return update.effective_user and update.effective_user.id == ALLOWED_USER_ID

def trim_history():
    """Maintains system prompt at index 0 and evicts older messages beyond MAX_HISTORY_TURNS."""
    global conversation_history
    if len(conversation_history) > 1 + (2 * MAX_HISTORY_TURNS):
        conversation_history = [conversation_history[0]] + conversation_history[-(2 * MAX_HISTORY_TURNS):]

def set_system_context(info_text: str):
    """Safely sets dynamic factual context in the system prompt without unbounded token growth."""
    clean_info = info_text.strip()[:200]
    conversation_history[0]["content"] = f"{BASE_SYSTEM_PROMPT}\n\n[Active Context]:\n{clean_info}"

async def safe_reply(target, text: str, edit_msg=None, disable_preview: bool = True):
    """Safely sends or edits text in Telegram, falling back to plain text if Markdown parsing fails."""
    trimmed = text[:4000]
    try:
        if edit_msg:
            return await edit_msg.edit_text(trimmed, parse_mode="Markdown", disable_web_page_preview=disable_preview)
        else:
            return await target.reply_text(trimmed, parse_mode="Markdown", disable_web_page_preview=disable_preview)
    except Exception:
        if edit_msg:
            return await edit_msg.edit_text(trimmed, disable_web_page_preview=disable_preview)
        else:
            return await target.reply_text(trimmed, disable_web_page_preview=disable_preview)

async def ask_llm(user_prompt: str, context_info: str = "", isolated: bool = False, max_tokens: int = 120) -> str:
    """
    Safely queries the local LLM:
    - isolated=True: used for search/read synthesis, passes ONLY system prompt + retrieved snippet
      to avoid evaluating bloated history.
    - isolated=False: used for natural conversational chat, passes sliding window history.
    - Enforces max_tokens to prevent CPU generation stalls.
    """
    if isolated:
        messages = [conversation_history[0]]
    else:
        trim_history()
        messages = list(conversation_history)

    if context_info:
        full_content = (
            f"Retrieved Facts:\n{context_info.strip()}\n\n"
            f"User Question: {user_prompt}\n\n"
            f"Instruction: Answer concisely in 2-3 direct sentences based ONLY on the retrieved facts above. No fluff."
        )
    else:
        full_content = user_prompt

    messages.append({"role": "user", "content": full_content})

    loop = asyncio.get_running_loop()
    try:
        response = await loop.run_in_executor(
            None,
            lambda: client.chat.completions.create(
                model=Config.LLM_MODEL,
                messages=messages,
                max_tokens=max_tokens,
                temperature=0.3,
                extra_body={"reasoning_budget": 0}
            )
        )
        reply = (response.choices[0].message.content or "").strip()
        if not reply:
            reply = "(No response generated)"
    except Exception as e:
        reply = f"⚠️ Generation notice: {str(e)}"

    # Append to sliding history so follow-up questions work
    conversation_history.append({"role": "user", "content": user_prompt})
    conversation_history.append({"role": "assistant", "content": reply})
    trim_history()

    return reply

# /start and /help command
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    text = (
        "👋 **Deterministic Local AI Assistant**\n\n"
        "⚡ **Direct Tool Commands (Instant / ~15s):**\n"
        "• `/time` -> Current system date & time\n"
        "• `/search <query>` -> DuckDuckGo search + AI summary\n"
        "• `/read <url>` -> Extract & summarize webpage\n"
        "• `/emails` -> Check unread emails\n"
        "• `/calendar [YYYY-MM-DD]` -> Check events\n"
        "• `/resume` -> View local resume summary\n"
        "• `/fit <Role> | <Skills>` -> Calculate job fit\n"
        "• `/clear` -> Reset chat history & context\n\n"
        "💬 Or simply send any message to chat directly!"
    )
    await safe_reply(update.message, text)

# /clear command
async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    global conversation_history
    conversation_history = [
        {"role": "system", "content": BASE_SYSTEM_PROMPT}
    ]
    await safe_reply(update.message, "🧹 Conversation history cleared. Ready for fresh queries.")

# /time tool
async def time_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    t = get_current_time()
    msg = f"🕒 **Current Local Time:**\n• Date: `{t['date']}` ({t['day']})\n• Time: `{t['time']}`"
    
    # Store bounded fact in system context
    set_system_context(f"Current date/time: {t['datetime']} ({t['day']})")
    
    # Record into sliding history so follow-ups like 'what time is it' work naturally
    conversation_history.append({"role": "user", "content": "What is the current time and date?"})
    conversation_history.append({"role": "assistant", "content": f"The current date is {t['date']} ({t['day']}) and time is {t['time']}."})
    trim_history()
    
    await safe_reply(update.message, msg)

# /search tool
async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    if not context.args:
        await safe_reply(update.message, "Usage: `/search <query>`\nExample: `/search Ariana grande`")
        return

    query = " ".join(context.args)
    status_msg = await update.message.reply_text(f"🔍 Searching DuckDuckGo for: `{query}`...", parse_mode="Markdown")

    # 1. Python executes search instantly
    results = search_web(query, max_results=3)

    if not results or "error" in results[0]:
        err_msg = results[0].get("error", "No results found") if results else "No results found"
        await safe_reply(update.message, f"⚠️ Search error: {err_msg}", edit_msg=status_msg)
        return

    valid_results = [r for r in results if r.get("title") and r.get("url")]
    if not valid_results:
        await safe_reply(update.message, f"ℹ️ No relevant web results found for `{query}`.", edit_msg=status_msg)
        return

    await safe_reply(update.message, f"🔍 Found {len(valid_results)} results. Synthesizing concise answer...", edit_msg=status_msg)

    # 2. Build tightly bounded snippets (top 2 results, max 180 chars each = ~80 tokens)
    snippets_text = "\n".join([f"• {r['title']}: {r.get('snippet', '')[:180]}" for r in valid_results[:2]])

    # 3. Local LLM synthesizes answer with isolated=True (no history bloat, max 100 tokens generation)
    prompt = f"What are the key facts about '{query}'?"
    answer = await ask_llm(prompt, context_info=snippets_text, isolated=True, max_tokens=100)

    # 4. Format clean response with source links
    final_output = f"🔍 **Search Results for:** _{query}_\n\n{answer}\n\n**Sources:**\n"
    for r in valid_results[:3]:
        final_output += f"• [{r['title']}]({r['url']})\n"

    await safe_reply(update.message, final_output, edit_msg=status_msg, disable_preview=True)

# /read tool
async def read_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    if not context.args:
        await safe_reply(update.message, "Usage: `/read <url>`\nExample: `/read https://en.wikipedia.org/wiki/Artificial_intelligence`")
        return

    url = context.args[0]
    status_msg = await update.message.reply_text(f"📖 Fetching webpage text from:\n`{url}`...", parse_mode="Markdown")

    data = read_webpage(url)
    if "error" in data:
        await safe_reply(update.message, f"⚠️ Error reading webpage: {data['error']}", edit_msg=status_msg)
        return

    await safe_reply(update.message, "📖 Extracted page text. Summarizing key insights...", edit_msg=status_msg)
    prompt = "Summarize the key takeaways from this page excerpt in 2-3 concise bullet points:"
    answer = await ask_llm(prompt, context_info=data["text"], isolated=True, max_tokens=100)

    await safe_reply(update.message, f"📖 **Summary for:** {url}\n\n{answer}", edit_msg=status_msg)

# /emails tool
async def emails_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    emails = list_unread_emails(max_results=5)
    out = "📬 **Unread Emails:**\n\n"
    for e in emails:
        out += f"• **From:** {e['sender']}\n  **Subject:** {e['subject']}\n  **Snippet:** {e['snippet']}\n\n"

    set_system_context(f"Unread emails: {len(emails)} emails from {', '.join([e['sender'] for e in emails[:3]])}")
    conversation_history.append({"role": "user", "content": "Check unread emails."})
    conversation_history.append({"role": "assistant", "content": f"You have {len(emails)} unread emails. Recent senders: {', '.join([e['sender'] for e in emails[:3]])}."})
    trim_history()

    await safe_reply(update.message, out)

# /calendar tool
async def calendar_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    date_str = context.args[0] if context.args else datetime.now().strftime("%Y-%m-%d")
    events = check_calendar_events(date_str)

    if not events:
        out = f"📅 No events scheduled for `{date_str}`."
        summary = f"No events scheduled for {date_str}."
    else:
        out = f"📅 **Schedule for {date_str}:**\n\n"
        for ev in events:
            out += f"• **{ev['title']}**\n  Time: {ev['start']} to {ev['end']}\n  Location: {ev.get('location', 'N/A')}\n\n"
        summary = f"Events on {date_str}: {', '.join([ev['title'] for ev in events])}."

    set_system_context(summary)
    conversation_history.append({"role": "user", "content": f"Check calendar for {date_str}."})
    conversation_history.append({"role": "assistant", "content": summary})
    trim_history()

    await safe_reply(update.message, out)

# /resume tool
async def resume_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    res = get_my_resume_summary()
    if "error" in res:
        await safe_reply(update.message, f"⚠️ {res['error']}")
        return

    skills = ", ".join(res.get("skills_detected", []))
    roles = ", ".join(res.get("target_roles", []))
    out = (
        f"📄 **Your Resume Profile:**\n"
        f"• **Education:** {res['education']}\n"
        f"• **Target Roles:** {roles}\n"
        f"• **Skills Detected ({len(res.get('skills_detected', []))}):** `{skills}`\n"
    )
    set_system_context(f"Resume: {res['education']}, Skills: {skills[:120]}")
    conversation_history.append({"role": "user", "content": "Show my resume profile."})
    conversation_history.append({"role": "assistant", "content": f"Education: {res['education']}. Target roles: {roles}. Skills: {skills[:120]}."})
    trim_history()

    await safe_reply(update.message, out)

# /fit tool
async def fit_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    full_arg = " ".join(context.args)
    if not full_arg or "|" not in full_arg:
        await safe_reply(update.message, "Usage: `/fit <Job Title> | <Required Skills>`\nExample: `/fit Junior AI Engineer | Python, PyTorch, Docker, AWS`")
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
    await safe_reply(update.message, msg)

# /agent command (Unified router that accepts `/agent <tool_name>` or `/agent <query>`)
async def agent_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    if not context.args:
        await start_command(update, context)
        return

    subcommand = context.args[0].lower()
    sub_args = context.args[1:]

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
    if not user_text:
        return

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)

    try:
        reply = await ask_llm(user_text, isolated=False, max_tokens=120)
        await safe_reply(update.message, reply)
    except Exception as e:
        await safe_reply(update.message, f"⚠️ Error: {str(e)}")

def main():
    if not BOT_TOKEN or not ALLOWED_USER_ID:
        print("[Error] Please configure TELEGRAM_BOT_TOKEN and TELEGRAM_ALLOWED_USER_ID in .env!")
        return

    print("=" * 60)
    print("  Deterministic Telegram Local AI Assistant")
    print(f"  Target LLM: {Config.LLM_MODEL} @ {Config.LLM_BASE_URL}")
    print(f"  Authorized User ID: {ALLOWED_USER_ID}")
    print(f"  History Sliding Window: {MAX_HISTORY_TURNS} turns max")
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