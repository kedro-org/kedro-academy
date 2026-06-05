# Configuration

This folder holds Kedro configuration. The project uses three envs:

| Env | Path | Loaded when |
|---|---|---|
| `base` | `conf/base/` | Always — shared catalog, parameters, credentials template |
| `langfuse` | `conf/langfuse/` | Default — provider-specific catalog + eval catalog (Langfuse) |
| `opik` | `conf/opik/` | When you pass `--env opik` — provider-specific catalog (Opik) |
| `local` | `conf/local/` | **Only** when explicitly layered, e.g. `--env langfuse,local` |

`default_run_env = "langfuse"` (in `src/kedro_agentic_workflows/settings.py`), so a plain `kedro run` loads `conf/base/` + `conf/langfuse/`. Switching providers is `--env opik` (loads `conf/base/` + `conf/opik/`).

## Credentials

Copy [`base/credentials.yml.template`](base/credentials.yml.template) to `base/credentials.yml` and fill in real values. The template is the only credentials file tracked in git; `conf/**/*credentials*` in `.gitignore` keeps everything else out (with a single negation exception for the `.template` file).

If you'd rather keep credentials in `conf/local/credentials.yml` (the more conventional Kedro location for secrets), that's fine — but you must stack the env explicitly because `local` is no longer in the default run env:

```bash
kedro run --env langfuse,local --params user_id=3
kedro run --env opik,local     --params user_id=3
```

The trade-off: `conf/base/credentials.yml` keeps the command line short (just `kedro run`); `conf/local/credentials.yml` is conventional but requires the `--env …,local` flag every time.

## Catalog layout

- `base/catalog.yml` — DB tables and shared datasets.
- `base/catalog_genai_config.yml` — provider-agnostic entries (`llm`, `tool_prompt`, `response_prompt`, …) shared across both providers.
- `langfuse/catalog_genai_config.yml` — Langfuse-specific bindings for `intent_prompt`, `intent_tracer`, `autogen_tracer`.
- `langfuse/catalog_evaluation.yml` — evaluation pipeline catalog (Langfuse-only today; reorg tracked in a follow-up PR).
- `opik/catalog_genai_config.yml` — Opik-specific bindings for the same three generic names.

## Need help?

[Kedro configuration docs](https://docs.kedro.org/en/stable/kedro_project_setup/configuration.html).
