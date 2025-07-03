"""
This is a boilerplate pipeline 'load_data'
generated using Kedro 0.19.14
"""

import typing as t

type T = t.TypeVar("T")


def _noop(data: T) -> T:
    return data
