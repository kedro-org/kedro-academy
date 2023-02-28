# Kedro pipelines

It is time to introduce the most basic elements of Kedro before we dive into the spaceflights pipelines. 

## Introduction to nodes and pipelines

A `node` is a Kedro concept. It is a wrapper for a Python function that names the inputs and outputs of that function. It is the building block of a pipeline. Nodes can be linked when the output of one node is the input of another.

A pipeline organises the dependencies and execution order of a collection of nodes, and connects inputs and outputs while keeping your code modular. The pipeline determines the node execution order by resolving dependencies and does *not* necessarily run the nodes in the order in which they are passed in.

A Runner is an object that runs the pipeline once Kedro resolves the order in which the nodes are executed.

## Spaceflights nodes

Let's create a file `src/kedro_training/pipelines/data_processing/nodes.py` and add the following functions:

```python
import pandas as pd


def _is_true(x):
    return x == "t"


def _parse_percentage(x):
    x = x.str.replace("%", "")
    x = x.astype(float) / 100
    return x


def _parse_money(x):
    x = x.str.replace("$", "").str.replace(",", "")
    x = x.astype(float)
    return x
```

You should also add these empty functions and follow the instructions to complete them:

```python
def preprocess_companies(companies: pd.DataFrame) -> pd.DataFrame:
    """Preprocesses the data for companies.

    Args:
        companies: Raw data.
    Returns:
        Preprocessed data, with `company_rating` converted to a float and
        `iata_approved` converted to boolean.
    """
    # This function should preprocess the 'companies' DataFrame by doing the following:
    # 1. Convert 'iata_approved' column to boolean using _is_true
    # 2. Convert 'company_rating' column to float using _parse_percentage
    return companies


def preprocess_shuttles(shuttles: pd.DataFrame) -> pd.DataFrame:
    """Preprocesses the data for shuttles.

    Args:
        shuttles: Raw data.
    Returns:
        Preprocessed data, with `price` converted to a float and `d_check_complete`,
        `moon_clearance_complete` converted to boolean.
    """
    # This function should preprocess the 'shuttles' DataFrame by doing the following:
    # 1. Convert 'd_check_complete' and 'moon_clearance_complete' columns to boolean
    # using _is_true
    # 2. Convert 'price' column to float using _parse_money
    return shuttles


def create_master_table(
    shuttles: pd.DataFrame, companies: pd.DataFrame, reviews: pd.DataFrame
) -> pd.DataFrame:
    """Combines all data to create a master table.

    Args:
        shuttles: Preprocessed data for shuttles.
        companies: Preprocessed data for companies.
        reviews: Raw data for reviews.
    Returns:
        Master table.

    """
    # This function should prepare the master table by doing the following:
    # 1. Join 'shuttles' with 'reviews' based on shuttle IDs
    # 2. Join the result of step 1 with 'companies' based on company IDs
    # 3. Drop rows with any missing values from the resulting master table
    return master_table
```

<details>
<summary><b>CLICK TO SEE THE ANSWER</b></summary>

```python
import pandas as pd


def _is_true(x):
    return x == "t"


def _parse_percentage(x):
    x = x.str.replace("%", "")
    x = x.astype(float) / 100
    return x


def _parse_money(x):
    x = x.str.replace("$", "").str.replace(",", "")
    x = x.astype(float)
    return x


def preprocess_companies(companies: pd.DataFrame) -> pd.DataFrame:
    """Preprocesses the data for companies.

    Args:
        companies: Raw data.
    Returns:
        Preprocessed data, with `company_rating` converted to a float and
        `iata_approved` converted to boolean.
    """
    companies["iata_approved"] = _is_true(companies["iata_approved"])
    companies["company_rating"] = _parse_percentage(companies["company_rating"])
    return companies


def preprocess_shuttles(shuttles: pd.DataFrame) -> pd.DataFrame:
    """Preprocesses the data for shuttles.

    Args:
        shuttles: Raw data.
    Returns:
        Preprocessed data, with `price` converted to a float and `d_check_complete`,
        `moon_clearance_complete` converted to boolean.
    """
    shuttles["d_check_complete"] = _is_true(shuttles["d_check_complete"])
    shuttles["moon_clearance_complete"] = _is_true(shuttles["moon_clearance_complete"])
    shuttles["price"] = _parse_money(shuttles["price"])
    return shuttles


def create_master_table(
    shuttles: pd.DataFrame, companies: pd.DataFrame, reviews: pd.DataFrame
) -> pd.DataFrame:
    """Combines all data to create a master table.

    Args:
        shuttles: Preprocessed data for shuttles.
        companies: Preprocessed data for companies.
        reviews: Raw data for reviews.
    Returns:
        Master table.

    """
    rated_shuttles = shuttles.merge(reviews, left_on="id", right_on="shuttle_id")
    master_table = rated_shuttles.merge(companies, left_on="company_id", right_on="id")
    master_table = master_table.dropna()
    return master_table
```


