# Kedro Tutorial: Image Classification

This Kedro project demonstrates how to use Kedro for image classification tasks. For this tutorial, we'll be using the [Ships in Satellite Imagery dataset from Kaggle](https://www.kaggle.com/datasets/rhammell/ships-in-satellite-imagery). The dataset contains 4000 images in total, with 1000 images containing ships(positive class) and 3000 images not containing ships or partially containing ships(negative class).

## Setup

1. Clone this project locally
2. Install dependencies
```bash
pip install -r requirements.txt
```
3. Download the [dataset from Kaggle](https://www.kaggle.com/datasets/rhammell/ships-in-satellite-imagery) and place it in the `data/01_raw` directory

## Setup Minio (optional)
1. Spin up MinIO:

```
$ docker compose up -d 
```
2. Create a `data` bucket:

```
$ mc alias set myminio http://127.0.0.1:9010 minioadmin minioadmin
$ mc mb myminio/data
```

3. Add to local/credentials.yml
```
minio_credentials:
    key: minioadmin
    secret: minioadmin
    client_kwargs:
        endpoint_url: http://127.0.0.1:9010
```

4. Update `catalog.py` datasets:

```
accuracy_plot:
  type: plotly.JSONDataset
  filepath: s3://data/08_reporting/accuracy_plot.json
  credentials: minio_credentials

loss_plot:
  type: plotly.JSONDataset
  filepath: s3://data/08_reporting/loss_plot.json
  credentials: minio_credentials
```



## Part 1: Introduction to the project and Kedro concepts

For the first part of the tutorial, we'll be going through the raw data science code and see how to refactor it to make it more modular and reusable. We'll also start using Kedro as a library to explore and process the data with the help of `DataCatalog` and `OmegaConfigLoader` components.

This project contains three notebooks:
- `notebook_raw.ipynb`: This notebook contains the raw unstructured code for the image classification task
- `notebook_refactor.ipynb`: This notebook contains refactored code which uses methods and contains some degree of separation of configuration.
- `notebook_kedro.ipynb`: This notebook introduces Kedro's `DataCatalog` and the `OmegaConfigLoader` to perform the loading and processing of the data.

## Part 2: Introduction to Kedro framework

In this part, we'll be introduced to the Kedro project structure, how to structure the image classification code from notebooks to pipelines.

The following documentation pages will be helpful to follow along:
- [Creating a new Kedro project](https://docs.kedro.org/en/stable/get_started/new_project.html)
- [Kedro project directory structure](https://docs.kedro.org/en/stable/get_started/kedro_concepts.html#kedro-project-directory-structure)
- Organising code into [nodes](https://docs.kedro.org/en/stable/nodes_and_pipelines/nodes.html) and [pipelines](https://docs.kedro.org/en/stable/nodes_and_pipelines/pipeline_introduction.html)
- Making development easier on VSCode with the [VSCode Kedro extension](https://marketplace.visualstudio.com/items?itemName=kedro.Kedro)
- [Visualising the pipeline with Kedro-Viz](https://docs.kedro.org/projects/kedro-viz/en/stable/kedro-viz_visualisation.html)

## Part 3: Experiment tracking with Kedro and Mlflow

In this part, we'll be talking about how Kedro can be used to track experiments with the help of Mlflow. We'll be using the [`kedro-mlflow` plugin](https://kedro-mlflow.readthedocs.io/en/stable/) to help log metrics, parameters, and artifacts to Mlflow. Here's [a tutorial on the Kedro docs to add Mlflow to your Kedro workflow](https://docs.kedro.org/en/stable/integrations/mlflow.html).

## Part 4: Deploying a Kedro project on Airflow

Finally, we'll explore how to deploy a Kedro project on Airflow. We'll be using the `kedro-airflow` plugin to help us deploy the Kedro project on Airflow. Here's [a tutorial on the Kedro docs to deploy a Kedro project on Airflow](https://docs.kedro.org/en/stable/deployment/airflow.html).
