# Introduction to Software Engineering principles for Data Scientists

Materials for the course.

## How to create a new virtual environment

```bash
conda create -n {env_name} python={python_version} --channel conda-forge
```

For example: `conda create -n kedro310 python=3.10 --channel conda-forge`.

**Notes**:

- This also works with `mamba` and `micromamba`.
- Specifying the Python version with `python={python_version}` is optional, but highly recommended.
- Using the conda-forge community channel with `--channel conda-forge` is the preferred option when a commercial agreement with Anaconda Inc. is not available.

## How to activate a conda environment

```bash
conda activate {env_name}
```

For example: `conda activate kedro310`

You should see a change in prompt to `(kedro310)`.

## Other useful conda commands
![image](https://user-images.githubusercontent.com/5180475/225661321-185a93b2-ab23-463b-90da-d53948b95c6b.png)


## How to install packages inside an active environment

> **Always remember to activate your virtual environment first, as above**.

To use `pip`:

```bash
pip install {package_name}
```

For example: `pip install kedro`

## Install from a requirements file
![image](https://user-images.githubusercontent.com/5180475/225661177-3cf580d1-37d7-466a-b3b7-9789c6382071.png)

## Other useful `pip` commands
![image](https://user-images.githubusercontent.com/5180475/225661004-4f2492a0-3697-4694-accc-41887bef1cfd.png)

### How to run tests

> **Always remember to install the `pytest` package first**.

```bash
pytest
```


