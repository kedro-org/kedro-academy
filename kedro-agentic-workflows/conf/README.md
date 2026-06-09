# Configuration

This folder holds Kedro configuration. The project uses three envs:

| Env | Path | Loaded when |
|---|---|---|
| `base` | `conf/base/` | Always — shared catalog, parameters, credentials |
| `langfuse` | `conf/langfuse/` | Default — provider-specific catalog + eval catalog (Langfuse) |
| `opik` | `conf/opik/` | When you pass `--env opik` — provider-specific catalog (Opik) |
| `local` | `conf/local/` | Only when `--env local` is passed explicitly (replaces the run env — not layered on top) |

`default_run_env = "langfuse"` (in `src/kedro_agentic_workflows/settings.py`), so a plain `kedro run` loads `conf/base/` + `conf/langfuse/`. Switching providers is `--env opik` (loads `conf/base/` + `conf/opik/`).

The Kedro CLI's `--env <name>` flag takes a single env directory name; it doesn't accept multiple envs or comma-separated stacking. `conf/local/` is therefore not in the default stack — it's only loaded if you pass `--env local`, which would replace `conf/langfuse/` entirely (and then nothing would bind `intent_prompt` / `intent_tracer` / `autogen_tracer`, so most pipelines would fail).

## Credentials

Copy [`base/credentials.yml.template`](base/credentials.yml.template) to `base/credentials.yml` and fill in real values. The template is the only credentials file tracked in git; `conf/**/*credentials*` in `.gitignore` keeps everything else out (with a single negation exception for the `.template` file).

`conf/base/credentials.yml` is the right place because it's loaded under every env. Putting credentials in `conf/local/credentials.yml` wouldn't work with the default setup — `conf/local/` isn't loaded by default, and the CLI doesn't support layering it on top of the active env.

## Catalog layout

- `base/catalog.yml` — DB tables and shared datasets.
- `base/catalog_genai_config.yml` — provider-agnostic entries (`llm`, `tool_prompt`, `response_prompt`, …) shared across both providers.
- `langfuse/catalog_genai_config.yml` — Langfuse-specific bindings for `intent_prompt`, `intent_tracer`, `autogen_tracer`.
- `langfuse/catalog_evaluation.yml` — evaluation pipeline catalog (Langfuse-only today; reorg tracked in a follow-up PR).
- `opik/catalog_genai_config.yml` — Opik-specific bindings for the same three generic names.

## Need help?

[Kedro configuration docs](https://docs.kedro.org/en/stable/kedro_project_setup/configuration.html).
