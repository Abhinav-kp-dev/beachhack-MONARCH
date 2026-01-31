"""
Demo script for Graph-Driven Customer Memory System

This script demonstrates the deterministic, graph-based profile update pipeline.
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.graph_engine import graph_engine, StateTransition
from app.services.customer import customer_service
from app.services.ai_service import ai_service
from datetime import datetime
import json


def print_section(title):
    """Print a section header"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")


def print_transitions(decisions):
    """Pretty print transition decisions"""
    if not decisions:
        print("  No transitions")
        return
    
    for i, decision in enumerate(decisions, 1):
        print(f"  {i}. {decision.field}")
        print(f"     Action: {decision.action.value}")
        print(f"     Old Value: {decision.old_value}")
        print(f"     New Value: {decision.new_value}")
        print(f"     Confidence: {decision.confidence:.2f}")
        print(f"     Reason: {decision.reason}")
        print()


async def demo_graph_engine():
    """Demonstrate the graph engine in action"""
    
    print_section("GRAPH ENGINE DEMO: Deterministic Customer Memory System")
    
    # ===== SCENARIO 1: First Interaction =====
    print_section("Scenario 1: First Interaction (New Customer)")
    
    print("Current State: Empty (new customer)")
    current_state = {}
    
    print("\nLLM Proposals:")
    llm_proposals = {
        "intent": {"value": "support_request", "confidence": 0.95},
        "entities": {
            "budget": {"value": "30000", "confidence": 0.85}
        },
        "topics": {
            "billing": {"value": "billing", "confidence": 0.82}
        }
    }
    print(json.dumps(llm_proposals, indent=2))
    
    print("\nGraph Engine Evaluation:")
    decisions = await graph_engine.evaluate_transitions(current_state, llm_proposals)
    print_transitions(decisions)
    
    # Calculate final state
    final_state = graph_engine.get_final_state(current_state, decisions)
    print("Final State:")
    print(json.dumps(final_state, indent=2, default=str))
    
    # ===== SCENARIO 2: Preference Update =====
    print_section("Scenario 2: Preference Update (Budget Change)")
    
    print("Current State:")
    current_state = {
        "context": {
            "intent": {"value": "support_request", "confidence": 0.95, "confirmed": True},
            "entities": {
                "budget": {"value": "30000", "confidence": 0.85, "confirmed": True}
            }
        }
    }
    print(json.dumps(current_state, indent=2))
    
    print("\nLLM Proposals (Budget changed to 50000):")
    llm_proposals = {
        "intent": {"value": "support_request", "confidence": 0.92},
        "entities": {
            "budget": {"value": "50000", "confidence": 0.88}
        }
    }
    print(json.dumps(llm_proposals, indent=2))
    
    print("\nGraph Engine Evaluation:")
    decisions = await graph_engine.evaluate_transitions(
        current_state.get("context", {}),
        llm_proposals
    )
    print_transitions(decisions)
    
    # ===== SCENARIO 3: Repeated Information =====
    print_section("Scenario 3: Repeated Information (No Change)")
    
    print("Current State:")
    current_state = {
        "context": {
            "intent": {"value": "support_request", "confidence": 0.95, "confirmed": True}
        }
    }
    print(json.dumps(current_state, indent=2))
    
    print("\nLLM Proposals (Same intent):")
    llm_proposals = {
        "intent": {"value": "support_request", "confidence": 0.90}
    }
    print(json.dumps(llm_proposals, indent=2))
    
    print("\nGraph Engine Evaluation:")
    decisions = await graph_engine.evaluate_transitions(
        current_state.get("context", {}),
        llm_proposals
    )
    print_transitions(decisions)
    
    # ===== SCENARIO 4: Confidence Thresholds =====
    print_section("Scenario 4: Confidence Thresholds")
    
    print("Testing different confidence levels:\n")
    
    test_cases = [
        ("HIGH (0.85)", {"value": "test_high", "confidence": 0.85}),
        ("MEDIUM (0.65)", {"value": "test_medium", "confidence": 0.65}),
        ("LOW (0.45)", {"value": "test_low", "confidence": 0.45})
    ]
    
    for label, entity_data in test_cases:
        print(f"{label}:")
        llm_proposals = {
            "entities": {
                "test_entity": entity_data
            }
        }
        
        decisions = await graph_engine.evaluate_transitions({}, llm_proposals)
        entity_decision = next(d for d in decisions if "test_entity" in d.field)
        print(f"  Action: {entity_decision.action.value}")
        print(f"  Reason: {entity_decision.reason}\n")
    
    # ===== SCENARIO 5: Determinism Test =====
    print_section("Scenario 5: Determinism Test")
    
    print("Running same evaluation 3 times to verify determinism...\n")
    
    current_state = {
        "context": {
            "intent": {"value": "support_request", "confidence": 0.90}
        }
    }
    
    llm_proposals = {
        "intent": {"value": "purchase_inquiry", "confidence": 0.92},
        "entities": {
            "budget": {"value": "50000", "confidence": 0.85}
        }
    }
    
    results = []
    for i in range(3):
        decisions = await graph_engine.evaluate_transitions(
            current_state.get("context", {}),
            llm_proposals
        )
        results.append([(d.field, d.action.value, d.new_value) for d in decisions])
    
    if results[0] == results[1] == results[2]:
        print("✅ DETERMINISM VERIFIED: All 3 runs produced identical results")
        print(f"\nTransitions:")
        for field, action, value in results[0]:
            print(f"  - {field}: {action} → {value}")
    else:
        print("❌ DETERMINISM FAILED: Results differ between runs")
    
    print_section("Demo Complete")
    print("The graph engine ensures:")
    print("  ✓ LLM only proposes facts")
    print("  ✓ Backend makes all truth decisions")
    print("  ✓ All transitions are deterministic")
    print("  ✓ Historical data is preserved")
    print("  ✓ Every decision is explainable")
    print()


if __name__ == "__main__":
    asyncio.run(demo_graph_engine())
