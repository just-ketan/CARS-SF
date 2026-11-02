#!/usr/bin/env python3
"""
Real Open vSwitch validation (Step 7): actuation and self-healing on OVS bridges.

    python experiments/ovs_validation.py [--seeds 30 31 32] [--only actuation|backend|resilience]

Every run executes in a fresh privileged container of the project image
(`cars-sf:latest`, Mininet + Open vSwitch 3.3, see Dockerfile) with the current
source tree mounted, through `run_experiment.py` as root, so the switches are real
OVS bridges (kernel datapath) instead of the Linux bridges of the sudo-free harness.
Results land in results/runs/<run_id>/ like any other run; run_meta.json records the
study, parameters, code/model fingerprints, image id and kernel.

Studies (fixed here, before running):
  ovs_actuation   school, disaster × no_slicing, static_equal, qos_adaptive   (kernel HTB on OVS ports)
  ovs_backend     disaster × proposed with the OVS-native linux-htb queue backend (queue read-back)
  ovs_resilience  fiber_cut, repeated_fiber_cut, backhaul_degradation, core_switch_failure × qos_adaptive
False positives = backup activations in runs with no injected fault (ovs_actuation, ovs_backend).
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from core.provenance import code_fingerprint, model_fingerprint  # noqa: E402

IMAGE = "cars-sf:latest"
STUDIES = {
    "ovs_actuation": [dict(scenario=s, scheduler=k, duration=40)
                      for s in ("school", "disaster") for k in ("no_slicing", "static_equal", "qos_adaptive")],
    "ovs_backend": [dict(scenario="disaster", scheduler="proposed", duration=40, qos_backend="ovs")],
    "ovs_resilience": [dict(scenario=s, scheduler="qos_adaptive", duration=60 if s == "repeated_fiber_cut" else 45)
                       for s in ("fiber_cut", "repeated_fiber_cut", "backhaul_degradation", "core_switch_failure")],
}


def run_one(study: str, params: dict, seed: int) -> dict:
    run_id = f"{study}__{params['scenario']}__{params['scheduler']}" \
             f"{'__' + params['qos_backend'] if params.get('qos_backend') else ''}__s{seed}"
    run_dir = REPO_ROOT / "results" / "runs" / run_id
    if (run_dir / "summary.json").exists():
        meta = json.loads((run_dir / "run_meta.json").read_text()) if (run_dir / "run_meta.json").exists() else {}
        if meta.get("code_fingerprint") == code_fingerprint():
            return {"run_id": run_id, "status": "skipped"}
    args = ["/cars-sf/.venv/bin/python", "run_experiment.py", "--scenario", params["scenario"],
            "--duration", str(params["duration"]), "--apply-qos", "--scheduler", params["scheduler"],
            "--seed", str(seed), "--run-id", run_id]
    if params.get("qos_backend"):
        args += ["--qos-backend", params["qos_backend"]]
    command = " ".join(args) + "; rc=$?; mn -c >/dev/null 2>&1; chown -R %d:%d results generated; exit $rc" % (
        os.getuid(), os.getgid())
    started = time.time()
    proc = subprocess.run(
        ["docker", "run", "--rm", "--privileged", "-v", "/lib/modules:/lib/modules:ro",
         "-v", f"{REPO_ROOT}:/work", "-w", "/work", IMAGE, "sh", "-c", command],
        capture_output=True, text=True, timeout=params["duration"] * 8 + 300, check=False,
    )
    log = REPO_ROOT / "results" / "evidence" / "ovs_logs" / f"{run_id}.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text(proc.stdout[-20000:] + "\n--- stderr ---\n" + proc.stderr[-20000:])
    ok = proc.returncode == 0 and (run_dir / "summary.json").exists()
    if ok:
        image = subprocess.run(["docker", "image", "inspect", IMAGE, "--format", "{{.Id}}"],
                               capture_output=True, text=True).stdout.strip()
        (run_dir / "run_meta.json").write_text(json.dumps({
            "params": {**params, "seed": seed, "run_id": run_id, "study": study, "switch": "OVSBridge (real OVS)"},
            "code_fingerprint": code_fingerprint(), "model_fingerprint": model_fingerprint(),
            "docker_image": image, "kernel": platform.release(),
            "wall_time_s": round(time.time() - started, 1),
        }, indent=2))
    return {"run_id": run_id, "status": "ok" if ok else f"failed (rc {proc.returncode}, log {log})"}


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--seeds", nargs="+", type=int, default=[30, 31, 32])
    parser.add_argument("--only", choices=list(STUDIES))
    args = parser.parse_args()
    studies = {args.only: STUDIES[args.only]} if args.only else STUDIES
    for study, configs in studies.items():
        for params in configs:
            for seed in args.seeds:
                outcome = run_one(study, params, seed)
                print(json.dumps(outcome), flush=True)


if __name__ == "__main__":
    main()
