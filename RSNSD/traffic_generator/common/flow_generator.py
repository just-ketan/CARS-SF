"""
Flow Generator

Generates synthetic flow records from application profiles.
"""

from uuid import uuid4

from RSNSD.domain.flow import FlowRecord

from .application_profile import ApplicationProfile
from .sampler import Sampler


class FlowGenerator:

    def __init__(self, sampler: Sampler):

        self.sampler = sampler

    def generate(self, profile: ApplicationProfile) -> FlowRecord:

        packet_size = self.sampler.sample(
            profile.packet_size_distribution
        )

        inter_arrival = self.sampler.sample(
            profile.inter_arrival_distribution
        )

        duration = self.sampler.sample(
            profile.session_duration_distribution
        )

        bitrate = self.sampler.sample(
            profile.bitrate_distribution
        )

        return FlowRecord(

            flow_id=str(uuid4()),

            application_id=profile.application_id,

            service_class=profile.service_class.value,

            packet_size=packet_size,

            inter_arrival_time_ms=inter_arrival,

            session_duration_s=duration,

            bitrate_mbps=bitrate,

            latency_requirement_ms=profile.latency_requirement_ms,

            jitter_requirement_ms=profile.jitter_requirement_ms,

            packet_loss_requirement_pct=profile.packet_loss_requirement_pct,

            throughput_requirement_mbps=profile.throughput_requirement_mbps,

            metadata=profile.metadata.copy(),
        )