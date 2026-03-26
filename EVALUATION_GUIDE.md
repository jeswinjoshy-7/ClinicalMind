# ClinicalMind Evaluation Metrics - Testing Guide

## Overview

This guide explains how to test and evaluate your ClinicalMind RAG system using the provided evaluation scripts.

## Evaluation Metrics

The evaluation system tests the following metrics:

### 1. **Context Relevancy** (0.0 - 1.0)
- **What it measures**: How relevant is the response to the user's query?
- **How it's calculated**: Keyword overlap between query and response
- **Threshold**: ≥ 0.5 is passing
- **Why it matters**: Ensures the system answers the actual question asked

### 2. **Answer Relevancy** (0.0 - 1.0)
- **What it measures**: Does the response cover expected topics?
- **How it's calculated**: Coverage of predefined expected topics
- **Threshold**: ≥ 0.5 is passing
- **Why it matters**: Ensures comprehensive answers

### 3. **Groundedness** (0.0 - 1.0)
- **What it measures**: Is the response grounded in retrieved sources?
- **How it's calculated**: Presence of source citations
- **Threshold**: ≥ 0.5 is passing
- **Why it matters**: Prevents hallucination, ensures traceability

### 4. **Faithfulness** (0.0 - 1.0)
- **What it measures**: Does the response use appropriate hedging language?
- **How it's calculated**: Presence of cautious language ("may", "typically", etc.)
- **Threshold**: ≥ 0.4 is passing
- **Why it matters**: Indicates appropriate uncertainty expression

### 5. **Hallucination Detection** (0.0 - 1.0)
- **What it measures**: Does the response contain absolute/unverified claims?
- **How it's calculated**: Detection of absolute language ("always", "never", "100%")
- **Threshold**: ≥ 0.5 is passing
- **Why it matters**: Critical for clinical safety

### 6. **Response Quality** (0.0 - 1.0)
- **What it measures**: Overall response quality (length, structure, tone)
- **How it's calculated**: Word count, formatting, disclaimers
- **Threshold**: ≥ 0.5 is passing
- **Why it matters**: Ensures professional, useful responses

### 7. **Latency** (milliseconds)
- **What it measures**: Response time
- **Target**: < 5000ms
- **Why it matters**: User experience

---

## Quick Start

### Prerequisites

1. Ensure backend is running:
```bash
cd /home/jeswin/Downloads/RAG_Chatbot/ClinicalMind
python3 -m uvicorn backend.app.main:app --port 8000
```

2. Ensure frontend is running (optional):
```bash
cd frontend
npm run dev
```

### Run Quick Tests

```bash
# Run all quick tests
python3 tests/test_quick.py

# Run evaluation metrics only
python3 tests/test_quick.py --eval

# Test a specific query
python3 tests/test_quick.py --query "What is Metformin?"
```

### Run Comprehensive Evaluation

```bash
# Run full evaluation suite (5 test queries)
python3 tests/test_evaluation.py
```

### Run LLM-Based Evaluation (Requires Groq API)

```bash
# Set your Groq API key
export GROQ_API_KEY="your-api-key-here"

# Run LLM-based evaluation
python3 tests/test_llm_evaluation.py
```

---

## Output Examples

### Quick Test Output

```
============================================================
ClinicalMind Quick Test Suite
============================================================

📡 Testing backend health... ✅ OK
📊 Testing system status... ✅ OK
   Guidelines: 5010 docs
   Drugs: 438 docs
   Patients: 42 docs

💬 Testing query: 'What is Metformin used for?...'
   ✅ Response received (2518ms)
   Safety Level: LOW
   Sources: 2
   Response length: 456 chars

   Quick Quality Checks:
   ✅ Response not empty
   ✅ Has 2 sources
   ✅ Includes disclaimer
   ✅ Good latency (2518ms)

============================================================
TEST SUMMARY
============================================================
✅ PASS - Health Check
✅ PASS - System Status
✅ PASS - Sample Query

Total: 3/3 tests passed
============================================================
```

