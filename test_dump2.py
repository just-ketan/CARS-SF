import sys
import os
import pandas as pd
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))
from RSNSD.scripts.generate_release import generate_balanced_dataset
from RSNSD.feature_extractor.extractor import FeatureExtractor
records = generate_balanced_dataset(1)
ext = FeatureExtractor()
chunk = [ext.extract(record) for record in records]
df = pd.DataFrame(chunk)
print(df["forward_packet_count"].head())
