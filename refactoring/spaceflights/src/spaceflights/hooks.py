# Copyright 2021 QuantumBlack Visual Analytics Limited
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
# OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, AND
# NONINFRINGEMENT. IN NO EVENT WILL THE LICENSOR OR OTHER CONTRIBUTORS
# BE LIABLE FOR ANY CLAIM, DAMAGES, OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF, OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#
# The QuantumBlack Visual Analytics Limited ("QuantumBlack") name and logo
# (either separately or in combination, "QuantumBlack Trademarks") are
# trademarks of QuantumBlack. The License does not grant you any right or
# license to the QuantumBlack Trademarks. You may not use the QuantumBlack
# Trademarks or any confusingly similar mark as a trademark for your product,
# or use the QuantumBlack Trademarks in any other manner that might cause
# confusion in the marketplace, including but not limited to in advertising,
# on websites, or on software.
#
# See the License for the specific language governing permissions and
# limitations under the License.

"""Project hooks."""
from typing import Any, Dict, Iterable, Optional

from kedro.config import ConfigLoader
from kedro.framework.hooks import hook_impl
from kedro.io import DataCatalog
from kedro.versioning import Journal


class ProjectHooks:
    @hook_impl
    def register_config_loader(
        self, conf_paths: Iterable[str], env: str, extra_params: Dict[str, Any]
    ) -> ConfigLoader:
        return ConfigLoader(conf_paths)

    @hook_impl
    def register_catalog(
        self,
        catalog: Optional[Dict[str, Dict[str, Any]]],
        credentials: Dict[str, Dict[str, Any]],
        load_versions: Dict[str, str],
        save_version: str,
        journal: Journal,
    ) -> DataCatalog:
        return DataCatalog.from_config(
            catalog, credentials, load_versions, save_version, journal
        )


from kedro.framework.hooks import hook_impl
from kedro.pipeline.node import Node
from typing import Callable, Tuple, Any
import inspect
import logging
import pandas as pd

log = logging.getLogger(__name__)


class InspectHooks:
    @hook_impl
    def before_node_run(self, node: Node) -> None:
        node_name, location, number_lines = None, None, None
        # TODO: Find the real value of each of the above variables.
        #  Use _inspect_func to find location and number_lines.
        #  Do not print the information if the node is tagged with "no_inspect".
        log.info(f"`{node_name}` defined at {location} and is {number_lines} lines long")

    @hook_impl
    def after_dataset_loaded(self, dataset_name: str, data: Any) -> None:
        # TODO: Log the shape of the dataset if it is a pandas DataFrame.
        pass

def _inspect_func(func: Callable) -> Tuple[str, int]:
    """Gives the location (file and line number) and number of lines in `func`."""
    file = inspect.getsourcefile(func)
    lines, first_line = inspect.getsourcelines(func)
    location = f"{file}:{first_line}"
    return location, len(lines)


import time

class TimeDatasetLoadingHooks:
    def __init__(self):
        self._start_times = {}

    @hook_impl
    def before_dataset_loaded(self, dataset_name: str) -> None:
        self._start_times[dataset_name] = time.time()

    @hook_impl
    def after_dataset_loaded(self, dataset_name: str) -> None:
        elapsed_time = time.time() - self._start_times[dataset_name]
        log.info(f"Loading `{dataset_name}` took {elapsed_time:.3} seconds")