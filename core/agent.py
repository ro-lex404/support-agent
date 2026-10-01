import json
from typing import Dict, Any, List, Optional, Callable
from openai import OpenAI
from tools.base import ToolRegistry

class Agent:
    """
    A lightweight, framework-free autonomous ReAct agent.
    Maintains execution state, tool schemas, and manages the iterative loop.
    """
    def __init__(
        self,
        client: OpenAI,
        model: str,
        system_prompt: str,
        registry: ToolRegistry,
        max_iterations: int = 5,
        max_tokens: int = 350,
        verbose: bool = True
    ):
        self.client = client
        self.model = model
        self.system_prompt = system_prompt
        self.registry = registry
        self.max_iterations = max_iterations
        self.max_tokens = max_tokens
        self.verbose = verbose

    def _log(self, message: str, prefix: str = "[Agent]"):
        if self.verbose:
            print(f"{prefix} {message}")

    def run(self, user_goal: str, on_step: Optional[Callable[[str], None]] = None) -> str:
        """
        Executes the autonomous loop until a final answer is generated
        or the maximum iteration limit is reached.
        """
        messages: List[Dict[str, Any]] = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_goal}
        ]

        schemas = self.registry.get_schemas()
        self._log(f"Starting task: '{user_goal}'")
        self._log(f"Registered tools: {[s['function']['name'] for s in schemas]}")

        for step in range(1, self.max_iterations + 1):
            self._log(f"\n--- Iteration {step}/{self.max_iterations} ---")
            
            try:
                # 1. Ask LLM for next action
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    tools=schemas if schemas else None,
                    tool_choice="auto" if schemas else None,
                    max_tokens=self.max_tokens,
                    extra_body={"reasoning_budget": 0}
                )
            except Exception as e:
                self._log(f"LLM API Error: {e}", prefix="[Error]")
                return f"Agent stopped due to LLM error: {e}"

            choice = response.choices[0]
            message = choice.message
            
            # Record assistant turn in context
            messages.append(message)

            # 2. Check if model produced a final textual response without tool calls
            tool_calls = getattr(message, "tool_calls", None)
            if not tool_calls:
                self._log("Final answer generated.", prefix="[Completed]")
                if on_step:
                    on_step("✅ Final answer generated!")
                return message.content or getattr(message, "reasoning_content", None) or "(Empty response)"

            # 3. Model decided to invoke one or more tools
            for tool_call in tool_calls:
                func_name = tool_call.function.name
                raw_args = tool_call.function.arguments

                self._log(f"Selected tool '{func_name}' with args: {raw_args}", prefix="[Action]")
                if on_step:
                    on_step(f"⚙️ Step {step}/{self.max_iterations}: Calling tool '{func_name}'...")
                
                try:
                    args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
                except json.JSONDecodeError as json_err:
                    tool_result = {"error": f"Failed to parse arguments JSON: {json_err}"}
                    self._log(f"Argument parsing error: {json_err}", prefix="[Warning]")
                else:
                    # Execute tool safely
                    try:
                        tool_result = self.registry.execute(func_name, args)
                    except Exception as exec_err:
                        tool_result = {"error": f"Execution failed: {str(exec_err)}"}
                        self._log(f"Tool execution exception: {exec_err}", prefix="[Warning]")

                self._log(f"Result -> {tool_result}", prefix="[Observation]")
                if on_step:
                    on_step(f"🔍 Step {step}/{self.max_iterations}: Received results from '{func_name}', reasoning...")

                # 4. Feed tool result back into context
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": func_name,
                    "content": json.dumps(tool_result, default=str)
                })

        return "Agent reached maximum iteration limit without concluding."
