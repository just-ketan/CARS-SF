#!/usr/bin/env python3
"""
Reproducible batch experiment runner for thesis artifacts.

Runs allocation experiments across all scenarios and generates results.
"""

import csv
import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import load_scenarios, ensure_output_dirs, RESULTS_DIR
from slicing.allocation_engine import AllocationEngine
from slicing.context_engine import ContextEngine
from traffic_models.demand_generator import DemandGenerator


def run_allocation_experiments(total_bandwidth: float = 100.0) -> str:
    ensure_output_dirs()
    context_engine = ContextEngine()
    allocation_engine = AllocationEngine()
    demand_generator = DemandGenerator()

    results = []
    for scenario in load_scenarios():
        sid = scenario["id"]
        priorities = scenario.get("priority_weights") or context_engine.get_context(sid)
        demands = scenario.get("demand_mbps") or demand_generator.get_demands(sid)
        allocation = allocation_engine.allocate(total_bandwidth, priorities, demands)

        for service in allocation:
            results.append({
                "scenario": sid,
                "scenario_name": scenario["name"],
                "service": service,
                "demand_mbps": demands.get(service, 0),
                "allocation_mbps": allocation[service],
                "priority_weight": priorities.get(service, 0),
                "timestamp": datetime.now().isoformat(),
            })

    output_path = str(RESULTS_DIR / "allocation_results.csv")
    with open(output_path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)

    summary_path = str(RESULTS_DIR / "experiment_summary.json")
    with open(summary_path, "w", encoding="utf-8") as handle:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "scenarios_tested": len(load_scenarios()),
            "total_bandwidth_mbps": total_bandwidth,
            "output_csv": output_path,
        }, handle, indent=2)

    print(f"Results: {output_path}")
    print(f"Summary: {summary_path}")
    return output_path


if __name__ == "__main__":
    run_allocation_experiments()
