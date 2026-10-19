"""
Self-Healing Engine (architecture.md §4.7).

State machine over detector events:

    NORMAL ──fiber_cut / predicted degradation──▶ ON_BACKUP
    ON_BACKUP ──core still unreachable──▶ DEGRADED   (fault localised to the core switch)
    ON_BACKUP / DEGRADED ──primary repaired──▶ fail-back ──▶ NORMAL

Network actions (reroute, backup activation, MAC flush, fail-back) are taken
directly; bandwidth consequences are expressed as *constraints* for the slice
controller rather than by overwriting its allocation, so the controller stays
the single owner of QoS policy:

  core_capacity_mbps   cap on slices whose servers sit behind the backhaul
  core_down            core-bound slices keep only their floor; edge slices
                       may use the freed capacity
  boosts               temporary priority multipliers (latency spikes, congestion)
"""

from __future__ import annotations

import time
from typing import Any

from core.config import load_applications
from mininet.log import info

NORMAL, ON_BACKUP, DEGRADED = "normal", "on_backup", "degraded"
BOOST_TICKS = 6
HOLD_DOWN_TICKS = 5            # minimum time on backup before failing back
SELF_CHANGE_WINDOW_S = 1.0     # link events this soon after our own action are ours
CORE_HEADROOM = 0.95   # keep the backup link's own queue empty


def ceilings_for(allocation: dict[str, float], constraints: dict[str, Any] | None) -> dict[str, float]:
    """HTB ceilings: while on backup, core-bound slices may not borrow beyond their
    (constrained) allocation, or they would overflow the smaller backup link."""
    if not constraints or constraints.get("core_capacity_mbps") is None:
        return {}
    locations = constraints.get("locations", {})
    return {s: v for s, v in allocation.items() if locations.get(s) == "core"}


def service_locations() -> dict[str, str]:
    """'core' if any of the service's applications is served from the core cloud."""
    locations: dict[str, str] = {}
    for app in load_applications():
        where = "core" if app["server"] == "srv_core" else "edge"
        if locations.get(app["service_class"]) != "core":
            locations[app["service_class"]] = where
    return locations


