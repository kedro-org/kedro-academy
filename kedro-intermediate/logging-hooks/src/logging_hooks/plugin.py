import logging
from kedro.framework.hooks import hook_impl

logger = logging.getLogger(__name__)


class LoggingLastHooks:
    prefix = "logging"
    #@hook_impl
    #def after_context_created(self, context):
    #    self.prefix = context.config_loader.get("hook_config.yml")["prefix"]

    @hook_impl
    def before_pipeline_run(self, run_params, pipeline):
        logger.warning("%s: Running a pipeline using datasets: %s", self.prefix, pipeline.all_inputs())


hooks = LoggingLastHooks()
