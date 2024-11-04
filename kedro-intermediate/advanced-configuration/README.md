# Advanced configuration with `OmegaConfigLoader`

The goal is to use `OmegaConfigLoader` resolvers to be able to load a file using Polars.

1. Tweak the `companies` entry in the catalog so that it looks as follows:

```yaml
companies:
  type: polars.PolarsEagerDataset
  file_format: csv
  filepath: data/01_raw/companies.csv
  load_args:
    schema_overrides:
      id: ${pl:Utf8}
```

2. Add a function in `settings.py` that takes a string and uses the `getattr` built-in to retrieve objects from the `polars` package, as follows:

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

3. Add that function as a custom resolver in `settings.py` with the prefix `pl` by leveraging the `CONFIG_LOADER_ARGS` variable:

```python
CONFIG_LOADER_ARGS = {
    "custom_resolvers": {
        "pl": get_polars_object,
    }
}
```

4. Run `catalog.load("companies")` on an IPython session and verify that it works
