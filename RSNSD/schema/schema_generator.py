"""
RSNSD Schema Generator

Generates all schema-related artifacts from the feature registry.
"""

import json
from dataclasses import asdict
from pathlib import Path

from .feature_registry import FEATURES
from .validator import SchemaValidator


OUTPUT_DIR = Path(__file__).parent


def serialize_feature(feature):
    """
    Convert Feature dataclass into JSON serializable dictionary.
    """

    d = asdict(feature)

    for key, value in d.items():
        if hasattr(value, "value"):
            d[key] = value.value

    return d


def generate_schema():

    SchemaValidator.validate(FEATURES)

    schema = [serialize_feature(feature) for feature in FEATURES]

    with open(
        OUTPUT_DIR / "schema.json",
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(schema, f, indent=4)

    print("✓ Generated schema.json")

    generate_feature_catalog(schema)

    generate_labels(schema)


def generate_feature_catalog(schema):

    lines = []

    lines.append("# RSNSD Feature Catalog\n")

    lines.append(
        "| Feature | Category | Type | Source | ML Role | Description |"
    )

    lines.append(
        "|---------|----------|------|--------|---------|-------------|"
    )

    for feature in schema:

        lines.append(
            f"| {feature['name']} "
            f"| {feature['category']} "
            f"| {feature['datatype']} "
            f"| {feature['source']} "
            f"| {feature['ml_role']} "
            f"| {feature['description']} |"
        )

    with open(
        OUTPUT_DIR / "feature_catalog.md",
        "w",
        encoding="utf-8",
    ) as f:

        f.write("\n".join(lines))

    print("✓ Generated feature_catalog.md")


def generate_labels(schema):

    labels = {}

    for feature in schema:

        if feature["ml_role"] == "label":

            labels[feature["name"]] = {
                "datatype": feature["datatype"],
                "description": feature["description"],
            }

    with open(
        OUTPUT_DIR / "labels.json",
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(labels, f, indent=4)

    print("✓ Generated labels.json")


if __name__ == "__main__":

    generate_schema()