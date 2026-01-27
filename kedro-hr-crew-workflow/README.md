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
# data/hr_recruiting/prompts/resume_evaluator_agent_system_prompt.yml
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
# data/hr_recruiting/config/scoring_config.yml
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
  filepath: data/hr_recruiting/intermediate/screening/screening_result.json
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
data/hr_recruiting/
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

### Customizing Behavior

#### Update Email Templates

```bash
# Edit data/hr_recruiting/config/email_templates.yml
proceed:
  subject: "Next Steps: {job_title}"
  body: |
    Dear {candidate_name},
    Congratulations! We'd like to move forward...
```

#### Adjust Scoring Weights

```bash
# Edit data/hr_recruiting/config/scoring_config.yml
weights:
  must_have_coverage: 0.8  # Emphasize must-haves more
  avg_confidence: 0.2
```

#### Modify Agent Prompts

```bash
# Edit data/hr_recruiting/prompts/resume_evaluator_agent_system_prompt.yml
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
│   │   ├── genai-config.yml     # LLM and prompt configurations
│   │   └── parameters.yml       # Project parameters
│   └── local/
│       └── credentials.yml      # API keys (gitignored)
│
├── data/hr_recruiting/
│   ├── prompts/                 # Agent and task prompts (YAML)
│   │   ├── resume_parser_agent_system_prompt.yml
│   │   ├── requirements_matcher_agent_system_prompt.yml
│   │   ├── resume_evaluator_agent_system_prompt.yml
│   │   └── *_user_prompt.yml
│   │
│   ├── config/                  # Business rules & templates
│   │   ├── email_templates.yml
│   │   ├── scoring_config.yml
│   │   └── matching_config.yml
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
│   └── reports/                  # Final reports
│       └── hr_report.docx
│
└── src/hr_recruiting/
    ├── base/
    │   ├── agent.py             # Base agent class (Kedro + CrewAI integration)
    │   └── utils.py             # Shared utilities
    │
    ├── datasets/
    │   └── crew_model_client.py # CrewAI LLM dataset
    │
    └── pipelines/
        ├── jobs/                # Deterministic job processing
        ├── applications/        # Agentic resume parsing + application creation
        ├── screening/           # Agentic candidate screening (2 agents)
        └── reporting/           # Deterministic email + report generation
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

Edit `conf/base/genai-config.yml`:

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
  filepath: data/hr_recruiting/sample/jobs/my_job_posting.docx

raw_resume:
  type: openxml.DocxDataset
  filepath: data/hr_recruiting/sample/resumes/candidate_resume.docx
```

## Output Data Models

## Jobs Pipeline
- **`JobMetadata`**: Job metadata for applications pipeline
- **`JobRequirements`**: Job requirements for screening pipeline

### Applications Pipeline
- **`Application`**: Links candidate to job (application_id, job_id, candidate_id, artifacts with candidate_name and job_title)
- **`EvidenceSnippet`**: Text snippets with source metadata

### Screening Pipeline
- **`ScreeningResult`**: Complete evaluation (includes candidate_name, job_title, match_score, recommendation, gaps, strengths, etc.)

### Reporting Pipeline
- **`EmailDraft`**: Email with subject, body, and placeholders

## Output Files

After running the pipeline:

- **`intermediate/jobs/job_metadata.json`** - Structured job metadata
- **`intermediate/jobs/job_requirements.json`** - Structured job requirements
- **`intermediate/applications/application.json`** - Application linking candidate to job
- **`intermediate/applications/evidence_snippets.json`** - Candidate evidence snippets
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
