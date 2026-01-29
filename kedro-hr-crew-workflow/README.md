# HR Recruiting Agentic Workflow

An intelligent HR recruiting system that combines deterministic data processing with AI agents for candidate screening and evaluation. Built with **Kedro** for production-ready data pipeline orchestration and **CrewAI** for multi-agent collaboration.

## Table of Contents

- [Overview](#overview)
- [Why Kedro + CrewAI?](#why-kedro--crewai)
- [Architecture](#architecture)
- [Quick Start](#quick-start)
- [Usage](#usage)
- [Project Structure](#project-structure)
- [Configuration](#configuration)
- [Data Models](#data-models)
- [Troubleshooting](#troubleshooting)
- [Future Enhancements](#future-enhancements-multi-resume-batch-processing)

## Overview

This project automates candidate screening through a hybrid workflow:

1. **Parse** job postings and resumes from Word documents (deterministic)
2. **Extract** structured candidate information using AI agents (agentic)
3. **Match** requirements to candidate evidence using AI reasoning (agentic)
4. **Evaluate** candidates and generate screening recommendations (agentic)
5. **Draft** communications and generate professional HR reports (deterministic)

### Pipeline Flow

```
Jobs Pipeline → Applications Pipeline → Screening Pipeline → Reporting Pipeline
(deterministic)    (agentic)              (agentic)           (deterministic)
```

**Key Insight**: This architecture demonstrates the power of combining rule-based processing (parsing, formatting) with AI agents (reasoning, evaluation) - using each approach where it excels.

## Why Kedro + CrewAI?

### The Challenge

Building production-ready AI agent systems requires more than just agent orchestration. You need:
- **Maintainable prompts** that non-developers can update
- **Configurable business rules** without code changes
- **Data pipeline orchestration** across multiple processing stages
- **Clear separation** between AI logic and infrastructure
- **Observability** into agent workflows and data flow

### The Solution: Kedro + CrewAI

**CrewAI** provides autonomous multi-agent collaboration and intelligent task execution.

**Kedro** provides the production infrastructure that makes agentic workflows enterprise-ready.

### What This Combination Delivers

#### 1. **Externalized Prompt Management**

**Problem**: Prompts hardcoded in code require deployments to update, making experimentation difficult.

**Solution**: Kedro's PromptDatasets store prompts as YAML files separate from code.

```yaml
# data/prompts/screening/resume_evaluator_agent_system_prompt.yml
role: Senior HR Analyst
goal: Evaluate candidate qualifications against job requirements
backstory: |
  You are an experienced HR professional who excels at assessing
  candidate fit based on evidence and job requirements...
```

**Benefits**:
- Prompt engineers and business users update prompts without touching code
- A/B test different prompt strategies by editing YAML files
- Track prompt changes through Git (commit prompts like any other file)
- Environment-specific prompts via Kedro's configuration layers (base/local)
- Pydantic schemas automatically injected into prompts for structured outputs

#### 2. **Unified AI Configuration**

**Problem**: LLM settings, prompts, and tools scattered across codebase.

**Solution**: Kedro's `llm_context_node` bundles everything into a context object.

```python
# Pipeline definition
llm_context_node(
    outputs="requirements_matcher_context",
    llm="llm_crew_ai",  # Centralized LLM config
    prompts=[
        "requirements_matcher_agent_system_prompt",
        "requirements_matching_user_prompt",
    ],
    tools=[
        tool(build_requirements_matcher_tool, "application", "job_requirements", ...)
    ],
)
```

**Benefits**:
- Swap LLM models by updating one config file
- Tools automatically receive data from Kedro catalog
- Clear separation: AI configuration vs business logic
- Type-safe context objects

#### 3. **Configuration-Driven Business Logic**

**Problem**: Business rules hardcoded mean every change requires code deployment.

**Solution**: Store templates, weights, and rules in YAML configuration files.

```yaml
# data/config/scoring_config.yml
weights:
  must_have_coverage: 0.7
  avg_confidence: 0.3
bounds:
  match_score: {min: 0.0, max: 100.0}
```

**Benefits**:
- Business users update email templates, scoring weights, matching rules
- Experiment with different configurations without code changes
- Compliance teams review and approve config changes separately
- Different configurations for dev, staging, production

#### 4. **Declarative Data Management**

**Problem**: I/O logic mixed with business logic makes code brittle.

**Solution**: Kedro's DataCatalog handles all data access declaratively.

```yaml
# conf/base/catalog.yml
screening_result:
  type: json.JSONDataset
  filepath: data/intermediate/screening/screening_result.json
```

**Benefits**:
- Switch from local files to cloud storage without code changes
- Memory datasets reduce disk I/O for intermediate data
- Type-safe serialization/deserialization
- Automatic support for partitioned datasets (multiple candidates)

#### 5. **Hybrid Workflows**

**Problem**: Pure AI solutions are expensive; pure rule-based solutions aren't flexible.

**Solution**: Kedro pipelines seamlessly blend deterministic and agentic processing.

**In This Project**:
- **Deterministic**: Document parsing, text extraction, report formatting, email templating
- **Agentic**: Resume structure parsing, requirement matching, candidate evaluation

**Benefits**:
- Use LLMs only where reasoning is needed (cost optimization)
- Deterministic steps are reliable, testable, and fast
- Clear boundaries between rule-based and AI-powered logic

#### 6. **Production-Ready Structure**

**Problem**: Prototype scripts don't scale to team projects.

**Solution**: Kedro's convention-based structure organizes everything predictably.

```
data/
├── prompts/           # AI prompts
├── config/            # Business rules & templates
├── sample/            # Raw input data
├── intermediate/      # Processing artifacts (by pipeline)
└── reports/           # Final reports
```

**Benefits**:
- New team members understand structure immediately
- Clear data lineage from raw → intermediate → reports
- Multiple developers work without conflicts
- Scalable from prototype to enterprise

#### 7. **Observability & Visualization**

**Problem**: Black-box agent execution makes debugging difficult.

**Solution**: Kedro-Viz + preview functions expose workflow internals.

```python
def preview_screening_crew() -> MermaidPreview:
    """Show agent workflow as Mermaid diagram"""
    return MermaidPreview(content=build_screening_graph())
```

**Benefits**:
- Interactive pipeline visualization shows data dependencies
- Preview functions expose agent workflow details (diagrams, code)
- Non-technical stakeholders understand the system
- Quick identification of bottlenecks and issues

### Real-World Impact

This integration enables:

✅ **Non-developer updates**: Prompt engineers and business analysts modify prompts and rules without engineering support

✅ **Fast experimentation**: Test different prompt strategies, scoring weights, or matching rules by editing YAML files

✅ **Cost optimization**: Use expensive LLM calls only for complex reasoning, not simple data transformations

✅ **Team scalability**: Clear structure and boundaries enable multiple developers to work in parallel

✅ **Production confidence**: Kedro's proven patterns + CrewAI's agent capabilities = reliable AI workflows

### The Result

**CrewAI agents** handle the intelligence: reasoning about candidate fit, evaluating evidence, making recommendations.

**Kedro infrastructure** handles everything else: data I/O, configuration management, pipeline orchestration, and observability.

Together, they deliver **production-ready AI agent systems** that are maintainable, configurable, and scalable.

## Architecture

### Complete Pipeline Flow

```
┌─────────────────────────────────────────────────────────────────┐
│ Jobs Pipeline (Deterministic)                                   │
│   Parse Job Posting → Normalize → Split into Metadata + Reqs    │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│ Applications Pipeline (Deterministic + Agentic - 1 Agent)       │
│   Parse Resume → ResumeParserAgent → Create Application         │
│   Output: Evidence Snippets + Application                       │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│ Screening Pipeline (Agentic - 2 Agents)                         │
│   RequirementsMatcherAgent → ResumeEvaluatorAgent               │
│   Output: Screening Result (with candidate info embedded)       │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│ Reporting Pipeline (Deterministic)                              │
│   Draft Email (templates) → Generate HR Report (Word doc)       │
└─────────────────────────────────────────────────────────────────┘
```

### Key Design Decisions

1. **`create_application` in Applications Pipeline**: Links candidate to job, creating the Application object with candidate_name and job_title in artifacts

2. **Screening Result Includes Candidate Info**: `candidate_name` and `job_title` are embedded in `ScreeningResult`, eliminating need to pass Application to Reporting pipeline

3. **Email Drafting is Deterministic**: Uses templates from `email_templates.yml` instead of LLM - more reliable and cost-effective

4. **Two-Agent Screening**: Requirements matcher identifies evidence, evaluator makes final judgment - clear separation of concerns


## Quick Start

### Prerequisites

- Python 3.9+
- OpenAI API key (for CrewAI agents)

### Installation

```bash
# Clone repository
git clone <repository-url>
cd kedro-hr-crew-workflow

# Install project
pip install -e .

# Set up credentials
cp conf/local/cred.yml.example conf/local/credentials.yml
# Edit conf/local/credentials.yml and add your OPENAI_API_KEY 
# and OPENAI_API_BASE
```

### Run the Pipeline

```bash
# Run complete workflow
kedro run

# Visualize pipeline
kedro viz
```

## Usage

### Running Individual Pipelines

```bash
# Process job postings
kedro run --pipeline jobs

# Parse resumes and create applications
kedro run --pipeline applications

# Run AI agent screening
kedro run --pipeline screening

# Generate reports
kedro run --pipeline reporting
```

### Processing Different Resumes

The pipeline supports event-driven processing where each resume triggers a complete pipeline run. A single `resume_id` parameter controls both the input file and output file prefixes.

```bash
# Process default resume (raw_resume_data_scientist.docx)
kedro run

# Process a specific resume
kedro run --params resume_id=se
```

**How it works:**
- **Input**: `data/sample/resumes/{resume_id}.docx`
- **Outputs**: `{resume_id}_application.json`, `{resume_id}_screening_result.json`, `{resume_id}_hr_report.docx`

**Output files are per-candidate:**
```
data/
├── sample/resumes/
│   ├── ds.docx   # Input
│   └── se.docx   # Input
├── intermediate/
│   ├── applications/
│   │   ├── ds_application.json
│   │   └── se_application.json
│   └── screening/
│       ├── ds_screening_result.json
│       └── se_screening_result.json
└── reports/
    ├── ds_hr_report.docx
    └── se_hr_report.docx
```

#### Event-Driven Architecture Example

In production, the `resume_id` is generated by an upstream system that:
1. Receives the resume (e.g., from email, file upload, or message queue)
2. Generates a unique `resume_id` (e.g., UUID, timestamp-based, or candidate identifier)
3. Saves the resume as `{resume_id}.docx` in the resumes folder
4. Triggers the Kedro pipeline with the `resume_id`

```python
# resume_ingestion_service.py (external to Kedro)
import subprocess
import uuid
import shutil
from pathlib import Path
from your_queue_library import consume_messages

RESUMES_DIR = Path("data/sample/resumes")

def ingest_resume(message):
    """
    Upstream service that:
    1. Generates a unique resume_id
    2. Saves the resume with that ID
    3. Triggers the Kedro pipeline
    """
    # Generate unique resume_id (production systems may use different strategies)
    resume_id = f"candidate_{uuid.uuid4().hex[:8]}"

    # Save incoming resume with the generated ID
    incoming_file = message["file_path"]
    target_path = RESUMES_DIR / f"{resume_id}.docx"
    shutil.copy(incoming_file, target_path)

    # Trigger Kedro pipeline with the resume_id
    subprocess.run([
        "kedro", "run",
        "--params", f"resume_id={resume_id}"
    ])

# Consumer processes resumes as they arrive
for message in consume_messages("resume-queue"):
    ingest_resume(message)
```

**Production `resume_id` strategies:**
- **UUID-based**: `candidate_a1b2c3d4` - ensures uniqueness
- **Timestamp-based**: `resume_20240115_143022` - easy to sort chronologically
- **Candidate ID**: `john_doe_senior_engineer` - human-readable
- **External system ID**: `ats_12345` - integrates with Applicant Tracking Systems

### Customizing Behavior

#### Update Email Templates

```bash
# Edit data/config/email_templates.yml
proceed:
  subject: "Next Steps: {job_title}"
  body: |
    Dear {candidate_name},
    Congratulations! We'd like to move forward...
```

#### Adjust Scoring Weights

```bash
# Edit data/config/scoring_config.yml
weights:
  must_have_coverage: 0.8  # Emphasize must-haves more
  avg_confidence: 0.2
```

#### Modify Agent Prompts

```bash
# Edit data/prompts/screening/resume_evaluator_agent_system_prompt.yml
role: Senior Technical Recruiter
goal: Evaluate technical candidates for engineering roles
backstory: |
  You are a technical recruiting specialist with deep expertise in...
```

## Project Structure

```
kedro-hr-crew-workflow/
│
├── conf/
│   ├── base/
│   │   ├── catalog.yml          # Data catalog (all I/O defined here)
│   │   ├── config_genai.yml     # LLM and prompt configurations
│   │   └── parameters.yml       # Project parameters
│   └── local/
│       └── credentials.yml      # API keys (gitignored)
│
├── data/
│   ├── prompts/                 # Agent prompts
│   │   ├── applications/        # Applications pipeline prompts
│   │   │   ├── resume_parser_agent_system_prompt.yml
│   │   │   └── resume_parsing_user_prompt.yml
│   │   └── screening/           # Screening pipeline prompts
│   │       ├── requirements_matcher_agent_system_prompt.yml
│   │       ├── requirements_matching_user_prompt.yml
│   │       ├── resume_evaluator_agent_system_prompt.yml
│   │       └── resume_evaluation_user_prompt.yml
│   │
│   ├── config/                  # Business rules & templates
│   │   ├── screening/           # Screening pipeline configuration
│   │   │   ├── matching_config.yml
│   │   │   └── scoring_config.yml
│   │   └── reporting/           # Reporting pipeline configuration
│   │       └── email_templates.yml
│   │
│   ├── sample/                  # Raw input documents
│   │   ├── jobs/raw_job_posting.docx
│   │   └── resumes/*.docx
│   │
│   ├── intermediate/            # Processing artifacts
│   │   ├── jobs/                # Job metadata + requirements
│   │   ├── applications/        # Evidence snippets + application
│   │   └── screening/           # Screening results
│   │
│   └── reports/                 # Final reports
│       └── *_hr_report.docx
│
└── src/hr_recruiting/
    ├── base/
    │   ├── agent.py             # Base agent class
    │   └── utils.py             # Shared utilities
    │
    ├── datasets/
    │   └── crew_model_client.py # CrewAI LLM dataset
    │
    └── pipelines/
        ├── jobs/                # Deterministic job processing
        ├── applications/        # Agentic application creation (1 agent)
        ├── screening/           # Agentic candidate screening (2 agents)
        └── reporting/           # Deterministic report generation
```

### Pipeline-Specific Files

Each pipeline contains:
- `models.py` - Pydantic models for type safety
- `nodes.py` - Node implementations
- `pipeline.py` - Pipeline definition
- `helper.py` - Helper functions (optional)
- `agents.py` - Agent factory functions (agentic pipelines only)
- `tasks.py` - Task creation functions (agentic pipelines only)
- `tools.py` - Agent tools (screening pipeline only)

## Configuration

### LLM Configuration

Edit `conf/base/config_genai.yml`:

```yaml
llm_crew_ai:
  type: hr_recruiting.datasets.crew_model_client.CrewAILLMDataset
  model: gpt-4o-mini  # or gpt-4o for better quality
  kwargs:
    temperature: 0.1
  credentials: openai
```

### Credentials

Edit `conf/local/credentials.yml`:

```yaml
openai:
  api_key: "${oc.env:OPENAI_API_KEY}"
  base_url: "${oc.env:OPENAI_API_BASE}"  # Optional: for Azure or proxies
```

### Data Paths

Update `conf/base/catalog.yml` for your documents:

```yaml
raw_job_posting:
  type: openxml.DocxDataset
  filepath: data/sample/jobs/my_job_posting.docx

raw_resume:
  type: openxml.DocxDataset
  filepath: data/sample/resumes/candidate_resume.docx
```

## Output Data Models

## Jobs Pipeline
- **`JobMetadata`**: Job metadata for applications pipeline
- **`JobRequirements`**: Job requirements for screening pipeline

### Applications Pipeline
- **`Application`**: Links candidate to job (application_id, job_id, candidate_id, evidence snippets, artifacts with candidate_name and job_title)

### Screening Pipeline
- **`ScreeningResult`**: Complete evaluation (includes candidate_name, job_title, match_score, recommendation, gaps, strengths, etc.)

### Reporting Pipeline
- **`EmailDraft`**: Email with subject, body, and placeholders

## Output Files

After running the pipeline:

- **`intermediate/jobs/job_metadata.json`** - Structured job metadata
- **`intermediate/jobs/job_requirements.json`** - Structured job requirements
- **`intermediate/applications/application.json`** - Application containing parsed candidate information, evidence snippets and job metadata required for screening
- **`intermediate/screening/screening_result.json`** - AI evaluation with recommendation
- **`reports/hr_report.docx`** - Professional Word document with:
  - Executive summary
  - Match analysis
  - Candidate strengths and gaps
  - Risk flags
  - Drafted email communication
  - QA suggestions

## Troubleshooting

### Common Issues

- **Missing API Key**: Ensure `OPENAI_API_KEY` is set in `conf/local/credentials.yml`
- **Document Not Found**: Verify file paths in `conf/base/catalog.yml`
- **Import Errors**: Run `pip install -e .` to install dependencies
- **Validation Errors**: Check Pydantic model structure matches your data

## Future Enhancements: Multi-Resume Batch Processing

The current architecture processes **one resume per pipeline run**, which is optimal for event-driven scenarios where resumes arrive via a queue. For production systems requiring batch processing of multiple resumes, consider these approaches:

### Option 1: IncrementalDataset (Process New Files Only)

Kedro's `IncrementalDataset` tracks which files have been processed using a checkpoint, only loading new/unprocessed partitions on each run.

**Catalog Configuration:**

```yaml
# conf/base/catalog.yml
raw_resumes:
  type: partitions.IncrementalDataset
  path: data/sample/resumes
  dataset:
    type: openxml.DocxDataset
  filename_suffix: .docx
  checkpoint:
    type: json.JSONDataset
    filepath: data/checkpoints/resumes_checkpoint.json
```

**Use Case:** Periodic batch processing (e.g., cron job every hour) that only processes newly added resumes since the last run.

**Production Considerations:**
- Requires pipeline node modifications to iterate over dictionary of partitions
- Checkpoint file tracks processed state - ensure it's persisted reliably
- Combine with a scheduler (cron, Airflow) for periodic execution
- Failed runs need checkpoint rollback strategy

**Trade-offs:**
| Pros | Cons |
|------|------|
| Only processes new files | Requires code changes to nodes |
| Built-in state tracking | Checkpoint management overhead |
| Efficient for incremental loads | Still requires external trigger |

---

### Option 2: PartitionedDataset (Batch All Files)

Kedro's `PartitionedDataset` loads all files matching a pattern for bulk processing in a single pipeline run.

**Catalog Configuration:**

```yaml
# conf/base/catalog.yml
raw_resumes:
  type: partitions.PartitionedDataset
  path: data/sample/resumes
  dataset:
    type: openxml.DocxDataset
  filename_suffix: .docx

# Output datasets also partitioned
applications:
  type: partitions.PartitionedDataset
  path: data/intermediate/applications
  dataset:
    type: json.JSONDataset
  filename_suffix: .json

screening_results:
  type: partitions.PartitionedDataset
  path: data/intermediate/screening
  dataset:
    type: json.JSONDataset
  filename_suffix: .json

hr_reports:
  type: partitions.PartitionedDataset
  path: data/reports
  dataset:
    type: openxml.DocxDataset
  filename_suffix: .docx
```

**Use Case:** Bulk processing of all resumes in a folder (e.g., initial data migration, reprocessing historical data, batch screening events).

**Production Considerations:**
- Modify pipeline nodes to accept `dict[str, Callable]` and iterate over partitions
- Consider parallel processing within nodes for large batches
- Monitor LLM API rate limits when processing many resumes
- Implement proper error handling for partial failures

**Trade-offs:**
| Pros | Cons |
|------|------|
| Process entire folder at once | No incremental tracking |
| Single pipeline run | Higher compute/API costs |
| Simple mental model | Reprocesses all files every run |

---

### Option 3: External Orchestration (Recommended for Production)

Keep the current single-file architecture and use an external orchestrator for maximum flexibility and control.

**Architecture:**

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Message Queue  │────▶│   Orchestrator  │────▶│   Kedro Run     │
│  (SQS, RabbitMQ)│     │ (Airflow/Prefect)│    │   (1 resume)    │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                                        │
                               ┌────────────────────────┴────────────────────────┐
                               │                                                  │
                               ▼                                                  ▼
                      ┌─────────────────┐                                ┌─────────────────┐
                      │  Success: Move  │                                │  Failure: Retry │
                      │  to completed/  │                                │  or Dead Letter │
                      └─────────────────┘                                └─────────────────┘
```

**Example with Apache Airflow:**

```python
# dags/hr_screening_dag.py
from airflow import DAG
from airflow.operators.bash import BashOperator
from datetime import datetime

with DAG(
    'hr_resume_screening',
    start_date=datetime(2024, 1, 1),
    schedule_interval=None,  # Triggered externally
    catchup=False,
) as dag:

    process_resume = BashOperator(
        task_id='process_resume',
        bash_command='kedro run --params resume_id={{ dag_run.conf["resume_id"] }}',
        cwd='/path/to/kedro-hr-crew-workflow',
    )
```

**Example with Prefect:**

```python
# flows/hr_screening_flow.py
from prefect import flow, task
import subprocess

@task(retries=3, retry_delay_seconds=60)
def run_kedro_pipeline(resume_id: str):
    result = subprocess.run(
        ["kedro", "run", "--params", f"resume_id={resume_id}"],
        cwd="/path/to/kedro-hr-crew-workflow",
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise Exception(f"Pipeline failed: {result.stderr}")
    return result.stdout

@flow
def process_resume_batch(resume_ids: list[str]):
    for resume_id in resume_ids:
        run_kedro_pipeline(resume_id)
```

**Use Case:** Production systems requiring enterprise-grade reliability, monitoring, and scalability.

**Production Considerations:**
- Built-in retry logic and dead-letter queues for failed processing
- Centralized monitoring and alerting (Airflow UI, Prefect Cloud)
- Horizontal scaling by running multiple workers
- Clear audit trail of all processed resumes
- Integration with existing CI/CD and deployment pipelines

**Trade-offs:**
| Pros | Cons |
|------|------|
| Production-grade reliability | Additional infrastructure |
| Built-in monitoring & alerting | Learning curve for orchestrator |
| Retry logic & error handling | More complex deployment |
| Horizontal scalability | Overkill for simple use cases |

---

### Recommendation Summary

| Scenario | Recommended Approach |
|----------|---------------------|
| Event-driven (queue-based) | **Current setup** with runtime params |
| Periodic batch (new files only) | **IncrementalDataset** + cron/scheduler |
| One-time bulk processing | **PartitionedDataset** |
| Production with SLA requirements | **External Orchestration** (Airflow/Prefect) |

For most production deployments, we recommend starting with the **current event-driven approach** and migrating to **external orchestration** as requirements grow.
