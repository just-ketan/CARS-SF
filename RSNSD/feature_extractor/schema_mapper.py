"""
Schema Mapper

Maps DatasetRecord objects into the exact feature names
defined in the schema registry.
"""

from dataclasses import asdict

from RSNSD.domain.dataset import DatasetRecord
from RSNSD.schema.feature_registry import FEATURES


class SchemaMapper:
    """
    Converts DatasetRecord into a schema-compliant dictionary.
    """

    def map(self, record: DatasetRecord) -> dict:

        # ------------------------------
        # Flatten all domain objects
        # ------------------------------

        flow = asdict(record.flow)
        metadata = flow.pop("metadata", {})

        available = {}

        available.update(flow)
        available.update(metadata)
        available.update(asdict(record.context))
        available.update(asdict(record.qos))

        # ------------------------------
        # Keep only schema features
        # ------------------------------

        output = {}

        for feature in FEATURES:

            name = feature.name

            if name in available:
                output[name] = available[name]

            else:
                output[name] = None

        return output