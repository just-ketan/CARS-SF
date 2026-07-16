from RSNSD.traffic_generator.common.dataset_builder import DatasetBuilder
from RSNSD.traffic_generator.common.flow_generator import FlowGenerator
from RSNSD.traffic_generator.common.context_generator import ContextGenerator
from RSNSD.traffic_generator.common.qos_generator import QoSGenerator
from RSNSD.traffic_generator.common.sampler import Sampler

from RSNSD.traffic_generator.healthcare.telemedicine import TELEMEDICINE
from RSNSD.traffic_generator.common.scenarios import SCHOOL_HOURS


builder = DatasetBuilder(

    FlowGenerator(Sampler(seed=42)),

    ContextGenerator(seed=42),

    QoSGenerator(seed=42),

    seed=42,

)

dataset = builder.generate_dataset(

    profiles=[
        TELEMEDICINE,
    ],

    scenario=SCHOOL_HOURS,

    n_records=10,

)

print(f"Generated {len(dataset)} records")

print()

print(dataset[0].to_dict())