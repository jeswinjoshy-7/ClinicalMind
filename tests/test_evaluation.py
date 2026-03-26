"""
ClinicalMind RAG Evaluation Test Suite

This module provides comprehensive evaluation metrics for the RAG system:
1. Context Relevancy - How relevant is retrieved context to the query?
2. Answer Relevancy - How relevant is the answer to the query?
3. Groundedness - Is the answer grounded in retrieved context?
4. Faithfulness - Does the answer stay faithful to context?
5. Hallucination Detection - Does the answer contain unsupported claims?
6. Response Quality - Overall response quality assessment

Usage:
    python -m pytest tests/test_evaluation.py -v
    python tests/test_evaluation.py  # Run standalone
"""

import json
import time
import requests
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime
import statistics


# Configuration
BACKEND_URL = "http://localhost:8000"


class EvaluationMetric(Enum):
    """RAG evaluation metrics."""
    CONTEXT_RELEVANCY = "context_relevancy"
    ANSWER_RELEVANCY = "answer_relevancy"
    GROUNDEDNESS = "groundedness"
    FAITHFULNESS = "faithfulness"
    HALLUCINATION_DETECTION = "hallucination_detection"
    RESPONSE_QUALITY = "response_quality"
    LATENCY = "latency"
    SOURCE_CITATION = "source_citation"


@dataclass
class MetricResult:
    """Result of a single metric evaluation."""
    metric: str
    score: float  # 0.0 to 1.0
    max_score: float
    explanation: str
    passed: bool
    threshold: float


@dataclass
class QueryEvaluationResult:
    """Complete evaluation result for a single query."""
    query: str
    response: str
    safety_level: str
    sources: List[str]
    latency_ms: float
    metrics: List[MetricResult]
    overall_score: float
    timestamp: str


@dataclass
class TestQuery:
    """Test query with expected outcomes."""
    query: str
    expected_topics: List[str]  # Topics that should be covered
    min_sources: int = 1  # Minimum expected sources
    category: str = "general"  # drug, guideline, patient, general


# Test Dataset - Clinical Evaluation Queries
CLINICAL_TEST_QUERIES = [
    TestQuery(
        query="What is the first-line treatment for Type 2 Diabetes?",
        expected_topics=["metformin", "lifestyle", "diet", "exercise"],
        min_sources=1,
        category="guideline"
    ),
    TestQuery(
        query="What are the common side effects of Metformin?",
        expected_topics=["side effects", "nausea", "diarrhea", "lactic acidosis"],
        min_sources=1,
        category="drug"
    ),
    TestQuery(
        query="What is the dosage for Amoxicillin in adults?",
        expected_topics=["dosage", "mg", "frequency", "administration"],
        min_sources=1,
        category="drug"
    ),
    TestQuery(
        query="How do you manage hypertension in elderly patients?",
        expected_topics=["blood pressure", "treatment", "medication", "lifestyle"],
        min_sources=1,
        category="guideline"
    ),
    TestQuery(
        query="What are the contraindications for Warfarin?",
        expected_topics=["contraindications", "bleeding", "pregnancy", "interactions"],
        min_sources=1,
        category="drug"
    ),
]


