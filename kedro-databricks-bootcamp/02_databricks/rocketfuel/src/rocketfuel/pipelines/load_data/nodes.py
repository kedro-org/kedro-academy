"""
This is a boilerplate pipeline 'load_data'
generated using Kedro 0.19.10
"""

import pandas as pd
from pyspark.sql import DataFrame
from pyspark.sql import SparkSession

from kedro_datasets._utils.spark_utils import get_spark


### Your code goes here
# def my_method(): ....


# To be used for the shuttles dataset
def spark_from_pandas(df: pd.DataFrame) -> DataFrame:
    """Convert a Pandas DataFrame to a Spark DataFrame."""
    _spark_session = get_spark()
    return _spark_session.createDataFrame(df)
