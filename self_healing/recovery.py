"""
Recovery planning and automatic network restoration.
"""

from __future__ import annotations

from typing import Any

from slicing.allocation_engine import AllocationEngine
from slicing.context_engine import ContextEngine


class RecoveryPlanner:
    """Plans and executes recovery actions after failure detection."""

    RECOVERY_ACTIONS = {
        "congestion": "boost_priority",
        "link_saturation": "throttle_general",
        "fiber_cut": "reroute_and_protect",
    }

    def __init__(self, total_bandwidth: float = 100.0):
        self.total_bandwidth = total_bandwidth
        self.context_engine = ContextEngine()
        self.allocation_engine = AllocationEngine()
        self.recovery_log: list[dict[str, Any]] = []

    def plan_recovery(self, failure: dict[str, Any]) -> dict[str, Any]:
        failure_type = failure.get("type", "unknown")
        action = self.RECOVERY_ACTIONS.get(failure_type, "boost_priority")

        plan = {
            "failure": failure,
            "action": action,
            "new_allocation": None,
            "reroute": False,
        }

        if action == "boost_priority":
            plan["new_allocation"] = self._boost_healthcare()

        elif action == "throttle_general":
            plan["new_allocation"] = self._throttle_general()

        elif action == "reroute_and_protect":
            plan["new_allocation"] = self._disaster_allocation()
            plan["reroute"] = True

        self.recovery_log.append(plan)
        return plan

    def execute_recovery(
        self,
        plan: dict[str, Any],
        qos_enforcer=None,
        net=None,
    ) -> bool:
        allocation = plan.get("new_allocation")
        if allocation is None:
            return False

        if qos_enforcer is not None:
            qos_enforcer.apply_allocation(allocation)

        if plan.get("reroute") and net is not None:
            self._reroute_traffic(net)

        return True

    def _boost_healthcare(self) -> dict[str, float]:
        priorities = {"healthcare": 15, "education": 3, "agriculture": 2, "general": 1}
        demands = {"healthcare": 50, "education": 20, "agriculture": 10, "general": 10}
        return self.allocation_engine.allocate(self.total_bandwidth, priorities, demands)

    def _throttle_general(self) -> dict[str, float]:
        priorities = {"healthcare": 10, "education": 5, "agriculture": 3, "general": 1}
        demands = {"healthcare": 40, "education": 30, "agriculture": 20, "general": 5}
        return self.allocation_engine.allocate(self.total_bandwidth, priorities, demands)

    def _disaster_allocation(self) -> dict[str, float]:
        return self.allocation_engine.allocate(
            self.total_bandwidth,
            self.context_engine.get_context("disaster"),
            {"healthcare": 90, "education": 5, "agriculture": 5, "general": 10},
        )

    def _reroute_traffic(self, net):
        try:
            switch = net.get("s_edge")
            switch.cmd("ip link set s_edge-eth2 up 2>/dev/null")
        except Exception:
            pass

    def get_recovery_log(self) -> list[dict[str, Any]]:
        return list(self.recovery_log)
