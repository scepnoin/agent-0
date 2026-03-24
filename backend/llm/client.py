"""
Agent-0 LLM Client
Direct API calls to Anthropic, OpenAI, or Google.
Handles tool use (function calling) for the ReACT loop.
"""

import json
from logger import get_logger

log = get_logger("llm")


class LLMClient:
    """Unified LLM client supporting multiple providers with tiered model strategy."""

    # Model tiers for cost optimization (updated March 2026)
    MODEL_TIERS = {
        "google": {
            "fast": "gemini-2.0-flash",
            "mid": "gemini-2.5-flash",
            "smart": "gemini-2.5-pro"
        },
        "anthropic": {
            "fast": "claude-haiku-4-5",
            "mid": "claude-sonnet-4-6",
            "smart": "claude-opus-4-6"
        },
        "openai": {
            "fast": "gpt-5-mini",
            "mid": "gpt-5.3-codex",
            "smart": "gpt-5.4"
        }
    }

    TOKEN_LIMITS = {
        "fast": {"max_input": 4000, "max_output": 500},
        "mid": {"max_input": 12000, "max_output": 4000},
        "smart": {"max_input": 25000, "max_output": 8000}
    }

    def __init__(self, config):
        self.config = config
        self.provider = config.get("llm.provider")
        self.api_key = config.get("llm.api_key")
        self.model = config.get("llm.model")

        # Embedding config
        self.embed_api_key = config.get("embeddings.api_key") or self.api_key
        self.embed_model = config.get("embeddings.model", "gemini-embedding-001")

        self._client = None
        self._embed_client = None

        # Retry config
        self.max_retries = 3
        self.retry_delays = [2, 5, 15]  # seconds

        # Pending queue for when API is down
        self._pending_queue = []

    @property
    def client(self):
        """Lazy-initialize the LLM client."""
        if self._client is None:
            if self.provider == "anthropic":
                import anthropic
                self._client = anthropic.Anthropic(api_key=self.api_key)
            elif self.provider == "openai":
                import openai
                self._client = openai.OpenAI(api_key=self.api_key)
            elif self.provider == "google":
                from google import genai
                self._client = genai.Client(api_key=self.api_key)
        return self._client

    def reload_config(self, config):
        """Reload API keys from config (after settings change)."""
        self.provider = config.get("llm.provider")
        self.api_key = config.get("llm.api_key")
        self.model = config.get("llm.model")
        self.embed_api_key = config.get("embeddings.api_key") or self.api_key
        self.embed_model = config.get("embeddings.model", "gemini-embedding-001")
        # Force re-initialization
        self._client = None
        self._embed_client = None
        log.info(f"LLM client reloaded: provider={self.provider}, model={self.model}")

    def get_model_for_tier(self, tier: str = "mid") -> str:
        """Get the model name for a given tier."""
        provider_tiers = self.MODEL_TIERS.get(self.provider, {})
        return provider_tiers.get(tier, self.model)

    def call_tiered(self, messages: list, tools: list = None, system: str = None,
                    tier: str = "mid") -> dict:
        """Call with a specific tier (fast/mid/smart). Auto-selects model."""
        limits = self.TOKEN_LIMITS.get(tier, self.TOKEN_LIMITS["mid"])
        model = self.get_model_for_tier(tier)

        # Temporarily override model
        original_model = self.model
        self.model = model
        result = self.call(messages, tools, system, max_tokens=limits["max_output"])
        self.model = original_model
        return result

    def call(self, messages: list, tools: list = None, system: str = None,
             max_tokens: int = 1000) -> dict:
        """
        Call the LLM with messages and optional tools.

        Returns:
            dict with keys:
            - "type": "text" or "tool_call"
            - "text": response text (if type is "text")
            - "tool_name": tool name (if type is "tool_call")
            - "tool_args": tool arguments dict (if type is "tool_call")
            - "raw": raw API response
        """
        log.info(f"LLM call: provider={self.provider}, model={self.model}, tools={len(tools) if tools else 0}")
        log.debug(f"Messages: {len(messages)}, system prompt: {len(system) if system else 0} chars")

        if not self.api_key:
            log.error("No API key set! Cannot make LLM call.")
            return {"type": "text", "text": "Error: No API key configured. Go to Settings and enter your API key.", "raw": None}

        import time

        last_error = None
        for attempt in range(self.max_retries):
            try:
                if self.provider == "anthropic":
                    result = self._call_anthropic(messages, tools, system, max_tokens)
                elif self.provider == "openai":
                    result = self._call_openai(messages, tools, system, max_tokens)
                elif self.provider == "google":
                    result = self._call_google(messages, tools, system, max_tokens)
                else:
                    raise ValueError(f"Unknown provider: {self.provider}")

                log.info(f"LLM response: type={result['type']}" +
                         (f", tool={result.get('tool_name')}" if result['type'] == 'tool_call' else ''))
                return result

            except Exception as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    delay = self.retry_delays[min(attempt, len(self.retry_delays) - 1)]
                    log.warning(f"LLM call failed (attempt {attempt + 1}/{self.max_retries}): {e}. Retrying in {delay}s...")
                    time.sleep(delay)
                else:
                    log.error(f"LLM call failed after {self.max_retries} attempts: {e}")

        return {"type": "text", "text": f"Error calling LLM after {self.max_retries} retries: {str(last_error)}", "raw": None}

    def _call_anthropic(self, messages, tools, system, max_tokens):
        kwargs = {
            "model": self.model,
            "max_tokens": max_tokens,
            "messages": messages,
        }
        if system:
            kwargs["system"] = system
        if tools:
            kwargs["tools"] = [
                {"name": t["name"], "description": t["description"],
                 "input_schema": t["input_schema"]}
                for t in tools
            ]

        response = self.client.messages.create(**kwargs)

        # Parse response
        for block in response.content:
            if block.type == "tool_use":
                return {
                    "type": "tool_call",
                    "tool_name": block.name,
                    "tool_args": block.input,
                    "tool_use_id": block.id,
                    "raw": response
                }
            elif block.type == "text":
                return {
                    "type": "text",
                    "text": block.text,
                    "raw": response
                }

        return {"type": "text", "text": "", "raw": response}

    def _call_openai(self, messages, tools, system, max_tokens):
        # Convert messages format
        oai_messages = []
        if system:
            oai_messages.append({"role": "system", "content": system})

        for msg in messages:
            if msg["role"] == "tool":
                oai_messages.append({
                    "role": "tool",
                    "tool_call_id": msg.get("tool_use_id", ""),
                    "content": msg["content"]
                })
            else:
                oai_messages.append(msg)

        kwargs = {
            "model": self.model,
            "messages": oai_messages,
            "max_tokens": max_tokens,
        }
        if tools:
            kwargs["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": t["name"],
                        "description": t["description"],
                        "parameters": t["input_schema"]
                    }
                }
                for t in tools
            ]

        response = self.client.chat.completions.create(**kwargs)
        choice = response.choices[0]

        if choice.message.tool_calls:
            tc = choice.message.tool_calls[0]
            return {
                "type": "tool_call",
                "tool_name": tc.function.name,
                "tool_args": json.loads(tc.function.arguments),
                "tool_use_id": tc.id,
                "raw": response
            }

        return {
            "type": "text",
            "text": choice.message.content or "",
            "raw": response
        }

    def _call_google(self, messages, tools, system, max_tokens):
        from google import genai
        from google.genai import types

        if self._client is None or not isinstance(self._client, genai.Client):
            self._client = genai.Client(api_key=self.api_key)

        # Build tool declarations for Gemini
        gemini_tools = None
        if tools:
            function_declarations = []
            for t in tools:
                # Convert JSON schema properties to Gemini format
                params = dict(t["input_schema"]) if t.get("input_schema") else {}
                function_declarations.append(types.FunctionDeclaration(
                    name=t["name"],
                    description=t["description"],
                    parameters=params if params.get("properties") else None
                ))
            gemini_tools = [types.Tool(function_declarations=function_declarations)]

        # Build contents from messages
        contents = []
        for msg in messages:
            if msg["role"] == "user":
                if isinstance(msg["content"], str):
                    contents.append(types.Content(
                        role="user",
                        parts=[types.Part(text=msg["content"])]
                    ))
                elif isinstance(msg["content"], list):
                    # Handle tool_result format
                    parts = []
                    for item in msg["content"]:
                        if isinstance(item, dict) and item.get("type") == "tool_result":
                            parts.append(types.Part(
                                function_response=types.FunctionResponse(
                                    name=item.get("tool_name", "unknown"),
                                    response={"result": item.get("content", "")}
                                )
                            ))
                        elif isinstance(item, dict) and item.get("type") == "text":
                            parts.append(types.Part(text=item.get("text", "")))
                    if parts:
                        contents.append(types.Content(role="user", parts=parts))
            elif msg["role"] == "assistant":
                if isinstance(msg["content"], str):
                    contents.append(types.Content(
                        role="model",
                        parts=[types.Part(text=msg["content"])]
                    ))
                elif isinstance(msg["content"], list):
                    parts = []
                    for item in msg["content"]:
                        if isinstance(item, dict) and item.get("type") == "tool_use":
                            parts.append(types.Part(
                                function_call=types.FunctionCall(
                                    name=item["name"],
                                    args=item.get("input", {})
                                )
                            ))
                        elif isinstance(item, dict) and item.get("type") == "text":
                            parts.append(types.Part(text=item.get("text", "")))
                    if parts:
                        contents.append(types.Content(role="model", parts=parts))

        # Build config
        gen_config = types.GenerateContentConfig(
            max_output_tokens=max_tokens,
            tools=gemini_tools,
            system_instruction=system
        )

        response = self._client.models.generate_content(
            model=self.model,
            contents=contents,
            config=gen_config
        )

        # Parse response
        if response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if part.function_call:
                    fc = part.function_call
                    return {
                        "type": "tool_call",
                        "tool_name": fc.name,
                        "tool_args": dict(fc.args) if fc.args else {},
                        "tool_use_id": f"call_{fc.name}",
                        "raw": response
                    }
                elif part.text:
                    return {
                        "type": "text",
                        "text": part.text,
                        "raw": response
                    }

        return {"type": "text", "text": "", "raw": response}

    def embed(self, text: str) -> list[float]:
        """
        Get embedding vector for text using Google Gemini Embedding API.
        Always uses Gemini regardless of LLM provider (free tier).
        """
        from google import genai

        if self._embed_client is None:
            self._embed_client = genai.Client(api_key=self.embed_api_key)

        result = self._embed_client.models.embed_content(
            model=self.embed_model,
            contents=text,
            config={"task_type": "RETRIEVAL_DOCUMENT"}
        )
        return result.embeddings[0].values

    def embed_query(self, text: str) -> list[float]:
        """Get embedding for a search query (uses RETRIEVAL_QUERY task type)."""
        from google import genai

        if self._embed_client is None:
            self._embed_client = genai.Client(api_key=self.embed_api_key)

        result = self._embed_client.models.embed_content(
            model=self.embed_model,
            contents=text,
            config={"task_type": "RETRIEVAL_QUERY"}
        )
        return result.embeddings[0].values
