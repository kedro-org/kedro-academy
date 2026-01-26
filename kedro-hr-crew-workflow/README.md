# HR Recruiting Agentic Workflow

An HR recruiting system that uses AI agents to screen candidates, match job requirements, and generate reports. Built with Kedro for data pipeline orchestration and CrewAI for multi-agent workflows.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [CrewAI Integration](#crewai-integration)
- [Kedro Features Used](#kedro-features-used)
- [Getting Started](#getting-started)
- [Usage](#usage)
- [Configuration](#configuration)

## Overview

This project automates the HR candidate screening process:

1. **Parse** job postings and resumes from Word documents
2. **Normalize** data into structured formats using Pydantic models
3. **Extract** evidence snippets from candidate profiles using AI agents
4. **Screen** candidates using AI agents (CrewAI) to match requirements and evaluate fit
5. **Generate** professional HR reports with recommendations

The system uses a combination of:
- **Deterministic pipelines** for data processing (parsing, normalization, report generation)
- **Agentic pipelines** for intelligent processing (resume parsing, candidate screening)

## Architecture

### Pipeline Flow

```
Jobs Pipeline (Deterministic)
  └─> Parse Job Posting → Split into Job Metadata & Job Requirements

Applications Pipeline (Agentic - CrewAI)
  └─> Parse Resume Text → Resume Parser Agent → Split Results
  └─> Create Application (links candidate to job)
  └─> Output: Evidence Snippets + Application

Screening Pipeline (Agentic - CrewAI)
  └─> Requirements Matcher Agent → Resume Evaluator Agent
  └─> Output: Validated Screening Result (includes email_draft)

Reporting Pipeline (Deterministic)
  └─> Draft Email → Generate HR Report
```

### Key Components

- **Deterministic Pipelines**: Process data using fixed rules (parsing, validation, report generation)
- **Agentic Pipelines**: Use AI agents to make intelligent decisions (resume parsing, screening, evaluation)
- **Pydantic Models**: Type-safe data validation and serialization
- **Tools**: Reusable functions that agents can use (matching, scoring)
- **Configuration Datasets**: Versioned YAML files for templates, rules, and parameters

## Project Structure

```
kedro-hr-crew-workflow/
├── conf/
│   ├── base/
│   │   ├── catalog.yml          # Data datasets (Word docs, JSON files, configs)
│   │   ├── genai-config.yml     # AI datasets (LLM, prompts)
│   │   └── parameters.yml       # Project parameters
│   └── local/
│       └── credentials.yml      # API keys (gitignored)
│
├── data/
│   └── hr_recruiting/
│       ├── prompts/              # Prompt datasets (YAML)
│       │   ├── *_agent_system_prompt.yml    # Agent instructions
│       │   └── *_user_prompt.yml            # Task descriptions
│       ├── config/               # Configuration files (YAML)
│       │   ├── email_templates.yml          # Email templates
│       │   ├── scoring_config.yml           # Scoring weights
│       │   └── matching_config.yml          # Matching parameters
│       ├── sample/               # Sample data files
│       │   ├── jobs/
│       │   │   └── raw_job_posting.docx
│       │   └── resumes/
│       │       ├── raw_resume_data_scientist.docx
│       │       └── raw_resume_software_engineer.docx
│       ├── intermediate/         # Processed data (organized by pipeline)
│       │   ├── jobs/
│       │   │   ├── job_metadata.json
│       │   │   └── job_requirements.json
│       │   ├── applications/
│       │   │   ├── evidence_snippets.json
│       │   │   └── application.json
│       │   └── screening/
│       │       └── screening_result.json
│       └── output/               # Generated reports (Word docs)
│           └── hr_report.docx
│
└── src/
    └── hr_recruiting/
        ├── base/
        │   ├── agent.py          # Base agent class for CrewAI
        │   └── utils.py          # Shared utility functions
        │
        ├── datasets/
        │   └── crew_model_client.py  # CrewAI LLM client
        │
        └── pipelines/
            ├── jobs/              # Job posting processing
            │   ├── models.py      # JobMetadata, JobRequirements, Requirements models
            │   ├── helper.py      # Helper functions
            │   ├── nodes.py       # Parse and split job postings
            │   └── pipeline.py
            │
            ├── applications/      # Resume processing (agentic)
            │   ├── models.py      # CandidateProfile, EvidenceSnippet, WorkHistory, Education, Application models
            │   ├── agents.py      # Agent factory functions
            │   ├── tasks.py       # Task creation functions
            │   ├── helper.py      # Helper functions
            │   ├── nodes.py       # Parse resume, run crew
            │   └── pipeline.py
            │
            ├── screening/         # AI agent screening
            │   ├── models.py     # MatchResult, ScreeningResult models
            │   ├── agents.py     # Agent factory functions
            │   ├── tasks.py      # Task creation functions
            │   ├── tools.py      # Agent tools (matching, scoring)
            │   ├── helper.py     # Helper functions
            │   ├── nodes.py      # Crew orchestration
            │   └── pipeline.py
            │
            └── reporting/        # Report generation
                ├── models.py     # EmailDraft model
                ├── helper.py     # Document formatting functions
                ├── nodes.py      # Generate reports
                └── pipeline.py
```

## CrewAI Integration

### What is CrewAI?

CrewAI is a framework for building multi-agent AI systems. It allows you to:
- Create specialized AI agents with specific roles
- Give agents tools to perform tasks
- Orchestrate agents working together
- Get structured outputs from agent workflows

### CrewAI Components Used

1. **Agents**: Specialized AI assistants
   - `ResumeParserAgent`: Parses resumes and extracts structured candidate information
   - `RequirementsMatcherAgent`: Matches job requirements to candidate evidence snippets
   - `ResumeEvaluatorAgent`: Evaluates candidates and provides recommendations

2. **Tools**: Functions agents can use
   - `Requirements Matcher`: Matches requirements to evidence snippets with stop word filtering, technical term prioritization, and confidence scoring
   - `Scoring Tool`: Calculates match scores based on configuration

3. **Crew**: Orchestrates agents working together
   - Creates tasks for each agent
   - Manages agent communication
   - Executes the workflow sequentially

### How We Integrated CrewAI with Kedro

1. **Base Agent Class** (`base/agent.py`):
   - Wraps CrewAI agents with Kedro's `LLMContext`
   - Extracts role, goal, and backstory from prompt datasets
   - Manages agent compilation and tool assignment

2. **Tool Builders** (`screening/tools.py`):
   - Functions that create CrewAI tools from Kedro datasets
   - Tools receive data from Kedro catalog (job requirements, evidence, configs)
   - Tools are versioned and configurable via YAML files

3. **LLM Context Nodes**:
   - Kedro's `llm_context_node` creates agent contexts
   - Each context includes: LLM, prompts, and tools
   - Contexts are passed to orchestrator nodes

4. **Orchestrator Nodes**:
   - Create CrewAI agents from contexts
   - Build tasks and crew
   - Execute the agentic workflow
   - Extract and structure results with Pydantic validation

## Kedro Features Used

### 1. Prompt Datasets

**What they are**: YAML files containing prompts for AI agents.

**How we use them**:
- Agent system prompts define agent roles and behavior
- Task user prompts define what agents should do and expected outputs
- Schema JSON is injected directly from Pydantic models into prompts
- Stored in `data/hr_recruiting/prompts/`
- Configured in `conf/base/genai-config.yml`

**Benefits**:
- Easy to update without code changes
- Can A/B test different prompts
- Schema validation instructions come from Pydantic models

### 2. LLM Context Nodes

**What they are**: Kedro's special node type for AI workflows that bundles LLM, prompts, and tools together.

**How we use them**:
- Each agent gets its own `llm_context_node`
- Context includes: LLM model, system/user prompts, and tools
- Tools are built from datasets (job requirements, evidence, configs)

**Benefits**:
- Clean separation of AI configuration
- Easy to swap LLM models
- Tools automatically get the right data

### 3. Configuration Datasets

**What they are**: YAML files with configurable parameters.

**How we use them**:
- `email_templates.yml`: Email templates for different recommendations
- `scoring_config.yml`: Weights for calculating scores
- `matching_config.yml`: Parameters for matching requirements (stop words, thresholds, technical terms)

**Benefits**:
- No hardcoded values in code
- Easy to tune and experiment
- Business users can update configs

### 4. Pydantic Models

**What they are**: Type-safe data models for validation and serialization.

**How we use them**:
- Pipeline-specific models in `pipelines/<pipeline>/models.py`
- Models ensure data quality and structure
- Schema JSON is generated from models and injected into prompts
- Validation happens at pipeline boundaries

**Benefits**:
- Type safety and validation
- Clear data contracts
- Automatic schema generation for LLM instructions

## Getting Started

### Prerequisites

- Python 3.9+
- OpenAI API key (or other LLM provider)

### Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd kedro-hr-crew-workflow
   ```

2. **Install dependencies**:
   ```bash
   pip install -e ".[dev]"
   ```

3. **Set up credentials**:
   ```bash
   # Copy the template
   cp conf/local/cred.yml.example conf/local/credentials.yml
   
   # Add your API keys
   # Edit conf/local/credentials.yml
   ```

4. **Create sample documents** (optional):
   ```bash
   python scripts/create_sample_documents.py
   ```

### Configuration

#### 1. LLM Configuration

Edit `conf/base/genai-config.yml`:
```yaml
llm_crew_ai:
  type: hr_recruiting.datasets.crew_model_client.CrewAILLMDataset
  model: gpt-4o-mini
  kwargs:
    temperature: 0.1
  credentials: openai
```

#### 2. Credentials

Edit `conf/local/credentials.yml`:
```yaml
# OpenAI Credentials for CrewAI
openai:
  api_key: "${oc.env:OPENAI_API_KEY}"
  base_url: "${oc.env:OPENAI_API_BASE}"
```

#### 3. Data Paths

Update `conf/base/catalog.yml` to point to your documents:
```yaml
raw_job_posting:
  type: openxml.DocxDataset
  filepath: data/hr_recruiting/sample/jobs/raw_job_posting.docx

raw_resume:
  type: openxml.DocxDataset
  filepath: data/hr_recruiting/sample/resumes/raw_resume_data_scientist.docx
```

## Usage

### Running the Full Pipeline

```bash
kedro run
```

This runs all pipelines in sequence:
1. Jobs pipeline (parse job posting, split into metadata and requirements)
2. Applications pipeline (parse resume with AI agent, extract evidence, create application)
3. Screening pipeline (AI agents evaluate candidate and match requirements)
4. Reporting pipeline (generate HR report)

### Running Individual Pipelines

```bash
# Just process the job postings
kedro run --pipeline jobs

# Just process the job applications
kedro run --pipeline applications

# Just run screening (requires processed job and resume)
kedro run --pipeline screening

# Just generate report (requires screening result)
kedro run --pipeline reporting
```

### Viewing Pipeline Visualization

```bash
kedro viz
```

Opens a web interface showing the pipeline structure and data flow.

### Customizing Behavior

#### Update Email Templates

Edit `data/hr_recruiting/config/email_templates.yml`:
```yaml
proceed:
  subject: "Application Update: {job_title}"
  body: |
    Dear {candidate_name},
    ...
```

#### Adjust Scoring Weights

Edit `data/hr_recruiting/config/scoring_config.yml`:
```yaml
weights:
  must_have_coverage: 0.7  # Increase to weight must-haves more
  avg_confidence: 0.3
```

#### Update Matching Configuration

Edit `data/hr_recruiting/config/matching_config.yml`:
```yaml
stop_words:
  - "the"
  - "a"
  - "an"
min_word_length: 3
confidence:
  must_have:
    base: 0.5
    increment: 0.1
    max: 0.9
technical_terms:
  - "python"
  - "docker"
  - "kubernetes"
```

#### Update Agent Prompts

Edit files in `data/hr_recruiting/prompts/`:
- `*_agent_system_prompt.yml`: Change agent behavior
- `*_user_prompt.yml`: Change task descriptions and expected outputs

## How Kedro Features Shaped the Project

### LLM Context Nodes

**Before**: LLM configuration was scattered across code, making it hard to manage.

**With Kedro**: `llm_context_node` provides:
- Centralized LLM configuration
- Automatic tool building from datasets
- Clean separation of AI logic from business logic
- Easy model swapping (just change the dataset)

### Configuration Datasets

**Before**: Business rules were hardcoded (email templates, scoring weights, etc.).

**With Kedro**: Configuration datasets allow:
- Business users to update rules
- Experimenting with different configurations
- Versioning configuration changes
- Environment-specific configs (dev, staging, prod)

### Pydantic Models

**Before**: Data validation was ad-hoc and error-prone.

**With Kedro + Pydantic**: Models provide:
- Type safety and validation at pipeline boundaries
- Automatic schema generation for LLM instructions
- Clear data contracts between pipelines
- Serialization to JSON with proper handling of datetime objects

## Key Design Decisions

1. **Separation of Deterministic and Agentic**: Clear split between rule-based processing and AI decision-making
2. **Pipeline-Specific Models**: Each pipeline has its own models file for better modularity
3. **Tool Builders**: Tools are built from datasets, making them data-driven
4. **Base Agent Pattern**: Reusable agent class following kedro-academy patterns
5. **Configuration-Driven**: All business logic in YAML configs, not code
6. **Modular Pipelines**: Each pipeline is self-contained with helper functions, models, and nodes
7. **Schema Injection**: Pydantic model schemas are injected into prompts dynamically, avoiding hardcoded schema descriptions
8. **Strict Validation**: No fallback code - failures are immediately visible
9. **Organized Intermediate Data**: Intermediate files are organized by pipeline (jobs/, applications/, screening/)
10. **Job Posting Split**: Job postings are split into `job_metadata` (for applications pipeline) and `job_requirements` (for screening pipeline) to reduce coupling

## Data Models

### Jobs Pipeline Models
- `JobMetadata`: job_id, title, location
- `JobRequirements`: job_id, requirements (must_have, nice_to_have)

### Applications Pipeline Models
- `CandidateProfile`: candidate_id, name, email, skills, work_history, education, raw_resume_text
- `EvidenceSnippet`: snippet_id, text, source, metadata
- `Application`: application_id, job_id, candidate_id, submitted_at, status, artifacts
- `WorkHistory`: company, role, duration, description
- `Education`: institution, degree, field, year

### Screening Pipeline Models
- `MatchResult`: requirement, snippet_ids, confidence
- `ScreeningResult`: application_id, candidate_name, job_title, match_score, must_have_coverage, gaps, strengths, risk_flags, recommendation, qa_suggestions, match_results

### Reporting Pipeline Models
- `EmailDraft`: subject, body, placeholders

## Output

After running the pipeline, you'll find:

- **Job Metadata** (`data/hr_recruiting/intermediate/jobs/job_metadata.json`):
  - Job ID, title, location

- **Job Requirements** (`data/hr_recruiting/intermediate/jobs/job_requirements.json`):
  - Job ID, must-have and nice-to-have requirements

- **Evidence Snippets** (`data/hr_recruiting/intermediate/applications/evidence_snippets.json`):
  - Candidate ID, candidate name, and array of evidence snippets with IDs, text, source, and metadata

- **Application** (`data/hr_recruiting/intermediate/applications/application.json`):
  - Application ID (candidate_id_job_id), job_id, candidate_id, submitted_at, status, artifacts (candidate_name, job_title)

- **Screening Result** (`data/hr_recruiting/intermediate/screening/screening_result.json`):
  - Application ID (candidate_id_job_id)
  - Candidate name and job title
  - Match score (0-100)
  - Recommendation (proceed/review/reject)
  - Must-have coverage (0.0-1.0)
  - Strengths and gaps
  - Risk flags
  - QA suggestions
  - Detailed match results

- **HR Report** (`data/hr_recruiting/output/hr_report.docx`):
  - Professional Word document
  - Executive summary table
  - Candidate strengths
  - Identified gaps
  - Risk flags
  - Detailed match results table
  - Drafted email communication
  - Next steps / QA suggestions

## Troubleshooting

### Common Issues

1. **Missing API Key**: Ensure `conf/local/credentials.yml` has your OpenAI API key
2. **Missing Documents**: Check that Word documents exist in the paths specified in `catalog.yml`
3. **Import Errors**: Make sure you've installed dependencies with `pip install -e ".[dev]"`
4. **LLM Errors**: Check your API key and model name in `genai-config.yml`
5. **Validation Errors**: Check that Pydantic models match the data structure - errors will surface immediately without fallbacks
6. **Deprecation Warning**: If you see a warning about `pipeline_name`, this is from Kedro's main branch and can be safely ignored

## Next Steps

- Customize agent prompts for your use case
- Adjust scoring weights based on your requirements
- Add more tools for agents to use
- Integrate with your HR systems
- Add more validation rules
- Support multiple jobs and multiple candidates (many-to-many relationships)
