# Custom datasets

Kedro supports a number of datasets out of the box, but you can also add support for any proprietary data format or filesystem in your pipeline.

You can find further information about [how to add support for custom datasets](https://kedro.readthedocs.io/en/stable/07_extend_kedro/03_custom_datasets.html) in specific documentation covering advanced usage.

## Contributing a custom dataset implementation

One of the easiest ways to contribute back to Kedro is to share a custom dataset. Kedro has a `kedro.extras.datasets` sub-package where you can add a new custom dataset implementation to share it with others. You can find out more in the [Kedro contribution guide](https://github.com/kedro-org/kedro/blob/main/CONTRIBUTING.md) on Github.

To contribute your custom dataset:

1. Add your dataset package to `kedro/extras/datasets/`.

For example, in our `ImageDataSet` example, the directory structure should be:

```
kedro/extras/datasets/image
├── __init__.py
└── image_dataset.py
```

2. If the dataset is complex, create a `README.md` file to explain how it works and document its API.

3. The dataset should be accompanied by full test coverage in `tests/extras/datasets`.

4. Make a pull request against the `main` branch of [Kedro's Github repository](https://github.com/kedro-org/kedro).


_[Go to the next page](./14_custom_cli_commands.md)_

