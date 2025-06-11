"""Project settings. There is no need to edit this file unless you want to change values
from the Kedro defaults. For further information, including these default values, see
https://docs.kedro.org/en/stable/kedro_project_setup/settings.html."""

# Instantiated project hooks.
# from rocketfuel.hooks import SparkHooks  # noqa: E402

# Hooks are executed in a Last-In-First-Out (LIFO) order.
# NOTE: This is actually not required
# HOOKS = (SparkHooks(),)

# Installed plugins for which to disable hook auto-registration.
# DISABLE_HOOKS_FOR_PLUGINS = ("kedro-viz",)

# Class that manages storing KedroSession data.
# from kedro.framework.session.store import BaseSessionStore
# SESSION_STORE_CLASS = BaseSessionStore
# Keyword arguments to pass to the `SESSION_STORE_CLASS` constructor.
# SESSION_STORE_ARGS = {
#     "path": "./sessions"
# }

# Directory that holds configuration.
# CONF_SOURCE = "conf"

# Class that manages how configuration is loaded.
from pathlib import Path

from kedro.config import OmegaConfigLoader  # noqa: E402


def find_kedro_root():
    from kedro.utils import _find_kedro_project

    try:
        current_dir = Path(__file__).resolve().parent
    except NameError:
        current_dir = Path.cwd()

    project_root = _find_kedro_project(current_dir)
    if project_root is None:
        raise ValueError("Kedro project root not found. Ensure you are in a Kedro project directory.")

    return str(project_root)


CONFIG_LOADER_CLASS = OmegaConfigLoader
# Keyword arguments to pass to the `CONFIG_LOADER_CLASS` constructor.
CONFIG_LOADER_ARGS = {
    "base_env": "base",
    "default_run_env": "databricks",
    "custom_resolvers": {
        "kedro_root": find_kedro_root,
    },
    "config_patterns": {
        "spark": ["spark*", "spark*/**"],
    },
}

# Class that manages Kedro's library components.
# from kedro.framework.context import KedroContext
# CONTEXT_CLASS = KedroContext

# Class that manages the Data Catalog.
# from kedro.io import DataCatalog
# DATA_CATALOG_CLASS = DataCatalog
