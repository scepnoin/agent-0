# Agent-0: Setup Flow

## First Run — User Experience

```
1. User double-clicks agent-0.exe
2. Small setup window appears:
   - "Select project folder" → file picker
   - "Select LLM provider" → Anthropic / OpenAI / Google
   - "Enter API key" → text field
   - "Start" button
3. Agent-0 bonds to the folder
4. Onboarding begins (see 04_ONBOARDING.md)
5. When onboarding completes → confirmation screen
6. Agent-0 goes idle, widget stays on desktop
7. Watching begins
```

## Subsequent Runs

```
1. User double-clicks agent-0.exe
2. Agent-0 detects existing .agent0/ folder in project
3. Reads back its knowledge
4. Goes idle immediately
5. Widget appears, watching resumes
```

## Configuration (config stored in .agent0/config.json)

```json
{
    "project_path": "/path/to/project",
    "provider": "anthropic",
    "api_key": "sk-...",
    "model": "claude-sonnet-4-6",
    "strictness": "normal",
    "ignore_patterns": [
        "node_modules", "venv", "__pycache__",
        "*.pyc", ".git", "tmp*", "*.log"
    ],
    "alert_enabled": true,
    "widget_always_on_top": false,
    "checkpoint_interval_hours": 24
}
```

## Requirements

- Python 3.10+
- API key for one LLM provider (Google Gemini recommended - free embedding tier)
- Rust toolchain (for Tauri desktop app build)
- Node.js 18+ (for Tauri frontend)
- That's it
