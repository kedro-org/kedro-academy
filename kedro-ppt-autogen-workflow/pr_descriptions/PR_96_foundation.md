# PR #96: Add PPT AutoGen workflow foundation and utilities

## Summary

- Adds foundational infrastructure for AutoGen-based PPT generation pipelines
- Implements `BaseAgent` class with structured output support using Pydantic models
- Provides shared utilities for fonts and YAML instruction parsing
- Sets up `OpenAIChatCompletionClientDataset` for LLM configuration via Kedro catalog

## Key Components

### Base Agent Infrastructure (`base/`)
- `BaseAgent`: Generic agent class with `_run_with_output()` for structured responses
- `AgentContext`: Dataclass bundling model client, tools, system prompt, and agent name
- Pydantic output models: `ChartOutput`, `SummaryOutput`, `PlanOutput`, `QAFeedbackOutput`

### Datasets (`datasets/`)
- `OpenAIChatCompletionClientDataset`: Kedro dataset for AutoGen model client configuration

### Utilities (`utils/`)
- `fonts.py`: System font detection for cross-platform compatibility
- `instruction_parser.py`: YAML parsing for slide generation requirements

## Files Added

```
src/ppt_autogen_workflow/
├── base/
│   ├── __init__.py
│   └── agent.py              # BaseAgent with structured output
├── datasets/
│   └── autogen_model_client.py
└── utils/
    ├── __init__.py
    ├── fonts.py
    └── instruction_parser.py
```

## Test Plan

- [ ] Verify `BaseAgent` can be subclassed for specific agent types
- [ ] Test Pydantic models serialize/deserialize correctly
- [ ] Confirm `OpenAIChatCompletionClientDataset` loads from catalog
- [ ] Validate font detection works on target platforms

---
🤖 Generated with [Claude Code](https://claude.com/claude-code)
