import logging

from kedro.framework.hooks import hook_impl
from kedro.pipeline.node import Node
from kedro.io import DataCatalog

logger = logging.getLogger(__name__)


class PipelineLoggingHooks:
    @hook_impl
    def before_pipeline_run(self, run_params, pipeline):
        logger.error("About to run pipeline: %s", pipeline.nodes)


hooks = PipelineLoggingHooks()
