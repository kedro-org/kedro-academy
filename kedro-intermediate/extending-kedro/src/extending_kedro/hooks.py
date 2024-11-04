import logging

from kedro.framework.hooks import hook_impl
from kedro.pipeline.node import Node
from kedro.io import DataCatalog

logger = logging.getLogger(__name__)


class NodeLoggingHooks:
    @hook_impl
    def before_node_run(self, node: Node, catalog: DataCatalog):
        logger.warning("About to run node: %s", node.name)
