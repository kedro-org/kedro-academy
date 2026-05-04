"""
MLRun handler for Risk Profile Classifier Kedro pipelines.

This handler:
1. Downloads and unpacks the Kedro project tar archive
2. Downloads the CSV data artifact to data/raw directory
3. Runs the specified Kedro pipeline
4. Logs all output artifacts back to MLRun

Environment variables:
- KEDRO_PIPELINE_NAME: Pipeline to run (default: "training")
- KEDRO_PROJECT_ARTIFACT: Name of the tar artifact (default: "kedro-risk-profile-classifier.tar")
- DATA_ARTIFACT: Name of the CSV data artifact (default: "user_data")
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
from kedro_datasets.pickle import PickleDataset
from kedro_datasets.json import JSONDataset
from kedro.io import MemoryDataset


def init_context(context):
    context.project = mlrun.get_current_project()

def setup_project(context, project_artifact: str, data_artifact: str = None):
    """Download and unpack Kedro project and data.
    
    Args:
        context: MLRun execution context.
        project_artifact: Name of the tar artifact containing Kedro project.
        data_artifact: Name of the CSV data artifact (optional).
        
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

    # Download data artifact if specified
    if data_artifact:
        context.logger.info(f"Downloading data artifact: {data_artifact}")
        csv_dataitem = project.get_artifact(data_artifact).to_dataitem()

        csv_target_path = data_dir / "user_data.csv"
        csv_dataitem.download(target_path=str(csv_target_path))

        if csv_target_path.exists():
            context.logger.info(f"Data saved to: {csv_target_path}")
        else:
            context.logger.warn(f"Data file not created at: {csv_target_path}")

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


def preprocess_artifacts(context, catalog, project_path: Path):
    """Download artifacts from MLRun project that match catalog dataset names.

    This function looks for artifacts in MLRun with names like:
    - {job_name}_{catalog_name} (e.g., "kedro-training-handler_raw_user_data")

    It extracts the catalog name (everything after first underscore) and downloads
    the artifact to the location specified in the Kedro catalog.

    Args:
        context: MLRun execution context.
        catalog: Kedro data catalog.
        project_path: Path to the Kedro project.
    """
    context.logger.info("Preprocessing: Checking for catalog artifacts in MLRun...")

    try:
        # Get MLRun project
        project = _get_mlrun_project(context)

        if not project:
            context.logger.warn("Could not get MLRun project for artifact preprocessing")
            return


        # Get all artifacts from MLRun project
        try:
            # TODO: set tag from env
            artifacts = project.list_artifacts(tag="latest")
            context.logger.info(f"Found {len(artifacts)} artifacts in MLRun project")
        except Exception as e:
            context.logger.warn(f"Could not list artifacts: {e}")
            return

        downloaded_count = 0

        # First, log what we're looking for in the catalog
        catalog_keys = list(catalog.keys())
        context.logger.info(f"Catalog datasets available ({len(catalog_keys)}): {catalog_keys}")
        context.logger.info("-" * 60)

        # Log all artifact keys for debugging
        all_artifact_keys = []
        context.logger.info("Raw artifact objects (first 5):")
        for i, artifact in enumerate(artifacts[:5]):
            context.logger.info(f"  Artifact {i}: {artifact}")

        for artifact in artifacts:
            key = artifact.get("metadata", {}).get("key")
            if key:
                all_artifact_keys.append(key)

        context.logger.info(f"All MLRun artifact keys ({len(artifacts)}): {all_artifact_keys}")

        for artifact in artifacts:
            artifact_key = db_key = artifact.get("spec", {}).get("db_key")
            artifact_kind = artifact.get("kind")
            if not artifact_key:
                continue
            context.logger.info(f"🔍 Processing artifact: '{artifact_key}'")

            catalog_name = None

            # Strategy 1: Try splitting by underscore FIRST (for patterns like kedro-training-handler_catalog-name)
            if '_' in artifact_key:
                parts = artifact_key.split('_', 1)
                if len(parts) >= 2:
                    potential_catalog_name = parts[1]  # Everything after first underscore
                    if potential_catalog_name in catalog_keys:
                        catalog_name = potential_catalog_name
                        context.logger.info(f"  ✅ Split match! Job: '{parts[0]}' → Catalog: '{catalog_name}'")

            # Strategy 2: Try direct match (artifact key == catalog name) only if split didn't work
            if not catalog_name and artifact_key in catalog_keys:
                catalog_name = artifact_key
                context.logger.info(f"  ✅ Direct match! Catalog name: '{catalog_name}'")

            # Skip if no match found
            if not catalog_name:
                context.logger.debug(f"  ⏭️  SKIP: '{artifact_key}' - no catalog match found")
                continue

            # Check if this name exists in Kedro catalog
            if catalog_name not in list(catalog.keys()):
                context.logger.info(f"  ❌ SKIP: '{catalog_name}' not in Kedro catalog")
                continue

            context.logger.info(f"  ✓ Found '{catalog_name}' in catalog!")

            # Get the dataset from catalog
            ds = catalog[catalog_name]

            # Skip if no filepath
            if not hasattr(ds, "_filepath"):
                context.logger.info(f"  ❌ SKIP: {catalog_name} has no filepath attribute")
                continue

            # Get target filepath
            target_filepath = str(ds._filepath)
            if not target_filepath.startswith("/"):
                target_filepath = str(project_path / target_filepath)

            context.logger.info(f"  📁 Target path: {target_filepath}")

            # Check if file already exists
            if Path(target_filepath).exists():
                context.logger.info(f"  ⏭️  File already exists, skipping download")
                continue

            # Download the artifact
            try:
                context.logger.info(f"  ⬇️  Downloading '{artifact_key}'...")

                # Ensure parent directory exists
                Path(target_filepath).parent.mkdir(parents=True, exist_ok=True)

                # Download using get_artifact (works for both models and regular artifacts)
                context.logger.info(f"  Fetching artifact with key: '{artifact_key}'")
                artifact_obj = project.get_artifact(db_key, tag="latest")
                if artifact_obj:

                    if artifact_kind == "model":
                        dataitem = mlrun.get_dataitem(artifact_obj.get_target_path()+artifact_obj.model_file)
                    else:
                        dataitem = artifact_obj.to_dataitem()

                    dataitem.download(target_path=target_filepath)
                    context.logger.info(f"  ✅ SUCCESS: Downloaded to {target_filepath}")
                    downloaded_count += 1
                else:
                    context.logger.warn(f"  Could not get artifact object for '{db_key}'")

            except Exception as e:
                context.logger.warn(f"  Failed to download '{artifact_key}': {e}")
                import traceback
                context.logger.debug(traceback.format_exc())

        context.logger.info(f"Preprocessing complete: Downloaded {downloaded_count} catalog artifacts")

    except Exception as e:
        context.logger.warn(f"Error in artifact preprocessing: {e}")
        import traceback
        context.logger.debug(traceback.format_exc())


