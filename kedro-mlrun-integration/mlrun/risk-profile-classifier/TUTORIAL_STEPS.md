# Serving a Kedro project on MLRun

This tutorial shows how to run and serve a standard Kedro project on MLRun,
using the Risk Profile Classifier project as the example. It covers the full
flow — packaging the project, training as an MLRun job, and serving predictions
through a Nuclio endpoint — along with the configuration details that make it
work.

## Overview

The demo runs a normal Kedro project inside MLRun by:
1. Zipping the Kedro project and logging it as an MLRun artifact.
2. Running it inside MLRun functions via a generic handler (`mlrun_handler.py`)
   that downloads the zip, bootstraps Kedro, and runs a pipeline with the
   `mlrun` Kedro environment (`conf/mlrun`), whose catalog swaps the file-based
   datasets for MLRun-native dataset types (`kedro-datasets[mlrun]`) that
   read/write the MLRun artifact store and model registry.
3. The same handler powers both a **training job** and a **serving** (Nuclio)
   endpoint, switched via the `KEDRO_PIPELINE_NAME` env var.

Driver notebook: `mlrun/risk-profile-classifier/run-and-serve-kedro.ipynb`.

## Prerequisites

- **MLRun CE (Community Edition) installed and running** on a Kubernetes
  cluster, with access to its API server. All notebooks deploy and run their
  functions on that cluster, so MLRun must be up before executing any cells.
  See https://docs.mlrun.org/en/stable/install/kubernetes.html for the CE
  install, then set `MLRUN_DBPATH` to the cluster's API server URL.
- A function image containing Kedro + `kedro-datasets[mlrun]`. To build your
  own, set `DOCKER_REGISTRY` and run `make build-kedro push-kedro` (see
  `Makefile` + `kedro/Dockerfile`), then use that image tag below.
- Local env set up via the `make` install targets (see Step 0).

## Step 0 — Install dependencies (run from repo root)

Run these `make` targets once to set up the local environment:

```bash
make install-requirements        # uv pip install -r requirements-dev.txt (mlrun==1.10.0 + kedro reqs)
make install-kedro               # uv pip install -r kedro/requirements.txt
make install-kedro-mlrun-dataset # pip install "kedro-datasets[mlrun]" (MLRun-native dataset types)
```

- `install-requirements` also pulls in `kedro/requirements.txt` (it's `-r`'d
  from `requirements-dev.txt`), so it overlaps with `install-kedro`.
- `install-kedro-mlrun-dataset` is **required**: the handler runs the pipeline
  with the `mlrun` Kedro environment, whose catalog (`conf/mlrun/catalog.yml`)
  uses the MLRun-native dataset types provided by `kedro-datasets[mlrun]`.

## Step 0.5 — Build the function image

The MLRun functions run inside a custom image (Kedro + `kedro-datasets[mlrun]`).

1. Set the `DOCKER_REGISTRY` env var first — `make build-kedro` uses it to tag
   the image so it can be pushed and pulled by the cluster:
   ```bash
   export DOCKER_REGISTRY=<your-registry>
   ```
   - Find the value via MLRun's configured default registry:
     `python -c "import mlrun; print(mlrun.mlconf.httpdb.builder.docker_registry)"`,
     or use your Docker Hub username, or a cloud registry host (ECR/GCR/ACR).
2. Make sure Docker is running (`docker info`).
3. Build the image from the repo root:
   ```bash
   make build-kedro        # builds mlrun-kedro:latest and tags it as $DOCKER_REGISTRY/mlrun-kedro:latest
   ```
4. Push it so the cluster can pull it:
   ```bash
   make push-kedro         # or use `make deploy-kedro` to build + push in one step
   ```
5. Use this image tag (`$DOCKER_REGISTRY/mlrun-kedro:latest`) in place of
   `rokatyy/kedro-mlrun:0.0.1` in steps 4 and 5.

## Steps (following run-and-serve-kedro.ipynb)

1. **Create / load the MLRun project**
   ```python
   import mlrun
   project = mlrun.get_or_create_project("kedro-test")
   ```

