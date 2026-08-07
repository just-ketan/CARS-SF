import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os

DATASET_PATH = "/home/ketan/Desktop/Projects/CARS-SF/RSNSD/dataset/raw/rsnsd_v1.0.csv"
OUTPUT_DIR = "/home/ketan/Desktop/Projects/CARS-SF/docs/figures"

def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)

def load_data():
    if not os.path.exists(DATASET_PATH):
        print(f"Dataset not found at {DATASET_PATH}.")
        return None
    return pd.read_csv(DATASET_PATH)

def plot_end_to_end_latency(df):
    plt.figure(figsize=(10, 6))
    if 'slice_type_label' in df.columns and 'end_to_end_latency_ms' in df.columns:
        sns.boxplot(data=df, x='slice_type_label', y='end_to_end_latency_ms', palette='Set3')
        plt.title('End-to-End Latency by Slice Type')
        plt.xlabel('Slice Type')
        plt.ylabel('Latency (ms)')
        plt.yscale('log') # Log scale for better visibility if large variance
        plt.tight_layout()
        plt.savefig(f"{OUTPUT_DIR}/end_to_end_latency.png")
    plt.close()

def plot_throughput(df):
    plt.figure(figsize=(10, 6))
    if 'slice_type_label' in df.columns and 'throughput_mbps' in df.columns:
        sns.barplot(data=df, x='slice_type_label', y='throughput_mbps', palette='Set1')
        plt.title('Average Throughput by Slice Type')
        plt.xlabel('Slice Type')
        plt.ylabel('Throughput (Mbps)')
        plt.tight_layout()
        plt.savefig(f"{OUTPUT_DIR}/throughput.png")
    plt.close()

def plot_bandwidth_utilization(df):
    plt.figure(figsize=(10, 6))
    if 'slice_type_label' in df.columns and 'bandwidth_utilization_pct' in df.columns:
        sns.violinplot(data=df, x='slice_type_label', y='bandwidth_utilization_pct', palette='muted')
        plt.title('Bandwidth Utilization by Slice Type')
        plt.xlabel('Slice Type')
        plt.ylabel('Bandwidth Utilization (%)')
        plt.tight_layout()
        plt.savefig(f"{OUTPUT_DIR}/bandwidth_utilization.png")
    plt.close()

def main():
    ensure_dir(OUTPUT_DIR)
    print("Loading data for simulation performance...")
    df = load_data()
    if df is None:
        return
    
    print("Generating simulation performance plots...")
    plot_end_to_end_latency(df)
    plot_throughput(df)
    plot_bandwidth_utilization(df)
    print(f"Simulation performance plots saved to {OUTPUT_DIR}/")

if __name__ == "__main__":
    main()
