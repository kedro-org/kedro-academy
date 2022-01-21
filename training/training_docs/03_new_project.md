# Create a new project

This section mirrors the [spaceflights tutorial in the Kedro documentation](https://kedro.readthedocs.io/en/stable/03_tutorial/01_spaceflights_tutorial.html). 

As we work with the spaceflights tutorial, we will follow these steps:

### 1. Set up the project template

* Create a new project with `kedro new`
* Install project dependencies with `pip install -r src/requirements.txt`
* Configure the following in the `conf` folder:
	* Logging
	* Credentials
	* Any other sensitive / personal content

### 2. Set up the data

* Add data to the `data/` folder
* Reference all datasets for the project in `conf/base/catalog.yml`

### 3. Create the pipeline

* Create the data transformation steps as Python functions
* Construct the pipeline by adding your functions as nodes
* Choose how to run the pipeline: sequentially or in parallel

### 4. Package the project

 * Build the project documentation
 * Package the project for distribution


## Create and set up a new project

In this section, we discuss the project set-up phase, with the following steps:


* Create a new project
* Install dependencies
* Configure the project

----
In the text, we assume that you create an empty project and follow the flow of the tutorial by copying and pasting the example code into the project as we describe. This tutorial will take approximately 2 hours and you will learn each step of the Kedro project development workflow, by working on an example to construct nodes and pipelines for the price-prediction model.

However, you may prefer to get up and running more swiftly so we provide the full spaceflights example project as a [Kedro starter](https://kedro.readthedocs.io/en/stable/02_get_started/06_starters.html). 

Follow one or other of these instructions to create the project:

* If you decide to create the example project fully populated with code, navigate to your chosen working directory and run the following: `kedro new --starter=spaceflights`

     - Feel free to name your project as you like, but this guide will assume the project is named **`Kedro Training`**, and that your project is in a sub-folder in your working directory that was created by `kedro new`, named `kedro-training`.

     - Keep the default names for the `repo_name` and `python_package` when prompted.

    - The project will be populated with the template code from the [Kedro starter for the spaceflights tutorial](https://github.com/kedro-org/kedro-starters/tree/main/spaceflights). This means that you can follow the tutorial without any of the copy/pasting.

* If you prefer to create an empty tutorial and copy and paste the code to follow along with the steps, you should instead run `kedro new` to [create a new empty Kedro project](https://kedro.readthedocs.io/en/stable/02_get_started/04_new_project.html#create-a-new-project-interactively).

     - Feel free to name your project as you like, but this guide will assume the project is named **`Kedro Training`**, and that your project is in a sub-folder in your working directory that was created by `kedro new`, named `kedro-training`.

    - Keep the default names for the `repo_name` and `python_package` when prompted.


### Project structure
Take a few minutes to familiarise yourself with the [Kedro project structure](https://kedro.readthedocs.io/en/stable/02_get_started/05_example_project.html#project-directory-structure) by exploring the contents of the `kedro-training` folder that you created from either of the steps you chose above.


## Configure the project

You may optionally add in any credentials to `conf/local/credentials.yml` that you would need to load specific data sources like usernames and passwords. Some examples are given within the file to illustrate how you store credentials. Additional information can be found in a later page on [advanced configuration](./11_configuration.md).

When it runs, Kedro automatically reads credentials from the `conf` folder and feeds them into the Data Catalog, which is responsible for loading and saving data as inputs and outputs of pipeline nodes. You can configure your credentials once and then reuse them in multiple datasets.

Example of `conf/local/credentials.yml`:

```yaml
dev_s3:
  client_kwargs:
    aws_access_key_id: key
    aws_secret_access_key: secret
```


For security reasons, we strongly recommend not committing any credentials or other secrets to the Version Control System. By default any file inside the `conf` folder (and subfolders) in your Kedro project containing `credentials` in its name will be ignored and not committed to your repository.

> Note: If you maintain a project, you should document how to configure any required credentials in your project's documentation.

The Kedro documentation lists some [best practices to avoid leaking confidential data](https://kedro.readthedocs.io/en/stable/02_get_started/05_example_project.html#what-best-practice-should-i-follow-to-avoid-leaking-confidential-data).


Example of the dataset using those credentials defined in `conf/base/catalog.yml`:

```yaml
cars:
  type: pandas.CSVDataSet
  filepath: s3://my_bucket/data/02_intermediate/company/cars.csv
  credentials: dev_s3
```

_[Go to the next page](./04_dependencies.md)_
