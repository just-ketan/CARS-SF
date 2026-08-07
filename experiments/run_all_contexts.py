import csv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from slicing.context_engine import ContextEngine
from slicing.allocation_engine import AllocationEngine
from traffic_models.demand_generator import DemandGenerator


TOTAL_BANDWIDTH = 100

contexts = [
    "normal",
    "school",
    "harvest",
    "disaster"
]

context_engine = ContextEngine()
allocation_engine = AllocationEngine()
demand_generator = DemandGenerator()

results = []

for context in contexts:

    priorities = context_engine.get_context(
        context
    )

    demands = demand_generator.get_demands(
        context
    )

    allocation = allocation_engine.allocate(
        TOTAL_BANDWIDTH,
        priorities,
        demands
    )

    for service in allocation:

        results.append({
            "context": context,
            "service": service,
            "demand": demands[service],
            "allocation": allocation[service]
        })

with open(
    "results/allocation_results.csv",
    "w",
    newline=""
) as file:

    writer = csv.DictWriter(
        file,
        fieldnames=[
            "context",
            "service",
            "demand",
            "allocation"
        ]
    )

    writer.writeheader()
    writer.writerows(results)

print(
    "Results written to "
    "results/allocation_results.csv"
)
