"""
QoS violation monitor: the "evaluate QoS" stage of the closed loop.

Every tick each class is compared with its thresholds for the current scenario
(``registries/qos_thresholds.yaml``, resolved by ``load_thresholds``) on measured values:

  loss_pct       queue drops on the class's two enforcement points
  latency_ms     probe RTT / 2 (one-way estimate); the queue delay if no probe answered
  jitter_ms      mean successive probe difference / 2, when the backend measures it
  satisfaction   delivered / offered, for inelastic classes (TCP adapts to what it gets)

A breach is **transient** until it has lasted ``PERSIST_TICKS`` consecutive ticks,
then **persistent**; it ends after ``CLEAR_TICKS`` clean ticks, so one good tick does
not end a persistent violation. Episodes are logged with their duration and the
metrics that breached. Only persistent violations trigger RL adaptation: a burst that
clears within a tick or two is the queue's job, not a reason to re-plan.
"""

from __future__ import annotations

from typing import Any

from core.config import load_scenarios, load_yaml

SERVICES = ("healthcare", "education", "agriculture", "general")
PERSIST_TICKS, CLEAR_TICKS = 3, 3
METRICS = ("latency_ms", "jitter_ms", "loss_pct", "min_satisfaction")


def load_thresholds(path: str = "qos_thresholds.yaml") -> dict[str, dict[str, dict[str, float]]]:
    """Scenario → class → thresholds. Every class gets the baseline of slices.yaml; a scenario
    override may only tighten it, so a hard scenario can never be made to pass by relaxing it."""
    base = load_yaml("slices.yaml")["service_slices"]
    overrides = load_yaml(path).get("overrides") or {}
    table: dict[str, dict[str, dict[str, float]]] = {}
    for scenario in load_scenarios():
        sid = scenario["id"]
        table[sid] = {}
        for service in SERVICES:
            entry = {m: float(base[service]["sla"][m]) for m in METRICS}
            for metric, value in ((overrides.get(sid) or {}).get(service) or {}).items():
                value = float(value)
                tighter = value >= entry[metric] if metric == "min_satisfaction" else value <= entry[metric]
                if not tighter:
                    raise ValueError(f"{sid}/{service}/{metric}: override {value} relaxes baseline {entry[metric]}")
                entry[metric] = value
            table[sid][service] = entry
    return table


class QoSViolationMonitor:
    def __init__(self, thresholds: dict | None = None, elastic: set[str] | None = None):
        self.thresholds = thresholds or load_thresholds()
        self.elastic = elastic if elastic is not None else set()
        self.state = {s: {"bad": 0, "good": 0, "persistent": False, "episode": None} for s in SERVICES}
        self.episodes: list[dict[str, Any]] = []
        self.ticks = 0

    def measure(self, service: str, snapshot: dict[str, Any], demand: dict[str, float] | None) -> dict[str, float | None]:
        qos = (snapshot.get("slice_qos") or {}).get(service) or {}
        rtt = (snapshot.get("service_rtt_ms") or {}).get(service)
        jitter = (snapshot.get("service_jitter_ms") or {}).get(service)
        delivered, offered = qos.get("delivered_mbps"), (demand or {}).get(service)
        return {
            "latency_ms": None if rtt is None else rtt / 2,
            "queue_delay_ms": qos.get("queue_delay_ms"),
            "jitter_ms": None if jitter is None else jitter / 2,
            "loss_pct": qos.get("loss_pct"),
            "probe_answered": rtt is not None,
            "satisfaction": None if not offered or offered < 0.5 or delivered is None else delivered / offered,
        }

    def breaches(self, service: str, measured: dict[str, Any], context: str) -> list[str]:
        limits = (self.thresholds.get(context) or self.thresholds["normal"])[service]
        found = []
        latency = measured["latency_ms"] if measured["latency_ms"] is not None else measured["queue_delay_ms"]
        if latency is not None and latency > limits["latency_ms"]:
            found.append("latency")
        if measured["jitter_ms"] is not None and measured["jitter_ms"] > limits["jitter_ms"]:
            found.append("jitter")
        if measured["loss_pct"] is not None and measured["loss_pct"] > limits["loss_pct"]:
            found.append("loss")
        if not measured["probe_answered"] and measured["queue_delay_ms"] is None:
            found.append("unreachable")
        satisfaction = measured["satisfaction"]
        if service not in self.elastic and satisfaction is not None and satisfaction < limits["min_satisfaction"]:
            found.append("throughput")
        return found

    def observe(self, tick: int, snapshot: dict[str, Any], context: str,
                demand: dict[str, float] | None = None) -> dict[str, dict[str, Any]]:
        """One tick. Returns per class: status (ok | transient | persistent) and breached metrics."""
        self.ticks += 1
        status = {}
        for service in SERVICES:
            st = self.state[service]
            found = self.breaches(service, self.measure(service, snapshot, demand), context)
            if found:
                st["bad"] += 1
                st["good"] = 0
                if st["episode"] is None:
                    st["episode"] = {"class": service, "context": context, "start_tick": tick,
                                     "metrics": set(), "persistent": False}
                st["episode"]["metrics"].update(found)
                if st["bad"] >= PERSIST_TICKS and not st["persistent"]:
                    st["persistent"] = True
                    st["episode"]["persistent"] = True
                    st["episode"]["persistent_tick"] = tick
            else:
                st["good"] += 1
                if not st["persistent"]:
                    st["bad"] = 0
                if st["episode"] is not None and (not st["persistent"] or st["good"] >= CLEAR_TICKS):
                    self._close(service, tick)
            state_name = "persistent" if st["persistent"] else "transient" if found else "ok"
            status[service] = {"status": state_name, "breaches": found}
        return status

    def _close(self, service: str, tick: int):
        st = self.state[service]
        if st["episode"] is not None:
            episode = st["episode"]
            episode["end_tick"] = tick
            episode["metrics"] = sorted(episode["metrics"])
            episode["duration_ticks"] = tick - episode["start_tick"]
            self.episodes.append(episode)
        st.update({"bad": 0, "persistent": False, "episode": None})

    def persistent(self) -> set[str]:
        return {s for s, st in self.state.items() if st["persistent"]}

    def finish(self, tick: int):
        for service in SERVICES:
            if self.state[service]["episode"] is not None:
                self.state[service]["episode"]["unresolved"] = True
                self._close(service, tick)

    def summary(self) -> dict[str, Any]:
        persistent = [e for e in self.episodes if e["persistent"]]
        transient = [e for e in self.episodes if not e["persistent"]]
        return {
            "transient_episodes": len(transient), "persistent_episodes": len(persistent),
            "unresolved_persistent": sum(bool(e.get("unresolved")) for e in persistent),
            "per_class_persistent_ticks": {
                s: sum(e["duration_ticks"] for e in persistent if e["class"] == s) for s in SERVICES},
            "episodes": self.episodes,
        }
