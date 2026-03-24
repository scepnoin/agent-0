"""
Agent-0 ReACT Loop
Think → Act → Observe → Repeat → Done

The core agent loop. Takes a trigger (file change or query),
reasons about it using the LLM, calls tools, and writes knowledge.
"""

import json
from tools import get_tool_schemas, execute_tool
from logger import get_logger

log = get_logger("loop")


class ReACTLoop:
    """ReACT agent loop for Agent-0."""

    def __init__(self, llm_client, config):
        self.llm = llm_client
        self.config = config
        self.max_iterations = config.get("agent.max_iterations", 10)

    def build_system_prompt(self) -> str:
        """Build the system prompt with dynamic context."""
        from agent.system_prompt import build_prompt
        return build_prompt(self.config)

    def run(self, trigger: str) -> str:
        """
        Run the ReACT loop for a given trigger.

        Args:
            trigger: The trigger message (e.g., "File changed: core/foo.py"
                     or "User query: what's the state of phase 16?")

        Returns:
            Final text response from the agent.
        """
        system = self.build_system_prompt()
        tools = get_tool_schemas()

        messages = [
            {"role": "user", "content": trigger}
        ]

        log.info(f"ReACT loop started. Trigger: {trigger[:80]}...")
        log.debug(f"System prompt: {len(system)} chars, Tools: {len(tools)}")

        for i in range(self.max_iterations):
            log.info(f"Iteration {i+1}/{self.max_iterations}")
            response = self.llm.call(
                messages=messages,
                tools=tools,
                system=system,
                max_tokens=12000
            )

            if response["type"] == "tool_call":
                tool_name = response["tool_name"]
                tool_args = response["tool_args"]

                log.info(f"TOOL CALL: {tool_name}({json.dumps(tool_args)[:200]})")

                # Execute the tool
                result = execute_tool(tool_name, tool_args)
                log.info(f"TOOL RESULT: {result[:200]}...")

                provider = self.config.get("llm.provider", "google")

                if provider == "anthropic":
                    # Anthropic format
                    messages.append({
                        "role": "assistant",
                        "content": [
                            {
                                "type": "tool_use",
                                "id": response.get("tool_use_id", f"tool_{i}"),
                                "name": tool_name,
                                "input": tool_args
                            }
                        ]
                    })
                    messages.append({
                        "role": "user",
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": response.get("tool_use_id", f"tool_{i}"),
                                "content": result
                            }
                        ]
                    })
                elif provider == "google":
                    # Google Gemini format
                    messages.append({
                        "role": "assistant",
                        "content": [
                            {
                                "type": "tool_use",
                                "name": tool_name,
                                "input": tool_args
                            }
                        ]
                    })
                    messages.append({
                        "role": "user",
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_name": tool_name,
                                "content": result
                            }
                        ]
                    })
                else:
                    # OpenAI format
                    messages.append({
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [{
                            "id": response.get("tool_use_id", f"tool_{i}"),
                            "type": "function",
                            "function": {"name": tool_name, "arguments": json.dumps(tool_args)}
                        }]
                    })
                    messages.append({
                        "role": "tool",
                        "tool_call_id": response.get("tool_use_id", f"tool_{i}"),
                        "content": result
                    })

                continue

            elif response["type"] == "text":
                log.info(f"DONE: {response['text'][:200]}")
                return response["text"]

        log.warning("Max iterations reached!")
        return "[Agent-0] Max iterations reached."
