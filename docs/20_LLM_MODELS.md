# Agent-0: LLM Models Reference (March 2026)

## Supported Providers & Models

### Anthropic Claude (Feb 2026)

| Model | Tier | Pricing (input/output per 1M) | Use Case |
|-------|------|------|---------|
| claude-opus-4-6 | SMART | $5 / $25 | Deep reasoning, synthesis, complex analysis |
| claude-sonnet-4-6 | MID | ~$3 / $15 | General analysis, gospel checking, queries |
| claude-haiku-4-5 | FAST | ~$0.80 / $4 | Classification, quick summaries |

### OpenAI GPT (March 2026)

| Model | Tier | Pricing (input/output per 1M) | Use Case |
|-------|------|------|---------|
| gpt-5.4 | SMART | ~$10 / $40 | Deep reasoning, complex tasks |
| gpt-5.3-codex | MID | ~$3 / $15 | Code analysis, general reasoning |
| gpt-5-mini | FAST | ~$0.15 / $0.60 | Classification, quick tasks |

### Google Gemini (March 2026)

| Model | Tier | Pricing (input/output per 1M) | Use Case |
|-------|------|------|---------|
| gemini-3.1-pro | SMART | ~$3 / $15 | Deep reasoning, 1M context window |
| gemini-3.1-flash-lite | FAST | $0.25 / $1.50 | Classification, 45% faster generation |
| gemini-2.5-flash | MID (legacy) | $0.15 / $0.60 | Current default, still works |

### Embeddings

| Model | Provider | Pricing | Notes |
|-------|----------|---------|-------|
| gemini-embedding-001 | Google | FREE (1,500 req/day) | Default for all providers |

## Agent-0 Tier Strategy

| Tier | Purpose | Default Models |
|------|---------|---------------|
| FAST | Classification, quick summary | haiku-4.5 / gpt-5-mini / gemini-3.1-flash-lite |
| MID | Analysis, queries, gospel checks | sonnet-4.6 / gpt-5.3-codex / gemini-2.5-flash |
| SMART | Synthesis, deep reasoning, onboarding | opus-4.6 / gpt-5.4 / gemini-3.1-pro |

## Key Changes from Previous Spec

- Gemini 2.5 Flash is now legacy — Gemini 3.1 Flash-Lite is the new fast option
- Gemini 3.1 Pro is the new smart tier for Google (replaces 2.5 Pro)
- GPT-5.4 replaces GPT-4o as the smart option
- GPT-5.3-Codex is specifically optimized for code analysis
- All old GPT-5.1 models retired as of March 11, 2026
