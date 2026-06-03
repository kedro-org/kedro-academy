"""Project settings. There is no need to edit this file unless you want to change values
from the Kedro defaults. For further information, including these default values, see
https://docs.kedro.org/en/stable/configure/configuration_basics/#configuration"""

from kedro_reflection_agent.hooks import RunIndexHook

# Hooks execute in Last-In-First-Out order.
HOOKS = (RunIndexHook(),)

# Installed plugins for which to disable hook auto-registration.
# DISABLE_HOOKS_FOR_PLUGINS = ("kedro-viz",)

# Class that manages the KedroSession.
# from kedro.framework.session import KedroSession
# SESSION_CLASS = KedroSession

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
# from kedro.config import OmegaConfigLoader

# CONFIG_LOADER_CLASS = OmegaConfigLoader

# Keyword arguments to pass to the `CONFIG_LOADER_CLASS` constructor.
CONFIG_LOADER_ARGS = {
    "base_env": "base",
    "default_run_env": "local",
    # "config_patterns": {
    #     "spark" : ["spark*/"],
    #     "parameters": ["parameters*", "parameters*/**", "**/parameters*"],
    # }
}

# Class that manages Kedro's library components.
# from kedro.framework.context import KedroContext
# CONTEXT_CLASS = KedroContext

# Class that manages the Data Catalog.
# from kedro.io import DataCatalog
# DATA_CATALOG_CLASS = DataCatalog


# --- Warning filters ---------------------------------------------------------
# We deliberately silence two noisy warning categories on every run:
#
#   * KedroExperimentalWarning — emitted by Kedro's `LLMContextNode` (which is
#     experimental, but stable enough for us). One warning per pipeline
#     assembly is enough; we don't need it on every catalog load.
#   * Pydantic serializer warnings — emitted by LangChain's
#     `with_structured_output(EmailOutput)` flow on every LLM call. Benign:
#     LangChain's internal schema dump triggers a Pydantic v2 strict-mode
#     complaint that has no effect on the actual structured response.
#
# Both are suppressed in `kedro-agentic-workflows` (the source-of-truth project)
# for the same reasons.
import warnings

from kedro.utils import KedroExperimentalWarning

warnings.filterwarnings("ignore", category=KedroExperimentalWarning)
warnings.filterwarnings("ignore", message="Pydantic serializer warnings")
