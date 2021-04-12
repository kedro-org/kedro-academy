
# Versioning

## Data versioning
Making a simple addition to your Data Catalog allows you to perform versioning of datasets and machine learning models.

Suppose you want to version `master_table`. To enable versioning, simply add a `versioned` entry in `catalog.yml` as follows:

```yaml
master_table:
  type: pandas.CSVDataSet
  filepath: data/03_primary/master_table.csv
  versioned: true
```

The `DataCatalog` will create a versioned `CSVDataSet` called `master_table`. The actual csv file location will be `data/03_primary/master_table.csv/<version>/master_table.csv`, where the first `/master_table.csv/` is a directory and `<version>` corresponds to a global save version string formatted as `YYYY-MM-DDThh.mm.ss.sssZ`.

In a similar way, you can version your machine learning model. Enable versioning for `regressor` as follow:

```yaml
regressor:
  type: pickle.PickleDataSet
  filepath: data/06_models/regressor.pickle
  versioned: true
```

This will save versioned pickle models every time you run the pipeline.

> *Note:* The list of the datasets supporting versioning can be find in [the documentation](https://kedro.readthedocs.io/en/stable/05_data/02_kedro_io.html#supported-datasets).

## Loading a versioned dataset
By default, the `DataCatalog` will load the latest version of the dataset. However, you can run the pipeline with a particular versioned dataset with `--load-version` flag as follows:

```bash
kedro run --load-version="master_table:YYYY-MM-DDThh.mm.ss.sssZ"
```
where `--load-version` contains a dataset name and a version timestamp separated by `:`.


_[Go to the next page](./10_package_project.md)_