class RAGEvaluator:
    """
    Comprehensive RAG evaluation system for ClinicalMind.
    
    Evaluates:
    1. Context Relevancy
    2. Answer Relevancy
    3. Groundedness
    4. Faithfulness
    5. Hallucination Detection
    6. Response Quality
    """
    
    def __init__(self, backend_url: str = BACKEND_URL):
        self.backend_url = backend_url
        self.results: List[QueryEvaluationResult] = []
    
    def send_query(self, query: str) -> Dict[str, Any]:
        """Send a query to the ClinicalMind backend."""
        start_time = time.time()
        
        try:
            response = requests.post(
                f"{self.backend_url}/query",
                json={"query": query},
                timeout=60
            )
            response.raise_for_status()
            
            latency_ms = (time.time() - start_time) * 1000
            data = response.json()
            
            return {
                "success": True,
                "response": data.get("response", ""),
                "safety_level": data.get("safety_level", "UNKNOWN"),
                "sources": data.get("sources", []),
                "latency_ms": latency_ms
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "latency_ms": (time.time() - start_time) * 1000
            }
    
    def evaluate_context_relevancy(self, query: str, response: str) -> MetricResult:
        """
        Evaluate if the response is relevant to the query.
        
        Heuristic: Check if query keywords appear in response.
        """
        query_words = set(query.lower().split())
        response_words = set(response.lower().split())
        
        # Remove common stop words
        stop_words = {"what", "is", "the", "are", "for", "in", "to", "a", "an", "and", "or"}
        query_words = query_words - stop_words
        
        if not query_words:
            return MetricResult(
                metric=EvaluationMetric.CONTEXT_RELEVANCY.value,
                score=0.0,
                max_score=1.0,
                explanation="No meaningful query words to evaluate",
                passed=False,
                threshold=0.5
            )
        
        # Calculate overlap
        overlap = query_words & response_words
        score = len(overlap) / len(query_words)
        
        return MetricResult(
            metric=EvaluationMetric.CONTEXT_RELEVANCY.value,
            score=score,
            max_score=1.0,
            explanation=f"Query-Reponse overlap: {len(overlap)}/{len(query_words)} keywords ({score:.1%})",
            passed=score >= 0.5,
            threshold=0.5
        )
    
    def evaluate_answer_relevancy(self, query: str, response: str, expected_topics: List[str]) -> MetricResult:
        """
        Evaluate if the response covers expected topics.
        """
        if not expected_topics:
            return MetricResult(
                metric=EvaluationMetric.ANSWER_RELEVANCY.value,
                score=1.0,
                max_score=1.0,
                explanation="No expected topics defined",
                passed=True,
                threshold=0.5
            )
        
        response_lower = response.lower()
        covered_topics = [
            topic for topic in expected_topics
            if topic.lower() in response_lower
        ]
        
        score = len(covered_topics) / len(expected_topics)
        
        return MetricResult(
            metric=EvaluationMetric.ANSWER_RELEVANCY.value,
            score=score,
            max_score=1.0,
            explanation=f"Covered {len(covered_topics)}/{len(expected_topics)} expected topics: {covered_topics}",
            passed=score >= 0.5,
            threshold=0.5
        )
    
    def evaluate_groundedness(self, response: str, sources: List[str]) -> MetricResult:
        """
        Evaluate if the response cites sources (groundedness proxy).
        """
        if not sources:
            return MetricResult(
                metric=EvaluationMetric.GROUNDEDNESS.value,
                score=0.0,
                max_score=1.0,
                explanation="No sources cited in response",
                passed=False,
                threshold=0.5
            )
        
        # Check for source citations in response
        has_citation_section = "source" in response.lower() or "reference" in response.lower()
        citation_score = 0.7 if has_citation_section else 0.3
        
        # Bonus for multiple sources
        source_bonus = min(0.3, len(sources) * 0.1)
        score = min(1.0, citation_score + source_bonus)
        
        return MetricResult(
            metric=EvaluationMetric.GROUNDEDNESS.value,
            score=score,
            max_score=1.0,
            explanation=f"Cited {len(sources)} sources. Response {'includes' if has_citation_section else 'lacks'} explicit citation section.",
            passed=score >= 0.5,
            threshold=0.5
        )
    
    def evaluate_faithfulness(self, response: str) -> MetricResult:
        """
        Evaluate if response contains hedging language (indicates faithfulness).
        
        Faithful responses typically use cautious language when uncertain.
        """
        faithfulness_indicators = [
            "according to", "based on", "the guidelines state",
            "evidence suggests", "studies show", "recommended",
            "may", "might", "could", "typically", "generally"
        ]
        
        response_lower = response.lower()
        indicators_found = [
            indicator for indicator in faithfulness_indicators
            if indicator in response_lower
        ]
        
        score = min(1.0, len(indicators_found) / 5)  # Normalize to 5 indicators
        
        return MetricResult(
            metric=EvaluationMetric.FAITHFULNESS.value,
            score=score,
            max_score=1.0,
            explanation=f"Found {len(indicators_found)} faithfulness indicators: {indicators_found[:5]}",
            passed=score >= 0.4,
            threshold=0.4
        )
    
    def evaluate_hallucination(self, response: str, sources: List[str]) -> MetricResult:
        """
        Detect potential hallucinations.
        
        Hallucination indicators:
        - Very specific numbers without sources
        - Absolute claims without evidence
        - Made-up statistics
        """
        hallucination_patterns = [
            "100%", "always", "never", "definitely", "certainly",
            "proven to", "guaranteed", "without doubt"
        ]
        
        response_lower = response.lower()
        absolute_claims = sum(
            1 for pattern in hallucination_patterns
            if pattern in response_lower
        )
        
        # Penalize absolute claims, especially without sources
        penalty = absolute_claims * 0.2
        base_score = 1.0
        
        if not sources and absolute_claims > 0:
            penalty += 0.3
        
        score = max(0.0, base_score - penalty)
        
        return MetricResult(
            metric=EvaluationMetric.HALLUCINATION_DETECTION.value,
            score=score,
            max_score=1.0,
            explanation=f"Found {absolute_claims} absolute claims. {'No sources to verify claims.' if not sources else ''}",
            passed=score >= 0.5,
            threshold=0.5
        )
    
    def evaluate_response_quality(self, response: str, sources: List[str]) -> MetricResult:
        """
        Evaluate overall response quality.
        
        Quality indicators:
        - Response length (not too short, not too long)
        - Structured format (bullet points, sections)
        - Source citations
        - Professional tone
        """
        quality_score = 0.0
        
        # Length check (ideal: 100-1000 words)
        word_count = len(response.split())
        if 100 <= word_count <= 1000:
            quality_score += 0.3
        elif 50 <= word_count < 100 or 1000 < word_count <= 1500:
            quality_score += 0.15
        
        # Structure check
        if any(marker in response for marker in ["\n-", "\n•", "\n1.", "\n**", "###"]):
            quality_score += 0.3
        
        # Source citation
        if sources:
            quality_score += 0.2
        
        # Professional tone (check for disclaimer)
        if "disclaimer" in response.lower() or "consult" in response.lower():
            quality_score += 0.2
        
        return MetricResult(
            metric=EvaluationMetric.RESPONSE_QUALITY.value,
            score=quality_score,
            max_score=1.0,
            explanation=f"Quality score based on length ({word_count} words), structure, citations, and tone",
            passed=quality_score >= 0.5,
            threshold=0.5
        )
    
    def evaluate_query(self, test_query: TestQuery) -> QueryEvaluationResult:
        """Run full evaluation suite on a single query."""
        # Send query to backend
        result = self.send_query(test_query.query)
        
        if not result["success"]:
            return QueryEvaluationResult(
                query=test_query.query,
                response="",
                safety_level="ERROR",
                sources=[],
                latency_ms=result.get("latency_ms", 0),
                metrics=[],
                overall_score=0.0,
                timestamp=datetime.now().isoformat()
            )
        
        response = result["response"]
        sources = result["sources"]
        
        # Run all evaluations
        metrics = [
            self.evaluate_context_relevancy(test_query.query, response),
            self.evaluate_answer_relevancy(test_query.query, response, test_query.expected_topics),
            self.evaluate_groundedness(response, sources),
            self.evaluate_faithfulness(response),
            self.evaluate_hallucination(response, sources),
            self.evaluate_response_quality(response, sources),
        ]
        
        # Calculate overall score
        scores = [m.score for m in metrics]
        overall_score = statistics.mean(scores)
        
        return QueryEvaluationResult(
            query=test_query.query,
            response=response[:500] + "..." if len(response) > 500 else response,
            safety_level=result["safety_level"],
            sources=sources,
            latency_ms=result["latency_ms"],
            metrics=metrics,
            overall_score=overall_score,
            timestamp=datetime.now().isoformat()
        )
    
    def run_full_evaluation(self, test_queries: List[TestQuery] = None) -> Dict[str, Any]:
        """Run evaluation on all test queries."""
        if test_queries is None:
            test_queries = CLINICAL_TEST_QUERIES
        
        print(f"\n{'='*60}")
        print(f"ClinicalMind RAG Evaluation")
        print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}\n")
        
        results = []
        for i, test_query in enumerate(test_queries, 1):
            print(f"[{i}/{len(test_queries)}] Evaluating: {test_query.query[:60]}...")
            result = self.evaluate_query(test_query)
            results.append(result)
            
            # Print quick summary
            status = "✅ PASS" if result.overall_score >= 0.6 else "⚠️ NEEDS IMPROVEMENT"
            print(f"      Score: {result.overall_score:.2f} | Latency: {result.latency_ms:.0f}ms | {status}\n")
        
        self.results = results
        
        # Generate aggregate report
        return self.generate_report()
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate aggregate evaluation report."""
        if not self.results:
            return {"error": "No results to report"}
        
        # Calculate aggregate metrics
        metric_scores = {}
        for result in self.results:
            for metric in result.metrics:
                if metric.metric not in metric_scores:
                    metric_scores[metric.metric] = []
                metric_scores[metric.metric].append(metric.score)
        
        # Build report
        report = {
            "summary": {
                "total_queries": len(self.results),
                "average_overall_score": statistics.mean([r.overall_score for r in self.results]),
                "pass_rate": sum(1 for r in self.results if r.overall_score >= 0.6) / len(self.results),
                "average_latency_ms": statistics.mean([r.latency_ms for r in self.results]),
                "timestamp": datetime.now().isoformat()
            },
            "metrics": {},
            "results": [asdict(r) for r in self.results]
        }
        
        # Add per-metric statistics
        for metric_name, scores in metric_scores.items():
            report["metrics"][metric_name] = {
                "mean": statistics.mean(scores),
                "median": statistics.median(scores),
                "min": min(scores),
                "max": max(scores),
                "pass_rate": sum(1 for s in scores if s >= 0.5) / len(scores)
            }
        
        # Print detailed report
        self._print_report(report)
        
        return report
    
    def _print_report(self, report: Dict[str, Any]):
        """Print formatted evaluation report."""
        print("\n" + "="*60)
        print("EVALUATION REPORT")
        print("="*60)
        
        summary = report["summary"]
        print(f"\n📊 SUMMARY")
        print(f"   Total Queries: {summary['total_queries']}")
        print(f"   Average Score: {summary['average_overall_score']:.2f}/1.00")
        print(f"   Pass Rate: {summary['pass_rate']:.1%}")
        print(f"   Avg Latency: {summary['average_latency_ms']:.0f}ms")
        
        print(f"\n📈 METRICS BREAKDOWN")
        for metric_name, stats in report["metrics"].items():
            emoji = "✅" if stats["pass_rate"] >= 0.8 else "⚠️" if stats["pass_rate"] >= 0.5 else "❌"
            print(f"   {emoji} {metric_name.replace('_', ' ').title()}")
            print(f"      Mean: {stats['mean']:.2f} | Median: {stats['median']:.2f} | Pass Rate: {stats['pass_rate']:.1%}")
        
        print(f"\n📝 DETAILED RESULTS")
        for i, result in enumerate(self.results, 1):
            print(f"\n   Query {i}: {result.query[:50]}...")
            print(f"   Overall Score: {result.overall_score:.2f}")
            print(f"   Safety Level: {result.safety_level}")
            print(f"   Sources: {len(result.sources)}")
            print(f"   Latency: {result.latency_ms:.0f}ms")
            
            for metric in result.metrics:
                status = "✅" if metric.passed else "❌"
                print(f"   {status} {metric.metric}: {metric.score:.2f} - {metric.explanation[:60]}")
        
        print("\n" + "="*60)
        print("Evaluation Complete!")
        print("="*60 + "\n")


def main():
    """Run evaluation tests."""
    evaluator = RAGEvaluator()
    report = evaluator.run_full_evaluation()
    
    # Save report to file
    with open("evaluation_report.json", "w") as f:
        json.dump(report, f, indent=2)
    
    print(f"\n💾 Report saved to: evaluation_report.json")
    
    return report


if __name__ == "__main__":
    main()
