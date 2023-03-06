import pytest

from main import load_yaml


def test_shuttles_includes_adjust_factor():
    catalog = load_yaml("catalog.yaml")
    str_shuttles = str(catalog["shuttles"])
    assert "1.597463007" in str_shuttles


@pytest.mark.parametrize("dataset", ("companies", "reviews", "shuttles"))
def test_catalog_contains_required_keys(dataset):
    catalog = load_yaml("catalog.yaml")

    assert "filepath" in catalog[dataset]
    assert "index_col" in catalog[dataset]
