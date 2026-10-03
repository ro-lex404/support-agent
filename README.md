# Autonomous Support Agent (From Scratch)

A zero-framework, privacy-first, lightweight autonomous AI assistant built in pure Python. Designed from first principles to run on low-power consumer hardware (dual-core CPUs without AVX2 vector instructions, or 2 GB RAM Android tablets via Termux), controlled remotely and securely via Telegram.

---

## Key Highlights

- **Zero Heavy Frameworks:** Built in pure Python without LangChain, LlamaIndex, or AutoGen. Every mechanism—ReAct loops, OpenAI schema derivation, context pruning, prompt grounding, and HTTP clients—is explicit and transparent.
- **100% Private & Offline-Capable:** Runs against local `llama.cpp` (`llama-server`) GGUF models. No user data, messages, or resume details leave your local network.
- **Deterministic-First Tool Routing:** High-frequency tasks (calendar checks, email previews, resume parsing, job match scoring, web scraping) execute deterministically in Python in sub-second time (<0.01s). The local LLM is reserved strictly for synthesis and reasoning, saving massive compute.
- **Multi-Platform Deployment:**
  - **Windows Laptop:** Runs locally using `bin/llama-server.exe` with `Qwen3.5-4B-Q4_K_M.gguf`.
  - **Standalone Android Appliance:** Runs 24/7 on an idle Android tablet (e.g., Lenovo Tab M10 HD, 2 GB RAM) via native Termux + PRoot Ubuntu, pushing **10–15 tokens/second** using `Qwen3.5-0.8B-Q4_K_M.gguf`.
- **Multiple Frontends:** Secure Telegram Bot (with long-polling and user ID whitelist), modern streaming web chat UI (port 3000), and terminal CLI.

---

## System Architecture

```
support-agent/
│
├── core/
│   ├── agent.py            # Framework-free ReAct loop (Reason -> Act -> Observe)
│   ├── llm_client.py       # Robust OpenAI-compatible client interface
│   └── prompts.py          # Grounded system prompts with dynamic date/time injection
│
├── tools/
│   ├── base.py             # ToolRegistry & @tool decorator (auto-derives JSON schemas)
│   ├── mock_tools.py       # Realistic mock productivity tools (time, email, calendar, jobs)
│   ├── web_tools.py        # Live DuckDuckGo search & BeautifulSoup web scraper
│   └── resume_tools.py     # Local resume parser & deterministic job fit matching engine
│
├── data/
│   └── resume.txt          # Plaintext candidate resume for local skill extraction
│
├── telegram_agent.py       # Autonomous Telegram bot with sliding window memory & keep-typing heartbeat
├── web_chat.py             # ChatGPT/Claude-style streaming browser UI (FastAPI/HTML/JS)
├── chat_cli.py             # Interactive terminal chat with execution modes (low/med/high)
├── main.py                 # Single-shot command line runner
│
├── start_llama_server.ps1  # Automated PowerShell launcher for local llama-server
├── config.py               # Unified application configuration (.env loader)
└── requirements.txt        # Minimal Python dependencies
```

---

## Tool Registry & Capabilities

The system includes **8 deterministic and live tools**:

| Tool | Source File | Description | Execution Speed |
| :--- | :--- | :--- | :--- |
| `get_current_time` | `tools/mock_tools.py` | Retrieves system date, 24h/12h time, and day of week. | Instant (<0.001s) |
| `list_unread_emails` | `tools/mock_tools.py` | Fetches unread inbox messages with sender, subject, and snippet. | Instant (<0.001s) |
| `check_calendar_events` | `tools/mock_tools.py` | Checks meetings, reviews, and conflicts for any `YYYY-MM-DD`. | Instant (<0.001s) |
| `search_job_postings` | `tools/mock_tools.py` | Searches job listings matching a role keyword. | Instant (<0.001s) |
| `search_web` | `tools/web_tools.py` | Live anonymous search via DuckDuckGo (bounded to 220 chars/snippet). | ~0.4s |
| `read_webpage` | `tools/web_tools.py` | Scrapes & extracts clean article body text (bounded to 450 chars). | ~0.8s |
| `get_my_resume_summary` | `tools/resume_tools.py` | Reads `data/resume.txt` and auto-extracts detected technical skills. | Instant (<0.001s) |
| `analyze_job_fit` | `tools/resume_tools.py` | Deterministically compares job requirements against resume skills; returns match %, matching skills, missing skills, and fit rating. | Instant (<0.001s) |

