import polars as pl

from kedro.io import AbstractDataset


class SimplePolarsDatabaseDataset(AbstractDataset):
    """A simple dataset to read and write from a Snowflake database using Polars."""

    def __init__(self, *, uri: str, table_name: str, engine: str = "adbc", save_args=None):
        self.uri = uri
        self.table_name = table_name
        self.engine = engine

        self.save_args = save_args or {}

    def _load(self):
        return pl.read_database_uri(
            f"SELECT * FROM {self.table_name}",
            self.uri,
            engine=self.engine,
        )

    def _save(self, data: pl.DataFrame):
        data.write_database(
            self.table_name,
            self.uri,
            engine=self.engine,
            **self.save_args,
        )

    def _describe(self):
        return {
            "uri": self.uri,
            "table_name": self.table_name,
            "engine": self.engine,
        }