def handler(context, event=None):
    """MLRun handler for running Kedro pipelines.

    Environment variables:
        KEDRO_PIPELINE_NAME: Pipeline to run (default: training)
        KEDRO_PROJECT_ARTIFACT: Name of tar artifact (default: risk-classifier)
        DATA_ARTIFACT: Name of CSV data artifact (default: user_data)

    Args:
        context: MLRun execution context.
        event: Optional event data (not used).
    """
    # Get configuration from environment
    pipeline_name = os.getenv("KEDRO_PIPELINE_NAME", "training")
    project_artifact = os.getenv("KEDRO_PROJECT_ARTIFACT", "risk-classifier")
    data_artifact = os.getenv("DATA_ARTIFACT", "generate-data-main_user_data.csv")

    context.logger.info(f"Starting Kedro pipeline: {pipeline_name}")
    context.logger.info(f"Project artifact: {project_artifact}")
    context.logger.info(f"Data artifact: {data_artifact}")

    # Setup project (download and unpack)
    project_path = setup_project(context, project_artifact, data_artifact)

    # Bootstrap Kedro project
    context.logger.info("Bootstrapping Kedro project...")
    bootstrap_project(project_path)

    # Create Kedro session
    context.logger.info(f"Creating Kedro session at {project_path}")
    with KedroSession.create(project_path=project_path) as session:
        copy_catalog = session.load_context().catalog
        # Preprocess: Download catalog artifacts from MLRun
        preprocess_artifacts(context, copy_catalog, project_path)

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

        from kedro.runner import SequentialRunner
        from risk_profile_classifier.pipeline_registry import register_pipelines

        runner = SequentialRunner()
        pipelines = register_pipelines()
        pipeline = pipelines.get(pipeline_name)

        # Run with the catalog that has the event data
        # hook_mng ??
        runner.run(pipeline, copy_catalog, ctx._hook_manager)
 
        context.logger.info(f"Pipeline '{pipeline_name}' completed successfully")
 
        # Post-process and log artifacts (returns results for serving pipeline)
        return post_processing(context, project_path, event, copy_catalog)