---

## Telegram Bot Interface (`telegram_agent.py`)

The Telegram bot acts as the central remote control for your agent. It is fortified with several edge-computing guardrails:

### Supported Commands
- `/time` (or `/agent time`) — Displays current system time and date.
- `/search <query>` (or `/agent search <query>`) — Live DuckDuckGo web search + concise AI summary + clickable source links.
- `/read <url>` (or `/agent read <url>`) — Scrapes webpage and generates a 3-bullet takeaway summary.
- `/emails` (or `/agent emails`) — Checks unread emails.
- `/calendar [YYYY-MM-DD]` (or `/agent calendar`) — Checks scheduled events for today or a specific date.
- `/resume` (or `/agent resume`) — Displays your parsed resume profile and detected skills.
- `/fit <Job Title> | <Required Skills>` — Instant skill-gap analysis and hiring recommendation.
- `/agent <any general question>` — Automatically routes to web search and synthesizes an answer.
- `/clear` — Clears conversation history and resets active context.
- `Any direct message` — Natural conversational chat with sliding window context.

### Built-In Reliability Guardrails
1. **Sliding Context Window (`MAX_HISTORY_TURNS = 2`):** Keeps only `messages[0]` (system prompt) + the last 2 user/assistant turn pairs (max 4 messages). Older turns are automatically evicted to prevent prompt bloat on low-power CPUs.
2. **Isolated Tool Synthesis (`isolated=True`):** For `/search` and `/read`, the prompt includes *only* the system prompt and the newly retrieved snippets. Past chat history is not re-evaluated, keeping prompts under ~150 tokens.
3. **Background Typing Heartbeat (`keep_typing`):** Telegram clears the `"typing..."` action after 5 seconds. An async background task pulses the typing indicator every 4 seconds until LLM generation finishes, giving real-time feedback.
4. **Safe Markdown Parser (`safe_reply`):** Automatically catches unescaped Markdown symbols (`_`, `*`, `[`) common in web snippets and gracefully falls back to plain text, preventing silent message delivery failures.
5. **Cryptographic Gatekeeper:** Enforces `ALLOWED_USER_ID` checks on every message. Unauthorized users receive no response.

---

## Quickstart (Windows Setup)

### 1. Environment Setup
```powershell
# Clone the repository
git clone https://github.com/ro-lex404/support-agent.git
cd support-agent

# Create and activate virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure `.env`
Create a `.env` file in the project root:
```env
# Local LLM Server
LLM_BASE_URL="http://localhost:8080/v1"
LLM_API_KEY="local"
LLM_MODEL="qwen"

# Telegram Bot Credentials (Get from @BotFather and @userinfobot)
TELEGRAM_BOT_TOKEN="your_telegram_bot_token"
TELEGRAM_ALLOWED_USER_ID=your_numeric_telegram_user_id
```

### 3. Launch `llama-server`
Place your quantized `.gguf` model in the `models/` directory (e.g., `Qwen3.5-4B-Q4_K_M.gguf` or `Qwen2.5-3B-Instruct-Q4_K_M.gguf`), then run:
```powershell
.\start_llama_server.ps1
```
*(Or run `bin\llama-server.exe -m models\your_model.gguf -c 2048 -t 2 --reasoning off --port 8080`)*

### 4. Run the Agent Frontends
- **Telegram Bot:**
  ```powershell
  python telegram_agent.py
  ```
- **Web Browser UI:**
  ```powershell
  python web_chat.py
  # Open http://localhost:3000 in your browser
  ```
- **Terminal CLI:**
  ```powershell
  python chat_cli.py
  ```

---

## Standalone Android Tablet Server (Termux + PRoot)

You can turn an old Android tablet (e.g., Lenovo Tab M10 HD, MediaTek Helio P22T, 2 GB RAM) into a dedicated, silent, 24/7 personal AI server plugged into a wall charger.

### Architecture on Android
- **Native Termux:** Runs `llama-server` natively with ARM NEON SIMD acceleration for maximum matrix-multiplication performance (**10–15 tokens/second**).
- **PRoot Ubuntu:** Runs Python 3 and `telegram_agent.py` using standard `glibc` `aarch64` wheels (avoiding Rust/`jiter` compilation issues).
- Both communicate locally over `http://127.0.0.1:8080`.

