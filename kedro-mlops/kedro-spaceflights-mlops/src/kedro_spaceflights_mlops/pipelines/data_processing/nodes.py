import polars as pl


def preprocess_companies(companies: pl.DataFrame) -> pl.DataFrame:
    """Preprocesses the data for companies.

    Args:
        companies: Raw data.
    Returns:
        Preprocessed data, with `company_rating` converted to a float and
        `iata_approved` converted to boolean.
    """
    return companies.with_columns(
        [
            (pl.col("iata_approved") == "t").alias("iata_approved"),
            (
                pl.col("company_rating").str.replace("%", "").cast(pl.Float64) / 100
            ).alias("company_rating"),
        ]
    )


def preprocess_shuttles(shuttles: pl.DataFrame) -> pl.DataFrame:
    """Preprocesses the data for shuttles.

    Args:
        shuttles: Raw data.
    Returns:
        Preprocessed data, with `price` converted to a float and `d_check_complete`,
        `moon_clearance_complete` converted to boolean.
    """
    return shuttles.with_columns(
        [
            (pl.col("d_check_complete") == "t").alias("d_check_complete"),
            (pl.col("moon_clearance_complete") == "t").alias("moon_clearance_complete"),
            (
                pl.col("price")
                .str.replace_all("$", "", literal=True)
                .str.replace_all(",", "", literal=True)
                .cast(pl.Float64)
            ).alias("price"),
        ]
    )


def create_model_input_table(
    shuttles: pl.DataFrame, companies: pl.DataFrame, reviews: pl.DataFrame
) -> pl.DataFrame:
    """Combines all data to create a model input table.

    Args:
        shuttles: Preprocessed data for shuttles.
        companies: Preprocessed data for companies.
        reviews: Raw data for reviews.
    Returns:
        Model input table.

    """
    # Data coming from the database has Decimal types,
    # so we need to cast them to Int64 for proper joining with Polars
    rated_shuttles = (
        shuttles.with_columns(pl.col("id", "company_id").cast(pl.Int64))
        .join(
            reviews.with_columns(pl.col("shuttle_id").cast(pl.Int64)),
            left_on="id",
            right_on="shuttle_id",
        )
        .drop("id")
    )
    model_input_table = rated_shuttles.join(
        companies.with_columns(pl.col("id").cast(pl.Int64)),
        left_on="company_id",
        right_on="id",
    )
    return model_input_table.drop_nulls()
