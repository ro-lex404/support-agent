from datetime import datetime

DEFAULT_BASE_PROMPT = """You are a helpful, autonomous personal AI assistant.
Your goal is to assist the user by answering queries, checking information, and executing tasks using available tools.

Key Guidelines:
1. Always check the current date and time provided below when reasoning about dates, schedules, relative terms like 'today', 'tomorrow', 'next week', or calendar conflicts.
2. If you need external data or real-time action, call the appropriate tool.
3. If the tool results give you the needed answer, synthesize a clear, helpful response for the user. Do not call tools needlessly.
4. If you have enough information to fulfill the user's request, formulate your final response directly without calling further tools.
5. PRIVACY GUARDRAIL: When formulating search queries for search_web, NEVER include personal identifiable information (PII) such as the user's name, email, phone number, address, or credentials. Always use generic, objective keywords.
"""

def get_system_prompt(custom_instructions: str = "") -> str:
    """
    Constructs a dynamic system prompt with real-time temporal grounding.
    """
    now = datetime.now()
    temporal_context = (
        f"\n[Temporal Context]\n"
        f"Current Datetime: {now.strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"Current Day: {now.strftime('%A')}\n"
        f"Timezone: Local System Time\n"
    )
    
    prompt = DEFAULT_BASE_PROMPT + temporal_context
    if custom_instructions:
        prompt += f"\n[User Specific Instructions]\n{custom_instructions}\n"
        
    return prompt
