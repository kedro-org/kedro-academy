# Environment and dependencies

Your client is trying to run a very old code delivered by a former colleague, but they're unable to do so.

**Install the necessary dependencies for the script to work, without changing the code**.

> **Note**:
> This assumes a Python 3.7 environment.

## Steps

### Create and activate a virtual environment

1. Try running the script. Verify that it doesn't work because of missing dependencies.
2. Try running `pip --help`, and observe that the Shell says `pip: command not found`. This is a good thing! It prevented you from using `pip` without a virtual environment. Never do such a thing.
3. Go ahead and create a virtual environment. Since conda is not available in this environment, use native virtual environments instead: run `python3 -m venv .venv` to create a virtual environment in the the `.venv` directory.
4. Notice that the environment was created, but not activated yet, hence running `pip` again would result in another error. Activate the environment running `source .venv/bin/activate`.

Finally! There's a `(.venv)` at the beginning of the prompt, which means that activation was successful. Now we can actually install the dependencies.

### First attempt at installing the dependencies

1. Try running the script, and for every `ModuleNotFoundError` you find, install the corresponding dependency. Notice how the process is relatively fast.
2. At some point, you might spot a big error mentioning the `SKLEARN_ALLOW_DEPRECATED_SKLEARN_PACKAGE_INSTALL` variable. This is because the import name is **not** always equal to the package name! Refer to the top-left corner of [the PyPI page](https://pypi.org/project/scikit-learn/) for the precise command that you must run.
3. Now all the dependencies should be in place, but there's an error with the line `from sklearn.gaussian_process import GaussianProcess`. The reason is that the model name changed after this code was written. We could change the line to `from sklearn.gaussian_process import GaussianProcessRegressor`, but more code changes would be needed because of changes introduced in newer scikit-learn versions, and it's not allowed. Take a deep breath.
4. Remember that this code is old: therefore, an older version of scikit-learn will do the trick! Install `scikit-learn` 0.19 and rerun the script.

Finally! That was a bit frustrating but at least an `errorbars.png` appears in the filesystem, and the script finishes (although with lots of deprecation warnings).

### Declare the dependencies

Create a `requirements.txt` file with the dependencies you have to install. To verify that it works:

1. Deactivate the environment running `deactivate`
2. Delete the old environment with `rm -rf .venv`
3. Create a new one with the command given above
4. Add the dependencies to `requirements.txt`
5. Install those dependencies with `pip install -r requirements.txt`
6. Repeat until the script works again
