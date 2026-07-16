"""
Generate RSNSD Dataset

Author: RSNSD
"""

from RSNSD.exporter import CSVExporter

from RSNSD.traffic_generator.common.dataset_builder import DatasetBuilder
from RSNSD.traffic_generator.common.flow_generator import FlowGenerator
from RSNSD.traffic_generator.common.context_generator import ContextGenerator
from RSNSD.traffic_generator.common.qos_generator import QoSGenerator
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

    QoSGenerator(seed=42),

    seed=42,

)

dataset = builder.generate_dataset(

    profiles=HEALTHCARE_PROFILE_REGISTRY,

    weights=HEALTHCARE_PROFILE_WEIGHTS,

    scenario=SCHOOL_HOURS,

    n_records=1000,

)

CSVExporter().export(

    dataset,

    "RSNSD/dataset/processed/healthcare_school.csv",

)