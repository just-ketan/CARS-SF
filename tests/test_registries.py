"""Tests for registry loading and configuration."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import load_applications, load_scenarios, load_features


def test_applications_loaded():
    apps = load_applications()
    assert len(apps) >= 16
    services = {a["service_class"] for a in apps}
    assert "healthcare" in services
    assert "education" in services
    assert "agriculture" in services
    assert "general" in services


def test_scenarios_loaded():
    scenarios = load_scenarios()
    assert len(scenarios) >= 4
    ids = {s["id"] for s in scenarios}
    assert "normal" in ids
    assert "disaster" in ids


def test_features_schema():
    features = load_features()
    assert "ml_feature_columns" in features
    assert "label_columns" in features
    assert "excluded_from_ml" in features
    assert "service_class" in features["label_columns"]
    assert "service_class" in features["excluded_from_ml"]


if __name__ == "__main__":
    test_applications_loaded()
    test_scenarios_loaded()
    test_features_schema()
    print("All registry tests passed.")
