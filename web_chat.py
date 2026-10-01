import http.server
import socketserver
import json
import urllib.request
import webbrowser
from config import Config

PORT = 3000

HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Local AI Chat</title>
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <style>
        :root {
            --bg-main: #131418;
            --bg-sidebar: #1a1b22;
            --bg-chat: #1e1f29;
            --user-bubble: #2b2d3d;
            --accent: #5e6ad2;
            --accent-hover: #707ce6;
            --text-main: #e6e8ee;
            --text-muted: #8c90a4;
            --border: #2d303e;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }
        body { background: var(--bg-main); color: var(--text-main); display: flex; flex-direction: column; height: 100vh; overflow: hidden; }
        
        /* Header */
        header {
            background: var(--bg-sidebar);
            border-bottom: 1px solid var(--border);
            padding: 12px 24px;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        .header-title { font-size: 16px; font-weight: 600; display: flex; align-items: center; gap: 8px; }
        .badge { background: #233526; color: #4ade80; font-size: 11px; padding: 2px 8px; border-radius: 12px; font-weight: 500; }
        .clear-btn { background: transparent; border: 1px solid var(--border); color: var(--text-muted); padding: 6px 12px; border-radius: 6px; cursor: pointer; font-size: 12px; transition: all 0.2s; }
        .clear-btn:hover { background: var(--border); color: var(--text-main); }

        .controls-group { display: flex; align-items: center; gap: 12px; }
        .toggle-group {
            display: flex;
            background: var(--bg-main);
            padding: 3px;
            border-radius: 8px;
            border: 1px solid var(--border);
        }
        .toggle-btn {
            background: transparent;
            border: none;
            color: var(--text-muted);
            font-size: 11.5px;
            font-weight: 500;
            padding: 4px 10px;
            border-radius: 6px;
            cursor: pointer;
            transition: all 0.2s;
        }
        .toggle-btn:hover { color: var(--text-main); }
        .toggle-btn.active {
            background: var(--accent);
            color: white;
        }

        /* Chat Area */
        #chat-container {
            flex: 1;
            overflow-y: auto;
            padding: 24px;
            display: flex;
            flex-direction: column;
            gap: 20px;
            max-width: 860px;
            width: 100%;
            margin: 0 auto;
        }
        .message-row { display: flex; gap: 12px; width: 100%; }
        .message-row.user { justify-content: flex-end; }
        .avatar { width: 32px; height: 32px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 14px; font-weight: 600; flex-shrink: 0; }
        .avatar.assistant { background: var(--accent); color: white; }
        .avatar.user { background: #3b82f6; color: white; }
        
        .bubble {
            max-width: 80%;
            padding: 12px 18px;
            border-radius: 14px;
            line-height: 1.5;
            font-size: 14.5px;
            word-break: break-word;
        }
        .message-row.user .bubble {
            background: var(--user-bubble);
            color: var(--text-main);
            border-bottom-right-radius: 2px;
        }
        .message-row.assistant .bubble {
            background: var(--bg-chat);
            color: var(--text-main);
            border-bottom-left-radius: 2px;
            border: 1px solid var(--border);
        }
        .bubble pre { background: #0c0d11; padding: 10px; border-radius: 6px; overflow-x: auto; margin: 8px 0; }
        .bubble code { font-family: Consolas, Monaco, monospace; font-size: 13px; }
        .bubble p:not(:last-child) { margin-bottom: 8px; }

        /* Input Area */
        footer {
            background: var(--bg-main);
            padding: 16px 24px 24px;
            border-top: 1px solid var(--border);
        }
        .input-box-wrapper {
            max-width: 860px;
            margin: 0 auto;
            position: relative;
            background: var(--bg-chat);
            border: 1px solid var(--border);
            border-radius: 12px;
            display: flex;
            align-items: flex-end;
            padding: 10px 14px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.25);
            transition: border-color 0.2s;
        }
        .input-box-wrapper:focus-within { border-color: var(--accent); }
        textarea {
            flex: 1;
            background: transparent;
            border: none;
            outline: none;
            color: var(--text-main);
            font-size: 14.5px;
            line-height: 1.4;
            max-height: 150px;
            resize: none;
        }
        button.send-btn {
            background: var(--accent);
            border: none;
            color: white;
            width: 32px;
            height: 32px;
            border-radius: 8px;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            margin-left: 8px;
            transition: background 0.2s;
        }
        button.send-btn:hover { background: var(--accent-hover); }
        button.send-btn:disabled { opacity: 0.4; cursor: not-allowed; }
        .status-bar { max-width: 860px; margin: 6px auto 0; font-size: 11px; color: var(--text-muted); text-align: center; }
    </style>
</head>
<body>
    <header>
        <div class="header-title">
            <span>Local Qwen 2.5 (3B)</span>
            <span class="badge">100% Offline</span>
        </div>
        <div class="controls-group">
            <div class="toggle-group" id="verbosity-group">
                <button class="toggle-btn active" id="btn-low" onclick="setVerbosity('low')">⚡ Low (Concise)</button>
                <button class="toggle-btn" id="btn-medium" onclick="setVerbosity('medium')">⚖️ Medium</button>
                <button class="toggle-btn" id="btn-high" onclick="setVerbosity('high')">🔬 High (Research)</button>
            </div>
            <button class="clear-btn" onclick="clearChat()">Clear Conversation</button>
        </div>
    </header>

    <div id="chat-container">
        <div class="message-row assistant">
            <div class="avatar assistant">AI</div>
            <div class="bubble">Hello! I am your local 3B model running offline on your computer. What would you like to discuss or learn today?</div>
        </div>
    </div>

    <footer>
        <div class="input-box-wrapper">
            <textarea id="prompt-input" rows="1" placeholder="Type a message... (Press Enter to send, Shift+Enter for new line)"></textarea>
            <button class="send-btn" id="send-btn" onclick="sendMessage()">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><line x1="22" y1="2" x2="11" y2="13"></line><polygon points="22 2 15 22 11 13 2 9 22 2"></polygon></svg>
            </button>
        </div>
        <div class="status-bar" id="status-bar">Ready &bull; Running directly via llama.cpp</div>
    </footer>

    <script>
        const chatContainer = document.getElementById('chat-container');
        const promptInput = document.getElementById('prompt-input');
        const sendBtn = document.getElementById('send-btn');
        const statusBar = document.getElementById('status-bar');

        const VERBOSITY_CONFIGS = {
            low: {
                max_tokens: 200,
                temperature: 0.3,
                reasoning_budget: 0,
                system_prompt: "You are a direct, concise AI assistant. Provide the final answer directly without any preamble or filler.",
                hint: "⚡ Low (Direct & Fast) • ~200 tokens max, thinking disabled"
            },
            medium: {
                max_tokens: 450,
                temperature: 0.5,
                reasoning_budget: 0,
                system_prompt: "You are a helpful, clear, and balanced AI assistant. Provide complete and informative answers directly.",
                hint: "⚖️ Medium (Balanced) • ~450 tokens max, thinking disabled"
            },
            high: {
                max_tokens: 1400,
                temperature: 0.7,
                reasoning_budget: -1,
                system_prompt: "You are an in-depth research and academic AI assistant. When answering, explore multiple angles, break down trade-offs, and provide comprehensive code/explanations.",
                hint: "🔬 High (Deep Research & Full Thinking) • ~1400 tokens max, thinking enabled"
            }
        };

        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        let currentVerbosity = 'low';

        function setVerbosity(level) {
            currentVerbosity = level;
            document.querySelectorAll('.toggle-btn').forEach(btn => btn.classList.remove('active'));
            const activeBtn = document.getElementById(`btn-${level}`);
            if (activeBtn) activeBtn.classList.add('active');
            
            // Dynamically update system prompt in memory
            history[0] = { role: "system", content: VERBOSITY_CONFIGS[level].system_prompt };
            statusBar.innerText = `Switched to ${VERBOSITY_CONFIGS[level].hint}`;
        }

        let history = [
            { role: "system", content: VERBOSITY_CONFIGS.low.system_prompt }
        ];

        promptInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });

        promptInput.addEventListener('input', () => {
            promptInput.style.height = 'auto';
            promptInput.style.height = (promptInput.scrollHeight) + 'px';
        });

        function clearChat() {
            history = [{ role: "system", content: VERBOSITY_CONFIGS[currentVerbosity].system_prompt }];
            chatContainer.innerHTML = `
                <div class="message-row assistant">
                    <div class="avatar assistant">AI</div>
                    <div class="bubble">Conversation cleared. What can I help you with?</div>
                </div>
            `;
            statusBar.innerText = `Ready • ${VERBOSITY_CONFIGS[currentVerbosity].hint}`;
        }

        async function sendMessage() {
            const text = promptInput.value.trim();
            if (!text) return;

            const config = VERBOSITY_CONFIGS[currentVerbosity];

            // Render user bubble
            appendMessage("user", text);
            history.push({ role: "user", content: text });
            
            promptInput.value = "";
            promptInput.style.height = 'auto';
            promptInput.disabled = true;
            sendBtn.disabled = true;
            statusBar.innerText = `Thinking & generating in ${currentVerbosity.toUpperCase()} mode on CPU...`;

            // Prepare assistant bubble for streaming
            const assistantBubble = appendMessage("assistant", "...");
            assistantBubble.innerText = "";
            let accumulatedReasoning = "";
            let accumulatedResponse = "";
            const startTime = performance.now();

            try {
                // Direct request to proxy endpoint
                const res = await fetch('/api/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        model: "Qwen3.5-4B-Q4_K_M.gguf",
                        messages: history,
                        stream: true,
                        max_tokens: config.max_tokens,
                        temperature: config.temperature,
                        reasoning_budget: config.reasoning_budget,
                        chat_template_kwargs: { reasoning: (config.reasoning_budget !== 0) }
                    })
                });

                if (!res.ok) throw new Error("HTTP error " + res.status);

                const reader = res.body.getReader();
                const decoder = new TextDecoder();
                let buffer = "";

                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;
                    buffer += decoder.decode(value, { stream: true });

                    const lines = buffer.split("\n");
                    buffer = lines.pop(); // Keep incomplete line

                    for (const line of lines) {
                        const trimmed = line.trim();
                        if (trimmed.startsWith("data: ")) {
                            const dataStr = trimmed.slice(6).trim();
                            if (dataStr === "[DONE]") break;
                            try {
                                const parsed = JSON.parse(dataStr);
                                const delta = parsed.choices?.[0]?.delta || {};
                                const reasoningToken = delta.reasoning_content || "";
                                const contentToken = delta.content || "";

                                if (reasoningToken) accumulatedReasoning += reasoningToken;
                                if (contentToken) accumulatedResponse += contentToken;

                                let html = "";
                                if (accumulatedReasoning) {
                                    html += `<details open style="margin-bottom:12px;background:#15161e;padding:10px 14px;border-radius:8px;border:1px solid #2d303e;color:#94a3b8;font-size:12.5px;"><summary style="cursor:pointer;font-weight:600;color:#818cf8;margin-bottom:6px;">💭 Thought Process</summary><div style="white-space:pre-wrap;line-height:1.4;">${escapeHtml(accumulatedReasoning)}</div></details>`;
                                }
                                if (accumulatedResponse) {
                                    html += marked.parse(accumulatedResponse);
                                }
                                assistantBubble.innerHTML = html;
                                chatContainer.scrollTop = chatContainer.scrollHeight;
                            } catch (e) {}
                        }
                    }
                }

                history.push({ role: "assistant", content: accumulatedResponse || accumulatedReasoning });
                const elapsedSec = ((performance.now() - startTime) / 1000).toFixed(1);
                statusBar.innerText = `Ready • Generated ${currentVerbosity} response in ${elapsedSec}s`;

            } catch (err) {
                assistantBubble.innerHTML = `<span style="color:#ef4444;">Error: ${err.message}. Make sure llama-server is running on :8080</span>`;
                statusBar.innerText = "Error connecting to model.";
            } finally {
                promptInput.disabled = false;
                sendBtn.disabled = false;
                promptInput.focus();
            }
        }

        function appendMessage(role, text) {
            const row = document.createElement('div');
            row.className = `message-row ${role}`;
            
            const avatar = document.createElement('div');
            avatar.className = `avatar ${role}`;
            avatar.innerText = role === 'user' ? 'U' : 'AI';

            const bubble = document.createElement('div');
            bubble.className = 'bubble';
            bubble.innerHTML = marked.parse(text);

            if (role === 'user') {
                row.appendChild(bubble);
                row.appendChild(avatar);
            } else {
                row.appendChild(avatar);
                row.appendChild(bubble);
            }

            chatContainer.appendChild(row);
            chatContainer.scrollTop = chatContainer.scrollHeight;
            return bubble;
        }
    </script>
