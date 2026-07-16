"""
Dataset Builder

Coordinates the complete dataset generation pipeline.
"""

from typing import Sequence
import random

from RSNSD.domain.dataset import DatasetRecord

from .context_generator import ContextGenerator
from .flow_generator import FlowGenerator
from .qos_generator import QoSGenerator
from RSNSD.traffic_generator.common.profile_sampler import (
    ProfileSampler,
)

class DatasetBuilder:

    def __init__(
        self,
        flow_generator: FlowGenerator,
        context_generator: ContextGenerator,
        qos_generator: QoSGenerator,
        seed: int | None = None,
    ):

        self.flow_generator = flow_generator
        self.context_generator = context_generator
        self.qos_generator = qos_generator

        self.random = random.Random(seed)
        self.profile_sampler = ProfileSampler(seed)

    # ----------------------------------------------------------
    # Generate One Record
    # ----------------------------------------------------------

    def generate_record(
        self,
        profile,
        scenario,
    ) -> DatasetRecord:

        flow = self.flow_generator.generate(profile)

        context = self.context_generator.generate(
            profile,
            scenario,
        )

        qos = self.qos_generator.generate(
            flow,
            context,
        )

        return DatasetRecord(
            flow=flow,
            context=context,
            qos=qos,
        )

    # ----------------------------------------------------------
    # Generate Entire Dataset
    # ----------------------------------------------------------

    def generate_dataset(
        self,
        profiles,
        scenario,
        n_records: int,
        weights=None,
    ):

        dataset = []

        for _ in range(n_records):

            if weights is None:
                profile = self.random.choice(profiles)
            else:
                profile = self.profile_sampler.sample(
                    profiles,
                    weights,
                    scenario,
                )

            record = self.generate_record(
                profile,
                scenario,
            )

            dataset.append(record)

        return dataset