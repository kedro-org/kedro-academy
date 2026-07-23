"""Project settings. There is no need to edit this file unless you want to change values
from the Kedro defaults. For further information, including these default values, see
https://docs.kedro.org/en/stable/kedro_project_setup/settings.html."""

import warnings

from kedro.utils import KedroExperimentalWarning

# Keyword arguments to pass to the `CONFIG_LOADER_CLASS` constructor.
CONFIG_LOADER_ARGS = {
    "base_env": "base",
    "default_run_env": "local",
    "config_patterns": {
        "catalog": ["catalog*", "catalog*/**", "**/catalog*"],
    }
}

# Silence benign warnings from experimental LLMContextNode and LangChain/CrewAI
# structured-output flows (same approach as kedro-reflection-agent).
warnings.filterwarnings("ignore", category=KedroExperimentalWarning)
warnings.filterwarnings("ignore", message="Pydantic serializer warnings")
