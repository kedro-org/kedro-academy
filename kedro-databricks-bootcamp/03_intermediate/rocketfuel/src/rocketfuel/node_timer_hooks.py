import logging
import time
from collections import defaultdict
from typing import Any, Dict
from kedro.framework.hooks import hook_impl
from kedro.pipeline.node import Node

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
