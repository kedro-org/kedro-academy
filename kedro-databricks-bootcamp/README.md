# Kedro on Databricks Bootcamp

## Overview

1. Day 1
   - First steps with Kedro
   - The Kedro Framework
2. Day 2
   - Kedro on Databricks
3. Day 3
   - Extending Kedro
   - Kedro in production

## Setup

### 1. Local setup
 
Clone the repository https://github.com/kedro-org/kedro-academy/tree/main/kedro-databricks-bootcamp to your machine.
 
Open the `kedro-databricks-bootcamp` as a VS Code folder.
 
If not present yet, install the official Python extension https://marketplace.visualstudio.com/items?itemName=ms-python.python
 
Create a new virtual environment with Python 3.11.10 to match the Databricks Serverless v2 environment (venv preferred, conda also supported) and configure it as the interpreter of the project in VS Code.

Install the dependencies inside the environment with `pip install -r requirements.txt` (you may need to activate it first).
 
Make sure that the first few cells of `01_1-First-Steps-With-Kedro.ipynb` execute normally.

Install the Kedro extension for VS Code https://marketplace.visualstudio.com/items?itemName=kedro.Kedro

### 2. Hybrid setup

Install the Databricks extension for VS Code https://marketplace.visualstudio.com/items?itemName=databricks.databricks

Follow the official instructions to configure Databricks Connect by authenticating with a Personal Access Token to the Databricks Cluster and choosing the Serverless compute cluster https://learn.microsoft.com/en-us/azure/databricks/dev-tools/vscode-ext/databricks-connect#install-databricks-connect
 
The end result should look more or less as follows

<img width="402" alt="image" src="https://github.com/user-attachments/assets/7bb99644-f543-40cd-af5b-9df7afe85ea7" />

### 3. Databricks setup

Create a new Git Folder with the repository URL, the configuration should look more or less as follows
 
![image](https://github.com/user-attachments/assets/c986faee-1402-47f1-9d59-9f2d2af444f1)
 
Inspect the 02_databricks/02_0-Unity-Catalog-checks.ipynb notebook to make sure there is a catalog you have write access to. You will need to tweak the catalog and schema names.
