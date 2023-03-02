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

"""Project pipelines."""
from typing import Dict

from kedro.pipeline import Pipeline, pipeline

# TODO 2: import the data_filtering pipeline.
from spaceflights.pipelines import data_processing as dp
from spaceflights.pipelines import data_science as ds


def register_pipelines() -> Dict[str, Pipeline]:
    """Register the project's pipelines.

    Returns:
        A mapping from a pipeline name to a ``Pipeline`` object.

    """
    data_processing_pipeline = dp.create_pipeline()
    data_science_pipeline = ds.create_pipeline()

    # TODO 1: give data_science_pipeline the namespace "unfiltered" and make sure it
    #  links up correctly to the model_input_table input.
    unfiltered_ds_pipeline = data_science_pipeline

    # TODO 2: create the data_filtering_pipeline using the create_pipeline method.
    # TODO 2: alter the appropriate parameters file to filter by engine_type == "Quantum".
    data_filtering_pipeline = Pipeline([])

    # TODO 3: give data_science_pipeline the namespace "filtered". Connect the
    #  data_filtering_pipeline onto the model_input_table as input and
    #  the data science pipeline as output using `inputs`, `outputs` and `namespace`.
    #  Add the pipeline to the __default__ and ds registered pipelines.
    filtered_ds_pipeline = pipeline(data_filtering_pipeline) + pipeline(
        data_science_pipeline
    )

    return {
        # TODO 4: update the pipeline registry to register two new pipelines
        #  "unfiltered_pipeline" and "filtered_pipeline" that run the data processing
        #  and appropriate data science pipelines.
        "__default__": (data_processing_pipeline + unfiltered_ds_pipeline),
        "dp": data_processing_pipeline,
        "ds": unfiltered_ds_pipeline,
    }


# EXTRA TODO 1: give data_processing_pipeline a namespace so that it can be
#  collapsed in kedro-viz. You will need to fix the inputs/outputs and/or edit the
#  names of the catalog entries to get a correctly connected pipeline.

# EXTRA TODO 2: run the data_filtering_pipeline twice in series to get model
#  performance after filtering by engine_type == "Quantum" AND then by
#  shuttle_type == "Type F5". You should do this just by altering this file and
#  parameters file without touching anything in pipelines/data_filtering.

# EXTRA TODO 3: run the data_filtering_pipeline onwards twice in parallel to get
#  model  performance after filtering by engine_type == "Quantum" OR by
#  shuttle_type == "Type F5". You should do this just by altering this file and
#  parameters file without touching anything in pipelines/data_filtering.
