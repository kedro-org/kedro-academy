# Dependencies

Up to this point, we haven't discussed project dependencies, so now is a good time to introduce them. Specifying a project's dependencies in Kedro makes it easier for others to run your project; it avoids version conflicts by use of the same Python packages.

The generic project template bundles some typical dependencies, in `src/requirements.txt`. Here's a typical example, although you may find that the version numbers are slightly different depending on the version of Kedro that you are using:

```text
black==v19.10b0 # Used for formatting code with `kedro lint`
flake8>=3.7.9, <4.0 # Used for linting code with `kedro lint`
ipython==7.0 # Used for an IPython session with `kedro ipython`
isort>=4.3.21, <5.0 # Used for linting code with `kedro lint`
jupyter~=1.0 # Used to open a Kedro-session in Jupyter Notebook & Lab
jupyter_client>=5.1.0, <7.0 # Used to open a Kedro-session in Jupyter Notebook & Lab
jupyterlab==0.31.1 # Used to open a Kedro-session in Jupyter Lab
kedro==0.17.2
nbstripout==0.3.3 # Strips the output of a Jupyter Notebook and writes the outputless version to the original file
pytest-cov~=2.5 # Produces test coverage reports
pytest-mock>=1.7.1,<2.0 # Wrapper around the mock package for easier use with pytest
pytest~=6.1.2 # Testing framework for Python code
wheel==0.32.2 # The reference implementation of the Python wheel packaging standard
```

> Note: If your project has `conda` dependencies, you can create a `src/environment.yml` file and list them there.

### Add and remove project-specific dependencies

The dependencies above may be sufficient for some projects, but for the spaceflights project, you need to add a requirement for the `pandas` project because you are working with CSV and Excel files. You can add the necessary dependencies for these files types as follows:

```bash
pip install kedro[pandas.CSVDataSet,pandas.ExcelDataSet]
```

Alternatively, if you need to, you can edit `src/requirements.txt` directly to modify your list of dependencies by replacing the requirement `kedro==0.17.2` with the following (your version of Kedro may be different):

```text
kedro[pandas.CSVDataSet,pandas.ExcelDataSet]==0.17.2
```

Then run the following:

```bash
kedro build-reqs
```

[`kedro build-reqs`](https://kedro.readthedocs.io/en/stable/09_development/03_commands_reference.html#build-the-project-s-dependency-tree) takes the `requirements.in` file (or `requirements.txt` if it does not yet exist), resolves all package versions and 'freezes' them by putting pinned versions back into `requirements.txt`. This significantly reduces the chances of dependencies issues due to downstream changes as you would always install the same package versions.


You can find out more about [how to work with project dependencies](https://kedro.readthedocs.io/en/stable/04_kedro_project_setup/01_dependencies.html) in the Kedro project documentation. 

## Install the project-specific dependencies

To install the project-specific dependencies, navigate to the root directory of the project and run:

```bash
pip install -r src/requirements.txt
```

_[Go to the next page](./05_connect_data_sources.md)_
