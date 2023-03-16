# Software Engineering for Data Scientists

Exercises for the Software Engineering for Data Scientists course.

## Cheatsheet

### Create a new virtual environment

```bash
conda env create -n {env_name} python={python_version} --channel conda-forge
```

For example: `conda env create -n kedro310 python=3.10 --channel conda-forge`.

Notes:

- This also works with `mamba` and `micromamba`.
- Specifying the Python version with `python={python_version}` is optional, but highly recommended.
- Using the conda-forge community channel with `--channel conda-forge` is the preferred option when a commercial agreement with Anaconda Inc. is not available.

### Activating a conda environment

```bash
conda activate {env_name}
```

For example: `conda activate kedro310`

You should see a change in prompt to `(kedro310)`.

### Installing packages inside an active environment

Using pip:

```bash
pip install {package_name}
```

For example: `pip install kedro`

**Always** remember to activate the environment first.

### Running the tests

```bash
pytest
```

Remember to install the `pytest` package first.
