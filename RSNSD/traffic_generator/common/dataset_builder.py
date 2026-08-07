"""
Dataset Builder

Coordinates the complete dataset generation pipeline.
"""

from typing import Sequence
import random

from RSNSD.domain.dataset import DatasetRecord

from .context_generator import ContextGenerator
from .flow_generator import FlowGenerator
from RSNSD.qos import QoSEngine
from RSNSD.traffic_generator.common.profile_sampler import (
    ProfileSampler,
)
from RSNSD.traffic_generator.common.clock import SimulationClock
from RSNSD.traffic_generator.common.scenario_evolver import ScenarioEvolver
from datetime import datetime

class DatasetBuilder:

    def __init__(
        self,
        flow_generator: FlowGenerator,
        context_generator: ContextGenerator,
        seed: int | None = None,
    ):

        self.flow_generator = flow_generator
        self.context_generator = context_generator
        self.qos_engine = QoSEngine()
        self.random = random.Random(seed)
        self.profile_sampler = ProfileSampler(seed)
        self.clock = SimulationClock(start_time=datetime(2026, 1, 1, 6, 0), step_minutes=5)

    # ----------------------------------------------------------
    # Generate One Record
    # ----------------------------------------------------------

    def generate_record(
        self,
        profile,
        scenario,
    ) -> DatasetRecord:

        context = self.context_generator.generate(
            profile,
            scenario,
            self.clock,
        )

        flow = self.flow_generator.generate(profile, context=context)

        qos = self.qos_engine.compute(
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
        """
        Yields records one-by-one to support streaming generation.
        """
        evolver = ScenarioEvolver(scenario)

        for _ in range(n_records):
            self.clock.tick()
            current_scenario = evolver.evolve(self.clock)

            if weights is None:
                profile = self.random.choice(profiles)
            else:
                profile = self.profile_sampler.sample(
                    profiles,
                    weights,
                    current_scenario,
                    self.clock,
                )

            record = self.generate_record(
                profile,
                current_scenario,
            )

            yield record