### Step-by-Step Tablet Setup

1. **Install Termux:** Download from [F-Droid](https://f-droid.org/en/packages/com.termux/) (do not use Google Play).
2. **Prevent Android Doze/Sleep:**
   ```bash
   termux-wake-lock
   ```
   *(Also set Termux battery usage to "Unrestricted" in Android Settings).*
3. **Compile `llama.cpp` in Native Termux:**
   ```bash
   pkg update -y && pkg install -y git cmake clang build-essential
   git clone https://github.com/ggerganov/llama.cpp
   cd llama.cpp
   cmake -B build -DGGML_OPENMP=OFF
   cmake --build build --config Release -j2 --target llama-server
   ```
   *(Note: Use `-j2` on 2 GB RAM devices to prevent compiler Out-Of-Memory crashes).*
4. **Download the 0.8B Model (~530 MB):**
   ```bash
   mkdir -p ~/models && cd ~/models
   curl -L -o Qwen3.5-0.8B-Q4_K_M.gguf "https://huggingface.co/lmstudio-community/Qwen3.5-0.8B-GGUF/resolve/main/Qwen3.5-0.8B-Q4_K_M.gguf"
   ```
5. **Start `llama-server` (Session 1):**
   ```bash
   cd ~/llama.cpp/build/bin
   ./llama-server -m ~/models/Qwen3.5-0.8B-Q4_K_M.gguf -c 2048 -t 8 --reasoning off --port 8080
   ```
6. **Set up PRoot Ubuntu for the Telegram Agent (Session 2):**
   ```bash
   pkg install -y proot-distro
   proot-distro install ubuntu
   proot-distro login ubuntu

   # Inside Ubuntu:
   apt update && apt install -y python3 python3-pip git
   git clone https://github.com/ro-lex404/support-agent.git
   cd support-agent
   pip3 install -r requirements.txt

   # Configure your .env and run:
   python3 telegram_agent.py
   ```

---

## Critical Engineering Insights & Lessons Learned

1. **The Low-Power CPU Prompt Prefill Bottleneck:**
   On dual-core CPUs without AVX2 (like the Intel Pentium 5405U), prompt evaluation runs at ~0.96 tokens/second. A raw search snippet dump totaling 1,020 tokens took ~17.7 minutes just to prefill before generating token #1, hitting HTTP timeouts. Bounding search snippets to 220 characters dropped prompt size to ~190 tokens, bringing response time to under 2 minutes.
2. **Jinja Role Alternation in Qwen 3.5:**
   The Qwen 3.5 ChatML template strictly enforces that `role: "system"` can only appear once, at `messages[0]`. Appending dynamic context as system messages mid-conversation causes an unrecoverable 500 Jinja template exception. Solved by updating `messages[0]` in-place and inlining retrieved facts into user turns.
3. **Small Models (0.8B) + Deterministic RAG:**
   An 800M parameter model lacks the capacity to store encyclopedic trivia in its weights (leading to hallucinations if asked raw trivia in direct chat). However, its *reading comprehension* is excellent. Combining deterministic DuckDuckGo retrieval with a 0.8B model delivers accurate, grounded answers in 2–3 seconds at 15 tokens/sec on mobile hardware.

---

## License

MIT License. Free for personal, academic, and commercial exploration.