</details>

## Assemble nodes into a modular pipeline

### Create the data processing pipeline

You have utility functions and two processing functions, `preprocess_companies` and `preprocess_shuttles`, which take Pandas dataframes for `companies` and `shuttles` respectively and output preprocessed versions of those dataframes.

Next you should create the data processing pipeline, which represents a collection of `Node` objects.  To do so, add the following code to `src/kedro_training/pipelines/data_processing/pipeline.py` and follow the instructions to complete it:

```python
from kedro.pipeline import Pipeline, node

from .nodes import create_master_table, preprocess_companies, preprocess_shuttles


def create_pipeline(**kwargs):
    # Here you need to construct a data processing ('dp_pipeline') object, which
    # satisfies the following requirements:
    # 1. Is an instance of the Pipeline class
    # 2. Contains 3 pipeline nodes:
    #   a. A node called 'preprocess_companies_node' that maps 'companies'
    #      to 'preprocessed_companies' by using the 'preprocess_companies' function
    #   b. A node called 'preprocess_shuttles_node' that maps 'shuttles'
    #      to 'preprocessed_shuttles' by using the 'preprocess_shuttles' function
    #   c. A node called 'create_master_table_node' that takes 'preprocessed_shuttles',
    #      'preprocessed_companies' and 'reviews' as inputs and produces a single output
    #      called 'master_table' by using the 'create_master_table' function
    return dp_pipeline
```



<details>
<summary><b>CLICK TO SEE THE ANSWER</b></summary>

```python
from kedro.pipeline import Pipeline, node

from .nodes import create_master_table, preprocess_companies, preprocess_shuttles


def create_pipeline(**kwargs):
    return Pipeline(
        [
            node(
                func=preprocess_companies,
                inputs="companies",
                outputs="preprocessed_companies",
                name="preprocess_companies_node",
            ),
            node(
                func=preprocess_shuttles,
                inputs="shuttles",
                outputs="preprocessed_shuttles",
                name="preprocess_shuttles_node",
            ),
            node(
                func=create_master_table,
                inputs=["preprocessed_shuttles", "preprocessed_companies", "reviews"],
                outputs="master_table",
                name="create_master_table_node",
            ),
        ]
    )
```
</details>

> Note: The `inputs` and `outputs` arguments are not passed into the underlying function as-is. Instead, Kedro locates the dataset with that name from `conf/base/catalog.yml`, loads it and passes the loaded data as the input for your function call. Outputs are handled similarly - Kedro captures all the outputs and saves them into the corresponding datasets.

To turn it into a Python package, create a file `src/kedro_training/pipelines/data_processing/__init__.py` containing the following:

```python
from .pipeline import create_pipeline  # NOQA
```


## Create the data science pipeline

The data science pipeline is similar conceptually; it requires nodes and the pipeline definition.

Let's create `src/kedro_training/pipelines/data_science/nodes.py`, put the following code in it to create the nodes, and follow the instructions to complete it:

```python
import logging
from typing import Dict, Tuple

import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score
from sklearn.model_selection import train_test_split


def split_data(data: pd.DataFrame, parameters: Dict) -> Tuple:
    """Splits data into features and targets training and test sets.

    Args:
        data: Data containing features and target.
        parameters: Parameters defined in parameters.yml.
    Returns:
        Split data.
    """
    # 1. Create X object that contains a subset of columns from data given by a list 
    # parameters["features"]
    # 2. Take the 'price' column from data and put them into 'y' object
    # 3. Split X and y into train and test sets X_train, X_test, y_train, y_test by
    # using 'train_test_split' and parameters["test_size"] and parameters["random_state"]
    return X_train, X_test, y_train, y_test


def train_model(X_train: pd.DataFrame, y_train: pd.Series) -> LinearRegression:
    """Trains the linear regression model.

    Args:
        X_train: Training data of independent features.
        y_train: Training data for price.

    Returns:
        Trained model.
    """
    regressor = LinearRegression()
    regressor.fit(X_train, y_train)
    return regressor


def evaluate_model(
    regressor: LinearRegression, X_test: pd.DataFrame, y_test: pd.Series
):
    """Calculates and logs the coefficient of determination.

    Args:
        regressor: Trained model.
        X_test: Testing data of independent features.
        y_test: Testing data for price.
    """
    # 1. Calculate predictions for X_test using the regressor object
    # 2. Calculate the R^2 score for the calculated predictions
    # 3. Log the calculated R^2 score

```

