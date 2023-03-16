# Software Engineering for Data Scientists

Exercises for the Software Engineering for Data Scientists course.

## Cheatsheet

### How to create a new virtual environment

```bash
conda env create -n {env_name} python={python_version} --channel conda-forge
```

For example: `conda env create -n kedro310 python=3.10 --channel conda-forge`.

**Notes**:

- This also works with `mamba` and `micromamba`.
- Specifying the Python version with `python={python_version}` is optional, but highly recommended.
- Using the conda-forge community channel with `--channel conda-forge` is the preferred option when a commercial agreement with Anaconda Inc. is not available.

### How to activate a conda environment

```bash
conda activate {env_name}
```

For example: `conda activate kedro310`

You should see a change in prompt to `(kedro310)`.

### How to install packages inside an active environment

> **Always remember to activate your virtual environment first, as above**.

To use `pip`:

```bash
pip install {package_name}
```

For example: `pip install kedro`

### How to run tests

> **Always remember to install the `pytest` package first**.

```bash
pytest
```


