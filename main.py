import sys
from config import Config
from core.llm_client import get_llm_client
from core.prompts import get_system_prompt
from core.agent import Agent
from tools.base import registry

# Import mock tools to trigger registration
import tools.mock_tools

def main():
    print("=" * 60)
    print("  Autonomous Agent Harness (From Scratch)")
    print(f"  Target LLM: {Config.LLM_MODEL} @ {Config.LLM_BASE_URL}")
    print("=" * 60)

    # 1. Initialize client and prompt
    client = get_llm_client()
    system_prompt = get_system_prompt(
        custom_instructions="Be concise. If checking scheduling conflicts, always specify both the proposed event and the conflicting event times."
    )

    # 2. Instantiate agent with our tool registry
    agent = Agent(
        client=client,
        model=Config.LLM_MODEL,
        system_prompt=system_prompt,
        registry=registry,
        max_iterations=Config.MAX_ITERATIONS,
        verbose=True
    )

    # 3. Default demo query or user query
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
    else:
        query = "Check my unread emails for any interview requests. If you find one, check my calendar for that date to see if there is a scheduling conflict."

    print(f"\n[User Query]: {query}\n")
    
    try:
        final_answer = agent.run(query)
        print("\n" + "=" * 60)
        print("  AGENT FINAL ANSWER")
        print("=" * 60)
        print(final_answer)
        print("=" * 60 + "\n")
    except ConnectionError:
        print("\n[Connection Error]: Could not reach the LLM server at " + Config.LLM_BASE_URL)
        print("Please ensure your local llama-server or alternative endpoint is running.")

if __name__ == "__main__":
    main()
