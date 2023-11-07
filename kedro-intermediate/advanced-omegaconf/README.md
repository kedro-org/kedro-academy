# Advanced configuration with `OmegaConfigLoader`

The goal is to use `OmegaConfigLoader` resolvers to be able to load a file using Polars.

1. Download the data from https://openrepair.org/open-data/downloads/ or use the direct URL https://openrepair.org/wp-content/uploads/2023/02/OpenRepairData_v0.3_aggregate_202210.zip
2. Load the `OpenRepairData_v0.3_aggregate_202210.csv` using Polars (`import polars as pl` and then using the function `pl.read_csv`). Notice the function crashes because of some dtype mismatch.
3. Add `dtypes={"group_identifier": pl.Utf8, "product_age": pl.Float64}` to `pl.read_csv` and verify that the file loads correctly.
4. Create a `catalog.yml` in this same directory containing a dataset definition with `type: polars.CSVDataset`, and load it with the following code:

```python
from omegaconf import OmegaConf
from kedro.io import DataCatalog

catalog = DataCatalog.from_config(OmegaConf.load("catalog.yml"))
catalog.load("openrepair_raw")
```

verify that the loading still fails.

5. Add a function in `settings.py` that takes a string and uses the `getattr` built-in to retrieve objects from the `polars` package, as follows:

```python
In [1]: def get_polars_object(value: str):
   ...:     ...  # complete this
   ...: 
In [2]: import polars as pl

In [3]: get_polars_object("Utf8")
Out[3]: Utf8

In [4]: get_polars_object("Utf8") is pl.Utf8
Out[4]: True
```

6. Add a custom resolver in `settings.py` with the prefix `pl` by leveraging the `CONFIG_LOADER_ARGS` variable:

```python
CONFIG_LOADER_ARGS = {
    "custom_resolvers": {
        "pl": get_polars_object,
    }
}
```

7. Adjust the syntax in `catalog.yml` to use said resolver as explained in https://docs.kedro.org/en/stable/configuration/advanced_configuration.html#how-to-use-resolvers-in-the-omegaconfigloader
8. Rerun the `catalog.load` code block until data loading completely works.
