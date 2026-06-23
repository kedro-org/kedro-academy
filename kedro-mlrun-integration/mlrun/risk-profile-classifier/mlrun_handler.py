"""
MLRun handler for Risk Profile Classifier Kedro pipelines.

This handler:
1. Downloads and unpacks the zipped Kedro project artifact.
2. Bootstraps the Kedro project and runs the requested pipeline with the
   ``mlrun`` Kedro environment (``conf/mlrun``).
3. Inputs and outputs are read/written through the MLRun-native dataset types
   declared in ``conf/mlrun/catalog.yml`` (``kedro-datasets[mlrun]``), so the
   pipeline itself logs models, metrics, and data back to MLRun.
4. For serving, returns the ``nuclio_response``-tagged dataset as the HTTP
   response (see ``post_processing``).

Environment variables:
- KEDRO_PIPELINE_NAME: Pipeline to run (default: "training").
- KEDRO_PROJECT_ARTIFACT: Name of the zipped project artifact (default: "risk-classifier").
"""

import os
import zipfile
import shutil
import json
import nuclio_sdk
from pathlib import Path

import mlrun
from kedro.framework.session import KedroSession
from kedro.framework.startup import bootstrap_project

# Kedro dataset classes
from kedro_datasets.pandas import CSVDataset, ParquetDataset
from kedro.framework.project import pipelines
from kedro_datasets.pickle import PickleDataset
from kedro.runner import SequentialRunner
from kedro_datasets.json import JSONDataset
from kedro.io import MemoryDataset


def init_context(context):
    context.project = mlrun.get_current_project()

def setup_project(context, project_artifact: str):
    """Download and unpack Kedro project and data.
    
    Args:
        context: MLRun execution context.
        project_artifact: Name of the tar artifact containing Kedro project.
        
    Returns:
        Path to the unpacked project directory.
    """
    # Create working directory
    work_dir = Path("/tmp/kedro_project")
    work_dir.mkdir(parents=True, exist_ok=True)
    
    context.logger.info(f"Working directory: {work_dir}")
    
    # Download project tar artifact
    context.logger.info(f"Downloading project artifact: {project_artifact}")
    project = _get_mlrun_project(context)
    tar_dataitem = project.get_artifact(project_artifact).to_dataitem()

    # Download tar file
    zip_path = work_dir / "project.zip"
    tar_dataitem.download(target_path=str(zip_path))
    context.logger.info(f"Downloaded project zip to: {zip_path}")

    if not zip_path.exists():
        raise FileNotFoundError(f"Zip file not found at {zip_path}")

    # Unpack zip archive
    context.logger.info(f"Unpacking project archive from {zip_path}...")
    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(path=work_dir)

    context.logger.info(f"Project unpacked to {work_dir}")

    # Create data directory structure
    data_dir = work_dir / "data" / "raw"
    data_dir.mkdir(parents=True, exist_ok=True)
    context.logger.info(f"Created data directory: {data_dir}")

    # Create other required directories
    (work_dir / "data" / "models").mkdir(parents=True, exist_ok=True)
    (work_dir / "data" / "predictions").mkdir(parents=True, exist_ok=True)
    (work_dir / "data" / "reporting").mkdir(parents=True, exist_ok=True)

    return work_dir


def handle_event_data(context, event):
    """Extract data from event body.

    This function extracts and parses data from event.body.

    Args:
        context: MLRun execution context.
        event: Event object (may contain body with data).

    Returns:
        Parsed event data, or None if no event data.
    """
    context.logger.info(f"handle_event_data called - event: {event is not None}, has body: {hasattr(event, 'body') if event else False}")

    if not event:
        context.logger.info("No event provided")
        return None

    if not hasattr(event, 'body'):
        context.logger.info("Event has no body attribute")
        return None

    if not event.body:
        context.logger.info("Event body is empty")
        return None

    context.logger.info("Processing event data...")

    try:
        # Parse event body
        if isinstance(event.body, bytes):
            event_data = json.loads(event.body.decode("utf-8"))
        elif isinstance(event.body, str):
            event_data = json.loads(event.body)
        else:
            event_data = event.body

        context.logger.info(f"Event data parsed: type={type(event_data)}")

        return event_data

    except Exception as e:
        context.logger.error(f"Error handling event data: {e}")
        import traceback
        context.logger.error(traceback.format_exc())
        return None

