<img width="294" height="76" alt="Screenshot From 2026-03-27 14-53-35" src="https://github.com/user-attachments/assets/567cbabe-cdd8-4a3e-bb23-458f60f3ef1b" />




# ClinicalMind: Multi-Agent Clinical Intelligence System

![CI Pipeline](https://github.com/YOUR_USERNAME/ClinicalMind/actions/workflows/ci.yml/badge.svg)
![CD Pipeline](https://github.com/YOUR_USERNAME/ClinicalMind/actions/workflows/cd.yml/badge.svg)
![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![Node.js](https://img.shields.io/badge/Node.js-18+-green.svg)
![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)

ClinicalMind is a production-grade, multi-agent Retrieval-Augmented Generation (RAG) system designed to provide evidence-based clinical insights. By leveraging LangGraph orchestration and high-speed Groq LLMs, it integrates clinical guidelines, pharmacological data, and patient history into a unified reasoning framework.

## Table of Contents

- [Problem Statement](#problem-statement)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running the Application](#running-the-application)
- [Docker Deployment](#docker-deployment)
- [Usage Guide](#usage-guide)
- [API Endpoints](#api-endpoints)
- [Project Structure](#project-structure)
- [Monitoring and Observability](#monitoring-and-observability)
- [Testing](#testing)
- [Safety Disclaimer](#safety-disclaimer)
- [Contributing](#contributing)
- [License](#license)

## Problem Statement

### The Challenge

Healthcare professionals face significant challenges in accessing and synthesizing critical medical information:

1. **Information Fragmentation**: Clinical data is scattered across multiple sources including clinical protocols, drug databases, electronic health records, and research literature. This fragmentation makes it difficult to obtain a comprehensive view during patient care decisions.

2. **Time Constraints**: Healthcare providers often have limited time to search through multiple databases and guidelines during consultations, leading to potential gaps in care or reliance on outdated information.

3. **Information Overload**: The volume of medical literature and guidelines continues to grow exponentially, making it challenging to stay current with the latest evidence-based recommendations.

4. **Lack of Traceability**: Many AI-powered clinical tools provide answers without citing sources, making it difficult for clinicians to verify the accuracy and relevance of the information.

5. **Safety Concerns**: Clinical decision support systems must incorporate safety checks to identify high-risk scenarios and ensure appropriate disclaimers are provided.

<img width="1353" height="942" alt="Screenshot From 2026-03-27 14-52-47" src="https://github.com/user-attachments/assets/dbd768bc-a42b-458f-9dba-c15d8959a675" />


### The ClinicalMind Solution

ClinicalMind addresses these challenges by providing a centralized intelligence layer with the following capabilities:

1. **Multi-Agent Orchestration**: Deploys specialized agents that reason over diverse datasets including clinical guidelines, pharmacological data, and anonymized patient records. Each agent focuses on its domain of expertise, ensuring comprehensive coverage.

2. **Evidence-Based Responses**: Every clinical claim is accompanied by citations from the source documents, enabling healthcare professionals to verify information and assess its credibility.

3. **Automated Safety Checks**: Implements automated high-risk keyword detection and clinical disclaimers to identify potentially dangerous scenarios and ensure appropriate caution is exercised.

4. **Unified Query Interface**: Provides a single point of access for querying multiple data sources simultaneously, reducing the time needed to gather relevant information.

5. **Caching and Performance**: Implements intelligent caching to improve response times for frequently asked queries while maintaining accuracy.

6. **Scalable Architecture**: Built on production-grade technologies (FastAPI, Next.js, FAISS) that can scale to handle multiple concurrent users in clinical settings.

### Key Benefits

- Reduced time to access critical clinical information
- Improved confidence in decision-making through source citations
- Enhanced patient safety through automated risk detection
- Streamlined workflow with unified search interface
- Continuous learning through document ingestion capabilities

## Architecture

```
User -> Frontend (Next.js/Tailwind)
       |
       v
     Backend (FastAPI)
       |
       v
     LangGraph Orchestrator (Supervisor Agent)
       |--- Tools: [Guidelines Search, Drug Search, Case History]
       |--- Safety: [MedicalSafetyChecker]
       |--- Logic: [Groq Llama-3-70b]
       |
       v
     Vector Database (FAISS Multi-Store)
       |--- Store A: Clinical Guidelines
       |--- Store B: Pharmacology & Drugs
       |--- Store C: Anonymized Patient Records
```

## Tech Stack

### Frontend
- Framework: Next.js 14 (App Router)
- Styling: Tailwind CSS
- API Client: Axios
- TypeScript

### Backend
- Orchestration: LangGraph (Multi-agent state machines)
- Framework: LangChain
- API: FastAPI
- Vector DB: FAISS (with HuggingFace `all-MiniLM-L6-v2` embeddings)
- LLM: Groq (Llama-3-70b-8192)
- Monitoring: Prometheus Client

### Additional Tools
- Document Processing: PyPDF, docx2txt
- Configuration: Pydantic, python-dotenv
- Logging: Loguru
- Testing: pytest

## Prerequisites

- Python 3.10 or higher
- Node.js 18 or higher
- Groq API Key (obtain from https://console.groq.com/)
- pip (Python package manager)
- npm or yarn (Node.js package manager)

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/ClinicalMind.git
cd ClinicalMind
```

### 2. Backend Setup

```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Additional dependencies (if needed)
pip install psutil prometheus-client sse-starlette
```

### 3. Frontend Setup

```bash
# Navigate to the frontend directory
cd frontend

# Install dependencies
npm install
```

## Configuration

### Environment Variables

Create a `.env` file in the project root directory:

```bash
GROQ_API_KEY=your_groq_api_key_here
```

Optional environment variables:

```bash
# HuggingFace token for faster model downloads (optional)
HF_TOKEN=your_huggingface_token

# Redis configuration for caching (optional)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
```

Copy the example environment file:

```bash
cp .env.example .env
```

Edit `.env` and add your Groq API key.

## Running the Application

### Option 1: Manual Start

1. Start the backend server:

```bash
# From project root (with virtual environment activated)
python -m uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

2. Start the frontend development server (in a new terminal):

```bash
cd frontend
npm run dev
```

### Option 2: Using Startup Script

```bash
chmod +x docker-start.sh
# Note: This script is designed for Docker deployment
```

Access the application:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/docs

## Docker Deployment

### Build and Run with Docker Compose

```bash
# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Stop and remove volumes
docker-compose down -v
```

### Docker Commands Reference

```bash
# Build images
docker-compose build

# Start services
docker-compose up

# Restart services
docker-compose restart

# View running containers
docker-compose ps
```

## Usage Guide

### Knowledge Base Ingestion

Before querying, populate the vector stores:

1. Use the Knowledge Base Management panel in the UI
2. Upload clinical PDFs/DOCX files to the Guidelines store
3. Upload pharmacological data to the Drug Database
4. Upload case studies to Patient Records

### Clinical Reasoning

1. Enter a query in the chat interface (e.g., "What is the standard dosage for Metformin in patients with CKD Stage 3?")
2. The Supervisor Agent will activate relevant tools and cross-reference the stores
3. View the response, citations, and the Safety Risk Badge

### Demo Steps

1. Upload: Index a PDF guideline for Diabetes Management
2. Query: Ask "Compare treatment protocols for Type 2 Diabetes vs Type 1"
3. Inspect: Verify that the Sources section lists the uploaded PDF and the Safety Risk is assessed

## API Endpoints

### Query Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /query | Execute a clinical query |
| POST | /query/stream | Streaming clinical query (SSE) |
| GET | /health | Health check endpoint |
| GET | /ready | Readiness check endpoint |
| GET | /status | System status |

### Document Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /upload/{doc_type} | Upload clinical document |
| DELETE | /clear | Clear all data |

### Cache Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /cache/stats | Get cache statistics |
| DELETE | /cache/clear | Clear query cache |

### Monitoring

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /metrics | Prometheus metrics |

### API Usage Examples

```bash
# Health check
curl http://localhost:8000/health

# Submit a query
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What are the guidelines for hypertension management?"}'

# Upload a document
curl -X POST http://localhost:8000/upload/guidelines \
  -F "file=@/path/to/document.pdf"

# Get system status
curl http://localhost:8000/status
```

## Project Structure

```
ClinicalMind/
├── backend/
│   └── app/
│       └── main.py          # FastAPI application
├── frontend/
│   ├── app/                 # Next.js app router
│   ├── components/          # React components
│   └── lib/                 # Utility libraries
├── src/
│   ├── agents/              # LangGraph agents
│   │   └── supervisor_agent.py
│   ├── vectorstore/         # FAISS store management
│   ├── cache/               # Caching layer
│   ├── monitoring/          # Prometheus metrics
│   └── api/                 # API utilities
├── data/
│   ├── raw/                 # Uploaded documents
│   └── stores/              # Vector store indexes
├── configs/                 # Configuration files
├── tests/                   # Test suite
├── .env                     # Environment variables
├── .env.example             # Environment template
├── docker-compose.yml       # Docker services
├── Dockerfile.backend       # Backend container
├── requirements.txt         # Python dependencies
└── README.md                # This file
```

## Monitoring and Observability

### Prometheus Metrics

ClinicalMind exposes the following metrics:

- `clinicalmind_queries_total` - Total query count with status labels
- `clinicalmind_query_latency_seconds` - Query latency histogram
- `clinicalmind_cache_operations_total` - Cache hit/miss counters
- `clinicalmind_tool_executions_total` - Tool execution counter
- `clinicalmind_errors_total` - Error counter by type
- `clinicalmind_vector_store_size` - Vector store document counts
- `clinicalmind_memory_usage_bytes` - Memory usage gauge

### Accessing Metrics

```bash
# Prometheus metrics endpoint
curl http://localhost:8000/metrics
```

### Logging

Structured logs are available for:
- Query processing
- Cache operations
- Tool executions
- Error tracking
- System events

## CI/CD Pipeline

ClinicalMind includes automated CI/CD pipelines using GitHub Actions.

### Pipeline Overview

| Pipeline | Trigger | Purpose |
|----------|---------|---------|
| CI | Push, Pull Request | Test, lint, build |
| CD | Push to main | Deploy to production |

### CI Pipeline Jobs

1. **Backend Tests**: Python unit tests, linting, type checking, coverage
2. **Frontend Tests**: Node.js tests, ESLint, TypeScript check, build
3. **Security Scan**: Bandit, pip-audit, safety checks
4. **Docker Build**: Build and validate Docker images

### CD Pipeline Jobs

1. **Deploy**: Build and push Docker images to Docker Hub

### Required Secrets

Configure these in GitHub Repository Settings > Secrets and variables > Actions:

| Secret | Description | Required |
|--------|-------------|----------|
| `GROQ_API_KEY` | Groq API key for testing | Yes |
| `DOCKER_USERNAME` | Docker Hub username | For CD |
| `DOCKER_PASSWORD` | Docker Hub token | For CD |

### Manual Workflow Trigger

You can manually trigger the CD pipeline:

1. Go to Actions tab
2. Select "CD Pipeline - Deploy"
3. Click "Run workflow"
4. Select branch and click "Run workflow"

### Viewing Pipeline Status

- Check the Actions tab in GitHub
- CI status badges are displayed at the top of this README
- Failed pipelines block pull request merges

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov=backend

# Run specific test file
pytest tests/test_specific.py -v
```

## Safety Disclaimer

**ClinicalMind.AI is a decision-support tool and NOT a medical device.**

- All AI-generated responses must be validated by a licensed healthcare professional
- The system is designed for informational purposes only
- Never use this system for emergency medical diagnosis or treatment decisions
- Prohibited from handling un-anonymized Patient Health Information (PHI) in its current configuration

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines

- Follow PEP 8 for Python code
- Follow ESLint/Prettier for TypeScript code
- Write tests for new features
- Update documentation as needed
- Use meaningful commit messages

## License

This project is licensed under the MIT License. See LICENSE file for details.

## Support

For issues and questions:
- GitHub Issues: https://github.com/yourusername/ClinicalMind/issues
- Documentation: https://github.com/yourusername/ClinicalMind/wiki

## Acknowledgments

- Groq for providing fast LLM inference
- LangChain and LangGraph for agent orchestration
- HuggingFace for embedding models
- FAISS for vector similarity search