<details>
<summary><b>CLICK TO SEE THE ANSWER</b></summary>

```python
import logging
from typing import Dict, Tuple

import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score
from sklearn.model_selection import train_test_split


def split_data(data: pd.DataFrame, parameters: Dict) -> Tuple:
    """Splits data into features and targets training and test sets.

    Args:
        data: Data containing features and target.
        parameters: Parameters defined in parameters.yml.
    Returns:
        Split data.
    """
    X = data[parameters["features"]]
    y = data["price"]
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=parameters["test_size"], random_state=parameters["random_state"]
    )
    return X_train, X_test, y_train, y_test


def train_model(X_train: pd.DataFrame, y_train: pd.Series) -> LinearRegression:
    """Trains the linear regression model.

    Args:
        X_train: Training data of independent features.
        y_train: Training data for price.

    Returns:
        Trained model.
    """
    regressor = LinearRegression()
    regressor.fit(X_train, y_train)
    return regressor


def evaluate_model(
    regressor: LinearRegression, X_test: pd.DataFrame, y_test: pd.Series
):
    """Calculates and logs the coefficient of determination.

    Args:
        regressor: Trained model.
        X_test: Testing data of independent features.
        y_test: Testing data for price.
    """
    y_pred = regressor.predict(X_test)
    score = r2_score(y_test, y_pred)
    logger = logging.getLogger(__name__)
    logger.info("Model has a coefficient R^2 of %.3f on test data.", score)

```
</details>

Then we have to build the data science pipeline definition in `src/kedro_training/pipelines/data_science/pipeline.py` with the following code. Follow the instructions to complete it:

```python
from kedro.pipeline import Pipeline, node

from .nodes import evaluate_model, split_data, train_model


def create_pipeline(**kwargs):
    # Here you need to construct a data science ('ds_pipeline') object, which satisfies
    # the following requirements:
    # 1. Is an instance of a Pipeline class
    # 2. Contains 3 pipeline nodes:
    #   a. Split data: a node that takes 'master_table' and 'parameters' as inputs and
    #   produces 4 objects: 'X_train', 'X_test', 'y_train', 'y_test' by using split_data 
    #   b. Train model: a node that takes 'X_train' and 'y_train' inputs and produces
    #   'regressor' object by using train_model 
    #   c. Evaluate model: a node that takes 'regressor', 'X_test', 'y_test' inputs and
    #   runs 'evaluate_model' function - note that this node does not produce any
    #   outputs

    return ds_pipeline
```

<details>
<summary><b>CLICK TO SEE THE ANSWER</b></summary>

```python
from kedro.pipeline import Pipeline, node

from .nodes import evaluate_model, split_data, train_model


def create_pipeline(**kwargs):
    return Pipeline(
        [
            node(
                func=split_data,
                inputs=["master_table", "parameters"],
                outputs=["X_train", "X_test", "y_train", "y_test"],
                name="split_data_node",
            ),
            node(
                func=train_model,
                inputs=["X_train", "y_train"],
                outputs="regressor",
                name="train_model_node",
            ),
            node(
                func=evaluate_model,
                inputs=["regressor", "X_test", "y_test"],
                outputs=None,
                name="evaluate_model_node",
            ),
        ]
    )
```
</details>


We also need to modify `conf/base/parameters.yml` by replacing its contents with the following:

```yaml
test_size: 0.2
random_state: 3
features:
  - engines
  - passenger_capacity
  - crew
  - d_check_complete
  - moon_clearance_complete
  - iata_approved
  - company_rating
  - review_scores_rating
```

Don't forget to create a file `src/kedro_training/pipelines/data_science/__init__.py` containing the following:

```python
from .pipeline import create_pipeline  # NOQA
```

## Register the pipelines

Finally, let's look at where to register both the data processing and data science pipelines, in `src/kedro_training/pipeline_registry.py`:

