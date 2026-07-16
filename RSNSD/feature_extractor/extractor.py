"""
Feature Extractor

Converts DatasetRecord objects into schema-compliant
machine learning features.

Author: RSNSD
"""

from RSNSD.domain.dataset import DatasetRecord

from .derived_flow_features import DerivedFlowFeatureExtractor
from .schema_mapper import SchemaMapper


class FeatureExtractor:

    def __init__(self):

        self.mapper = SchemaMapper()

        self.derived = DerivedFlowFeatureExtractor()

    def extract(
        self,
        record: DatasetRecord,
    ) -> dict:

        features = self.mapper.map(record)

        features.update(
            self.derived.extract(record)
        )

        return features