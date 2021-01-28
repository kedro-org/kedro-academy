# Create a new project

Create a new project in your current working directory:

```bash
kedro new
```

This will ask you to specify:
1. Project name - you can call it `Kedro Training`
2. Repository name - accept the default by pressing the `Enter` key
3. Python package name - accept the default by pressing the `Enter` key

Change your working directory so that you are in your newly created project folder with:

```bash
cd kedro-training
```

## Project structure

The [project structure](https://kedro.readthedocs.io/en/stable/02_get_started/05_example_project.html#project-directory-structure) is explained in the Kedro documentation. 

## Running Kedro commands

The list and the behaviour of Kedro CLI commands may vary depending of the working directory where Kedro command is executed. Kedro has 2 command types:

* global commands (e.g., `kedro new`, `kedro info`) which work regardless of the current working directory
* local or project-specific commands (e.g., `kedro run`, `kedro install`) that require the current working directory to be the root of your Kedro project

To see the full list of available commands, you can always run `kedro --help`.

### `kedro install`

This command allows you to easily install or update all your project third-party Python package dependencies. This is roughly equivalent to `pip install -r src/requirements.txt`, however `kedro install` is a bit smarter on Windows when it needs to upgrade its version. It also makes sure that the dependencies are always installed in the same virtual environment as Kedro.

One more very useful command is `kedro build-reqs`, which takes `requirements.in` file (or `requirements.txt` if the first one does not exist), resolves all package versions and 'freezes' them by putting pinned versions back into `requirements.txt`. It significantly reduces the chances of dependencies issues due to downstream changes as you would always install the same package versions.

#### Example

Let's install and try the [Kedro Viz](https://github.com/quantumblacklabs/kedro-viz) - the plugin that helps a lot visualising your Kedro pipelines. You can do this by running the following commands from the terminal:

```bash
echo "kedro-viz>=3.0" >> src/requirements.txt  # src\requirements.txt on Windows
kedro build-reqs  # creates src/requirements.in and pins package versions in src/requirements.txt
kedro install  # installs packages from src/requirements.txt
kedro viz  # start Kedro Viz server
```

## Credentials management

For security reasons, we strongly recommend not committing any credentials or other secrets to the Version Control System. By default any file inside the `conf` folder (and subfolders) in your Kedro project containing `credentials` word in its name will be gitignored and not committed to your repository.

Please bear it in mind when you start working with Kedro project that you have cloned from GitHub, for example, as you might need to configure required credentials first. If you are a project maintainer, you should document it in project prerequisites.

On run Kedro automatically reads the credentials from the `conf` folder and feeds them into the DataCatalog - a Kedro component responsible for loading and saving of the data that comes to and out of pipeline nodes. Shortly, you just need to configure your credentials once and then you can reuse them in multiple datasets.

Example of `conf/local/credentials.yml`:

```yaml
dev_s3:
  client_kwargs:
    aws_access_key_id: key
    aws_secret_access_key: secret
```

Example of the dataset using those credentials defined in `conf/base/catalog.yml`:

```yaml
cars:
  type: pandas.CSVDataSet
  filepath: s3://my_bucket/data/02_intermediate/company/cars.csv
  credentials: dev_s3
```

### Next section
[Go to the next section](./05_connecting-data-sources.md)
