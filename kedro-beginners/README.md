# Kedro Bootcamp for Beginners

## Overview

1. First steps with Kedro, library components
2. Framework and template, CLI usage, VS Code extension
3. Simple production deployments with GitHub Actions
4. Databricks Asset Bundles integration with `kedro-databricks`

## Guide

### 0. Getting started

First, install [uv](https://docs.astral.sh/uv/). For example, on macOS and Linux:

```
$ curl -LsSf https://astral.sh/uv/install.sh | sh
```

Create and synchronize a Python environment:

```
$ uv sync
Using CPython 3.11.9
Creating virtual environment at: .venv
Resolved 177 packages in 0.52ms
Installed 172 packages in 887ms
...
```

If this worked, you're good to go!

### 1. First Steps with Kedro

First, open the [first steps notebook](./First%20Steps%20with%20Kedro.ipynb).
You can do so on VS Code, or alternatively launching Jupyter:

```
$ uv run jupyter notebook
```

### 2. Framework and template

Outside of the `kedro-academy` directory, create a new Kedro project:

```
$ cd kedro-academy/..
$ uvx kedro new --name=spaceflights --tools=data --example=n
$ cd spaceflights/
```

Start a git repository on it:

```
$ git init
$ git add .
$ git commit -m 'First commit, basic structure'
```

Create and synchronize a Python environment:

```
$ uv sync -p 3.11
uv sync -p 3.11
Using CPython 3.11.9
Creating virtual environment at: .venv
Resolved 133 packages in 1ms
Installed 127 packages in 473ms
...
```

You can now start using the Kedro CLI.
For example, create a `data_processing` pipeline:

```
$ uv run kedro pipeline create
...
Creating the pipeline 'data_processing': OK
...
Pipeline 'data_processing' was successfully created.
...
```

A `src/spaceflights/pipelines/data_processing` Python package will be created,
with two modules:

- `nodes.py` (for the node functions that form the data processing)
- `pipeline.py` (to build the pipeline)

Using the example from the notebook,
the code would now be structured as follows:

```python
# pipeline.py
from kedro.pipeline import Pipeline, pipeline, node

from .nodes import preprocess_companies


def create_pipeline(**kwargs) -> Pipeline:
    return pipeline(
        [
            node(
                func=preprocess_companies,
                inputs="companies",
                outputs="preprocessed_companies",
                name="preprocess_companies_node",  # Notice the `name=`!
            )
        ]
    )

# nodes.py
import pandas as pd

def _is_true(x: pd.Series) -> pd.Series:
    return x == "t"


def _parse_percentage(x: pd.Series) -> pd.Series:
    x = x.str.replace("%", "")
    x = x.astype(float) / 100
    return x


def preprocess_companies(companies: pd.DataFrame) -> pd.DataFrame:
    companies["iata_approved"] = _is_true(companies["iata_approved"])
    companies["company_rating"] = _parse_percentage(companies["company_rating"])
    return companies
```

In addition, you will need the Data Catalog entries.
The default template places it in `conf/base/catalog.yml`:

```yaml
# catalog.yml
_root: https://raw.githubusercontent.com/kedro-org/kedro-starters/refs/heads/main/spaceflights-pandas/%7B%7B%20cookiecutter.repo_name%20%7D%7D/

companies:
  type: pandas.CSVDataset
  filepath: ${_root}data/01_raw/companies.csv

reviews:
  type: pandas.CSVDataset
  filepath: ${_root}data/01_raw/reviews.csv

shuttles:
  type: pandas.ExcelDataset
  filepath: ${_root}data/01_raw/shuttles.xlsx
  load_args:
    engine: openpyxl
```

Finally, you will need to install the appropriate dependencies:

```
$ uv add pandas requests aiohttp kedro-datasets[pandas]
...
```

With this, you should be able to run the pipeline:

```
$ uv run kedro run -p data_processing
...
INFO     Kedro project spacelights
INFO     Loading data from companies (CSVDataset)...
INFO     Running node: preprocess_companies([companies]) -> [preprocessed_companies]
INFO     Saving data to preprocessed_companies (MemoryDataset)...
INFO     Completed 1 out of 1 tasks
INFO     Pipeline execution completed successfully.
INFO     Loading data from preprocessed_companies (MemoryDataset)...
```

Done! Notice that you didn't have to instantiate
the `DataCatalog`, `OmegaConfigLoader`, or `SequentialRunner`.
Kedro does this for you behind the scenes.

#### Exercise

- Fill the rest of the pipeline from the notebook
- Declare the `model_input_table` in the catalog as a Parquet file
  to be saved in `data/03_primary`.
  Look for the appropriate dataset type in
  [the `kedro-datasets` API documentation].

[the `kedro-datasets` API documentation]: https://docs.kedro.org/projects/kedro-datasets/en/kedro-datasets-6.0.0/api/kedro_datasets.html

### 3. Simple production deployments with GitHub Actions

Create a new GitHub repository, and push the contents:

```
$ git remote add origin ...@github.com:.../kedro-beginners-....git
  git branch -M main
  git push -u origin main
```

Navigate to the "Actions" tab. You will see some suggested templates.
Locate the "Python application" one and click Configure
to use that as a template.

The steps should look like this:

```yaml
    steps:
    - uses: actions/checkout@v4
    - name: Set up Python
      uses: actions/setup-python@v3
      with:
        python-version: "3.11"
    - name: Install the latest version of uv
      uses: astral-sh/setup-uv@v5
      with:
        python-version: "3.11"
    - name: Run Kedro pipeline
      run: |
        uv run --frozen kedro run -p data_processing
```

Now GitHub Actions will execute `kedro run` every time you push to the main branch!

> [!WARNING]
> If your `uv.lock` refers to a private artifactory, you will have to deal with authentication.
> For example, you can create a `.netrc` file:
> ```
> - name: Create .netrc file
>   run: |
>     echo "machine ${{ secrets.ARTIFACTORY_DOMAIN }}" >> ~/.netrc
>     echo "  login ${{ secrets.ARTIFACTORY_USER }}" >> ~/.netrc
>     echo "  password ${{ secrets.ARTIFACTORY_PASS }}" >> ~/.netrc
> ```

#### Exercise

- Tweak the conditions so that this runs on a regular cadence (for example 5 minutes to see the effect).
  _Hint: Keyword is "cron"_.

### 4. Databricks Asset Bundles integration

First, authenticate to your Databricks instance using the Databricks CLI:

```
$ databricks configure --token
Databricks host: https://...
Personal access token: *****...
```

Verify that it worked:

```
$ databricks fs ls dbfs:/
Shared
Volume
Volumes
databricks-datasets
...
```

Now, install [`kedro-databricks`](https://pypi.org/project/kedro-databricks/):

```
$ uv add kedro-databricks
```

Initialise the `kedro-databricks` configuration:

```
$ uv run kedro databricks init
...
Please select your cloud provider:
1. Azure
2. AWS
3. GCP
 [1]: 1
...
INFO     Creating databricks configuration: Wrote databricks.yml
INFO     Creating bundle override configuration: Wrote conf/base/databricks.yml
...
```

Then, create the bundle:

```
$ uv run databricks bundle
...
INFO     Create Asset Bundle Resources: Databricks resources successfully generated.
INFO     Writing resource 'spacelights': Wrote resources/spacelights.yml
INFO     Writing resource 'spacelights_data_processing': Wrote resources/spacelights_data_processing.yml
...
```

Next, deploy it:

```
$ uv run kedro databricks deploy
```

> [!NOTE]
> Sometimes the logs will say `ERROR` even if the underlying command was successful,
> see [this issue](https://github.com/JenspederM/kedro-databricks/issues/97).

And finally, execute it:

```
$ databricks bundle run
Run URL: ...

... "[dev ...] spacelights_data_processing" RUNNING
...
```

> [!NOTE]
> If you get a permission error here because you cannot create new clusters,
> follow [these instructions] to use an existing one instead.

[these instructions]: https://docs.kedro.org/en/stable/deployment/databricks/databricks_ide_databricks_asset_bundles_workflow.html#running-a-databricks-job-using-an-existing-cluster

Seat back and relax while your Kedro pipeline should execute on Databricks!
