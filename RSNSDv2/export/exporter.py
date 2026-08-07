import os

class ExportEngine:
    """
    Phase 12: Export Engine
    Package dataset securely for public release.
    """
    def __init__(self, output_dir):
        self.output_dir = output_dir
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir, exist_ok=True)

    def export(self, df, report):
        csv_path = os.path.join(self.output_dir, "dataset_v2.csv")
        df.to_csv(csv_path, index=False)
        
        report_path = os.path.join(self.output_dir, "validation_report.txt")
        with open(report_path, "w") as f:
            f.write(report)
