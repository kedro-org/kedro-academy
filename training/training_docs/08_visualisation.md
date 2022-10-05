
## Visualise your pipeline

[Kedro Viz](https://github.com/kedro-org/kedro-viz) shows you how your Kedro data pipelines are structured. You can use it to:

 - See how your datasets and Python functions (nodes) are resolved in Kedro so that you can understand how your data pipeline is built
 - Get a clear picture when you have lots of datasets and nodes by using tags to visualise sub-pipelines
 - Search for nodes and datasets

Follow the [Kedro-Viz installation instructions](https://kedro.readthedocs.io/en/stable/03_tutorial/06_visualise_pipeline.html) to get set up.
### Using `kedro-viz`

From your terminal, run:

```
kedro viz
```

This command will run a server on http://127.0.0.1:4141 and will open up your visualisation on a browser.

> *Note:* If port `4141` is already occupied, you can run Kedro-Viz server on a different port by executing `kedro viz --port <alternative-port>`.

### Examples of `kedro-viz`

 - You can have a look at a retail ML use case [**here**](https://kedro-org.github.io/kedro-viz/)
 - And an example of this Spaceflights pipeline [**here**](https://medium.com/@QuantumBlack/demystifying-machine-learning-complexity-through-visualisation-11a9d73db3c5)

_[Go to the next page](./09_versioning.md)_
