#!/usr/bin/env python3
"""
Quick Test Script for ClinicalMind RAG System

Run quick tests to verify the system is working correctly.

Usage:
    python tests/test_quick.py              # Run all quick tests
    python tests/test_quick.py --query "..."  # Test specific query
"""

import json
import time
import requests
import sys
from datetime import datetime


BACKEND_URL = "http://localhost:8000"


def test_health():
    """Test backend health endpoint."""
    print("📡 Testing backend health...", end=" ")
    try:
        response = requests.get(f"{BACKEND_URL}/health", timeout=5)
        if response.status_code == 200:
            print("✅ OK")
            return True
        else:
            print(f"❌ Status: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_status():
    """Test system status endpoint."""
    print("📊 Testing system status...", end=" ")
    try:
        response = requests.get(f"{BACKEND_URL}/status", timeout=10)
        if response.status_code == 200:
            data = response.json()
            db = data.get("database", {})
            print("✅ OK")
            print(f"   Guidelines: {db.get('guidelines', {}).get('document_count', 0)} docs")
            print(f"   Drugs: {db.get('drugs', {}).get('document_count', 0)} docs")
            print(f"   Patients: {db.get('patients', {}).get('document_count', 0)} docs")
            return True
        else:
            print(f"❌ Status: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_query(query: str = "What is Metformin used for?"):
    """Test a clinical query."""
    print(f"\n💬 Testing query: '{query[:50]}...'")
    try:
        start = time.time()
        response = requests.post(
            f"{BACKEND_URL}/query",
            json={"query": query},
            timeout=60
        )
        latency = (time.time() - start) * 1000
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Response received ({latency:.0f}ms)")
            print(f"   Safety Level: {data.get('safety_level', 'UNKNOWN')}")
            print(f"   Sources: {len(data.get('sources', []))}")
            print(f"   Response length: {len(data.get('response', ''))} chars")
            
            # Quick quality checks
            checks = []
            
            # Check 1: Response not empty
            if data.get('response'):
                checks.append("✅ Response not empty")
            else:
                checks.append("❌ Empty response")
            
            # Check 2: Has sources
            if data.get('sources'):
                checks.append(f"✅ Has {len(data['sources'])} sources")
            else:
                checks.append("⚠️ No sources cited")
            
            # Check 3: Has disclaimer
            if 'disclaimer' in data.get('response', '').lower():
                checks.append("✅ Includes disclaimer")
            else:
                checks.append("⚠️ No disclaimer")
            
            # Check 4: Reasonable latency
            if latency < 5000:
                checks.append(f"✅ Good latency ({latency:.0f}ms)")
            else:
                checks.append(f"⚠️ High latency ({latency:.0f}ms)")
            
            print("\n   Quick Quality Checks:")
            for check in checks:
                print(f"   {check}")
            
            return True
        else:
            print(f"   ❌ Status: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False


def test_evaluation_metrics():
    """Run comprehensive evaluation on test queries."""
    print("\n" + "="*60)
    print("Running Evaluation Metrics Test")
    print("="*60)
    
    test_queries = [
        "What is the first-line treatment for Type 2 Diabetes?",
        "What are the side effects of Metformin?",
        "How do you diagnose hypertension?",
    ]
    
    results = []
    
    for query in test_queries:
        print(f"\n📝 Query: {query[:50]}...")
        try:
            start = time.time()
            response = requests.post(
                f"{BACKEND_URL}/query",
                json={"query": query},
                timeout=60
            )
            latency = (time.time() - start) * 1000
            
            if response.status_code == 200:
                data = response.json()
                
                # Calculate simple metrics
                response_text = data.get('response', '')
                sources = data.get('sources', [])
                
                # Metric 1: Response Quality (length-based)
                word_count = len(response_text.split())
                quality_score = min(1.0, word_count / 100)  # Target 100+ words
                
                # Metric 2: Source Citation
                source_score = min(1.0, len(sources) / 2)  # Target 2+ sources
                
                # Metric 3: Safety Check
                safety_score = 1.0 if data.get('safety_level') in ['LOW', 'MEDIUM'] else 0.5
                
                # Metric 4: Latency
                latency_score = max(0.0, 1.0 - (latency / 10000))  # Penalize >10s
                
                # Overall score
                overall = (quality_score + source_score + safety_score + latency_score) / 4
                
                result = {
                    "query": query,
                    "overall_score": overall,
                    "quality_score": quality_score,
                    "source_score": source_score,
                    "safety_score": safety_score,
                    "latency_score": latency_score,
                    "latency_ms": latency,
                    "safety_level": data.get('safety_level'),
                    "sources_count": len(sources)
                }
                results.append(result)
                
                print(f"   Overall Score: {overall:.2f}/1.00")
                print(f"   - Quality: {quality_score:.2f} ({word_count} words)")
                print(f"   - Sources: {source_score:.2f} ({len(sources)} sources)")
                print(f"   - Safety: {safety_score:.2f} ({data.get('safety_level')})")
                print(f"   - Latency: {latency_score:.2f} ({latency:.0f}ms)")
                
            else:
                print(f"   ❌ Request failed: {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    # Summary
    if results:
        avg_score = sum(r['overall_score'] for r in results) / len(results)
        print("\n" + "="*60)
        print(f"SUMMARY: Average Score {avg_score:.2f}/1.00 ({len(results)} queries)")
        print("="*60)
    
    return results


def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("ClinicalMind Quick Test Suite")
    print(f"Backend: {BACKEND_URL}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60 + "\n")
    
    # Check for custom query
    if len(sys.argv) > 1 and sys.argv[1] == "--query":
        if len(sys.argv) > 2:
            test_query(sys.argv[2])
        else:
            print("❌ Please provide a query after --query")
        return
    
    if len(sys.argv) > 1 and sys.argv[1] == "--eval":
        test_evaluation_metrics()
        return
    
    # Run all tests
    tests = [
        ("Health Check", test_health),
        ("System Status", test_status),
        ("Sample Query", lambda: test_query()),
    ]
    
    results = []
    for name, test_func in tests:
        result = test_func()
        results.append((name, result))
        time.sleep(0.5)
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    print("="*60 + "\n")
    
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
