from slicing.context_engine import ContextEngine
from slicing.priority_engine import PriorityEngine
from slicing.allocation_engine import AllocationEngine
from slicing.qos_enforcer import QoSEnforcer
from traffic.demand_generator import DemandGenerator


TOTAL_BANDWIDTH = 100

context = "disaster"

context_engine = ContextEngine()
priority_engine = PriorityEngine()
allocation_engine = AllocationEngine()
demand_generator = DemandGenerator()
qos = QoSEnforcer()

weights = context_engine.get_context(
    context
)

demands = demand_generator.get_demands(
    context
)

priority_engine.set_weights(
    weights
)

allocation = allocation_engine.allocate(
    TOTAL_BANDWIDTH,
    weights,
    demands
)

qos.apply_allocation(allocation)

print()
print("Context:", context.upper())
print()

print("Demands")
print("-------")

for k, v in demands.items():
    print(f"{k:12s}: {v} Mbps")

print()

print("Allocation")
print("----------")

for k, v in allocation.items():
    print(f"{k:12s}: {v} Mbps")
