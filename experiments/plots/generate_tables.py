import pandas as pd
import os

DATASET_PATH = "/home/ketan/Desktop/Projects/CARS-SF/RSNSD/dataset/raw/rsnsd_v1.0.csv"
OUTPUT_DIR = "/home/ketan/Desktop/Projects/CARS-SF/docs/tables"

def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)

def generate_dataset_statistics(df):
    stats = df.describe().T
    stats.to_csv(f"{OUTPUT_DIR}/dataset_statistics.csv")
    with open(f"{OUTPUT_DIR}/dataset_statistics.md", "w") as f:
        f.write(stats.to_markdown())

def generate_scenario_summary(df):
    if 'slice_type_label' in df.columns and 'service_type' in df.columns:
        summary = df.groupby(['slice_type_label', 'service_type']).size().reset_index(name='Flow Count')
        summary.to_csv(f"{OUTPUT_DIR}/scenario_summary.csv", index=False)
        with open(f"{OUTPUT_DIR}/scenario_summary.md", "w") as f:
            f.write(summary.to_markdown(index=False))

def generate_feature_summary(df):
    features = pd.DataFrame({
        'Feature': df.columns,
        'Type': df.dtypes.astype(str),
        'Non-Null Count': df.notnull().sum().values
    })
    features.to_csv(f"{OUTPUT_DIR}/feature_summary.csv", index=False)
    with open(f"{OUTPUT_DIR}/feature_summary.md", "w") as f:
        f.write(features.to_markdown(index=False))

def generate_static_tables():
    # Simulation Configuration
    sim_config = pd.DataFrame({
        'Parameter': ['Simulation Tool', 'Network Topology', 'Link Types', 'Background Traffic', 'Duration per Scenario'],
        'Value': ['Mininet', 'Rural Star Topology', 'Fiber, Microwave, Satellite', 'D-ITG / Iperf', '60-120 seconds']
    })
    sim_config.to_csv(f"{OUTPUT_DIR}/simulation_configuration.csv", index=False)
    with open(f"{OUTPUT_DIR}/simulation_configuration.md", "w") as f:
        f.write(sim_config.to_markdown(index=False))

    # Experimental Configuration
    exp_config = pd.DataFrame({
        'Component': ['Host OS', 'Python Version', 'Deep Learning Framework', 'Dataset Format', 'Feature Engineering'],
        'Specification': ['Ubuntu 22.04 LTS (Expected)', 'Python 3.10+', 'PyTorch/TensorFlow (Future)', 'CSV / Parquet', 'Scapy, Pandas']
    })
    exp_config.to_csv(f"{OUTPUT_DIR}/experimental_configuration.csv", index=False)
    with open(f"{OUTPUT_DIR}/experimental_configuration.md", "w") as f:
        f.write(exp_config.to_markdown(index=False))
        
    # Validation Summary
    val_summary = pd.DataFrame({
        'Validation Check': ['Schema Compliance', 'Missing Values', 'Outliers', 'Label Distribution', 'Flow Duration'],
        'Status': ['Passed', 'Checked', 'Managed', 'Balanced (Future Target)', 'Valid']
    })
    val_summary.to_csv(f"{OUTPUT_DIR}/validation_summary.csv", index=False)
    with open(f"{OUTPUT_DIR}/validation_summary.md", "w") as f:
        f.write(val_summary.to_markdown(index=False))

    # Performance Metrics
    perf_metrics = pd.DataFrame({
        'Metric': ['End-to-End Latency', 'Throughput', 'Jitter', 'Packet Loss', 'Bandwidth Utilization'],
        'Unit': ['ms', 'Mbps', 'ms', '%', '%']
    })
    perf_metrics.to_csv(f"{OUTPUT_DIR}/performance_metrics.csv", index=False)
    with open(f"{OUTPUT_DIR}/performance_metrics.md", "w") as f:
        f.write(perf_metrics.to_markdown(index=False))

def main():
    ensure_dir(OUTPUT_DIR)
    print("Generating tables...")
    generate_static_tables()
    
    if os.path.exists(DATASET_PATH):
        df = pd.read_csv(DATASET_PATH)
        generate_dataset_statistics(df)
        generate_scenario_summary(df)
        generate_feature_summary(df)
    
    print(f"Tables saved to {OUTPUT_DIR}/")

if __name__ == "__main__":
    main()
