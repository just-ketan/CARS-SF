"""Failure injection for resilience testing."""

from __future__ import annotations

from mininet.log import info


class FaultInjector:
    """Injects faults into Mininet topology for self-healing tests."""

    def __init__(self, net):
        self.net = net
        self.active_faults: list[str] = []

    def inject_link_down(self, src: str, dst: str):
        try:
            switch = self.net.get(src)
            intf = f"{src}-eth2"
            switch.cmd(f"ip link set {intf} down")
            self.active_faults.append(f"link_down:{src}-{dst}")
            info(f"*** Fault injected: {src} → {dst} link DOWN ***\n")
        except Exception as exc:
            info(f"*** Fault injection failed: {exc} ***\n")

    def inject_latency(self, switch_name: str, intf: str, delay_ms: int = 100):
        try:
            switch = self.net.get(switch_name)
            switch.cmd(
                f"tc qdisc add dev {intf} root netem delay {delay_ms}ms 2>/dev/null"
            )
            self.active_faults.append(f"latency:{switch_name}:{delay_ms}ms")
            info(f"*** Latency injected: {delay_ms}ms on {intf} ***\n")
        except Exception as exc:
            info(f"*** Latency injection failed: {exc} ***\n")

    def evaluate_scenario(self, scenario_state: dict):
        if scenario_state.get("backhaul_degraded"):
            self.inject_link_down("s_edge", "s_core")

    def cleanup(self):
        for fault in self.active_faults:
            if fault.startswith("link_down:"):
                parts = fault.split(":")[1].split("-")
                if len(parts) >= 1:
                    try:
                        switch = self.net.get(parts[0])
                        switch.cmd(f"ip link set {parts[0]}-eth2 up")
                    except Exception:
                        pass
        self.active_faults.clear()
        info("*** Faults cleaned up ***\n")
