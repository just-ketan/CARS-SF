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
        "latency_spike": "boost_priority",
        "link_saturation": "throttle_general",
        "fiber_cut": "reroute_and_protect",
        "connectivity_loss": "reroute_and_protect",
    }
    # Ticks to wait before acting on the same failure type again, so a
    # persisting symptom does not re-trigger the same recovery every second.
    COOLDOWN_TICKS = 5

    def __init__(
        self,
        total_bandwidth: float = 100.0,
        backup_bandwidth: float = 50.0,
        context_id: str = "normal",
        demands: dict[str, float] | None = None,
    ):
        self.total_bandwidth = total_bandwidth
        self.backup_bandwidth = backup_bandwidth
        self.context_engine = ContextEngine()
        self.context_id = context_id
        self.demands = demands
        self.allocation_engine = AllocationEngine()
        self.recovery_log: list[dict[str, Any]] = []
        self.backup_active = False
        self._last_action_tick: dict[str, int] = {}

    def should_act(self, failure: dict[str, Any]) -> bool:
        failure_type = failure.get("type", "unknown")
        if failure_type in ("fiber_cut", "connectivity_loss") and self.backup_active:
            return False
        last = self._last_action_tick.get(failure_type)
        tick = failure.get("tick", 0)
        return last is None or tick - last >= self.COOLDOWN_TICKS

    def plan_recovery(self, failure: dict[str, Any]) -> dict[str, Any]:
        failure_type = failure.get("type", "unknown")
        action = self.RECOVERY_ACTIONS.get(failure_type, "boost_priority")
        self._last_action_tick[failure_type] = failure.get("tick", 0)

        plan = {
            "failure": failure,
            "action": action,
            "new_allocation": None,
            "reroute": False,
            "executed": False,
        }

        if action == "boost_priority":
            plan["new_allocation"] = self._boost(failure.get("service_class", "healthcare"))

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
        topo=None,
    ) -> bool:
        if plan.get("reroute"):
            self._activate_backup(topo, net)

        allocation = plan.get("new_allocation")
        if allocation is not None and qos_enforcer is not None and qos_enforcer.net is not None:
            qos_enforcer.apply_allocation(allocation)

        plan["executed"] = True
        return True

    def _capacity(self) -> float:
        return min(self.total_bandwidth, self.backup_bandwidth) if self.backup_active else self.total_bandwidth

    def _current_demands(self) -> dict[str, float]:
        if self.demands:
            return dict(self.demands)
        return {"healthcare": 50, "education": 20, "agriculture": 10, "general": 10}

    def _current_priorities(self) -> dict[str, float]:
        try:
            return self.context_engine.get_context(self.context_id)
        except ValueError:
            return self.context_engine.get_context("normal")

    def _boost(self, service: str) -> dict[str, float]:
        """Triple the affected service's weight (healthcare for generic congestion)."""
        priorities = self._current_priorities()
        priorities[service] = priorities.get(service, 1) * 3
        return self.allocation_engine.allocate(self._capacity(), priorities, self._current_demands())

    def _boost_healthcare(self) -> dict[str, float]:
        return self._boost("healthcare")

    def _throttle_general(self) -> dict[str, float]:
        priorities = self._current_priorities()
        demands = self._current_demands()
        priorities["general"] = 1
        demands["general"] = min(demands.get("general", 5), 5)
        return self.allocation_engine.allocate(self._capacity(), priorities, demands)

    def _disaster_allocation(self) -> dict[str, float]:
        # Plan for the degraded (backup) capacity that will carry traffic after
        # rerouting, with disaster-grade priorities protecting healthcare.
        capacity = min(self.total_bandwidth, self.backup_bandwidth)
        return self.allocation_engine.allocate(
            capacity,
            self.context_engine.get_context("disaster"),
            self._current_demands(),
        )

    def _activate_backup(self, topo, net):
        """Backup activation: bring up the standby backhaul and flush stale MACs."""
        if topo is not None:
            topo.set_backup_backhaul(True)
            switches = (topo.s_edge, topo.s_core)
        elif net is not None:
            switches = (net.get("s_edge"), net.get("s_core"))
            switches[0].cmd("ip link set s_edge-bkp up")
            switches[1].cmd("ip link set s_core-bkp up")
        else:
            return
        for switch in switches:
            # Learned MACs still point at the dead port; OVS would otherwise
            # black-hole traffic until they age out (300 s by default).
            switch.cmd(f"ovs-appctl fdb/flush {switch.name} 2>/dev/null")
        self.backup_active = True

    def get_recovery_log(self) -> list[dict[str, Any]]:
        return list(self.recovery_log)