def handler(context, event=None):
    """MLRun handler for running Kedro pipelines.

    Environment variables:
        KEDRO_PIPELINE_NAME: Pipeline to run (default: training).
        KEDRO_PROJECT_ARTIFACT: Name of the zipped project artifact (default: risk-classifier).

    Args:
        context: MLRun execution context.
        event: Optional serving request. When present, its body is fed to the
            ``nuclio_event``-tagged dataset and the handler returns an HTTP response.

    Returns:
        For a serving request, a ``nuclio_sdk.Response`` with the prediction
        results; otherwise ``None``.
    """
    # Get configuration from environment
    pipeline_name = os.getenv("KEDRO_PIPELINE_NAME", "training")
    project_artifact = os.getenv("KEDRO_PROJECT_ARTIFACT", "risk-classifier")

    context.logger.info(f"Starting Kedro pipeline: {pipeline_name}")
    context.logger.info(f"Project artifact: {project_artifact}")

    # Setup project (download and unpack)
    project_path = setup_project(context, project_artifact)

    # Bootstrap Kedro project
    context.logger.info("Bootstrapping Kedro project...")
    bootstrap_project(project_path)

    # Create Kedro session
    context.logger.info(f"Creating Kedro session at {project_path}")
    with KedroSession.create(project_path=project_path, env="mlrun") as session:
        copy_catalog = session.load_context().catalog

        # Extract event data if present (for serving pipelines)
        event_data = handle_event_data(context, event)

        # Load context ONCE
        ctx = session.load_context()

        # Feed event data to MemoryDatasets if available
        if event_data:
            context.logger.info(f"Feeding event data to catalog datasets...")

            fed_count = 0
            # Find datasets tagged with nuclio_event metadata
            for dataset_name, ds in copy_catalog.items():
                # Debug: check what attributes the dataset has
                if isinstance(ds, MemoryDataset):
                    context.logger.debug(f"  Checking MemoryDataset: {dataset_name}")
                    context.logger.debug(f"    has metadata attr: {hasattr(ds, 'metadata')}")
                    if hasattr(ds, 'metadata'):
                        context.logger.debug(f"    metadata value: {ds.metadata}")

                # Check if dataset has nuclio_event metadata tag
                if isinstance(ds, MemoryDataset) and ds.metadata and ds.metadata.get("nuclio_event"):
                    context.logger.info(f"  ✓ Found tagged dataset: {dataset_name}")
                    # Save directly to the dataset in the catalog
                    copy_catalog[dataset_name].save(event_data)
                    context.logger.info(f"  ✓ Saved event data to {dataset_name}")
                    fed_count += 1

                    # Verify it can be loaded
                    try:
                        test_load = copy_catalog[dataset_name].load()
                        context.logger.info(f"  ✓ Verified: data loadable from {dataset_name} (type: {type(test_load)})")
                    except Exception as e:
                        context.logger.error(f"  ✗ Failed to verify load from {dataset_name}: {e}")

            # If no tagged datasets found, log warning and fallback
            if fed_count == 0:
                context.logger.warn("No datasets with nuclio_event tag found!")
                context.logger.info("Attempting fallback: feeding to 'user_input' if it exists")
                if 'user_input' in copy_catalog._datasets:
                    copy_catalog._datasets['user_input'].save(event_data)
                    context.logger.info("  ✓ Saved event data to user_input (fallback)")
                else:
                    context.logger.error("  ✗ user_input not found in catalog!")

        # Run pipeline using runner with the same catalog
        context.logger.info(f"Running pipeline: {pipeline_name}")

        runner = SequentialRunner()
        pipeline =  pipelines.get(pipeline_name)

        # Run with the catalog that has the event data
        # hook_mng ??
        runner.run(pipeline, copy_catalog, ctx._hook_manager)
 
        context.logger.info(f"Pipeline '{pipeline_name}' completed successfully")
 
        # Post-process and log artifacts (returns results for serving pipeline)
        return post_processing(context, project_path, event, copy_catalog)


def post_processing(context, project_path: Path, event = None, catalog = None):
    """Build the HTTP response for a serving request.

    Pipeline outputs (models, metrics, data) are logged to MLRun by the
    MLRun-native dataset types in ``conf/mlrun/catalog.yml`` while the pipeline
    runs, so this function does not log artifacts itself. It only handles the
    serving case: when an event is present, it loads every dataset tagged with
    ``nuclio_response`` metadata and returns it as the HTTP response body
    (DataFrames are converted to records).

    Args:
        context: MLRun execution context.
        project_path: Path to the Kedro project.
        event: Serving request, if any. Its presence indicates a serving call.
        catalog: Kedro catalog used to load the response datasets.

    Returns:
        A ``nuclio_sdk.Response`` with the ``nuclio_response`` datasets for a
        serving request, or ``None`` otherwise.
    """
    context.logger.info("Post-processing: Logging artifacts to MLRun...")
    # If event data provided, check for datasets tagged with nuclio_response
    if event and catalog:
        context.logger.info("Checking for datasets tagged for HTTP response...")

        result = {}

        # Iterate through catalog to find datasets with nuclio_response metadata
        for dataset_name, ds in catalog.items():
            # Debug all MemoryDatasets
            if isinstance(ds, MemoryDataset):
                context.logger.info(f"  Checking MemoryDataset: {dataset_name}")
                context.logger.info(f"    has metadata: {hasattr(ds, 'metadata')}")
                if hasattr(ds, 'metadata'):
                    context.logger.info(f"    metadata value: {ds.metadata}")

            try:
                # Check if dataset has nuclio_response metadata tag
                if isinstance(ds, MemoryDataset) and ds.metadata and ds.metadata.get("nuclio_response"):
                    context.logger.info(f"  ✅ Found response dataset: {dataset_name}")

                    # Load the dataset
                    data = ds.load()
                    context.logger.info(f"  Loaded data type: {type(data)}")

                    # Convert DataFrames to dict for JSON serialization
                    if hasattr(data, 'to_dict'):
                        result[dataset_name] = data.to_dict(orient="records")
                        context.logger.info(f"  Converted DataFrame with {len(data)} records")
                    else:
                        result[dataset_name] = data
                        context.logger.info(f"  Using data as-is: {type(data)}")

            except Exception as e:
                context.logger.warn(f"Could not load response dataset {dataset_name}: {e}")
                import traceback
                context.logger.warn(traceback.format_exc())

        context.logger.info(f"Result dict has {len(result)} keys: {list(result.keys())}")

        if result:
            context.logger.info(f"✅ Returning HTTP response with {len(result)} dataset(s)")
            return nuclio_sdk.Response(body=result)
        else:
            context.logger.warn("❌ No response datasets found - returning None")
    else:
        context.logger.info("No event or no catalog - skipping response building")

    # No event or no response datasets, return None
    return None

def _get_mlrun_project(context):
    project = context.project if hasattr(context, 'project') else None
    if isinstance(project, str):
        project = mlrun.get_or_create_project(project)
    return project