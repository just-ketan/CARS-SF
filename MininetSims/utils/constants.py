from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

GENERATED = PROJECT_ROOT / "generated"

PCAP_DIR = GENERATED / "pcap"

TELEMETRY_DIR = GENERATED / "telemetry"

FEATURE_DIR = GENERATED / "features"

DATASET_DIR = GENERATED / "datasets"

LOG_DIR = GENERATED / "logs"

for directory in [
    GENERATED,
    PCAP_DIR,
    TELEMETRY_DIR,
    FEATURE_DIR,
    DATASET_DIR,
    LOG_DIR,
]:
    directory.mkdir(parents=True, exist_ok=True)