"""
Generate RSNSD Dataset

Author: RSNSD
"""

from RSNSD.exporter import CSVExporter

from RSNSD.traffic_generator.common.dataset_builder import DatasetBuilder
from RSNSD.traffic_generator.common.flow_generator import FlowGenerator
from RSNSD.traffic_generator.common.context_generator import ContextGenerator
from RSNSD.traffic_generator.common.sampler import Sampler

from RSNSD.traffic_generator.common.scenarios import SCHOOL_HOURS

from RSNSD.traffic_generator import (
    ALL_PROFILES,
    ALL_WEIGHTS,
)


builder = DatasetBuilder(

    FlowGenerator(

        Sampler(seed=42)

    ),

    ContextGenerator(seed=42),

    seed=42,

)

dataset = builder.generate_dataset(

    profiles=ALL_PROFILES,

    weights=ALL_WEIGHTS,

    scenario=SCHOOL_HOURS,

    n_records=1000,

)

CSVExporter().export(

    dataset,

    "RSNSD/dataset/processed/rsnsd_dataset.csv"

)