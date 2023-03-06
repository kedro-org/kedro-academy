# Use configuration

You were given some code that reads a bunch of files and applies some basic preprocessing.

**Move hardcoded paths and magic numbers to a configuration file.**

## Steps

1. Observe that some absolute paths have been included in the script. Probably they worked on the author's computer, but not anymore. Move the data files to a `data/` directory, and make the paths relative.
2. Let's move the paths from the script from a `catalog.yaml` file. Load the YAML file to a variable named `catalog`, and structure the YAML file so that the path of each file can be accessed with `catalog["companies"]["filepath"]` (also `"reviews"` and `"shuttles"`). Modify the `pd.read_csv` and `pd.read_excel` lines accordingly.
3. Notice that each dataset has an `index_col`. Include them in the `catalog.yaml` file and adjust the script accordingly.
4. Finally, observe that there's a magic number that adjusts the shuttle prices (could be a currency conversion factor or anything else). Move that constant to a `metadata` key inside the corresponding dataset, and adjust the code accordingly.
5. (Extra) What if at some point we decide to use Parquet files instead of CSV ones (highly recommended)? We would like to parametrize the dataset type in the configuration file too, but right now the script has `pd.read_csv` calls hardcoded. Include a `type: pandas.CSVDataSet` or `type: pandas.ExcelDataSet` in `catalog.yaml`, and modify the code so that it uses this `type` to decide what function call to use. _By the way, this is what Kedro does for you transparently!_
