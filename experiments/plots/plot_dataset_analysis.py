import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os

# Configuration
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATASET_PATH = os.path.join(REPO_ROOT, "RSNSD", "dataset", "raw", "rsnsd_v1.0.csv")
OUTPUT_DIR = os.path.join(REPO_ROOT, "docs", "figures")

def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)

def load_data():
    if not os.path.exists(DATASET_PATH):
        print(f"Dataset not found at {DATASET_PATH}. Please generate it first.")
        return None
    return pd.read_csv(DATASET_PATH)

def plot_service_distribution(df):
    plt.figure(figsize=(10, 6))
    sns.countplot(data=df, y='service_type', order=df['service_type'].value_counts().index, palette='viridis')
    plt.title('Service Distribution')
    plt.xlabel('Count')
    plt.ylabel('Service Type')
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/service_distribution.png")
    plt.close()

def plot_scenario_distribution(df):
    plt.figure(figsize=(10, 6))
    if 'mobility_state' in df.columns:
        sns.countplot(data=df, x='mobility_state', palette='magma')
        plt.title('Scenario (Mobility State) Distribution')
        plt.xlabel('Mobility State')
        plt.ylabel('Count')
        plt.tight_layout()
        plt.savefig(f"{OUTPUT_DIR}/scenario_distribution.png")
        plt.close()

def plot_sim_vs_syn_contribution(df):
    # Currently assuming all are simulated as per the dataset generation, 
    # but we can create a pie chart representing this.
    plt.figure(figsize=(8, 8))
    labels = ['Simulation-derived']
    sizes = [len(df)]
    plt.pie(sizes, labels=labels, autopct='%1.1f%%', colors=['#4C72B0'])
    plt.title('Simulation vs Synthetic Contribution')
    plt.savefig(f"{OUTPUT_DIR}/simulation_vs_synthetic.png")
    plt.close()

def plot_feature_correlation(df):
    numeric_df = df.select_dtypes(include=['float64', 'int64'])
    # Select a subset of features to avoid massive heatmaps
    features = ['packet_count', 'byte_count', 'mean_packet_size', 'end_to_end_latency_ms', 
                'throughput_mbps', 'bandwidth_utilization_pct', 'signal_strength_dbm']
    features = [f for f in features if f in numeric_df.columns]
    
    if features:
        plt.figure(figsize=(10, 8))
        corr = numeric_df[features].corr()
        sns.heatmap(corr, annot=True, cmap='coolwarm', fmt=".2f")
        plt.title('Feature Correlation Heatmap')
        plt.tight_layout()
        plt.savefig(f"{OUTPUT_DIR}/feature_correlation_heatmap.png")
        plt.close()

def plot_feature_distributions(df):
    plt.figure(figsize=(12, 5))
    
    plt.subplot(1, 2, 1)
    if 'end_to_end_latency_ms' in df.columns:
        sns.histplot(df['end_to_end_latency_ms'], bins=30, kde=True)
        plt.title('End-to-End Latency Distribution')
    
    plt.subplot(1, 2, 2)
    if 'throughput_mbps' in df.columns:
        sns.histplot(df['throughput_mbps'], bins=30, kde=True, color='orange')
        plt.title('Throughput Distribution')
    
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/feature_distributions.png")
    plt.close()

def plot_context_distribution(df):
    if 'time_of_day' in df.columns:
        plt.figure(figsize=(10, 6))
        sns.countplot(data=df, y='time_of_day', order=df['time_of_day'].value_counts().index, palette='Set2')
        plt.title('Context (Time of Day) Distribution')
        plt.xlabel('Count')
        plt.ylabel('Time of Day')
        plt.tight_layout()
        plt.savefig(f"{OUTPUT_DIR}/context_distribution.png")
        plt.close()

def plot_label_distribution(df):
    if 'slice_type_label' in df.columns:
        plt.figure(figsize=(8, 6))
        sns.countplot(data=df, x='slice_type_label', order=df['slice_type_label'].value_counts().index, palette='pastel')
        plt.title('Label (Slice Type) Distribution')
        plt.xlabel('Slice Type')
        plt.ylabel('Count')
        plt.tight_layout()
        plt.savefig(f"{OUTPUT_DIR}/label_distribution.png")
        plt.close()

def plot_missing_value_analysis(df):
    plt.figure(figsize=(12, 6))
    missing = df.isnull().sum()
    missing = missing[missing > 0]
    if len(missing) == 0:
        plt.text(0.5, 0.5, 'No Missing Values Found', ha='center', va='center', fontsize=15)
        plt.axis('off')
    else:
        missing.plot(kind='bar', color='red')
        plt.title('Missing Value Analysis')
        plt.ylabel('Number of Missing Values')
        plt.xticks(rotation=45, ha='right')
    
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/missing_value_analysis.png")
    plt.close()

def main():
    ensure_dir(OUTPUT_DIR)
    print("Loading dataset...")
    df = load_data()
    if df is None:
        return
    
    print("Generating dataset analysis plots...")
    plot_service_distribution(df)
    plot_scenario_distribution(df)
    plot_sim_vs_syn_contribution(df)
    plot_feature_correlation(df)
    plot_feature_distributions(df)
    plot_context_distribution(df)
    plot_label_distribution(df)
    plot_missing_value_analysis(df)
    print(f"Dataset analysis plots saved to {OUTPUT_DIR}/")

if __name__ == "__main__":
    main()
