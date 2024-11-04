# Extending Kedro through hooks and plugins

The goal is to add custom hooks that log extra information during the execution of a pipeline.

## In-tree hooks

1. Create a new Kedro project using the `spaceflights` starter, install the dependencies from `requirements.txt`, and verify that `kedro run` runs without problems.
2. Create a `hooks.py` file inside the source directory and add a `NodeLoggingHooks` class with a `before_node_run` hook that logs the number of inputs for the node at `WARNING` level:

```python
...

class NodeLoggingHooks:

    # ...
    def before_node_run(self, ...):
        logger.warning("About to run node: %s", ...)
```

3. Register that hook in `settings.py` using the `HOOKS` variable.
4. Execute `kedro run --pipeline=data_processing` and verify that you see three new lines of logs.

## Out-of-tree hooks through plugins

1. Create a new empty directory called `kedro-custom-hook` _outside of `spaceflights`_.
2. Create a new Python library in that directory, including a `pyproject.toml` and the corresponding source directory.

To create the `pyproject.toml` file you can use `uv init`:

```
$ uv init --lib -p 3.11
```

3. Add another hook class to `src/kedro_custom_hook/__init__.py` with this structure:

```python
class PipelineLoggingHooks:

    # ...
    def before_pipeline_run(self, run_params, pipeline):
        logger.error("About to run pipeline with nodes: %s", ...)


hooks = PipelineLoggingHooks()
```

4. Add the appropriate entry points in `pyproject.toml`:

```toml
[project.entry-points."kedro.hooks"]
custom_kedro_hook = ...
```

5. Install the code with `uv pip install -e /path/to/kedro-custom-hook` and run the pipeline again to check that the logs appear
