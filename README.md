# Autonomous Support Agent (From Scratch)

A zero-framework, lightweight autonomous agent built in pure Python. Designed specifically for low-resource hardware (CPU-only, < 3GB disk, < 50MB idle RAM) with support for local models via `llama.cpp` (`llama-server`) or OpenAI-compatible endpoints.

---

## Architecture Overview

```
support-agent/
│
├── core/
│   ├── agent.py          # The pure Python ReAct loop (Reason -> Act -> Observe)
│   ├── llm_client.py     # OpenAI-compatible client interface
│   └── prompts.py        # System prompt builder with dynamic temporal grounding
│
├── tools/
│   ├── base.py           # ToolRegistry & @tool decorator for schema generation
│   └── mock_tools.py     # Realistic mock tools (emails, calendar, jobs, time)
│
├── config.py             # App configuration (.env loader)
├── main.py               # Runner CLI
├── requirements.txt      # Minimal Python dependencies
└── .env                  # Environment connection variables
```

---

## Quickstart

### 1. Create a Python Virtual Environment
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. Configure the Model Endpoint in `.env`

#### Option A: Free Cloud Testing (Instant, 0 local disk space)
Get a free API key from [Groq](https://console.groq.com) and set:
```env
LLM_BASE_URL="https://api.groq.com/openai/v1"
LLM_API_KEY="gsk_your_key_here"
LLM_MODEL="llama-3.3-70b-versatile"
```

#### Option B: Local `llama.cpp` (100% Offline & Private)
1. Download the pre-built CPU binary `llama-bXXXX-bin-win-cpu-x64.zip` from [llama.cpp releases](https://github.com/ggerganov/llama.cpp/releases).
2. Download a 4-bit GGUF model: `qwen2.5-3b-instruct-q4_k_m.gguf` (~2.05 GB).
3. Launch `llama-server.exe`:
   ```powershell
   .\bin\llama-server.exe -m .\models\qwen2.5-3b-instruct-q4_k_m.gguf -c 2048 -t 4 --port 8080
   ```
4. In `.env`:
   ```env
   LLM_BASE_URL="http://localhost:8080/v1"
   LLM_API_KEY="not-needed"
   LLM_MODEL="qwen2.5-3b-instruct"
   ```

### 3. Run the Agent
```powershell
python main.py
```

Or pass a custom prompt:
```powershell
python main.py "Find me junior AI job postings and tell me what skills they require."
```
