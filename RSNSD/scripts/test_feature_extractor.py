from pprint import pprint

from RSNSD.feature_extractor.extractor import FeatureExtractor

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

record = builder.generate_record(
    TELEMEDICINE,
    SCHOOL_HOURS,
)

extractor = FeatureExtractor()

features = extractor.extract(record)

pprint(features)