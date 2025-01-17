import pandas as pd

def _parse_money(x: pd.Series) -> pd.Series:
    x = x.str.replace("$", "").str.replace(",", "")
    x = x.astype(float)
    return x


def preprocess_shuttles(shuttles: pd.DataFrame) -> pd.DataFrame:
    shuttles["d_check_complete"] = _is_true(shuttles["d_check_complete"])
    shuttles["moon_clearance_complete"] = _is_true(shuttles["moon_clearance_complete"])
    shuttles["price"] = _parse_money(shuttles["price"])
    return shuttles


preprocess_shuttles_node = node(
    func=preprocess_shuttles,
    inputs="shuttles",
    outputs="preprocessed_shuttles"
)
