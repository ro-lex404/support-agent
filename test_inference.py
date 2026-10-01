import time
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8080/v1",
    api_key="not-needed"
)

prompt = "Say hello, and give a one-sentence tip for a 4th-year student learning to build autonomous AI agents."

print(f"Sending prompt to local llama-server: '{prompt}'")
start_time = time.time()

try:
    response = client.chat.completions.create(
        model="qwen2.5-3b-instruct",
        messages=[
            {"role": "system", "content": "You are a concise AI assistant."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=100,
        temperature=0.7
    )
    elapsed = time.time() - start_time
    content = response.choices[0].message.content
    usage = response.usage

    print("\n" + "=" * 50)
    print("RESPONSE FROM LOCAL MODEL:")
    print("=" * 50)
    print(content)
    print("=" * 50)
    print(f"Time taken: {elapsed:.2f} seconds")
    if usage:
        print(f"Tokens generated: {usage.completion_tokens}")
        if elapsed > 0:
            print(f"Speed: {usage.completion_tokens / elapsed:.2f} tokens/sec")

except Exception as e:
    print(f"\n[Error connecting to server]: {e}")
