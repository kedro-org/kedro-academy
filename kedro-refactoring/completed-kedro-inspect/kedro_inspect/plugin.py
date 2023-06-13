from kedro.framework.hooks import hook_impl
from kedro.pipeline.node import Node
from typing import Callable, Tuple, Any
import inspect
import logging
import pandas as pd

log = logging.getLogger(__name__)


class InspectHooks:
    @hook_impl
    def before_node_run(self, node: Node) -> None:
        if "no_inspect" in node.tags:
            return
        node_name = node.name
        location, number_lines = _inspect_func(node.func)
        log.info(f"`{node_name}` is defined at {location} and is {number_lines} lines long")

    @hook_impl
    def after_dataset_loaded(self, dataset_name: str, data: Any) -> None:
        if isinstance(data, pd.DataFrame):
            log.info(f"`{dataset_name}` has shape {data.shape}")


def _inspect_func(func: Callable) -> Tuple[str, int]:
    """Gives the location (file and line number) and number of lines in `func`."""
    file = inspect.getsourcefile(func)
    lines, first_line = inspect.getsourcelines(func)
    location = f"{file}:{first_line}"
    return location, len(lines)

import time

class TimeDatasetLoadingHooks:
    def __init__(self):
        self._start_times = {}

    @hook_impl
    def before_dataset_loaded(self, dataset_name: str) -> None:
        self._start_times[dataset_name] = time.time()

    @hook_impl
    def after_dataset_loaded(self, dataset_name: str) -> None:
        elapsed_time = time.time() - self._start_times[dataset_name]
        log.info(f"Loading `{dataset_name}` took {elapsed_time:.3} seconds")


inspect_hooks = InspectHooks()
time_dataset_loading_hooks = TimeDatasetLoadingHooks()
