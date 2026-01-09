import logging
from kedro.io import DataCatalog
from kedro.runner import SequentialRunner
from rocketfuel.pipelines.data_science import create_pipeline as create_ds_pipeline

def test_data_science_pipeline(caplog, dummy_data, dummy_parameters):
    pipeline = (
        create_ds_pipeline()
        .from_nodes("split_data_node")
        .to_nodes("evaluate_model_node")
    )
    catalog = DataCatalog()
    catalog.add_feed_dict(
        {
            "model_input_table": dummy_data,
            "params:model_options": dummy_parameters["model_options"],
        }
    )

    caplog.set_level(logging.DEBUG, logger="kedro")
    successful_run_msg = "Pipeline execution completed successfully."

    SequentialRunner().run(pipeline, catalog)

    assert successful_run_msg in caplog.text
