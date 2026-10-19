"""
Unified RSNSD data contract (schema version ``rsnsd-contract-2.0``).

Both data paths emit records against this one contract:

  synthetic_rsnsd     RSNSD generator (parametric traffic + QoS models)
  mininet_measured    emulated network, packet-matched endpoint captures
  5g_core_measured    Open5GS / UERANSIM deployment, same capture pipeline

Every record carries ``provenance_source``, ``schema_version``, ``seed`` and
``config_id``, so the paths stay distinguishable (a model trained on synthetic
data can be evaluated on measured data, never silently mixed).

``validate`` *rejects* incompatible data instead of coercing it: missing
columns, non-numeric values in numeric fields, labels outside the taxonomy,
physically impossible values, a wrong schema version or a mismatched source.

Each field has a per-source category (see ``field_category``):
  measured     observed on the network (captures, counters, tc, psutil)
  derived      computed from measured fields
  configured   set by the experiment, not observed (scenario context, L2 constants, radio placeholders)
  synthetic    produced by the RSNSD parametric models
  label        ground truth from the traffic generator
  identifier   keys and bookkeeping
  provenance   contract metadata
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

from core.config import load_features
from features.schema_mapper import (
    CONTEXT_INJECTED_COLUMNS, EXTRA_COLUMNS, LABEL_AND_ID_COLUMNS, SCHEMA_COLUMNS,
)

SCHEMA_VERSION = "rsnsd-contract-2.0"
SOURCES = ("synthetic_rsnsd", "mininet_measured", "5g_core_measured")
MEASURED_SOURCES = ("mininet_measured", "5g_core_measured")
SERVICE_CLASSES = ("healthcare", "education", "agriculture", "general")
PROVENANCE_COLUMNS = ("provenance_source", "schema_version", "seed", "config_id")

STRING_COLUMNS = {
    "flow_id", "device_type", "mobility_state", "time_of_day", "network_slice_id",
    "service_class", "application_id", "slice_type_label", "allocated_slice", "ue_host",
    "data_source", "provenance_source", "schema_version", "config_id",
    "service_type", "application_name", "slice_type", "run_id", "scheduler", "scenario_id",
    "context_name", "rsnsd_scenario",
}
BOOL_COLUMNS = {"sla_satisfied"}
LABEL_COLUMNS = {"service_class", "application_id", "slice_type_label", "priority_level",
                 "allocated_slice", "sla_satisfied", "reward_score", "qos_satisfaction_score"}
NON_NEGATIVE = (
    "flow_duration_ms", "packet_count", "byte_count", "forward_packet_count", "backward_packet_count",
    "forward_byte_count", "backward_byte_count", "packet_rate_pps", "byte_rate_bps",
    "mean_iat_ms", "std_iat_ms", "min_iat_ms", "max_iat_ms", "mean_packet_size",
    "min_packet_size", "max_packet_size", "throughput_mbps", "goodput_mbps", "jitter_ms",
    "end_to_end_latency_ms", "queueing_delay_ms",
)
NAN_ALLOWED_MEASURED = {"end_to_end_latency_ms", "p95_latency_ms"}   # no delivered packet in window


class ContractViolation(ValueError):
    pass


def unit_of(column: str) -> str:
    for suffix, unit in (("_ms", "ms"), ("_mbps", "Mb/s"), ("_bps", "bit/s"), ("_pps", "packet/s"),
                         ("_pct", "%"), ("_dbm", "dBm"), ("_db", "dB")):
        if column.endswith(suffix):
            return unit
    if column.endswith("_size") or column.endswith("byte_count") or column == "ip_packet_length":
        return "bytes"
    if column.endswith("_count") or column == "active_flows":
        return "count"
    if column in ("packet_loss_rate",):
        return "%"
    return ""


def field_category(column: str, source: str) -> str:
    if column in PROVENANCE_COLUMNS:
        return "provenance"
    if column in LABEL_COLUMNS:
        return "label"
    if column in LABEL_AND_ID_COLUMNS or column in ("run_id", "record_id", "window_index", "ue_host", "rsnsd_scenario"):
        return "identifier"
    if source == "synthetic_rsnsd":
        return "synthetic"
    if column.startswith("shape_"):
        return "derived"
    if column in CONTEXT_INJECTED_COLUMNS:
        return "configured"
    provenance = load_features().get("provenance", {})
    tag = provenance.get(column, "")
    if tag.startswith("PCAP") or tag in ("TC", "OVS", "PSUTIL"):
        return "measured"
    if tag.startswith("DERIVED"):
        return "derived"
    if column in ("ether_type", "vlan_present", "vlan_priority", "broadcast_frame", "multicast_frame",
                  "ip_version", "fragmented", "ip_header_length", "hop_limit"):
        return "configured"
    return "derived"


def data_dictionary(source: str) -> pd.DataFrame:
    columns = list(SCHEMA_COLUMNS) + [c for c in EXTRA_COLUMNS if c not in SCHEMA_COLUMNS] + list(PROVENANCE_COLUMNS)
    return pd.DataFrame([
        {"field": c, "type": "string" if c in STRING_COLUMNS else "bool" if c in BOOL_COLUMNS else "number",
         "unit": unit_of(c), "category": field_category(c, source)}
        for c in columns
    ])


def stamp(df: pd.DataFrame, source: str, seed: int | None, config_id: str) -> pd.DataFrame:
    if source not in SOURCES:
        raise ContractViolation(f"unknown provenance source {source!r}")
    out = df.copy()
    out["provenance_source"] = source
    out["schema_version"] = SCHEMA_VERSION
    out["seed"] = -1 if seed is None else int(seed)
    out["config_id"] = config_id
    return out


@dataclass
class ValidationReport:
    source: str
    rows: int
    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    def as_dict(self) -> dict[str, Any]:
        return {"source": self.source, "rows": self.rows, "ok": self.ok, "errors": self.errors}


def validate(df: pd.DataFrame, source: str, raise_on_error: bool = True) -> ValidationReport:
    report = ValidationReport(source, len(df))
    err = report.errors.append

    missing = [c for c in list(SCHEMA_COLUMNS) + list(PROVENANCE_COLUMNS) if c not in df.columns]
    if missing:
        err(f"missing required columns: {missing[:10]}{'…' if len(missing) > 10 else ''}")
    if df.empty:
        err("no records")

    if "provenance_source" in df.columns:
        sources = set(df["provenance_source"].dropna().unique())
        if sources != {source}:
            err(f"provenance_source {sorted(sources)} does not match expected {source!r}")
    if "schema_version" in df.columns and set(df["schema_version"].dropna().unique()) != {SCHEMA_VERSION}:
        err(f"schema_version must be {SCHEMA_VERSION}")

    for column in df.columns:
        if column in STRING_COLUMNS or column in BOOL_COLUMNS or column not in SCHEMA_COLUMNS:
            continue
        if not (pd.api.types.is_numeric_dtype(df[column]) or pd.api.types.is_bool_dtype(df[column])):
            err(f"{column}: non-numeric values in a numeric field (dtype {df[column].dtype})")

    if "service_class" in df.columns:
        bad = set(df["service_class"].dropna().unique()) - set(SERVICE_CLASSES)
        if bad:
            err(f"service_class outside the taxonomy: {sorted(bad)}")
        if df["service_class"].isna().any():
            err("service_class has missing labels")

    measured = source in MEASURED_SOURCES
    for column in NON_NEGATIVE:
        if column in df.columns and pd.api.types.is_numeric_dtype(df[column]):
            values = df[column]
            if (values < -1e-9).any():
                err(f"{column}: negative values ({int((values < -1e-9).sum())} rows)")
            nans = values.isna().sum()
            if nans and not (measured and column in NAN_ALLOWED_MEASURED):
                err(f"{column}: {int(nans)} missing values")

    if "packet_loss_rate" in df.columns and pd.api.types.is_numeric_dtype(df["packet_loss_rate"]):
        loss = df["packet_loss_rate"]
        if ((loss < 0) | (loss > 100)).any() or loss.isna().any():
            err("packet_loss_rate must be a percentage in [0, 100]")
    numeric = {c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])}
    if {"goodput_mbps", "throughput_mbps"} <= numeric:
        if (df["goodput_mbps"] > df["throughput_mbps"] + 1e-6).any():
            err("goodput_mbps exceeds throughput_mbps")
    if {"forward_packet_count", "backward_packet_count", "packet_count"} <= numeric:
        mismatch = (df["forward_packet_count"] + df["backward_packet_count"] - df["packet_count"]).abs() > 0
        if mismatch.any():
            err(f"forward+backward packets != packet_count ({int(mismatch.sum())} rows)")

    if raise_on_error and report.errors:
        raise ContractViolation(f"{source}: " + "; ".join(report.errors))
    return report
