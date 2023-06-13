# Transcoding

You may come across a situation where you would like to read the same file using two different dataset implementations. Use transcoding when you want to load and save the same file, via its specified `filepath`, using different `DataSet` implementations.

## A typical example of transcoding

For instance, parquet files can not only be loaded via the `ParquetDataSet` using `pandas`, but also directly by `SparkDataSet`. This conversion is typical when coordinating a `Spark` to `pandas` workflow.

To enable transcoding, define two `DataCatalog` entries for the same dataset in a common format (Parquet, JSON, CSV, etc.) in your `conf/base/catalog.yml`:

```yaml
my_dataframe@spark:
  type: spark.SparkDataSet
  filepath: data/02_intermediate/data.parquet
  file_format: parquet

my_dataframe@pandas:
  type: pandas.ParquetDataSet
  filepath: data/02_intermediate/data.parquet
```

These entries are used in the pipeline like this:

```python
Pipeline(
    [
        node(func=my_func1, inputs="spark_input", outputs="my_dataframe@spark"),
        node(func=my_func2, inputs="my_dataframe@pandas", outputs="pipeline_output"),
    ]
)
```

## How does transcoding work?

In this example, Kedro understands that `my_dataframe` is the same dataset in its `spark.SparkDataSet` and `pandas.ParquetDataSet` formats and helps resolve the node execution order.

In the pipeline, Kedro uses the `spark.SparkDataSet` implementation for saving and `pandas.ParquetDataSet`
for loading, so the first node should output a `pyspark.sql.DataFrame`, while the second node would receive a `pandas.Dataframe`.


_[Go to the next page](./13_custom_datasets.md)_