```python
from typing import Dict

from kedro.pipeline import Pipeline

from kedro_training.pipelines import data_processing as dp
from kedro_training.pipelines import data_science as ds


def register_pipelines() -> Dict[str, Pipeline]:
    """Register the project's pipelines.

    Returns:
        A mapping from a pipeline name to a ``Pipeline`` object.

    """
    data_processing_pipeline = dp.create_pipeline()
    data_science_pipeline = ds.create_pipeline()

    return {
        "__default__": data_processing_pipeline + data_science_pipeline,
        "dp": data_processing_pipeline,
        "ds": data_science_pipeline,
    }

```


## Run a modular pipeline

To run your data processing pipeline from the terminal:

```bash
kedro run --pipeline dp
```

Or run this pipeline from a Jupyter Notebook cell:

```python
context.run(pipeline_name="dp")
```

> Note: It is considered best-practice to restart your Jupyter Notebook kernel (`Kernel` menu -> `Restart`) every time you have made some changes to the pipeline and / or node code.

## Modular pipeline structure

Modular pipelines are intended to be reusable across various projects. As a pipeline developer, you should follow convention and document how your pipeline should be used.  Consult the extensive [Kedro documentation about modular pipelines](https://kedro.readthedocs.io/en/stable/06_nodes_and_pipelines/03_modular_pipelines.html) for further information

## Persist the intermediate data

It is important to emphasise that the Kedro pipeline is runnable only if _all_ free inputs, i.e. the datasets that are not produced by any of the nodes, are defined in `catalog.yml`. In the Spaceflights project those free inputs are: `companies`, `shuttles`, `reviews`.

All intermediate datasets, however, can be missing from the `catalog.yml`, and your pipeline will still run without errors. This is because Kedro automatically creates a `MemoryDataSet` for each intermediary dataset that is not defined in the `DataCatalog`. Intermediary datasets in the Spaceflights project are: `preprocessed_companies`, `preprocessed_shuttles`, `master_table`, `X_train`, `X_test`, `y_train`, `y_test`, `regressor`.

These `MemoryDataSet`s pass data across nodes during the run, but are automatically deleted after the run finishes, therefore if you want to have an access to those intermediary datasets after the run, you need to define them in `catalog.yml`.

Let's say, we want to persist the `regressor` dataset to local disk. `regressor` is a `LinearRegression` object returned by the `train_model` node. We can't use, for instance, `pandas.CSVDataSet` since it only works with `pandas` DataFrames, but we can instead utilise `pickle.PickleDataSet` that allows to serialise Python objects and store them in the file system. Now all you have to do is to add the following dataset definition to `conf/base/catalog.yml`:

```yaml
regressor:
  type: pickle.PickleDataSet
  filepath: data/06_models/regressor.pickle
```

## How to filter Kedro pipelines

Kedro has a flexible mechanism to filter the pipeline that you intend to run, which is described fully in the [Kedro CLI documentation](https://kedro.readthedocs.io/en/stable/09_development/03_commands_reference.html#modifying-a-kedro-run).

## Kedro runners

Having specified the data catalog and the pipeline, you are now ready to run the pipeline. There are three different Kedro runners that can run the pipeline:

* `SequentialRunner` - runs your nodes sequentially; once a node has completed its task then the next one starts.
* `ParallelRunner` - runs your nodes in parallel; independent nodes are able to run at the same time, which is more efficient when there are independent branches in your pipeline and allows you to take advantage of multiple CPU cores.
* `ThreadRunner` - runs your nodes in parallel, similarly to `ParallelRunner`, but uses multithreading instead of multiprocessing.

By default, Kedro uses a `SequentialRunner`, which is instantiated when you execute `kedro run` from the command line. If you decide to use `ParallelRunner`, provide an additional flag when running the pipeline from the command line:

```bash
kedro run --parallel
```

If you want to run using `ThreadRunner` or a custom runner, you can do so by running:

```bash
kedro run --runner=ThreadRunner
```

> *Note:* `ParallelRunner` performs task parallelisation, which is different from data parallelisation as seen in PySpark. `SparkDataSet` doesn't work correctly with `ParallelRunner`. To add concurrency to the pipeline with `SparkDataSet`, you must use `ThreadRunner`. For more information on how to maximise concurrency when using Kedro with PySpark, please visit our guide on [how to build a Kedro pipeline with PySpark](https://kedro.readthedocs.io/en/stable/11_tools_integration/01_pyspark.html).



_[Go to the next page](./08_visualisation.md)_
