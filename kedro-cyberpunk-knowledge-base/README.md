# Cyberpunk 2077 Knowledge Base with Kedro

[![Powered by Kedro](https://img.shields.io/badge/powered_by-kedro-ffc900?logo=kedro)](https://kedro.org)
[![Python](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org/)

A Kedro project that uses LangChain and OpenAI LLMs to answer questions about the videogame Cyberpunk 2077, by querying a transcript of the game and the content of the fan-maintained wiki.

## Table of Contents

- [Overview](#overview)
- [What is Kedro?](#what-is-kedro)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Project Structure](#project-structure)
- [Setup](#setup)
- [Data Sources](#data-sources)
- [Configuration](#configuration)
- [Usage](#usage)
- [How It Works](#how-it-works)
- [Troubleshooting](#troubleshooting)
- [Performance Notes](#performance-notes)
- [Limitations](#limitations)
- [Resources](#resources)

## Overview

This project demonstrates how to use Kedro to build a question-answering system that:

- Processes large text datasets (game transcripts and wiki content)
- Generates semantic embeddings for similarity search
- Retrieves relevant context for user queries
- Generates accurate responses using Large Language Models (LLMs)

The project can be used in two ways:
- **CLI Mode**: Interactive command-line chatbot
- **Discord Bot Mode**: Query the knowledge base from Discord

## What is Kedro?

**Kedro** is an open-source Python framework for creating reproducible, maintainable, and modular data science code. It helps you:

- **Organize your code** into pipelines (sequences of data processing steps)
- **Manage data** through a catalog system that tracks inputs and outputs
- **Separate configuration** from code (parameters, credentials, data paths)
- **Version control** your data science workflows

### Key Kedro Concepts Used in This Project

- **Pipelines**: Sequences of data processing steps (nodes) that transform data
- **Nodes**: Individual functions that process data (e.g., chunk text, generate embeddings)
- **Data Catalog**: Configuration file that defines where data comes from and where it goes
- **Parameters**: Configuration values stored separately from code
- **Datasets**: Kedro's way of loading and saving data (supports many formats)

## Prerequisites

Before you begin, ensure you have:

- **Python 3.9 or higher** installed
- **An OpenAI API key** (get one at [platform.openai.com](https://platform.openai.com))
- **A Discord bot token** (optional, only if using Discord integration)

## Quick Start

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure credentials:**
   Create `conf/local/credentials.yml`:
   ```yaml
   openai:
     api_key: "your-api-key-here"
   ```

3. **Add data files:**
   Place your data files in `data/raw/` (see [Data Sources](#data-sources))

4. **Process the data:**
   ```bash
   kedro run --pipeline=process_transcript
   ```

5. **Run the CLI bot:**
   ```bash
   kedro run --pipeline=query_pipeline --tags=cli
   ```

   Or run the Discord bot:
   ```bash
   export DISCORD_TOKEN=your-token
   python bot.py
   ```

## Project Structure

```
2077-langchain-test/
├── conf/                            # Configuration files
│   ├── base/                        # Base configuration (shared across environments)
│   │   ├── catalog.yml              # Data catalog: defines datasets (inputs/outputs)
│   │   └── parameters.yml           # Parameters: configurable values
│   └── local/                       # Local configuration (not version controlled)
│       └── credentials.yml          # API keys and secrets
│
├── data/                            # Data directory (gitignored by default)
│   ├── raw/                         # Raw input data (transcript, wiki)
│   ├── processed/                   # Processed data (embeddings, chunks)
│   └── prompts/                     # Prompt templates
│
├── src/                             # Source code
│   └── kedro_2077/                  # Main package
│       ├── pipelines/               # Kedro pipelines
│       │   ├── process_transcript/  # Data processing pipeline
│       │   └── query_pipeline/      # Query/LLM pipeline
│       └── utils/                   # Utility functions
│
├── bot.py                           # Discord bot entry point
├── requirements.txt                 # Python dependencies
└── pyproject.toml                   # Project metadata
```

### Understanding the Structure

- **`conf/`**: All configuration lives here. Kedro separates configuration from code, making it easy to change settings without modifying code.
- **`data/`**: Follows Kedro's convention for data organization (raw → processed). This helps track data lineage.
- **`src/kedro_2077/pipelines/`**: Each pipeline is a separate module containing:
  - `nodes.py`: Functions that process data
  - `pipeline.py`: Defines how nodes connect together
- **`catalog.yml`**: Maps dataset names to file paths and formats. This is how Kedro knows where to load/save data.

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Credentials

Create `conf/local/credentials.yml` (this file is gitignored for security):

```yaml
openai:
  api_key: "sk-your-api-key-here"
```

**Note**: The `local/` directory is for environment-specific configuration that shouldn't be version controlled.

### 3. Configure Parameters

Key parameters are defined in `conf/base/parameters.yml`. You can adjust:

- `chunk_size`: Number of sentences per transcript chunk (default: 1000)
- `overlap`: Overlap between chunks to preserve context (default: 200)
- `max_chunks`: Maximum number of context chunks to retrieve (default: 2)
- `max_context_length`: Maximum characters per context block (default: 2000)
- `embedding_model_name`: SentenceTransformer model (default: "all-MiniLM-L6-v2")
- `llm_model_name`: OpenAI model to use (default: "gpt-4o-mini")
- `llm_temperature`: Sampling temperature for LLM (default: 0.2)
- `character_bonus`: Similarity boost when character names match (default: 0.05)
- `wiki_weight`: Relative weight of wiki vs transcript similarity (default: 0.7)

## Data Sources

### 1. Cyberpunk 2077 Transcript

- **File**: `data/raw/Cyberpunk2077Transcript.txt`
- **Description**: A text file containing the full game transcript with all dialogue
- **Format**: Plain text, with character names followed by colons (e.g., "Johnny Silverhand: Hello there")
- **Source**: [Game Scripts Wiki Blog](https://game-scripts-wiki.blogspot.com/2020/12/cyberpunk-2077-full-transcript.html)

### 2. Cyberpunk Wiki

- **File**: `data/raw/wiki_clean_text.json`
- **Description**: JSON file containing wiki page content
- **Format**: `{"page_title": "page_content", ...}`
- **Source**: [Cyberpunk Wiki](https://cyberpunk.fandom.com/wiki/Cyberpunk_Wiki)


## Usage

### Processing Data

Before querying, you need to process the raw data:

```bash
kedro run --pipeline=process_transcript
```

This pipeline:
1. Chunks the transcript into overlapping segments
2. Extracts character names
3. Generates embeddings for wiki pages
4. Stores everything in the data catalog

### CLI Chatbot

Run an interactive command-line chatbot:

```bash
kedro run --pipeline=query_pipeline --tags=cli
```

The `--tags=cli` flag tells Kedro to only run nodes tagged with "cli" (the interactive loop node).

**Example interaction:**
```
I am a machine that answers questions about Cyberpunk 2077!
Type your question about the game world or characters.
Type 'exit' to quit.

🟢 You: Who is Johnny Silverhand?
⚪ LLM: [Response about Johnny Silverhand...]
```

### Discord Bot

#### Setting Up Discord Bot

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application" and name it
3. Go to "Bot" tab:
   - Enable "Message Content Intent" (required for reading messages)
   - Click "Reset Token" and save the token
4. Go to "OAuth2" → "URL Generator":
   - Select "bot" scope
   - Select permissions: View Channels, Read Message History, Send Messages
   - Copy the invite URL
5. Invite the bot to your server using the URL

#### Running the Bot

```bash
export DISCORD_TOKEN=your-bot-token
python bot.py
```

#### Bot Commands

- `/help`: Display all available commands
- `/build`: Rebuild embeddings and transcript partitions
- `/query <question>`: Ask a question about Cyberpunk 2077

## How It Works

1. **Data Processing**: Transform raw text into searchable embeddings
2. **Query Processing**: Find relevant context using semantic similarity
3. **Response Generation**: Use LLM to generate answers based on retrieved context

### Pipeline Flow

#### 1. Data Processing Pipeline (`process_transcript`)

```
Raw Transcript → Chunk Transcript → Partition Chunks
                                      ↓
Raw Wiki → Embed Wiki Pages → Store Embeddings
                                      ↓
Raw Transcript → Extract Characters → Character List
```

**Kedro Concepts Demonstrated:**
- **Nodes**: Each arrow represents a node (function) that processes data
- **Data Catalog**: Inputs/outputs are defined in `catalog.yml`
- **PartitionedDataset**: Transcript chunks are stored as separate partitions for efficient retrieval

#### 2. Query Pipeline (`query_pipeline`)

```
User Query → Find Relevant Contexts → Format Prompt → Query LLM → Response
```

**Kedro Concepts Demonstrated:**
- **Runtime Parameters**: User query is passed as a runtime parameter
- **Tags**: Nodes are tagged (`cli` or `discord`) to run different paths
- **Data Catalog**: Loads processed data (embeddings, chunks) from previous pipeline

### Retrieval Strategy

The system uses **semantic similarity search**:

1. **Embedding Generation**: Both queries and content are converted to embeddings using Sentence-Transformers
2. **Similarity Calculation**: Cosine similarity finds the most relevant chunks
3. **Character Boosting**: Queries mentioning character names get a relevance boost for transcript chunks
4. **Source Weighting**: Wiki and transcript sources are weighted differently (wiki_weight: 0.7)
5. **Top-K Retrieval**: Returns the top N most relevant contexts

### Prompt Engineering

The prompt template is stored as JSON (`data/prompts/query_prompt.json`) and loaded using a `LangChainPromptDataset`, one of the [experimental datasets available through the `kedro-datasets` plugin](https://github.com/kedro-org/kedro-plugins/blob/main/kedro-datasets/kedro_datasets_experimental/langchain/langchain_prompt_dataset.py) at the time this is being written. This allows:

- Easy experimentation with different prompt structures
- Separation of prompt design from code


## Troubleshooting

### "OpenAI API key not found"

- Ensure `conf/local/credentials.yml` exists
- Check the file uses correct YAML syntax (indentation matters!)
- Verify the API key is valid

### "DISCORD_TOKEN not set"

- Export the token: `export DISCORD_TOKEN=your-token`
- Or set it in your shell configuration file (`.bashrc`, `.zshrc`, etc.)
- On Windows, use `set DISCORD_TOKEN=your-token` (cmd) or `$env:DISCORD_TOKEN="your-token"` (PowerShell)

### "No data loaded" errors

- Ensure data files are in `data/raw/` directory
- Check file names match those in `catalog.yml`
- Run `kedro run --pipeline=process_transcript` first to process the data

### Bot not responding in Discord

- Verify "Message Content Intent" is enabled in Discord Developer Portal
- Check the bot has proper permissions in your server
- Look at bot console output for error messages
- Ensure the bot is online (green status indicator)

### Pipeline execution errors

- Check that all required datasets exist in the catalog
- Verify parameters are defined in `parameters.yml`
- Ensure dependencies are installed: `pip install -r requirements.txt`

### Import errors

- Make sure you're in the project root directory
- Verify the package is installed: `pip install -e .`
- Check Python version: `python --version` (needs 3.9+)

## Performance Notes

- **Initial embedding generation**: Can take several minutes depending on the user's hardware
- **Query responses**: Typically 5-15 seconds (depends on context retrieval and LLM response time)
- **Model loading**: Embedding model loads once per pipeline execution
- **Memory usage**: Embeddings are stored in memory
- **Discord bot**: Processes queries asynchronously, allowing multiple users simultaneously

## Limitations

- **In-memory search**: Uses simple similarity search; for production with large datasets, a vector database (e.g., Pinecone, Weaviate) would be preferable
- **Pickle storage**: Wiki embeddings stored as pickle files; may not scale well for very large datasets
- **Conversation history**: CLI mode maintains history only within a single session
- **No persistence**: Discord bot doesn't maintain conversation history between queries
- **Token limits**: Context is truncated to fit within LLM token limits

## Resources

- [Kedro Documentation](https://docs.kedro.org/) - Comprehensive guide to Kedro
- [LangChain Documentation](https://python.langchain.com/) - LLM framework
- [Discord.py Documentation](https://discordpy.readthedocs.io/) - Discord bot library
- [Sentence Transformers](https://www.sbert.net/) - Semantic embeddings
- [OpenAI API](https://platform.openai.com/docs) - LLM provider

- [Cyberpunk Wiki](https://cyberpunk.fandom.com/wiki/Cyberpunk_Wiki) - Game information source
- [Full Cyberpunk 2077 Transcript](https://game-scripts-wiki.blogspot.com/2020/12/cyberpunk-2077-full-transcript.html) - Game Scripts Wiki Blog

---

- Inspired by 466 gameplay hours and every single achievement in [Cyberpunk 2077](https://www.cyberpunk.net)

---

**Note**: This project is designed as a learning resource for understanding Kedro. Feel free to experiment, modify, and learn!
