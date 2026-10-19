#!/usr/bin/env python3
"""
CARS-SF experiment entry point (real Open vSwitch network; needs root).

    sudo .venv/bin/python run_experiment.py --scenario fiber_cut --duration 45 --apply-qos
    sudo .venv/bin/python run_experiment.py --timeline rural_day --duration 40 --apply-qos
    sudo .venv/bin/python run_experiment.py --scenario school --scheduler tgpp --apply-qos

Use the project venv's interpreter: plain `sudo python3` is the system
Python, which lacks numpy/pandas/scapy/scikit-learn. Without sudo, the same
pipeline runs on Linux bridges via `python -m tests.integration.harness`.
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main():
    from core.config import load_scenarios, load_yaml

    scenarios = [s["id"] for s in load_scenarios()]
    registry = load_yaml("schedulers.yaml")
    schedulers = sorted(registry["schedulers"]) + sorted(registry.get("aliases", {}))
    timelines = sorted(load_yaml("timelines.yaml")["timelines"])

    parser = argparse.ArgumentParser(description="CARS-SF Mininet Experiment")
    parser.add_argument("--scenario", default="normal", choices=scenarios)
    parser.add_argument("--timeline", choices=timelines, help="context timeline instead of a fixed scenario")
    parser.add_argument("--duration", type=int, default=30)
    parser.add_argument("--apply-qos", action="store_true", help="enforce slices (HTB + fq_codel)")
    parser.add_argument("--scheduler", default="proposed", choices=schedulers)
    parser.add_argument("--classification", default="host", choices=["host", "app", "slicenet"])
    parser.add_argument("--mixed-ue", action="store_true", help="add a UE running every service")
    parser.add_argument("--strict-caps", action="store_true", help="disable HTB borrowing")
    parser.add_argument("--oracle-demand", action="store_true", help="use design demand, not measured")
    parser.add_argument("--no-self-healing", action="store_true")
    parser.add_argument("--no-predictive", action="store_true")
    parser.add_argument("--qos-backend", default="tc", choices=["tc", "ovs"])
    parser.add_argument("--ues-per-service", type=int, default=2)
    parser.add_argument("--control-interval", type=int, default=5)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--run-id")
    args = parser.parse_args()

    missing = []
    for module in ("numpy", "pandas", "dpkt", "sklearn", "yaml", "mininet"):
        try:
            __import__(module)
        except ImportError:
            missing.append(module)
    if missing:
        print(f"ERROR: {sys.executable} is missing: {', '.join(missing)}")
        print("Run with the project venv: sudo .venv/bin/python run_experiment.py ...")
        sys.exit(1)

    if os.geteuid() != 0:
        print("ERROR: Mininet requires root privileges. Run with sudo.")
        print("No sudo? python -m tests.integration.harness <scenario> <duration> apply_qos=true")
        sys.exit(1)

    import signal

    # SIGTERM (e.g. a scheduler timeout) becomes SystemExit so the orchestrator's
    # teardown (traffic, captures, injected faults, Mininet) still runs.
    signal.signal(signal.SIGTERM, lambda signum, frame: sys.exit(128 + signum))

    from core.orchestrator import run_experiment

    results = run_experiment(
        scenario_id=args.scenario,
        duration=args.duration,
        apply_qos=args.apply_qos,
        scheduler=args.scheduler,
        timeline=args.timeline,
        classification=args.classification,
        mixed_ue=args.mixed_ue,
        work_conserving=not args.strict_caps,
        demand_mode="oracle" if args.oracle_demand else "measured",
        self_healing=not args.no_self_healing,
        predictive=not args.no_predictive,
        qos_backend=args.qos_backend,
        ues_per_service=args.ues_per_service,
        control_interval=args.control_interval,
        seed=args.seed,
        run_id=args.run_id,
    )

    print("\n=== Experiment Complete ===")
    for key in ("run_id", "scheduler", "data_source", "record_count", "fairness_satisfaction",
                "weighted_utility", "mean_reward", "failure_types", "resilience", "summary_path"):
        print(f"{key:22s} {json.dumps(results.get(key), default=str)}")
    print(f"{'validation':22s} {results.get('validation_report', {}).get('total_score')}/100")
    for service, kpi in (results.get("slice_kpis") or {}).items():
        print(f"  {service:12s} p95 {kpi['latency_p95_ms']} ms  loss {kpi['loss_pct']}%  "
              f"satisfaction {kpi['demand_satisfaction']}  SLA-ok {kpi['sla_satisfied_share']}")


if __name__ == "__main__":
    main()
