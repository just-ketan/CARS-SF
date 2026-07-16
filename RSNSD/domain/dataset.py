from dataclasses import asdict
from dataclasses import dataclass

from RSNSD.domain.context import ContextRecord
from RSNSD.domain.flow import FlowRecord
from RSNSD.domain.qos import QoSRecord


@dataclass(slots=True)
class DatasetRecord:

    flow: FlowRecord
    context: ContextRecord
    qos: QoSRecord

    def to_dict(self):

        row = {}

        flow = asdict(self.flow)

        metadata = flow.pop("metadata", {})

        row.update(flow)
        row.update(metadata)
        row.update(asdict(self.context))
        row.update(asdict(self.qos))

        return row