"""
Master script to generate, balance, validate, and package the RSNSD dataset.
"""

import os
import sys
import pandas as pd
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from RSNSD.exporter.csv_exporter import CSVExporter
from RSNSD.traffic_generator.common.dataset_builder import DatasetBuilder
from RSNSD.traffic_generator.common.flow_generator import FlowGenerator
from RSNSD.traffic_generator.common.context_generator import ContextGenerator
from RSNSD.traffic_generator.common.sampler import Sampler

from RSNSD.traffic_generator import ALL_PROFILES
from RSNSD.schema.feature_registry import FEATURES
from RSNSD.domain.enums import ServiceClass, SliceType, MobilityProfile, DeviceType

def balance_weights(profiles):
    """
    Generate weights to ensure equal representation of Service Classes and Slice Types.
    """
    class_counts = {sc: sum(1 for p in profiles if p.service_class == sc) for sc in ServiceClass}
    slice_counts = {st: sum(1 for p in profiles if p.slice_type == st) for st in SliceType}
    
    weights = []
    for p in profiles:
        # Base weight to balance classes
        w_class = 1.0 / max(1, class_counts[p.service_class])
        w_slice = 1.0 / max(1, slice_counts[p.slice_type])
        weights.append(w_class * w_slice)
        
    return weights

def generate_balanced_dataset(n_records_per_scenario=100):
    print("Initializing components...")
    
    sampler = Sampler(seed=42)
    fg = FlowGenerator(sampler)
    cg = ContextGenerator(seed=42)
    builder = DatasetBuilder(fg, cg, seed=42)
    
    from RSNSD.context.scenarios import ALL_SCENARIOS
    scenarios = ALL_SCENARIOS
    weights = balance_weights(ALL_PROFILES)
    
    for scenario in scenarios:
        print(f"Generating for scenario: {scenario.name} (evolving over time)")
        for record in builder.generate_dataset(
            profiles=ALL_PROFILES,
            weights=weights,
            scenario=scenario,
            n_records=n_records_per_scenario
        ):
            yield record

def validate_dataset(csv_path, output_dir):
    print("Running Statistical Validation...")
    from RSNSD.validator.validator import DatasetValidator
    from RSNSD.validator.plots import ValidationPlots
    
    validator = DatasetValidator()
    report = validator.validate(csv_path)
    
    report_path = os.path.join(output_dir, "validation_report.md")
    with open(report_path, "w") as f:
        # Assuming report object has some markdown capability or we just write a simple one.
        # It's an object with statistics, so we extract from it.
        f.write("# Dataset Validation Report\n\n")
        f.write(f"Total Score: {report.score}/100\n")
        f.write(f"Passed: {report.passed}\n\n")
        
        f.write("## Component Scores\n")
        f.write(f"- Schema: {report.schema_score}/25\n")
        f.write(f"- QoS: {report.qos_score}/25\n")
        f.write(f"- Correlation: {report.correlation_score}/20\n")
        f.write(f"- Distribution: {report.distribution_score}/15\n")
        f.write(f"- Outliers: {report.outlier_score}/15\n\n")
        
        f.write("## Schema Details\n")
        f.write(f"Missing columns: {report.schema.missing_columns}\n")
        f.write(f"Unexpected columns: {report.schema.unexpected_columns}\n")
        f.write(f"Missing values: {report.schema.missing_values}\n\n")
        
        f.write("## Recommendations\n")
        for rec in report.recommendations:
            f.write(f"- {rec}\n")
            
    print(f"Validation Score: {report.score}/100")
    print(f"Validation Result: {'PASS' if report.passed else 'FAIL'}")
    
    print("Generating validation plots...")
    df = pd.read_csv(csv_path)
    
    # Drop columns that are completely empty (features defined in schema but not generated)
    df.dropna(axis=1, how='all', inplace=True)
    df.fillna(0, inplace=True)
    df.to_csv(csv_path, index=False)
    
    plotter = ValidationPlots(output_dir)
    plotter.generate_pca(df, target_col="service_class")
    plotter.generate_correlation_matrix(df)
    plotter.generate_class_distribution(df, target_col="service_class")
    plotter.generate_class_distribution(df, target_col="slice_type")
    
    # Save advanced stats (Mutual info, Feature importance)
    if report.statistics.mutual_information:
        mi_df = pd.DataFrame(list(report.statistics.mutual_information.items()), columns=['Feature', 'Mutual Information'])
        mi_df.sort_values('Mutual Information', ascending=False).to_csv(os.path.join(output_dir, "mutual_information.csv"), index=False)
        
    if report.statistics.feature_importance:
        fi_df = pd.DataFrame(list(report.statistics.feature_importance.items()), columns=['Feature', 'Importance'])
        fi_df.sort_values('Importance', ascending=False).to_csv(os.path.join(output_dir, "feature_importance.csv"), index=False)
        
    print("Validation complete. Reports saved in dataset/metadata/")

def package_dataset():
    base_dir = os.path.join(os.path.dirname(__file__), "..", "dataset")
    raw_dir = os.path.join(base_dir, "raw")
    processed_dir = os.path.join(base_dir, "processed")
    metadata_dir = os.path.join(base_dir, "metadata")
    
    os.makedirs(raw_dir, exist_ok=True)
    os.makedirs(processed_dir, exist_ok=True)
    os.makedirs(metadata_dir, exist_ok=True)
    
    records = generate_balanced_dataset(6000)
    
    csv_path = os.path.join(raw_dir, "rsnsd_v1.0.csv")
    print(f"Exporting to {csv_path}...")
    CSVExporter().export(records, csv_path)
    
    validate_dataset(csv_path, metadata_dir)
    
    # Generate README and other files
    with open(os.path.join(base_dir, "README.md"), "w") as f:
        f.write("# RSNSD Dataset v1.0\n\nResearch-grade synthetic dataset for intelligent network slicing in rural 5G networks.\n")
        
    with open(os.path.join(base_dir, "CITATION.cff"), "w") as f:
        f.write("cff-version: 1.2.0\nmessage: If you use this dataset, please cite it as below.\nauthors:\n  - family-names: Researcher\n    given-names: AI\ntitle: Rural Service-aware Network Slice Dataset (RSNSD)\nversion: 1.0.0\ndate-released: 2026-07-17\n")
        
    with open(os.path.join(base_dir, "CHANGELOG.md"), "w") as f:
        f.write("# Changelog\n\n## [1.0.0] - 2026-07-17\n- Initial release of fully balanced, scenario-aware, time-evolved synthetic dataset.\n")

    print("Packaging complete. RSNSD v1.0 Ready for Research.")

if __name__ == "__main__":
    package_dataset()
