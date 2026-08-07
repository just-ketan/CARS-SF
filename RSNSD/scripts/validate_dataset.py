from pathlib import Path

from RSNSD.validator.validator import DatasetValidator
from RSNSD.validator.formatter import ValidationFormatter
from RSNSD.validator.exporter import ValidationExporter

validator = DatasetValidator()

report = validator.validate(
    Path("RSNSD/dataset/processed/rsnsd_dataset.csv")
)

ValidationFormatter().print_report(report)

exporter = ValidationExporter()

exporter.to_json(
    report,
    "reports/validation_report.json",
)

exporter.to_markdown(
    report,
    "reports/validation_report.md",
)

exporter.to_text(
    report,
    "reports/validation_report.txt",
)