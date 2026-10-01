import sys
import os
from openai import OpenAI
from config import Config

VERBOSITY_CONFIGS = {
    "low": {
        "max_tokens": 200,
        "temperature": 0.3,
        "reasoning_budget": 0,
        "system_prompt": "You are a direct, concise AI assistant. Provide the final answer directly without any preamble or filler.",
        "desc": "Low (Direct & Fast, ~200 tokens max, thinking disabled)"
    },
    "medium": {
        "max_tokens": 450,
        "temperature": 0.5,
        "reasoning_budget": 0,
        "system_prompt": "You are a helpful, clear, and balanced AI assistant. Provide complete and informative answers directly.",
        "desc": "Medium (Balanced, ~450 tokens max, thinking disabled)"
    },
    "high": {
        "max_tokens": 1400,
        "temperature": 0.7,
        "reasoning_budget": -1,
        "system_prompt": "You are an in-depth research and academic AI assistant. When answering, explore multiple angles, break down trade-offs, and provide comprehensive code/explanations.",
        "desc": "High (Deep Research & Full Thinking, ~1400 tokens max, thinking enabled)"
    }
}

def main():
    current_mode = "low"
    
    print("=" * 65)
    print("  Direct Local LLM Chat (Terminal)")
    print(f"  Connected to: {Config.LLM_MODEL} @ {Config.LLM_BASE_URL}")
    print("  Commands:")
    print("    /mode low | medium | high   -> Switch verbosity & depth")
    print("    clear                       -> Reset conversation history")
    print("    exit                        -> Quit")
    print(f"  Current Mode: {VERBOSITY_CONFIGS[current_mode]['desc']}")
    print("=" * 65)

    client = OpenAI(
        base_url=Config.LLM_BASE_URL,
        api_key=Config.LLM_API_KEY
    )

    history = [
        {"role": "system", "content": VERBOSITY_CONFIGS[current_mode]["system_prompt"]}
    ]

    while True:
        try:
            user_input = input(f"\nYou [{current_mode}]: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye!")
            break

        if not user_input:
            continue

        if user_input.lower() in ("exit", "quit"):
            print("Goodbye!")
            break

        if user_input.lower() == "clear":
            history = [{"role": "system", "content": VERBOSITY_CONFIGS[current_mode]["system_prompt"]}]
            print("[Conversation history cleared]")
            continue

        if user_input.lower().startswith("/mode"):
            parts = user_input.split()
            if len(parts) > 1 and parts[1].lower() in VERBOSITY_CONFIGS:
                current_mode = parts[1].lower()
                history[0] = {"role": "system", "content": VERBOSITY_CONFIGS[current_mode]["system_prompt"]}
                print(f"[Switched mode to: {VERBOSITY_CONFIGS[current_mode]['desc']}]")
            else:
                print(f"[Usage]: /mode low | medium | high (Available: {list(VERBOSITY_CONFIGS.keys())})")
            continue

        history.append({"role": "user", "content": user_input})

        print("\nAssistant: ", end="", flush=True)

        cfg = VERBOSITY_CONFIGS[current_mode]
        try:
            # Stream tokens live as they are generated
            response_stream = client.chat.completions.create(
                model=Config.LLM_MODEL,
                messages=history,
                stream=True,
                max_tokens=cfg["max_tokens"],
                temperature=cfg["temperature"],
                extra_body={
                    "reasoning_budget": cfg["reasoning_budget"],
                    "chat_template_kwargs": {"reasoning": (cfg["reasoning_budget"] != 0)}
                }
            )

            assistant_reply = ""
            thinking_shown = False

            for chunk in response_stream:
                choice = chunk.choices[0]
                delta = choice.delta

                # 1. Handle reasoning / thinking tokens (Qwen 3.5 / DeepSeek style)
                reasoning = getattr(delta, "reasoning_content", None) or ""
                if reasoning:
                    if not thinking_shown:
                        print("\n[Thinking...]\n", end="", flush=True)
                        thinking_shown = True
                    print(reasoning, end="", flush=True)

                # 2. Handle actual response tokens
                content = delta.content or ""
                if content:
                    if thinking_shown:
                        print("\n\n[Answer]:\n", end="", flush=True)
                        thinking_shown = False
                    assistant_reply += content
                    print(content, end="", flush=True)

            print() # Newline after response completes
            history.append({"role": "assistant", "content": assistant_reply})

        except Exception as e:
            print(f"\n[Error communicating with model]: {e}")
            print(f"Make sure llama-server is running on {Config.LLM_BASE_URL}")

if __name__ == "__main__":
    main()
