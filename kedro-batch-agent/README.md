# Batch Processing Agentic Workflow
[![Powered by Kedro](https://img.shields.io/badge/powered_by-kedro-ffc900?logo=kedro)](https://kedro.org)


## Overview

The goal of this project is to demonstrate how to build batch processing agentic workflows with Kedro and `LangGraph`.This project implements two agentic workflows related to the insurance domain. The goal is to extract information from unstructured text data and images for damage assessment.

### Agentic Workflows

This project showcases two agentic use-cases in the insurance domain:

#### 1. Document Analysis Agent

This agent processes unstructured text data (e.g., emails, chat records) related to insurance claims and extracts relevant information such as claim number, policy number, date of incident, type of damage, estimated cost of repair, and other pertinent details. The extracted information is then structured into a JSON format for further analysis and reporting. 

**Output**

The output of the document analysis agent is a JSON file saved in `data/results/response_completion_agent/<client_name>.json` with the following structure:
```json
{
  "policy_number": "012345",
  "user": {
    "name": "Alice",
    "user_id": "alice@gmail.com"
  },
  "cause": "flood",
  "date": "2022-02-20",
  "amount": 1200.0
}
```

#### 2. Image Analysis Agent

This agent processes images submitted along with insurance claims to assess the extent of damage and estimate repair costs. It analyses the images to identify visible damages, categorizes the type of damage (e.g., minor, moderate, severe), and provides an estimated cost for repairs. The analysis results are structured into a JSON format for easy interpretation and further processing. The agentic workflow is designed to read images one at a time and stop after either reaching the end of the list, or after processing a predefined number of images, or after a confidence threshold is met. The maximum number of images and the confidence threshold can be set in the `conf/base/parameters.yml` file.

**Output**

The output of the image analysis agent is a JSON file saved in `data/results/response_image_analysis_agent/<client_name>.json` with the following structure:
```json
{
  "image_1.png": {
    "severity": "moderate",
    "estimated_cost": 1500.0,
    "confidence": 0.85,
    "rationale": "The visible water damage and stains on walls indicate potential moisture issues that may require repair, treatment, and repainting."
  }
}
```


### Goals

1. Set an example for how to use Kedro's nodes and pipelines to encapsulate simple agentic workflows.
2. Use Kedro's data catalog to manage and version datasets used in the workflows.

### Data

The `data/` directory contains the necessary data files for the project, including:
- `prompts/`: Contains prompt text files `completion_agent_prompt.txt` and `image_analysis_agent_prompt.txt` used by the agents,
- `raw_data/`: Contains the raw input data for the agentic workflows.
    - `claims_docs/`: Contains unstructured text data organised in subfolders per client. These files currently are `.pdf` format. This can be emails, texts, chat records etc.
    - `claims_pics/`: Contains images submitted along with claims to be assessed by an agent to estimate costs of repair. [AI Generated]
- `results/`: Output folder for the project where extracted information and analysis results will be stored as `.json` files.

### Configuration

The `conf/` folder contains the catalog, parameters and credentials for the project.
- `base/`: Contains the base configuration files for the project.
    - `catalog.yml`: Defines the data catalog for the project.
    - `parameters.yml`: Contains the parameters used in the project.
- `local/`: Contains local configuration files for the project.
    - `credentials.yml`: Stores sensitive information such as API keys and passwords. [NOT COMMITTED TO THE REPO]

### Custom Datasets

The project includes a custom dataset `PDFDataset` defined in `kedro_batch_agent/datasets/pdf_dataset.py` to handle PDF files. This dataset is used to read unstructured text data from PDF files. The `PDFDataset` class extends Kedro's `AbstractDataSet`. It uses the [`pypdf` library](https://pypdf.readthedocs.io/en/stable/) to read and extract text from PDF files.

### Setup and run the project

1. Clone the repository:
   ```bash
   git clone https://github.com/kedro-org/kedro-academy.git
   cd kedro-batch-agent
   ```

2. Install the required packages:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up credentials
   In the `conf/local/` directory, create a file named `credentials.yml` and add your API keys and other sensitive information there.
   ```yaml
   openai:
     openai_api_key: your_openai_api_key
     openai_api_base: your_openai_api_base
   ```

4. Run the project:
   To the run the project for individual clients, use the following command:
   ```bash
   kedro run --params client_name=client_1
   ```

   To run the project for all clients:
   ```bash
   python run_multiple.py
   ```

### Considerations and future improvements

- We use `PartitionedDataset` to load text information from multiple files organized by client. The `PartitionedDataset` only supports one underlying data format at a time, which may limit its flexibility in handling diverse data sources. The idea is to extend the `PartitionedDataset` to support multiple data formats.
- For multiple users, the script `run_multiple.py` is provided to facilitate batch processing. The script iterates over all clients and then creates a new `KedroSession` and passes the `client_name` as a runtime parameter for each run. Running the pipeline for batch usecases can be done in multiple ways:
    - Dynamically create pipeline per client in `pipeline_registry.py` and run the project as a whole
    - External script (current implementation)
    - Using a `PartitionedDataset` that can handle subfolders for each client and let the agents handle the processing.
The current approach is the most straightforward and is selected to mitigate for partial failure of pipelines (eg. running out of OpenAI tokens) which would cause the whole workflow to fail. This allows for data to be saved for partially successful runs and facilitates manually running the pipeline for individual clients.
