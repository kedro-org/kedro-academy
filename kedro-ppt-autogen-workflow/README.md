# PPT AutoGen Workflow

Automated PowerPoint presentation generation from structured YAML instructions using AutoGen agents and data-driven utilities.

[![Powered by Kedro](https://img.shields.io/badge/powered_by-kedro-ffc900?logo=kedro)](https://kedro.org)

## Quick Start

### 1. Install Dependencies

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Credentials

Create `conf/local/credentials.yml`:

```yaml
openai:
  api_key: "${oc.env:OPENAI_API_KEY}"
  base_url: "${oc.env:OPENAI_API_BASE}"
```

### 3. Export your credentials in the terminal to make it available as env

```bash
export OPENAI_API_KEY="your-api-key"
export OPENAI_API_BASE="base-url"
```

### 4. Prepare Inputs

- **Instructions**: `data/01_raw/instructions.yaml` - Define slides with chart and summary instructions
- **Data**: `data/01_raw/sample_sales_50_products.csv` - Sales data for analysis

### 5. Run Pipeline

**Multi-Agent Pipeline** (recommended):
```bash
kedro run --pipeline=ma_slide_generation_autogen
```

**Single-Agent Pipeline**:
```bash
kedro run --pipeline=sa_slide_generation_autogen
```

**Default** (runs multi-agent):
```bash
kedro run
```

### 5. Check Outputs

- **Presentation**: `data/08_reporting/final_presentation.pptx`
- **Charts**: `data/02_intermediate/charts/slide_*.png`
- **Summaries**: `data/02_intermediate/summaries/slide_*.txt`

## Instructions Format

Edit `data/01_raw/instructions.yaml`:

```yaml
iterative_slide_generation:
  slide_1:
    objective:
      csv_path_input: "sample_sales_50_products.csv"
      chart_instruction: "Create a horizontal bar chart showing top 10 products by FY_Sales"
      summary_instruction: "Generate 3-5 bullet points summarizing top 10 products performance"
      slide_title: "Top 10 Products Performance"
  slide_2:
    objective:
      # ... next slide definition
```

## Pipeline Comparison

| Feature | Multi-Agent | Single-Agent |
|---------|------------|--------------|
| Agents | 4 specialized agents | 1 agent |
| QA Review | ✅ Critic agent | ❌ |
| LLM Logging | ✅ Detailed | ❌ |
| Conversation Flow | ✅ Context passing | ❌ |
| Intermediate Outputs | ✅ Charts & Summaries | ❌ |
| Use Case | Production, quality-focused | Simple, fast |

## Project Structure

```
├── conf/
│   ├── base/              # Base configuration
│   └── local/             # Local credentials (gitignored)
├── data/
│   ├── 01_raw/            # Input data
│   ├── 02_intermediate/   # Charts & summaries
│   └── 08_reporting/      # Final presentations
├── src/ppt_autogen_workflow/
│   ├── datasets/          # Autogen Model Client Datasets
│   ├── pipelines/         # Pipeline definitions
│   └── utils/             # Utility functions
└── requirements.txt
```

## Configuration

### Update User Query

Edit `conf/base/parameters.yml`:
```yaml
user_query: "Your presentation request here"
```

### Change LLM Model

Edit `conf/base/genai-config.yml`:
```yaml
llm_autogen:
  type: ppt_autogen_workflow.datasets.autogen_model_client.OpenAIChatCompletionClientDataset
  kwargs:
    model: "gpt-5-nano-2025-08-07" # your preferred model here
    temperature: 1
  credentials: openai
```

## Troubleshooting

**Error: "Environment variable 'OPENAI_API_KEY' not found"**
- Ensure `conf/local/credentials.yml` exists with your API key

**Error: "No 'iterative_slide_generation' found"**
- Check `instructions.yaml` format matches expected structure

**Empty presentations**
- Verify `sales_data` CSV is loaded correctly
- Check chart/summary generation logs for errors

## Documentation

- [Architecture](ARCHITECTURE.md) - Detailed pipeline architecture
- [Kedro Docs](https://docs.kedro.org) - Kedro framework documentation

## License

This project uses the Kedro framework. See [Kedro license](https://github.com/kedro-org/kedro/blob/main/LICENSE.md).
