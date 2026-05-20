"""Kedro project settings."""

from kedro.config import OmegaConfigLoader

CONF_SOURCE = "conf"
CONFIG_LOADER_CLASS = OmegaConfigLoader
CONFIG_LOADER_ARGS = {
    "base_env": "base",
    "default_run_env": "local",
    "config_patterns": {
        "catalog": ["catalog*", "catalog*/**", "**/catalog*"],
        "parameters": ["parameters*", "parameters*/**", "**/parameters*"],
        "credentials": ["credentials*", "credentials*/**", "**/credentials*"],
    },
}