2. **Generate + log the training data**
   ```python
   function = project.set_function(
       name="generate-data", func="../generate_data.py",
       requirements=["pandas", "numpy"], kind="job",
       image="mlrun/mlrun:1.10.0-rc41", handler="main")
   function.run()
   ```
   - Verify the logged artifact name: `project.list_artifacts()` → note the
     `db_key` (e.g. `generate-data-main_user_data_csv`). It must match the
     `raw_user_data` key in `conf/mlrun/catalog.yml`.

3. **Package the Kedro project and log it as the `risk-classifier` artifact**
   ```python
   from pathlib import Path
   import shutil
   Path("archive").mkdir(exist_ok=True)        # make_archive won't create this
   shutil.make_archive("archive/riskclassifier", "zip",
       root_dir="../../kedro/risk-profile-classifier")
   project.log_artifact(
       item="risk-classifier",                 # == KEDRO_PROJECT_ARTIFACT
       local_path="archive/riskclassifier.zip", format="zip",
       artifact_path="v3io:///projects/kedro-test/artifacts/", upload=True)
   ```
   - Re-run this step whenever the Kedro code changes.

4. **Train (MLRun job)** — runs the `training` pipeline (handler default):
   ```python
   training_function = project.set_function(
       name="kedro-training", func="mlrun_handler.py", kind="job",
       image="rokatyy/kedro-mlrun:0.0.1", handler="handler")
   training_function.with_code("mlrun_handler.py")
   training_function.run()
   ```
   - Produces + logs the model, feature scaler, and metrics. Must succeed
     before serving.

5. **Deploy serving (Nuclio remote function)** — switch pipeline to `serving`:
   ```python
   serving_function = project.set_function(
       name="kedro-serving", func="mlrun_handler.py", kind="remote",
       image="rokatyy/kedro-mlrun:0.0.1", handler="handler")
   serving_function.set_env("KEDRO_PIPELINE_NAME", "serving")
   serving_function.set_env("KEDRO_PROJECT_ARTIFACT", "risk-classifier")
   serving_function.with_code("mlrun_handler.py")
   serving_function.deploy()
   ```

6. **Invoke the endpoint**
   ```python
   serving_function.invoke(path="/", body={
     "age": 22, "income": 1200, "investment_experience_years": 20,
     "savings_ratio": 0.35, "debt_ratio": 0.10,
     "risk_tolerance_score": 3, "portfolio_volatility": 0.10
   })
   # -> {'predictions': [{'predicted_risk_profile': 'conservative', ...}]}
   ```

## How the serving I/O is wired

- `conf/mlrun/catalog.yml` tags the serving datasets:
  - `user_input` → `nuclio_event: true` (filled from the HTTP `event.body`)
  - `predictions` → `nuclio_response: true` (returned in the HTTP response)
- The handler feeds the request body into the `nuclio_event` dataset and returns
  the `nuclio_response` dataset.

## Notes and troubleshooting

- The `archive/` directory must exist before `shutil.make_archive` (step 3).
- The `raw_user_data` key in `conf/mlrun/catalog.yml` must match the data
  artifact's `db_key` from step 2. Watch for the dotted-vs-underscore form
  (`generate-data-main_user_data.csv` vs `..._user_data_csv`); update the
  catalog key if they differ.
- Train (step 4) must run before serving (steps 5–6) — serving loads the
  model and scaler artifacts produced by training.
- `generate_data.py` hardcodes `artifact_path="v3io:///projects/my-project/..."`
  — adjust it to the actual project (`kedro-test`).
- Swap `rokatyy/kedro-mlrun:0.0.1` for your own image if it isn't pullable.
- **Safe to ignore:** the warning `User code exceeds the maximum allowed size of
  10000 bytes for non remote source. Consider using with_source_archive ...`
  (from `with_code(...)` on the large `mlrun_handler.py`). It's cosmetic — MLRun
  still embeds the code and the function deploys and runs fine. To silence it,
  bake the handler into the image (`COPY mlrun_handler.py ...`) or use
  `with_repo=True` / `with_source_archive`.

