from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass(slots=True)
class Flow:
    """
    Represents one application flow generated during an experiment.
    """

    flow_id: str

    application: str

    service_class: str

    source: str

    destination: str

    protocol: str

    destination_port: int

    start_time: datetime = field(default_factory=datetime.now)

    end_time: Optional[datetime] = None

    status: str = "CREATED"

    experiment_id: str = ""