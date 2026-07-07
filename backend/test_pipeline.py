"""
Quick standalone smoke test for the full pipeline, using the real Claude API.
Run this after setting ANTHROPIC_API_KEY to confirm everything works before
starting the server.

Usage:
    export ANTHROPIC_API_KEY=sk-ant-...
    python3 test_pipeline.py
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from data.seed_fragments import generate_fragments
from engine import run_full_analysis


def main():
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERROR: set ANTHROPIC_API_KEY first.")
        sys.exit(1)

    fragments = generate_fragments()
    print(f"Loaded {len(fragments)} synthetic fragments. Running full analysis "
          f"(this makes real API calls and may take ~20-40 seconds)...\n")

    result = run_full_analysis(fragments)

    print(f"Analyzed {result['total_fragments_analyzed']} fragments, "
          f"filtered {result['noise_filtered_count']} as noise.\n")
    print(f"Found {len(result['actionable_clusters'])} actionable signal clusters:\n")

    for c in result["actionable_clusters"]:
        print(f"[{c.get('severity', '?').upper()}] {c['category']}  "
              f"({c['total_fragments']} fragments, {c['trend_pct_vs_last_week']:+.0f}% vs last week)")
        print(f"  -> {c.get('headline', 'NO HEADLINE GENERATED')}")
        print(f"  -> Suggested action: {c.get('suggested_action', 'N/A')}\n")

    with open("test_output.json", "w") as f:
        json.dump(result, f, indent=2)
    print("Full output written to test_output.json")


if __name__ == "__main__":
    main()
