#!/usr/bin/env python3
"""Standalone smoke test of the full pipeline."""
import json
import sys
from data.seed_tickets import generate_tickets
from engine import run_pipeline


def main():
    print("Generating synthetic tickets...")
    tickets = generate_tickets(seed=42, count=85)
    print(f"Generated {len(tickets)} tickets\n")
    
    print("Running pipeline...")
    result = run_pipeline(tickets)
    
    print("\n" + "=" * 60)
    print("PIPELINE RESULTS")
    print("=" * 60)
    
    print(f"\nTotal tickets: {len(result['tickets'])}")
    print(f"Categories found: {len(result['trends'])}")
    print(f"Signals generated: {len(result['signals'])}\n")
    
    print("TOP SIGNALS:")
    for i, signal in enumerate(result["signals"][:5], 1):
        print(f"\n{i}. {signal['headline']}")
        print(f"   Category: {signal['category']}")
        print(f"   Count: {signal['count']} | Trend: {signal['trend']} | Severity: {signal['severity']}")
        print(f"   Action: {signal['action']}")
    
    # Write full output
    with open("test_output.json", "w") as f:
        json.dump(result, f, indent=2, default=str)
    print("\n\nFull output written to test_output.json")


if __name__ == "__main__":
    main()

