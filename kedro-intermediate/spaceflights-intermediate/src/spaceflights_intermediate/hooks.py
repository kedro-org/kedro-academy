import logging
from kedro.framework.hooks import hook_impl

logger = logging.getLogger(__name__)


class LoggingFirstHooks:
    @hook_impl(tryfirst=True)
    def before_pipeline_run(self, run_params, pipeline):
        # `catalog` doesn't need to be included in the signature
        logger.warning("Running a pipeline of len: %d", len(pipeline.nodes))


class LoggingLastHooks:
    @hook_impl
    def before_pipeline_run(self, run_params, pipeline):
        logger.warning("Running a pipeline using datasets: %s", pipeline.all_inputs())
