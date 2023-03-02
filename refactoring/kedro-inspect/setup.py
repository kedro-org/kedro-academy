from setuptools import setup

setup(
    name="kedro-inspect",
    version="0.1",
    packages=["kedro_inspect"],
    entry_points={
        "kedro.hooks": [
            "inspect_hooks = kedro_inspect.plugin:inspect_hooks",
            # TODO: Add an entry point for the time_dataset_loading_hooks hooks.
        ],
        # TODO: Add an entry point to `kedro.project_commands` for the new inspect_cli.
    },
)
