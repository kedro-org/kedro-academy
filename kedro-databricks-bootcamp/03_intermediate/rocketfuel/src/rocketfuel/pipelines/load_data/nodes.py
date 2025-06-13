"""
This is a boilerplate pipeline 'load_data'
generated using Kedro 0.19.10
"""

import pandas as pd
from pyspark.sql import DataFrame
from pyspark.sql import SparkSession

from kedro_datasets._utils.spark_utils import get_spark


def _noop(df: DataFrame) -> DataFrame:
    """A no-operation node that simply returns the input Spark DataFrame."""
    return df


def spark_from_pandas(df: pd.DataFrame) -> DataFrame:
    """Convert a Pandas DataFrame to a Spark DataFrame."""
    _spark_session = get_spark()
    return _spark_session.createDataFrame(df)
