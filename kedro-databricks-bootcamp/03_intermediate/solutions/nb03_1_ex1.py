import logging
import time
from collections import defaultdict
from typing import Any, Dict
from kedro.framework.hooks import hook_impl
from kedro.pipeline.node import Node
import logging
import time

logger = logging.getLogger(__name__)

class NodeTimerHook:
    def __init__(self):
        self.node_times = defaultdict(list)

    @hook_impl
    def before_node_run(self, node: Node, inputs: Dict[str, Any]):
        node_name = node.name
        self.node_times[node_name].append({"start": time.perf_counter()})

    @hook_impl
    def after_node_run(self, node: Node, inputs: Dict[str, Any], outputs: Dict[str, Any]):
        node_name = node.name
        timing = self.node_times[node_name][-1]
        timing["end"] = time.perf_counter()
        timing["duration"] = timing["end"] - timing["start"]

    @hook_impl
    def after_pipeline_run(self, run_params: Dict[str, Any]):
        logger.info("Node execution timing summary:")
        for node_name, records in self.node_times.items():
            for i, record in enumerate(records):
                duration = record.get("duration", 0)
                logger.info(f"  - {node_name} [{i+1}]: {duration:.4f} seconds")


class LoggingHook:
    """A hook that logs how many time it takes to load each dataset."""

    def __init__(self):
        self._timers = {}

    @property
    def _logger(self):
        return logging.getLogger(__name__)

    @hook_impl
    def before_dataset_loaded(self, dataset_name: str, node: Node) -> None:
        start = time.time()
        self._timers[dataset_name] = start

    @hook_impl
    def after_dataset_loaded(self, dataset_name: str, data: Any, node: Node) -> None:
        start = self._timers[dataset_name]
        end = time.time()
        self._logger.info(
            "Loading dataset %s before node '%s' takes %0.2f seconds",
            dataset_name,
            node.name,
            end - start,
        )