### Evaluation Report Output

```
============================================================
EVALUATION REPORT
============================================================

📊 SUMMARY
   Total Queries: 5
   Average Score: 0.62/1.00
   Pass Rate: 60.0%
   Avg Latency: 2341ms

📈 METRICS BREAKDOWN
   ✅ Context Relevancy
      Mean: 0.80 | Median: 0.80 | Pass Rate: 100.0%
   ⚠️ Answer Relevancy
      Mean: 0.45 | Median: 0.45 | Pass Rate: 40.0%
   ✅ Groundedness
      Mean: 0.70 | Median: 0.70 | Pass Rate: 80.0%
   ❌ Faithfulness
      Mean: 0.30 | Median: 0.30 | Pass Rate: 20.0%
   ✅ Hallucination Detection
      Mean: 0.75 | Median: 0.75 | Pass Rate: 80.0%
   ✅ Response Quality
      Mean: 0.82 | Median: 0.82 | Pass Rate: 100.0%
```

---

## Interpreting Results

### Score Ranges

| Score | Rating | Action |
|-------|--------|--------|
| 0.8 - 1.0 | Excellent | No action needed |
| 0.6 - 0.8 | Good | Minor improvements optional |
| 0.4 - 0.6 | Needs Improvement | Investigate and improve |
| 0.0 - 0.4 | Poor | Immediate attention required |

### Common Issues & Fixes

#### Low Context Relevancy
**Problem**: Response doesn't match query
**Fix**: Improve retrieval quality, check embedding model

#### Low Answer Relevancy
**Problem**: Missing expected topics
**Fix**: Add more comprehensive test topics, improve retrieval

#### Low Groundedness
**Problem**: No source citations
**Fix**: Ensure vector stores have documents, check retrieval threshold

#### Low Faithfulness
**Problem**: Too many absolute claims
**Fix**: Improve system prompt to use hedging language

#### High Latency
**Problem**: Slow responses (>5s)
**Fix**: Enable caching, optimize retrieval, use faster embedding model

---

## Adding Custom Test Queries

Edit `tests/test_evaluation.py` and add to `CLINICAL_TEST_QUERIES`:

```python
TestQuery(
    query="Your custom query here?",
    expected_topics=["topic1", "topic2", "topic3"],
    min_sources=1,
    category="guideline"  # or "drug", "patient", "general"
)
```

---

## CI/CD Integration

### GitHub Actions Example

```yaml
# .github/workflows/evaluation.yml
name: RAG Evaluation

on: [push, pull_request]

jobs:
  evaluate:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.10'
    
    - name: Install dependencies
      run: pip install -r requirements.txt
    
    - name: Start backend
      run: |
        python -m uvicorn backend.app.main:app --port 8000 &
        sleep 10
    
    - name: Run evaluation
      run: python tests/test_evaluation.py
    
    - name: Upload results
      uses: actions/upload-artifact@v3
      with:
        name: evaluation-report
        path: evaluation_report.json
```

---

## Troubleshooting

### Backend Returns 500 Error

**Check Groq API Key**:
```bash
echo $GROQ_API_KEY
# Should show your key
```

**Check Vector Stores**:
```bash
curl http://localhost:8000/status
# Should show document counts
```

### Tests Timeout

**Increase timeout in test script**:
```python
response = requests.post(..., timeout=120)  # Increase from 60
```

### Low Scores Across All Metrics

**Possible causes**:
1. Empty vector stores - upload documents
2. Invalid API key - check Groq credentials
3. Network issues - check connectivity

---

## Best Practices

1. **Run evaluation regularly**: After each major change
2. **Track metrics over time**: Save reports for comparison
3. **Set baseline scores**: Know what "good" looks like
4. **Test edge cases**: Add difficult queries to test suite
5. **Use LLM evaluation**: For more nuanced assessment

---

## Contact & Support

For issues or questions about the evaluation system, refer to:
- IMPLEMENTATION.md - System architecture
- README.md - Setup instructions
- tests/ - Test source code