class SelfHealingEngine:
    def __init__(
        self,
        topo=None,
        backup_capacity_mbps: float = 50.0,
        enable_reroute: bool = True,
        enable_predictive: bool = True,
        escalate_after_ticks: int = 2,
    ):
        self.topo = topo
        self.backup_capacity = backup_capacity_mbps
        self.enable_reroute = enable_reroute
        self.enable_predictive = enable_predictive
        self.escalate_after = escalate_after_ticks
        self.state = NORMAL
        self.locations = service_locations()
        self.boosts: dict[str, tuple[float, int]] = {}
        self.actions: list[dict[str, Any]] = []
        self._core_unreachable_ticks = 0
        self._entered_backup_tick: int | None = None
        self._own_link_changes: list[float] = []
        self._pending_verification: dict[str, Any] | None = None
        self.verifications: list[dict[str, Any]] = []
        self.escalations: list[dict[str, Any]] = []
        self.primary_delay_limit_ms: float | None = None

    # --------------------------------------------------------------- events

    def _self_inflicted(self, event: dict[str, Any]) -> bool:
        """Link transitions caused by our own quarantine / fail-back, not by a fault."""
        ts = event.get("timestamp")
        if event.get("source") != "link_watcher" or ts is None:
            return False
        return any(0 <= ts - own <= SELF_CHANGE_WINDOW_S for own in self._own_link_changes)

    def handle(self, events: list[dict[str, Any]], tick: int):
        for event in events:
            kind = event["type"]
            if kind in ("fiber_cut", "primary_restored") and self._self_inflicted(event):
                continue
            if kind in ("fiber_cut", "predicted_backhaul_degradation") and self.state == NORMAL:
                if kind == "predicted_backhaul_degradation" and not self.enable_predictive:
                    continue
                self._switch_to_backup(event, tick, proactive=kind.startswith("predicted"))
            elif kind == "latency_spike" and event.get("service_class"):
                self._boost(event["service_class"], 2.0, tick, event)
            elif kind == "congestion":
                self._boost("healthcare", 2.0, tick, event)
            elif kind == "link_saturation":
                self._boost("general", 0.5, tick, event)

        core_dead = any(e["type"] in ("core_unreachable", "connectivity_loss") for e in events)
        self._core_unreachable_ticks = self._core_unreachable_ticks + 1 if core_dead else 0
        if (
            self.state == ON_BACKUP
            and self._core_unreachable_ticks >= self.escalate_after
            and tick - (self._entered_backup_tick or tick) >= self.escalate_after
        ):
            self.state = DEGRADED
            self._log("diagnose_core_switch_failure", tick, {"type": "core_unreachable"})
            self.escalations.append({"tick": tick, "reason": "core switch failure: needs physical repair",
                                     "state": DEGRADED})
            self._pending_verification = None   # nothing to verify until repair
        elif self.state == DEGRADED and not core_dead:
            self.state = ON_BACKUP
            self._log("core_reachable_again", tick, {"type": "core_reachable"})

        if self.state in (ON_BACKUP, DEGRADED) and self._primary_ready(tick):
            self._fail_back(tick)

        self.boosts = {s: (m, until) for s, (m, until) in self.boosts.items() if until > tick}

    def _primary_ready(self, tick: int) -> bool:
        """Fail back only after hold-down, with the far end up and the primary healthy."""
        if self.topo is None or tick - (self._entered_backup_tick or tick) < HOLD_DOWN_TICKS:
            return False
        if not self.topo.primary_repaired():
            return False
        delay_ms, loss_pct = self.topo.primary_link_quality()
        limit = self.primary_delay_limit_ms or delay_ms
        return delay_ms <= limit * 1.5 and loss_pct < 0.5

    # ------------------------------------------------------- verification

    VERIFY_CONSECUTIVE_TICKS = 2
    VERIFY_TIMEOUT_TICKS = 5

    def verify(self, snapshot: dict[str, Any], tick: int):
        """Post-action verification: did service actually come back?

        After every failover or fail-back the engine requires the core-hosted
        services to answer on the new path for ``VERIFY_CONSECUTIVE_TICKS``
        consecutive ticks; it records the measured time to restored service, or
        records a failed verification and escalates after ``VERIFY_TIMEOUT_TICKS``.
        """
        pending = self._pending_verification
        if pending is None:
            return
        rtts = snapshot.get("service_rtt_ms") or {}
        core = [s for s, where in self.locations.items() if where == "core"]
        reachable = bool(core) and all(rtts.get(s) is not None for s in core)
        pending["good_ticks"] = pending["good_ticks"] + 1 if reachable else 0
        if reachable and pending["first_good_ts"] is None:
            pending["first_good_ts"] = snapshot.get("timestamp")
        if not reachable:
            pending["first_good_ts"] = None
        if pending["good_ticks"] >= self.VERIFY_CONSECUTIVE_TICKS:
            restored_at = pending["first_good_ts"] or snapshot.get("timestamp")
            self._log("recovery_verified", tick, {
                "type": pending["action"], "timestamp": pending["started_ts"]})
            self.actions[-1]["time_to_restore_s"] = (
                round(restored_at - pending["fault_ts"], 3)
                if restored_at and pending.get("fault_ts") else None
            )
            self.verifications.append({**pending, "verified": True, "tick": tick})
            self._pending_verification = None
        elif tick - pending["tick"] >= self.VERIFY_TIMEOUT_TICKS:
            self._log("recovery_unverified_escalate", tick, {"type": pending["action"]})
            self.verifications.append({**pending, "verified": False, "tick": tick})
            self.escalations.append({"tick": tick, "reason": f"{pending['action']} not verified", "state": self.state})
            self._pending_verification = None

    def _expect_verification(self, action: str, tick: int, fault_ts: float | None):
        self._pending_verification = {
            "action": action, "tick": tick, "started_ts": time.time(),
            "fault_ts": fault_ts or time.time(), "good_ticks": 0, "first_good_ts": None,
        }

    def _switch_to_backup(self, event: dict[str, Any], tick: int, proactive: bool):
        if not self.enable_reroute:
            self._log("reroute_disabled", tick, event)
            return
        if self.topo is not None:
            if self.primary_delay_limit_ms is None:
                self.primary_delay_limit_ms = getattr(self.topo, "nominal_backhaul_delay_ms", None)
            self._own_link_changes.append(time.time())
            # Quarantine first so the primary can never form a loop with the backup.
            self.topo.set_primary_backhaul(False)
            self.topo.set_backup_backhaul(True)
            self._flush_fdb()
        self.state = ON_BACKUP
        self._entered_backup_tick = tick
        self._log("activate_backup_proactive" if proactive else "activate_backup", tick, event)
        self._expect_verification("activate_backup", tick, event.get("timestamp"))
        info(f"*** Self-healing: {'proactive ' if proactive else ''}switch to backup backhaul ***\n")

    def _fail_back(self, tick: int):
        if self.topo is not None:
            self._own_link_changes.append(time.time())
            self.topo.set_backup_backhaul(False)   # backup down before primary up: loop-free
            self.topo.set_primary_backhaul(True)
            self._flush_fdb()
        self.state = NORMAL
        self._entered_backup_tick = None
        self._log("fail_back", tick, {"type": "primary_repaired"})
        self._expect_verification("fail_back", tick, time.time())
        info("*** Self-healing: primary backhaul repaired, failing back ***\n")

    def _flush_fdb(self):
        for switch in (self.topo.s_rural, self.topo.s_edge, self.topo.s_core):
            # OVS keeps learned MACs on the dead port for 300 s; Linux bridges
            # flush on carrier loss but not on our admin changes of the peer.
            switch.cmd(f"ovs-appctl fdb/flush {switch.name} 2>/dev/null")
            switch.cmd(f"bridge fdb flush dev {switch.name} 2>/dev/null")

    def _boost(self, service: str, multiplier: float, tick: int, event: dict[str, Any]):
        current = self.boosts.get(service)
        if current and current[1] > tick:
            return
        self.boosts[service] = (multiplier, tick + BOOST_TICKS)
        self._log(f"priority_x{multiplier:g}:{service}", tick, event)

    def _log(self, action: str, tick: int, event: dict[str, Any]):
        self.actions.append({
            "action": action,
            "tick": tick,
            "timestamp": time.time(),
            "trigger": event.get("type"),
            "trigger_timestamp": event.get("timestamp"),
            "state": self.state,
        })

    # ----------------------------------------------------------- constraints

    def constraints(self) -> dict[str, Any]:
        return {
            "state": self.state,
            "core_capacity_mbps": self.backup_capacity if self.state in (ON_BACKUP, DEGRADED) else None,
            "core_down": self.state == DEGRADED,
            "boosts": {s: m for s, (m, _) in self.boosts.items()},
            "locations": self.locations,
        }

    def resilience_summary(self, injector_events: list[dict[str, Any]]) -> dict[str, Any]:
        """Control-plane MTTD/MTTR per injected failure (seconds)."""
        failures = [e for e in injector_events if e["event"] in (
            "fiber_cut", "degradation_start", "core_switch_failure")]
        summary: dict[str, Any] = {"state": self.state, "actions": len(self.actions)}
        if not failures:
            return summary
        injected = failures[0]
        detections = [
            a for a in self.actions
            if a["action"].startswith("activate_backup") and a["timestamp"] >= injected["timestamp"] - 30
        ]
        if detections:
            first = detections[0]
            detected_at = first.get("trigger_timestamp") or first["timestamp"]
            summary.update({
                "failure": injected["event"],
                "proactive": first["action"].endswith("proactive"),
                "mttd_s": round(detected_at - injected["timestamp"], 3),
                "mttr_control_s": round(first["timestamp"] - injected["timestamp"], 3),
            })
        cut = next((e for e in injector_events if e["event"] == "fiber_cut"), None)
        if cut and detections:
            summary["switched_before_cut"] = detections[0]["timestamp"] < cut["timestamp"]
        fail_backs = [a for a in self.actions if a["action"] == "fail_back"]
        repairs = [e for e in injector_events if e["event"] == "repair"]
        if fail_backs and repairs:
            summary["fail_back_delay_s"] = round(fail_backs[0]["timestamp"] - repairs[0]["timestamp"], 3)
        summary["verifications"] = [
            {"action": v["action"], "verified": v["verified"], "tick": v["tick"]} for v in self.verifications
        ]
        restores = [a.get("time_to_restore_s") for a in self.actions if a["action"] == "recovery_verified"]
        summary["time_to_restore_s"] = restores[0] if restores else None
        summary["escalations"] = self.escalations
        summary["diagnosed_core_switch_failure"] = any(
            a["action"] == "diagnose_core_switch_failure" for a in self.actions
        )
        return summary


def apply_constraints(
    allocation: dict[str, float],
    demands: dict[str, float],
    capacity: float,
    constraints: dict[str, Any],
    floors: dict[str, float] | None = None,
) -> dict[str, float]:
    """Post-process an allocation under self-healing constraints."""
    if not allocation or not constraints:
        return allocation
    locations = constraints.get("locations", {})
    core = [s for s in allocation if locations.get(s) == "core"]
    edge = [s for s in allocation if locations.get(s) != "core"]
    result = dict(allocation)
    floors = floors or {}

    if constraints.get("core_down"):
        for s in core:
            result[s] = min(result[s], floors.get(s, 1.0))
    elif constraints.get("core_capacity_mbps") is not None:
        cap = constraints["core_capacity_mbps"] * CORE_HEADROOM
        total = sum(result[s] for s in core)
        if total > cap > 0:
            for s in core:
                result[s] = result[s] * cap / total

    spare = capacity - sum(result.values())
    want = {s: max(demands.get(s, 0.0) - result[s], 0.0) for s in edge}
    if spare > 0 and sum(want.values()) > 0:
        total_want = sum(want.values())
        for s in edge:
            result[s] += min(want[s], spare * want[s] / total_want)
    return {s: round(v, 2) for s, v in result.items()}
