"""Scenario-driven traffic orchestration over Mininet."""

from __future__ import annotations

import json
import sys
import time
from collections import defaultdict
from typing import Any

from mininet.log import info

from core.config import GENERATED_DIR, REPO_ROOT, load_applications, load_scenarios
from traffic.models import mean_rate_mbps, scaled


class TrafficOrchestrator:
    """Spawns model-driven application traffic from the application registry.

    Every UE of a service runs every application of that service; the
    service's scenario demand is split evenly across its UEs. A ``mixed`` UE
    (if the topology has one) runs one application of every service, so its
    flows cannot be attributed to a slice by source address alone.
    """

    def __init__(self, topo, seed: int = 0, log_dir=None, load_scale: float = 1.0):
        self.topo = topo
        self.load_scale = load_scale
        self.seed = seed
        self.log_dir = log_dir or (GENERATED_DIR / "logs")
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.applications = load_applications()
        self.spawn_metadata: list[dict[str, Any]] = []
        self.bitrate_scale: dict[str, float] = {}
        self._sinks: list = []
        self._generators: list = []
        self._python = sys.executable
        self.context_changes: list[dict[str, Any]] = []

    # ----------------------------------------------------------------- planning

    def set_demands(self, demand_mbps: dict[str, float]):
        """Scale each service's applications so their mean rates sum to its demand."""
        nominal: dict[str, float] = defaultdict(float)
        for app in self.applications:
            nominal[app["service_class"]] += mean_rate_mbps(app["model"], app.get("params", {}))
        self.bitrate_scale = {
            service: demand_mbps[service] * self.load_scale / total
            for service, total in nominal.items()
            if service in demand_mbps and total > 0
        }
        info(f"*** Offered load per service (Mbps): {demand_mbps} ***\n")

    def plan(self, duration: float) -> list[dict[str, Any]]:
        """One spawn record per (application, UE) with scaled parameters."""
        plans = []
        ues = getattr(self.topo, "ues_by_service", None) or {
            s: [h] for s, h in self.topo.hosts_by_service.items()
        }
        for idx, app in enumerate(self.applications):
            service = app["service_class"]
            hosts = ues.get(service, [])
            if not hosts:
                continue
            scale = self.bitrate_scale.get(service, 1.0) / len(hosts)
            params, instances = scaled(app["model"], app.get("params", {}), scale)
            for ue_index, host in enumerate(hosts):
                plans.append(self._spawn_record(app, host, params, instances, duration, idx, ue_index))

        mixed = getattr(self.topo, "h_mixed", None) if getattr(self.topo, "mixed_ue", False) else None
        if mixed is not None:
            seen = set()
            for idx, app in enumerate(self.applications):
                if app["service_class"] in seen:
                    continue
                seen.add(app["service_class"])
                params, instances = scaled(app["model"], app.get("params", {}), 0.5)
                plans.append(self._spawn_record(app, mixed, params, instances, duration, idx, 99))
        return plans

    def _spawn_record(self, app, host, params, instances, duration, app_idx, ue_index) -> dict:
        return {
            "application_id": app["application_id"],
            "service_class": app["service_class"],
            "slice_type": app["slice_type"],
            "priority": app["priority"],
            "host": host.name,
            "host_ip": host.IP(),
            "server": app["server"],
            "server_ip": app["server_ip"],
            "port": app["port"],
            "protocol": app["protocol"],
            "direction": app.get("direction", "up"),
            "model": app["model"],
            "params": params,
            "instances": instances,
            "dscp": app.get("dscp", 0),
            "latency_requirement_ms": app.get("latency_requirement_ms", 100),
            "sla": app.get("sla", {}),
            "duration": duration,
            "seed": self.seed * 100_003 + app_idx * 101 + ue_index,
            "bitrate_mbps": round(mean_rate_mbps(app["model"], params) * instances, 4),
        }

    # ---------------------------------------------------------------- execution

    def start_sinks(self, plans: list[dict[str, Any]]):
        ports: dict[str, dict[str, set]] = defaultdict(lambda: {"udp": set(), "tcp": set()})
        for p in plans:
            # TCP request/response models always connect UE → server.
            receiver = p["host"] if (p["direction"] == "down" and p["model"] == "bulk_tcp") or (
                p["direction"] == "down" and p["protocol"] == "udp"
            ) else p["server"]
            ports[receiver][p["protocol"]].add(p["port"])
        for host_name, by_proto in ports.items():
            host = self.topo.get_host(host_name)
            cmd = [
                self._python, "-m", "traffic.sink",
                "--udp", ",".join(map(str, sorted(by_proto["udp"]))),
                "--tcp", ",".join(map(str, sorted(by_proto["tcp"]))),
            ]
            self._sinks.append(host.popen(cmd, cwd=str(REPO_ROOT)))
        info(f"*** Started traffic sinks on {len(ports)} hosts\n")

    def spawn(self, plan: dict[str, Any]):
        sender_is_server = plan["direction"] == "down" and (
            plan["protocol"] == "udp" or plan["model"] == "bulk_tcp"
        )
        sender = self.topo.get_host(plan["server"] if sender_is_server else plan["host"])
        dst = plan["host_ip"] if sender_is_server else plan["server_ip"]
        cmd = [
            self._python, "-m", "traffic.generator",
            "--proto", plan["protocol"], "--dst", dst, "--port", str(plan["port"]),
            "--model", plan["model"], "--params", json.dumps(plan["params"]),
            "--duration", str(plan["duration"]), "--dscp", str(plan["dscp"]),
            "--seed", str(plan["seed"]), "--instances", str(plan["instances"]),
        ]
        log = open(self.log_dir / f"{plan['application_id']}@{plan['host']}.log", "a")
        self._generators.append(sender.popen(cmd, cwd=str(REPO_ROOT), stdout=log, stderr=log))
        self.spawn_metadata.append(plan)

    def prepare(self, scenario_id: str, duration: float) -> list[dict[str, Any]]:
        """Plan (but do not start) the scenario's application instances."""
        self.set_demands(self._get_scenario(scenario_id).get("demand_mbps", {}))
        return self.plan(duration)

    def start(self, plans: list[dict[str, Any]], scenario_id: str):
        self.start_sinks(plans)
        time.sleep(1.0)
        for plan in plans:
            self.spawn(plan)
        self.context_changes.append({"context": scenario_id, "timestamp": time.time()})
        info(f"*** Spawned {len(plans)} application instances "
             f"({len({p['host'] for p in plans})} UEs)\n")

    def run_scenario(self, scenario_id: str, duration: int):
        scenario = self._get_scenario(scenario_id)
        self.set_demands(scenario.get("demand_mbps", {}))
        plans = self.plan(duration)
        self.start_sinks(plans)
        time.sleep(1.0)
        for plan in plans:
            self.spawn(plan)
        self.context_changes.append({"context": scenario_id, "timestamp": time.time()})
        info(f"*** Spawned {len(plans)} application instances "
             f"({len({p['host'] for p in plans})} UEs)\n")

    def switch_context(self, scenario_id: str, remaining_s: float):
        """Re-spawn generators with the new context's demand (sinks keep running)."""
        self._terminate(self._generators)
        scenario = self._get_scenario(scenario_id)
        self.set_demands(scenario.get("demand_mbps", {}))
        self.seed += 1
        for plan in self.plan(remaining_s):
            self.spawn(plan)
        self.context_changes.append({"context": scenario_id, "timestamp": time.time()})

    @staticmethod
    def _terminate(procs: list):
        for proc in procs:
            try:
                proc.terminate()
            except Exception:
                pass
        for proc in procs:
            try:
                proc.wait(timeout=3)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass
        procs.clear()

    def stop_all(self):
        info("*** Stopping traffic generators\n")
        self._terminate(self._generators)
        self._terminate(self._sinks)

    def get_spawn_metadata(self) -> list[dict[str, Any]]:
        return list(self.spawn_metadata)

    def _get_scenario(self, scenario_id: str) -> dict[str, Any]:
        for scenario in load_scenarios():
            if scenario["id"] == scenario_id:
                return scenario
        return load_scenarios()[0]


