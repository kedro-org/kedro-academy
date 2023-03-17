# Environment and dependencies

Your client is trying to run very old code delivered by a former colleague, but they're unable to get it working.

**Install the necessary dependencies for the script to work, without changing the code**.

## Steps

1. Create a new conda/mamba environment called `dependencies37` with Python 3.7.
2. Activate it and proceed with the following steps.

### First attempt at installing the dependencies

1. Try running the script, and for every `ModuleNotFoundError` you find, install the corresponding dependency using `pip`. Notice how the process is relatively fast.
2. At some point, you might spot a big error mentioning the `SKLEARN_ALLOW_DEPRECATED_SKLEARN_PACKAGE_INSTALL` variable. This is because the import name is **not** always equal to the package name! Refer to the top-left corner of [the PyPI page](https://pypi.org/project/scikit-learn/) for the precise command that you must run. (If you installed scikit-learn correctly, you won't see this error)
3. Now all the dependencies should be in place, but there's an error with the line `from sklearn.gaussian_process import GaussianProcess`. The reason is that the model name changed after this code was written. We could change the line to `from sklearn.gaussian_process import GaussianProcessRegressor`, but more code changes would be needed because of changes introduced in newer scikit-learn versions, and it's not allowed. Take a deep breath.
4. Remember that this code is old: therefore, an older version of scikit-learn will do the trick! Install `scikit-learn` 0.19 and rerun the script.
5. If your build fails, it's because you're trying to install scikit-learn 0.19.0, which doesn't have pre-compiled binary wheels for Python 3.7. Maybe there's a micro release in the 0.19.* series that addressed this issue? Keep trying until you find it.

Finally! That was a bit frustrating but at least an `errorbars.png` appears in the filesystem, and the script finishes (although with lots of deprecation warnings).

### Declare the dependencies

Create a `requirements.txt` file on the same level as this `README.md` file with the dependencies you have to install. To verify that it works:

1. Deactivate the environment running `conda deactivate`
2. Delete the old environment with `conda remove -n dependencies37 --all`
3. Create the environment again and activate it
4. Create a `requirements.txt` file with the dependencies you installed with `pip` previously
5. Install those dependencies with `pip install -r requirements.txt`
6. Verify that the script works, and if it doesn't, keep adding dependencies to `requirements.txt` and repeat the steps 5
