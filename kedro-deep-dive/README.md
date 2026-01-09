## Kedro deep dive project

This repository is a Kedro deep dive project designed to explain the Kedro ecosystem and its core components in action. It includes demos on:
 - The Kedro Framework: Overview and core concepts
 - Deploying and running Kedro on Databricks using asset bundles
 - Using Kedro as a library

The project uses a modular spaceflights example, which includes more pipelines and nodes than the standard Kedro spaceflights starter.
You can follow the instructions in the spaceflights [README](./spaceflights/README.md) to install and run this project in your own environment.

### Databricks Integration

In addition to the spaceflights example, this project demonstrates how to work with Databricks asset bundles using the [`kedro-databricks`](https://github.com/JenspederM/kedro-databricks) plugin.

The plugin generates multiple Databricks workflows under the [`/resources`](./spaceflights/resources) folder.

We've extended this and added additional workflows to show:
 - Run Databricks workflows in parallel using Kedro’s `ParallelRunner`.
 - Execute workflows both at a project level and at pipelines level.

This is meant to be a hands-on, simple example for those looking to understand and implement Kedro in a production-like setting.

## Other Useful links 
- [How to group nodes on Kedro?](https://docs.kedro.org/en/stable/deployment/nodes_grouping.html)
- [Modifying a run](https://docs.kedro.org/en/stable/development/commands_reference.html#modifying-a-kedro-run)
- Kedro GenAI related dataset
    - [HuggingFace](https://docs.kedro.org/projects/kedro-datasets/en/latest/api/kedro_datasets.huggingface.HFDataset.html)
    - [LangChain](https://docs.kedro.org/projects/kedro-datasets/en/latest/api/kedro_datasets_experimental.langchain.ChatOpenAIDataset.html)
  