</body>
</html>
"""

class ChatProxyHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_PAGE.encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == "/api/chat":
            content_length = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(content_length)

            # Forward directly to llama-server
            target_url = f"{Config.LLM_BASE_URL.rstrip('/')}/chat/completions"
            req = urllib.request.Request(
                target_url,
                data=post_data,
                headers={"Content-Type": "application/json"}
            )

            try:
                with urllib.request.urlopen(req) as resp:
                    self.send_response(resp.status)
                    for header, value in resp.getheaders():
                        if header.lower() in ("content-type", "cache-control", "connection"):
                            self.send_header(header, value)
                    self.end_headers()

                    # Stream data back chunk by chunk
                    while True:
                        chunk = resp.read(64)
                        if not chunk:
                            break
                        self.wfile.write(chunk)
                        self.wfile.flush()
            except Exception as e:
                self.send_response(502)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

def main():
    print("=" * 60)
    print("  Local ChatGPT-Style Web Interface")
    print(f"  Forwarding to: {Config.LLM_BASE_URL}")
    print(f"  Web UI running at: http://localhost:{PORT}")
    print("=" * 60)
    
    # Try opening the browser automatically
    webbrowser.open(f"http://localhost:{PORT}")
    
    with socketserver.TCPServer(("", PORT), ChatProxyHandler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down web interface.")

if __name__ == "__main__":
    main()
