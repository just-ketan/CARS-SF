"""Scenario-driven traffic orchestration over Mininet."""

from __future__ import annotations

import time
from typing import Any

from mininet.log import info

from core.config import load_applications, load_scenarios


class TrafficOrchestrator:
    """Spawns real traffic processes from application registry profiles."""

    def __init__(self, topo):
        self.topo = topo
        self.applications = load_applications()
        self.spawn_metadata: list[dict[str, Any]] = []
        self._started_servers: set[int] = set()

    def start_servers(self):
        info("*** Starting iperf3 servers on edge and core\n")
        ports_needed: set[tuple[str, int]] = set()
        for app in self.applications:
            if app.get("tool") == "iperf3":
                ports_needed.add((app["server"], app["port"]))

        for server_name, port in ports_needed:
            server = self.topo.get_host(server_name)
            if port not in self._started_servers:
                server.cmd(f"iperf3 -s -p {port} -D")
                self._started_servers.add(port)

    def spawn_application(self, app: dict[str, Any], duration: int):
        host = self.topo.get_host(app["host"])
        server_ip = app["server_ip"]
        port = app["port"]
        app_id = app["application_id"]

        metadata = {
            "application_id": app_id,
            "service_class": app["service_class"],
            "slice_type": app["slice_type"],
            "priority": app["priority"],
            "host": app["host"],
            "server_ip": server_ip,
            "port": port,
            "latency_requirement_ms": app.get("latency_requirement_ms", 100),
        }
        self.spawn_metadata.append(metadata)

        if app.get("tool") == "iperf3":
            proto_flag = "-u" if app.get("protocol") == "udp" else ""
            bitrate = app.get("bitrate_mbps", 5)
            cmd = (
                f"iperf3 -c {server_ip} -p {port} {proto_flag} "
                f"-b {bitrate}M -t {duration} > /dev/null 2>&1 &"
            )
            host.cmd(cmd)
            info(f"*** Spawned {app_id} ({app['tool']}) from {app['host']}\n")

        elif app.get("tool") == "ping":
            size = app.get("packet_size", 64)
            interval = app.get("interval_s", 1)
            cmd = (
                f"ping {server_ip} -i {interval} -s {size} "
                f"-w {duration} > /dev/null 2>&1 &"
            )
            host.cmd(cmd)
            info(f"*** Spawned {app_id} (ping) from {app['host']}\n")

    def run_scenario(self, scenario_id: str, duration: int):
        scenario = self._get_scenario(scenario_id)
        preferred = scenario.get("preferred_services", [])
        self.start_servers()
        time.sleep(1)

        for app in self.applications:
            service = app["service_class"]
            if preferred and service not in preferred:
                if scenario_id in ("disaster", "medical_emergency") and service != "healthcare":
                    continue
            self.spawn_application(app, duration)

    def run_all(self, duration: int = 30):
        """Spawn one application per service class for a quick experiment."""
        self.start_servers()
        time.sleep(1)
        seen_services: set[str] = set()
        for app in self.applications:
            if app["service_class"] not in seen_services:
                self.spawn_application(app, duration)
                seen_services.add(app["service_class"])

    def update_demands(self, scenario_state: dict[str, Any]):
        """Adjust traffic intensity based on scenario (called per tick)."""
        pass

    def stop_all(self):
        info("*** Stopping traffic generators\n")
        for host_name in ("srv_edge", "srv_core", "h_health", "h_edu", "h_agri", "h_gen"):
            try:
                host = self.topo.get_host(host_name)
                host.cmd("pkill iperf3")
                host.cmd("pkill ping")
            except Exception:
                pass

    def get_spawn_metadata(self) -> list[dict[str, Any]]:
        return list(self.spawn_metadata)

    def _get_scenario(self, scenario_id: str) -> dict[str, Any]:
        for scenario in load_scenarios():
            if scenario["id"] == scenario_id:
                return scenario
        return load_scenarios()[0]
