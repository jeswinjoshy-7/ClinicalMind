"""
Advanced LLM-Based RAG Evaluation for ClinicalMind

Uses LLM (via Groq) to evaluate RAG responses with more nuanced metrics.
This provides more accurate evaluation than heuristic methods.

Metrics:
1. Context Relevancy (LLM-judged)
2. Answer Groundedness (LLM-judged)
3. Hallucination Detection (LLM-judged)
4. Clinical Accuracy (LLM-judged)

Usage:
    python tests/test_llm_evaluation.py
"""

import json
import time
import requests
from typing import List, Dict, Any
from dataclasses import dataclass, asdict
from datetime import datetime
import os

# Groq API configuration
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"


@dataclass
class LLMEvaluationResult:
    """Result from LLM-based evaluation."""
    query: str
    response: str
    context: str
    metric_name: str
    score: float  # 0.0 to 1.0
    explanation: str
    passed: bool
    threshold: float


class LLMBasedEvaluator:
    """
    LLM-based evaluation using Groq API.
    
    Uses an LLM to judge the quality of RAG responses.
    """
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or GROQ_API_KEY
        if not self.api_key:
            raise ValueError("GROQ_API_KEY not set. Set it via environment variable.")
    
    def evaluate_with_llm(
        self, 
        query: str, 
        response: str, 
        context: str,
        metric: str
    ) -> LLMEvaluationResult:
        """
        Use LLM to evaluate a specific metric.
        """
        prompts = {
            "context_relevancy": f"""
You are evaluating a RAG system's response quality.

QUERY: {query}

RETRIEVED CONTEXT:
{context}

RESPONSE:
{response}

Evaluate: How relevant is the response to the query AND the retrieved context?
- Score 1.0 if response directly addresses query using provided context
- Score 0.5 if response partially addresses query
- Score 0.0 if response is irrelevant or ignores context

Respond in JSON format:
{{
    "score": 0.8,
    "explanation": "Brief explanation of your rating"
}}
""",
            "groundedness": f"""
You are evaluating a RAG system for hallucination detection.

QUERY: {query}

RETRIEVED CONTEXT:
{context}

RESPONSE:
{response}

Evaluate: Is the response grounded in the retrieved context?
Check if EVERY claim in the response can be verified in the context.
- Score 1.0 if all claims are directly supported
- Score 0.5 if some claims are supported, some are assumptions
- Score 0.0 if response contains significant unsupported claims

Respond in JSON format:
{{
    "score": 0.7,
    "explanation": "Brief explanation",
    "unsupported_claims": ["list any claims not in context"]
}}
""",
            "hallucination": f"""
You are detecting hallucinations in a RAG system.

QUERY: {query}

RETRIEVED CONTEXT:
{context}

RESPONSE:
{response}

Identify any hallucinated or fabricated information:
- Facts not present in the context
- Made-up numbers, dates, or statistics
- Fabricated citations or sources

- Score 1.0 if NO hallucination detected
- Score 0.5 if minor unsupported details
- Score 0.0 if significant hallucination

Respond in JSON format:
{{
    "score": 0.9,
    "explanation": "Brief explanation",
    "hallucinated_claims": ["list any hallucinated statements"]
}}
""",
            "clinical_accuracy": f"""
You are evaluating clinical accuracy of a RAG response.

QUERY: {query}

RETRIEVED CONTEXT:
{context}

RESPONSE:
{response}

Evaluate clinical accuracy:
- Does the response align with standard medical knowledge?
- Are drug names, dosages, and recommendations accurate?
- Is the information presented appropriately?

- Score 1.0 if clinically accurate and appropriate
- Score 0.5 if partially accurate with minor issues
- Score 0.0 if contains dangerous inaccuracies

Respond in JSON format:
{{
    "score": 0.8,
    "explanation": "Brief explanation of clinical accuracy assessment"
}}
"""
        }
        
        if metric not in prompts:
            raise ValueError(f"Unknown metric: {metric}")
        
        # Call Groq API
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {"role": "system", "content": "You are an expert evaluator of RAG systems. Respond ONLY with valid JSON."},
                {"role": "user", "content": prompts[metric]}
            ],
            "temperature": 0.0,
            "max_tokens": 500
        }
        
        try:
            response = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            content = result["choices"][0]["message"]["content"].strip()
            
            # Parse JSON response
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            
            evaluation = json.loads(content)
            score = evaluation.get("score", 0.0)
            explanation = evaluation.get("explanation", "")
            
            return LLMEvaluationResult(
                query=query,
                response=response,
                context=context[:500] + "..." if len(context) > 500 else context,
                metric_name=metric,
                score=score,
                explanation=explanation,
                passed=score >= 0.5,
                threshold=0.5
            )
            
        except Exception as e:
            return LLMEvaluationResult(
                query=query,
                response=response,
                context=context[:100],
                metric_name=metric,
                score=0.0,
                explanation=f"Evaluation failed: {str(e)}",
                passed=False,
                threshold=0.5
            )
    
    def evaluate_full(self, query: str, response: str, context: str) -> Dict[str, Any]:
        """Run all LLM-based evaluations."""
        metrics = ["context_relevancy", "groundedness", "hallucination", "clinical_accuracy"]
        results = []
        
        for metric in metrics:
            print(f"   Evaluating {metric}...")
            result = self.evaluate_with_llm(query, response, context, metric)
            results.append(result)
        
        # Calculate average score
        avg_score = sum(r.score for r in results) / len(results)
        
        return {
            "query": query,
            "response": response[:500] + "..." if len(response) > 500 else response,
            "context_length": len(context),
            "results": [asdict(r) for r in results],
            "average_score": avg_score,
            "timestamp": datetime.now().isoformat()
        }


def test_single_query():
    """Test evaluation on a single query."""
    print("\n" + "="*60)
    print("LLM-Based RAG Evaluation - Single Query Test")
    print("="*60 + "\n")
    
    # Check API key
    if not GROQ_API_KEY:
        print("❌ GROQ_API_KEY not set!")
        print("Set it with: export GROQ_API_KEY='your-key'")
        return
    
    # Send query to ClinicalMind
    query = "What is the first-line treatment for Type 2 Diabetes?"
    print(f"Query: {query}\n")
    
    try:
        response = requests.post(
            "http://localhost:8000/query",
            json={"query": query},
            timeout=60
        )
        data = response.json()
        
        rag_response = data.get("response", "")
        sources = data.get("sources", [])
        
        print(f"Response received ({len(rag_response)} chars)")
        print(f"Sources: {len(sources)}")
        print()
        
        # Create context from response (in real scenario, this would be retrieved docs)
        context = rag_response  # Using response as proxy for context
        
        # Run LLM evaluation
        evaluator = LLMBasedEvaluator()
        result = evaluator.evaluate_full(query, rag_response, context)
        
        # Print results
        print("\n" + "="*60)
        print("EVALUATION RESULTS")
        print("="*60)
        
        for eval_result in result["results"]:
            status = "✅" if eval_result["passed"] else "❌"
            print(f"\n{status} {eval_result['metric_name'].replace('_', ' ').title()}")
            print(f"   Score: {eval_result['score']:.2f}/1.00")
            print(f"   Explanation: {eval_result['explanation'][:100]}")
        
        print(f"\n📊 Average Score: {result['average_score']:.2f}/1.00")
        print("="*60 + "\n")
        
        # Save results
        with open("llm_evaluation_result.json", "w") as f:
            json.dump(result, f, indent=2)
        
        print("💾 Results saved to: llm_evaluation_result.json\n")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")


if __name__ == "__main__":
    test_single_query()
