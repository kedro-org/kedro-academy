from setuptools import setup

setup(
    name="kedro-inspect",
    version="0.1",
    packages=["kedro_inspect"],
    entry_points={
        "kedro.hooks": [
            "inspect_hooks = kedro_inspect.plugin:inspect_hooks",
            "time_dataset_loading_hooks = kedro_inspect.plugin:time_dataset_loading_hooks",
        ],
        "kedro.project_commands": "inspect_cli_hooks = kedro_inspect.cli_plugin:inspect_cli",
    },
)
