# Agent-0: Model Strategy

## Principle

Not every task needs the smartest model. Agent-0 uses a **tiered model approach** — cheap and fast for routine work, smart and expensive only when it matters.

## Three Tiers

### Tier 1: FAST (Classification & Logging)

**Purpose:** Quick, cheap classification of changes. No deep reasoning needed.

**Used for:**
- Classifying a file change (feature / bugfix / refactor / patch / test / config)
- Writing routine session log entries
- Simple state updates
- Acknowledging queries it can answer directly from search results

**Model examples:**
| Provider | Model | Input Cost | Output Cost |
|----------|-------|-----------|-------------|
| Anthropic | claude-haiku-4-5 | $0.80/M | $4/M |
| OpenAI | gpt-4o-mini | $0.15/M | $0.60/M |
| Google | gemini-2.0-flash | $0.10/M | $0.40/M |

**Token limits:** 2,000 input / 500 output
**Expected usage:** ~70% of all LLM calls

### Tier 2: MID (Analysis & Reasoning)

**Purpose:** Meaningful analysis — understanding context, checking gospels, synthesizing query answers.

**Used for:**
- Gospel validation against changes
- Drift detection (comparing changes against phase goals)
- Answering user/agent queries that require synthesis
- Onboarding (reading and understanding project structure/code)
- Checkpoint creation (summarizing project state)

**Model examples:**
| Provider | Model | Input Cost | Output Cost |
|----------|-------|-----------|-------------|
| Anthropic | claude-sonnet-4-6 | $3/M | $15/M |
| OpenAI | gpt-4o | $2.50/M | $10/M |
| Google | gemini-2.5-pro | $1.25/M | $10/M |

**Token limits:** 4,000 input / 1,000 output
**Expected usage:** ~25% of all LLM calls

### Tier 3: SMART (Deep Reasoning)

**Purpose:** Complex pattern matching, cross-referencing history, nuanced judgment calls.

**Used for:**
- Pattern matching across months of history ("has this happened before?")
- Complex dependency analysis
- Resolving ambiguous gospel checks
- Answering complex queries that require understanding multiple knowledge areas
- Gospel suggestions (identifying new rules from observed patterns)

**Model examples:**
| Provider | Model | Input Cost | Output Cost |
|----------|-------|-----------|-------------|
| Anthropic | claude-opus-4-6 | $15/M | $75/M |
| OpenAI | o3 | $10/M | $40/M |
| Google | gemini-2.5-ultra | $5/M | $20/M |

**Token limits:** 8,000 input / 2,000 output
**Expected usage:** ~5% of all LLM calls

## Escalation Flow

The ReACT loop starts at the appropriate tier and escalates if needed:

```
File change detected
    │
    ▼
TIER 1 (FAST): Classify the change
    │
    ├─ Routine, on-track → TIER 1 writes the record → DONE (cheap)
    │
    └─ Potential issue flagged (drift / gospel concern / unfamiliar pattern)
        │
        ▼
    TIER 2 (MID): Analyze the issue
        │
        ├─ Clear outcome → TIER 2 writes + alerts if needed → DONE
        │
        └─ Ambiguous / needs historical context
            │
            ▼
        TIER 3 (SMART): Deep reasoning
            │
            └─ Final decision → writes + alerts → DONE
```

**Key insight:** Most changes are routine. The fast model handles them in one call. Only edge cases escalate. This keeps costs low while maintaining quality where it matters.

## Configuration

```json
{
    "models": {
        "provider": "anthropic",
        "tiers": {
            "fast": {
                "model": "claude-haiku-4-5",
                "max_input_tokens": 2000,
                "max_output_tokens": 500
            },
            "mid": {
                "model": "claude-sonnet-4-6",
                "max_input_tokens": 4000,
                "max_output_tokens": 1000
            },
            "smart": {
                "model": "claude-opus-4-6",
                "max_input_tokens": 8000,
                "max_output_tokens": 2000
            }
        },
        "default_tier": "fast",
        "allow_escalation": true,
        "force_tier": null
    }
}
```

`force_tier`: user can override and force all calls to use a specific tier. Useful for:
- Debugging (force "smart" to see best reasoning)
- Cost saving (force "fast" when budget is tight)

## Model-Agnostic Design

Agent-0 doesn't care which provider or model is behind each tier. The `llm/client.py` abstraction:

```python
class LLMClient:
    def call(self, messages, tools, tier="fast"):
        model = self.config["tiers"][tier]["model"]
        provider = self.config["provider"]

        if provider == "anthropic":
            return self._call_anthropic(model, messages, tools)
        elif provider == "openai":
            return self._call_openai(model, messages, tools)
        elif provider == "google":
            return self._call_google(model, messages, tools)
```

Switching providers or models = change the config, not the code.

## Cost Projection by Provider

For an active project (100 file changes/day):

| Provider | Fast (70%) | Mid (25%) | Smart (5%) | Monthly Total |
|----------|-----------|-----------|------------|---------------|
| Anthropic | $3 | $9 | $7.50 | ~$20 |
| OpenAI | $1 | $6 | $5 | ~$12 |
| Google | $0.50 | $4 | $3 | ~$8 |

These are estimates. Actual cost depends on diff sizes, query frequency, and how often changes escalate.

## Embedding Model (for Vector Search)

Separate from the reasoning models. Used to create embeddings for the hybrid search index.

### Decision: API Embeddings via Google Gemini (No Local Model)

Agent-0 must stay lightweight — no PyTorch (~2GB), no heavy ML frameworks. Local embedding models add too much weight for a tool that should run effortlessly on any laptop.

**Default: Google Gemini Embedding API (`gemini-embedding-001`)**
- **Completely free** — 1,500 requests/day at no cost
- Paid tier (if you somehow exceed): $0.15/M tokens
- Agent-0 uses maybe 50-100 embedding calls on a heavy day — never hits the limit
- 768 dimensions
- Zero local weight — just an API call
- Top spot on MTEB Multilingual leaderboard — quality is excellent
- Apache 2.0 implementation — commercially safe

**Why `gemini-embedding-001` specifically:**
- **Free.** Not "basically free" — actually free. 1,500 req/day is massive headroom.
- Zero local weight — no PyTorch, no ONNX, no ML frameworks
- The embedding API key can be separate from the LLM provider key
- User can pick Anthropic or OpenAI for reasoning but still use Google's free embeddings
- Already proven in production on large-scale projects

**Configuration:**
```json
{
    "embeddings": {
        "provider": "google",
        "model": "gemini-embedding-001",
        "api_key": "Google API key (can be different from LLM provider key)",
        "task_type": "RETRIEVAL_DOCUMENT"
    }
}
```

**Future options (V2):**
- Upgrade to `gemini-embedding-2` (3072 dimensions, multimodal, $0.25/M tokens)
- Match LLM provider: OpenAI → text-embedding-3-small, Anthropic → Voyage
- Local fallback for offline use: Model2Vec (~30MB, no PyTorch) or fastembed (~200MB, ONNX)

**Cost estimate for embeddings: $0/month.** Free tier. Done.
