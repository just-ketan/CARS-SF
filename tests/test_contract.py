"""Unified RSNSD contract, seeded synthetic generation and SliceNet fallback policy."""

import numpy as np
import pandas as pd
import pytest

from classification.slicenet import (
    FALLBACK_CLASS, ModelNotTrained, SliceNetClassifier, group_labels, split_description,
)
from dataset.rsnsd import SOURCE, generate
from features.contract import (
    SCHEMA_VERSION, ContractViolation, data_dictionary, field_category, stamp, validate,
)


@pytest.fixture(scope="module")
def synthetic():
    return stamp(generate(10, seed=3), SOURCE, 3, "test")


def test_same_seed_reproduces_dataset_exactly():
    assert generate(5, seed=11).equals(generate(5, seed=11))
    assert not generate(5, seed=11).equals(generate(5, seed=12))


def test_generation_restores_global_rng():
    import random

    random.seed(99)
    expected = random.random()
    random.seed(99)
    generate(2, seed=1)
    assert random.random() == expected


def test_synthetic_records_conform_and_carry_provenance(synthetic):
    report = validate(synthetic, SOURCE)
    assert report.ok
    assert set(synthetic["schema_version"]) == {SCHEMA_VERSION}
    assert set(synthetic["provenance_source"]) == {SOURCE}
    assert synthetic["rsnsd_scenario"].nunique() > 1


def test_source_mismatch_is_rejected(synthetic):
    with pytest.raises(ContractViolation, match="provenance_source"):
        validate(synthetic, "mininet_measured")


def test_incompatible_records_are_rejected_not_coerced(synthetic):
    bad = synthetic.copy()
    bad.loc[0, "service_class"] = "video"
    bad["throughput_mbps"] = bad["throughput_mbps"].astype(str)
    bad.loc[1, "packet_loss_rate"] = 140.0
    report = validate(bad, SOURCE, raise_on_error=False)
    text = " ".join(report.errors)
    assert not report.ok
    assert "taxonomy" in text and "throughput_mbps" in text and "packet_loss_rate" in text


def test_missing_columns_and_unstamped_data_are_rejected(synthetic):
    unstamped = synthetic.drop(columns=["provenance_source", "schema_version", "seed", "config_id"])
    with pytest.raises(ContractViolation, match="missing required columns"):
        validate(unstamped, SOURCE)


def test_latency_nan_allowed_only_for_measured_sources(synthetic):
    rows = synthetic.copy()
    rows.loc[0, "end_to_end_latency_ms"] = np.nan
    assert not validate(rows, SOURCE, raise_on_error=False).ok
    measured = stamp(rows.drop(columns=list(rows.columns[-4:])), "mininet_measured", None, "run")
    assert not any("end_to_end_latency_ms" in e for e in validate(measured, "mininet_measured", raise_on_error=False).errors)


def test_field_categories_separate_measured_configured_synthetic():
    assert field_category("throughput_mbps", "synthetic_rsnsd") == "synthetic"
    assert field_category("service_class", "mininet_measured") == "label"
    assert field_category("provenance_source", "mininet_measured") == "provenance"
    dictionary = data_dictionary("mininet_measured")
    assert {"measured", "configured", "label", "provenance"} <= set(dictionary["category"])


def test_synthetic_split_holds_out_whole_scenarios(synthetic):
    assert len(set(group_labels(synthetic))) == synthetic["rsnsd_scenario"].nunique()
    assert "scenario held out" in split_description(synthetic)


def test_untrained_slicenet_never_returns_ground_truth(tmp_path, synthetic):
    classifier = SliceNetClassifier(model_path=str(tmp_path / "missing.pkl"))
    with pytest.raises(ModelNotTrained):
        classifier.predict_batch(synthetic)


def test_slicenet_abstains_on_low_confidence_and_invalid_input(tmp_path, synthetic):
    classifier = SliceNetClassifier(model_path=str(tmp_path / "rf.pkl"))
    metrics = classifier.train(synthetic, test_size=0.3)
    assert {"abstention_rate", "accepted_accuracy", "confusion_matrix"} <= set(metrics)

    rows = synthetic.head(3).copy()
    decided = classifier.predict_with_confidence(rows, threshold=0.0)
    assert not any(d["abstained"] for d in decided)
    assert all(d["abstained"] and d["reason"] == "low_confidence"
               for d in classifier.predict_with_confidence(rows, threshold=1.01))

    rows.loc[rows.index[0], classifier.feature_columns[0]] = np.inf
    assert classifier.predict_with_confidence(rows, threshold=0.0)[0]["reason"] == "invalid_features"
    assert FALLBACK_CLASS == "general"


def test_online_classifier_defers_then_falls_back(monkeypatch):
    from classification import online

    class FakeQos:
        def __init__(self):
            self.flow_rules = {}

        def classify_flow(self, flow, cls):
            self.flow_rules[flow] = cls
            return True

    class FakeModel:
        def predict_with_confidence(self, features):
            return [{"predicted": "healthcare", "confidence": 0.3, "abstained": True, "reason": "low_confidence"}]

    clf = online.OnlineSliceClassifier.__new__(online.OnlineSliceClassifier)
    clf.qos, clf.cnn, clf.rf, clf.traffic, clf.window_s = FakeQos(), None, FakeModel(), None, 5.0
    clf.enabled, clf.decisions, clf.deferrals, clf.abstentions = True, [], {}, 0
    flow = ("10.0.0.9", "10.0.1.1", 6, 4000, 80)
    packets = pd.DataFrame({
        "ts": np.arange(8) * 0.1, "flow": [flow] * 8, "direction": [1, -1] * 4, "ip_len": [200] * 8,
        "proto": [6] * 8, "tcp_flags": [0x10] * 8, "payload_len": [148] * 8,
    })
    monkeypatch.setattr(clf, "_packets", lambda: packets)
    for tick in range(online.MAX_DEFERRALS - 1):
        clf.step(tick)
        assert not clf.qos.flow_rules
    clf.step(online.MAX_DEFERRALS)
    assert clf.qos.flow_rules[flow] == FALLBACK_CLASS
    assert clf.decisions[-1]["fallback"] and clf.decisions[-1]["model_prediction"] == "healthcare"


def test_generation_is_identical_across_processes(tmp_path):
    import os
    import subprocess
    import sys

    digests = []
    for hash_seed in ("1", "2"):
        out = tmp_path / f"r{hash_seed}.csv"
        subprocess.run(
            [sys.executable, "-c", f"from dataset.rsnsd import generate; generate(4, 5).to_csv(r'{out}', index=False)"],
            check=True, env={**os.environ, "PYTHONHASHSEED": hash_seed},
        )
        digests.append(out.read_bytes())
    assert digests[0] == digests[1]
