"""Run the CARS-SF orchestrator on an emulated network without sudo.

The pipeline runs unchanged inside a user + network namespace; only the
switch implementation differs (Linux bridges instead of Open vSwitch, whose
ovsdb needs real root). Links, tc shaping, HTB/fq_codel QoS, traffic, packet
capture, fault injection and recovery are all real.

    python -m tests.integration.harness <scenario> <duration> [key=value ...]

`run_in_namespace()` wraps the call in `unshare` and returns the JSON result.
"""

from __future__ import annotations

import json
import os
import shutil
import signal
import subprocess
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RESULT_PREFIX = "HARNESS_RESULT "


def userns_available() -> bool:
    if shutil.which("unshare") is None or shutil.which("mnexec") is None:
        return False
    probe = subprocess.run(
        ["unshare", "-Urn", "true"], capture_output=True, text=True, check=False
    )
    return probe.returncode == 0


def run_in_namespace(scenario: str, duration: int, timeout: int = 900, **options) -> dict:
    """Run one experiment inside a fresh user+net+mount namespace."""
    def fmt(value):
        return str(value).lower() if isinstance(value, bool) else str(value)

    args = " ".join(f"{k}={fmt(v)}" for k, v in options.items() if v is not None)
    env = dict(os.environ, PATH=os.environ.get("PATH", "") + ":/usr/sbin:/sbin")
    command = (
        "mount -t sysfs none /sys && ip link set lo up && "
        f"{sys.executable} -u -m tests.integration.harness {scenario} {duration} {args}"
    )
    # Own process group: on timeout the whole run (generators, tcpdump, the
    # orchestrator) is signalled, not just the `sh` wrapper. SIGTERM first so the
    # orchestrator's teardown runs, SIGKILL if it does not finish.
    proc = subprocess.Popen(
        ["unshare", "-Urnm", "--propagation", "private", "sh", "-c", command],
        cwd=REPO_ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        start_new_session=True,
    )
    try:
        stdout, stderr = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        _signal_group(proc, signal.SIGTERM)
        try:
            stdout, stderr = proc.communicate(timeout=20)
        except subprocess.TimeoutExpired:
            _signal_group(proc, signal.SIGKILL)
            stdout, stderr = proc.communicate()
        raise RuntimeError(f"harness run timed out after {timeout}s:\n{stdout[-3000:]}\n{stderr[-3000:]}")
    proc = subprocess.CompletedProcess(proc.args, proc.returncode, stdout, stderr)
    for line in proc.stdout.splitlines():
        if line.startswith(RESULT_PREFIX):
            return json.loads(line[len(RESULT_PREFIX):])
    raise RuntimeError(
        f"harness run failed (exit {proc.returncode}):\n{proc.stdout[-3000:]}\n{proc.stderr[-3000:]}"
    )


def _signal_group(proc: subprocess.Popen, sig: int):
    try:
        os.killpg(proc.pid, sig)
    except ProcessLookupError:
        pass


def _exit_on_sigterm():
    """Turn SIGTERM into SystemExit so ``finally`` teardown runs."""
    signal.signal(signal.SIGTERM, lambda signum, frame: sys.exit(128 + signum))


def _parse_value(raw: str):
    for cast in (int, float):
        try:
            return cast(raw)
        except ValueError:
            pass
    if raw.lower() in ("true", "false"):
        return raw.lower() == "true"
    return raw


def main():
    sys.path.insert(0, REPO_ROOT)
    _exit_on_sigterm()
    from mininet.nodelib import LinuxBridge

    from core.orchestrator import ExperimentOrchestrator
    from topology.rural_topology import RuralNetworkTopology

    scenario, duration = sys.argv[1], int(sys.argv[2])
    options = dict(arg.split("=", 1) for arg in sys.argv[3:])
    options = {k: _parse_value(v) for k, v in options.items()}
    topo_kwargs = {
        k[len("topo_"):]: options.pop(k) for k in list(options) if k.startswith("topo_")
    }
    # The harness supplies its own topology factory, so topology-shaping
    # orchestrator options must be forwarded to it explicitly.
    for key in ("ues_per_service", "mixed_ue"):
        if key in options:
            topo_kwargs[key] = options[key]

    results = ExperimentOrchestrator(
        scenario_id=scenario,
        duration=duration,
        topology_factory=lambda: RuralNetworkTopology(switch_cls=LinuxBridge, **topo_kwargs),
        **options,
    ).run()
    print(RESULT_PREFIX + json.dumps(results, default=str))


if __name__ == "__main__":
    main()
