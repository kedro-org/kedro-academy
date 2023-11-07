# Extending Kedro through hooks and plugins

The goal is to add a custom hook that logs extra information during the execution of a pipeline.

## In-tree hooks

1. Create a new Kedro project using the `spaceflights` starter, install the dependencies from `requirements.txt`, and verify that `kedro run` runs without problems.
2. Create a `hooks.py` file inside the source directory and add a `ProjectHooks` class with a `before_node_run` hook that logs the number of inputs for the node at `WARNING` level:

```python
...

class ProjectHooks:

    # ...
    def before_node_run(self, ...):
        logger.warning("Number of inputs: %d", ...)
```

3. Register that hook in `settings.py` using the `HOOKS` variable.
4. Execute `kedro run --pipeline=data_processing` and verify that you see three new lines of logs.

## Out-of-tree hooks through plugins

1. Create a new empty directory called `kedro-pipeline-logging` _outside of `spaceflights`_.
2. Create a new Python library called `kedro_pipeline_logging` in that directory, including a `pyproject.toml` and the corresponding source directory.

To create the `pyproject.toml` file you can use `flit`:

```
$ pip install flit
$ flit init
Module name: kedro_pipeline_logging
Author: ...
...
Written pyproject.toml; edit that file to add optional extra info.
```

and then, create a `src/kedro_pipeline_logging/__init__.py` with these contents:

```python
"""
Simple Kedro plugin that adds pipeline logging.
"""

__version__ = "0.1.0"
```

verify that `pip install .` works from inside `kedro-pipeline-logging` (where `pyproject.toml` lives).

3. (TBC)
