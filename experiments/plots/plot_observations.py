import matplotlib.pyplot as plt
import os
import pandas as pd
import seaborn as sns

DATASET_PATH = "/home/ketan/Desktop/Projects/CARS-SF/RSNSD/dataset/raw/rsnsd_v1.0.csv"
OUTPUT_DIR = "/home/ketan/Desktop/Projects/CARS-SF/docs/figures"

def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)

def plot_network_behaviour_comparison(df):
    plt.figure(figsize=(10, 6))
    if 'slice_type_label' in df.columns and 'end_to_end_latency_ms' in df.columns and 'throughput_mbps' in df.columns:
        sns.scatterplot(data=df.sample(min(1000, len(df))), x='end_to_end_latency_ms', y='throughput_mbps', hue='slice_type_label', palette='viridis', alpha=0.7)
        plt.title('Network Behaviour Comparison')
        plt.xlabel('Latency (ms)')
        plt.ylabel('Throughput (Mbps)')
        plt.xscale('log')
        plt.yscale('log')
        plt.tight_layout()
        plt.savefig(f"{OUTPUT_DIR}/network_behaviour_comparison.png")
    plt.close()

def plot_feature_contribution():
    # Placeholder for Feature Contribution as it requires model analysis
    plt.figure(figsize=(8, 6))
    plt.text(0.5, 0.5, "Pending Data\nFeature Contribution\nRequires Model Analysis", 
             ha='center', va='center', fontsize=18, color='gray')
    plt.axis('off')
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, "feature_contribution.png"))
    plt.close()

def main():
    ensure_dir(OUTPUT_DIR)
    print("Generating observation plots...")
    
    if os.path.exists(DATASET_PATH):
        df = pd.read_csv(DATASET_PATH)
        plot_network_behaviour_comparison(df)
    
    plot_feature_contribution()
        
    print(f"Observation plots saved to {OUTPUT_DIR}/")

if __name__ == "__main__":
    main()
