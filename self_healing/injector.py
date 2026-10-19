"""Failure injection for resilience experiments.

Failure specs come from the scenario registry, e.g.::

    failure: {type: fiber_cut, at: 0.33, repair_at: 0.66}
    failure: {type: backhaul_degradation, at: 0.2, cut_at: 0.7,
              delay_step_ms: 15, loss_step_pct: 0.3}
    failure: {type: core_switch_failure, at: 0.33, repair_at: 0.66}

``at`` / ``repair_at`` / ``cut_at`` are fractions of the run duration.
"""

from __future__ import annotations

import time

from mininet.log import info

from topology.rural_topology import BACKHAUL_DELAY_MS, BACKHAUL_INTF

FAR_END_INTF = "s_core-bh"   # a cut is injected at the far end: s_edge sees loss of carrier


class FaultInjector:
    """Injects faults into Mininet topology for self-healing tests."""

    def __init__(self, net, spec: dict | None = None, duration: int = 30):
        self.net = net
        self.spec = spec or {}
        self.duration = duration
        self.active_faults: list[str] = []
        self.injection_tick: int | None = None
        self.events: list[dict] = []
        self._degradation_level = 0

    def _tick_of(self, key: str) -> int | None:
        if key not in self.spec:
            return None
        return max(1, int(round(self.spec[key] * self.duration)))

    def _record(self, kind: str, tick: int, **extra):
        self.events.append({"event": kind, "tick": tick, "timestamp": time.time(), **extra})

    # ------------------------------------------------------------- primitives

    def inject_link_down(self, switch_name: str, intf: str):
        fault = f"link_down:{switch_name}:{intf}"
        if fault in self.active_faults:
            return
        try:
            self.net.get(switch_name).cmd(f"ip link set {intf} down")
            self.active_faults.append(fault)
            info(f"*** Fault injected: {intf} on {switch_name} DOWN ***\n")
        except Exception as exc:
            info(f"*** Fault injection failed: {exc} ***\n")

    def restore_link(self, switch_name: str, intf: str):
        fault = f"link_down:{switch_name}:{intf}"
        self.net.get(switch_name).cmd(f"ip link set {intf} up")
        if fault in self.active_faults:
            self.active_faults.remove(fault)
        info(f"*** Repaired: {intf} on {switch_name} UP ***\n")

    def inject_fiber_cut(self):
        self.inject_link_down("s_core", FAR_END_INTF)

    def set_backhaul_impairment(self, extra_delay_ms: float, loss_pct: float):
        switch = self.net.get("s_edge")
        switch.cmd(
            f"tc qdisc change dev {BACKHAUL_INTF} root netem "
            f"delay {BACKHAUL_DELAY_MS + extra_delay_ms:.0f}ms loss {loss_pct:.2f}% 2>/dev/null"
        )
        if "impairment:s_edge:" + BACKHAUL_INTF not in self.active_faults:
            self.active_faults.append("impairment:s_edge:" + BACKHAUL_INTF)

    def inject_latency(self, switch_name: str, intf: str, delay_ms: int = 100):
        try:
            switch = self.net.get(switch_name)
            switch.cmd(f"tc qdisc add dev {intf} root netem delay {delay_ms}ms 2>/dev/null")
            self.active_faults.append(f"latency:{switch_name}:{intf}")
            info(f"*** Latency injected: {delay_ms}ms on {intf} ***\n")
        except Exception as exc:
            info(f"*** Latency injection failed: {exc} ***\n")

    def _core_ports(self) -> list[str]:
        switch = self.net.get("s_core")
        return [i.name for i in switch.intfList() if i.name != "lo"]

    # ------------------------------------------------------------ scenarios

    def evaluate_scenario(self, scenario_state: dict, inject_at_tick: int = 1):
        """Drive the scenario's failure spec; legacy ``backhaul_degraded`` = fiber cut."""
        tick = scenario_state.get("tick", 0)
        kind = self.spec.get("type") or ("fiber_cut" if scenario_state.get("backhaul_degraded") else None)
        if kind is None:
            return
        start = self._tick_of("at") or inject_at_tick
        repair = self._tick_of("repair_at")

        if kind == "fiber_cut":
            if self.injection_tick is None and tick >= start:
                self.inject_fiber_cut()
                self.injection_tick = tick
                self._record("fiber_cut", tick)
            elif repair and self.injection_tick is not None and tick == repair:
                self.restore_link("s_core", FAR_END_INTF)
                self._record("repair", tick)

        elif kind == "backhaul_degradation":
            cut = self._tick_of("cut_at")
            if tick >= start and (cut is None or tick < cut):
                self._degradation_level += 1
                self.set_backhaul_impairment(
                    self._degradation_level * self.spec.get("delay_step_ms", 15),
                    self._degradation_level * self.spec.get("loss_step_pct", 0.3),
                )
                if self.injection_tick is None:
                    self.injection_tick = tick
                    self._record("degradation_start", tick)
            if cut and tick == cut:
                self.inject_fiber_cut()
                self._record("fiber_cut", tick)

        elif kind == "core_switch_failure":
            if self.injection_tick is None and tick >= start:
                for port in self._core_ports():
                    self.inject_link_down("s_core", port)
                self.injection_tick = tick
                self._record("core_switch_failure", tick)
            elif repair and self.injection_tick is not None and tick == repair:
                for port in self._core_ports():
                    self.restore_link("s_core", port)
                self._record("repair", tick)

    def cleanup(self):
        for fault in self.active_faults:
            kind, switch_name, intf = fault.split(":", 2)
            try:
                switch = self.net.get(switch_name)
                if kind == "link_down":
                    switch.cmd(f"ip link set {intf} up")
                elif kind == "latency":
                    switch.cmd(f"tc qdisc del dev {intf} root 2>/dev/null")
                elif kind == "impairment":
                    switch.cmd(
                        f"tc qdisc change dev {intf} root netem delay {BACKHAUL_DELAY_MS}ms loss 0% 2>/dev/null"
                    )
            except Exception as exc:
                # A fault that could not be reverted must not pass silently: the next run would inherit it.
                info(f"*** WARNING: could not revert fault {fault}: {exc} ***\n")
        self.active_faults.clear()
        info("*** Faults cleaned up ***\n")