def post_processing(context, project_path: Path, event = None, catalog = None):
    """Process Kedro catalog and log artifacts to MLRun.
 
    This function automatically logs all datasets with file paths as MLRun artifacts:
    - Pickle datasets (models) → log_model()
    - CSV/Parquet datasets → log_artifact() with appropriate format
    - JSON datasets → log_artifact() with format="json"
    
    For serving pipeline with event data, also returns prediction results.
 
    Args:
        context: MLRun execution context.
        project_path: Path to the Kedro project.
        pipeline_name: Name of the pipeline that was run.
        event: Event object (if provided, indicates serving request).
        catalog: Kedro catalog (needed to load results for serving).
        
    Returns:
        For serving pipeline with event: dict with prediction results
        Otherwise: None
    """
    context.logger.info("Post-processing: Logging artifacts to MLRun...")
    project = _get_mlrun_project(context)

    artifacts_logged = 0

    # Only log artifacts if catalog is provided
    if catalog:
        for name, ds in catalog.items():
            # Skip memory datasets / parameters etc.
            if not hasattr(ds, "_filepath"):
                continue

            # Get correct path (handles versioned & non-versioned)
            filepath = str(ds._get_save_path()) if hasattr(ds, "_get_save_path") else str(ds._filepath)

            # Check if file exists before trying to log
            if not Path(filepath).exists():
                context.logger.debug(f"Skipping {name}: file doesn't exist at {filepath}")
                continue

            try:
                # ========== CSV ==========
                if isinstance(ds, CSVDataset):
                    context.logger.info(f"Logging CSV artifact: {name}")
                    logged_artifact = project.log_artifact(name, local_path=filepath, format="csv")
                    artifacts_logged += 1
                    # Print artifact URL
                    artifact_url = logged_artifact.target_path if logged_artifact else "N/A"
                    context.logger.info(f"  → Artifact URL: {artifact_url}")
                    continue

                # ========== PARQUET ==========
                if isinstance(ds, ParquetDataset):
                    context.logger.info(f"Logging Parquet artifact: {name}")
                    logger_artifact = project.log_artifact(name, local_path=filepath, format="parquet")
                    artifacts_logged += 1
                    # Print artifact URL
                    artifact_url = logger_artifact.target_path if logger_artifact else "N/A"
                    context.logger.info(f"  → Artifact URL: {artifact_url}")
                    continue

                # ========== PICKLE ==========
                if isinstance(ds, PickleDataset):
                    context.logger.info(f"Logging model: {name}")
                    logged_model = project.log_model(key=name, model_file=filepath)
                    artifacts_logged += 1
                    # Print model URL
                    model_url = logged_model.target_path if logged_model is not None else "N/A"
                    context.logger.info(f"  → Model URL: {model_url}")
                    continue

                # ========== JSON ==========
                if isinstance(ds, JSONDataset):
                    context.logger.info(f"Logging JSON artifact: {name}")
                    logged_artifact = project.log_artifact(name, local_path=filepath, format="json")

                    # If this is model_metrics, also log individual metrics as results
                    if name == "model_metrics":
                        import json
                        with open(filepath, "r") as f:
                            metrics = json.load(f)

                        # Log metrics only if context has log_result method (MLRun context, not Nuclio)
                        if hasattr(context, 'log_result'):
                            # Log accuracy
                            if "accuracy" in metrics:
                                context.log_result("accuracy", metrics["accuracy"])
                                context.logger.info(f"  → Logged metric: accuracy = {metrics['accuracy']:.4f}")

                            # Log per-class metrics from classification report
                            if "classification_report" in metrics:
                                for class_name, class_metrics in metrics["classification_report"].items():
                                    if isinstance(class_metrics, dict):
                                        for metric_name, value in class_metrics.items():
                                            if isinstance(value, (int, float)):
                                                context.log_result(f"{class_name}_{metric_name}", value)
                        else:
                            context.logger.debug("Skipping metric logging (Nuclio context)")

                    artifacts_logged += 1
                    # Print artifact URL
                    artifact_url = logged_artifact.target_path if logged_artifact else "N/A"
                    context.logger.info(f"  → Artifact URL: {artifact_url}")
                    continue

                # ========== FALLBACK: ANYTHING WITH A FILEPATH ==========
                context.logger.info(f"Logging generic artifact: {name}")
                logged_artifact = project.log_artifact(name, local_path=filepath)
                artifacts_logged += 1
                # Print artifact URL
                artifact_url = logged_artifact.target_path if logged_artifact else "N/A"
                context.logger.info(f"  → Artifact URL: {artifact_url}")

            except Exception as e:
                context.logger.warn(f"Failed to log {name}: {str(e)}")

    context.logger.info(f"Logged {artifacts_logged} artifacts to MLRun")
    
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