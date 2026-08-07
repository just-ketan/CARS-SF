"""
Validation Report Exporter

Exports validation reports to JSON, Markdown and Plain Text.
"""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
import json

from RSNSD.validator.report import ValidationReport


class ValidationExporter:

    def to_json(
        self,
        report: ValidationReport,
        output_path: str | Path,
    ) -> None:

        output_path = Path(output_path)
        output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with output_path.open(
            "w",
            encoding="utf-8",
        ) as file:

            json.dump(
                asdict(report),
                file,
                indent=4,
            )

    def to_markdown(
        self,
        report: ValidationReport,
        output_path: str | Path,
    ) -> None:

        output_path = Path(output_path)
        output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        lines = [

            "# RSNSD Dataset Validation Report",

            "",

            "## Dataset Summary",

            "",

            "| Metric | Value |",

            "|-------|------:|",

            f"| Rows | {report.statistics.rows} |",

            f"| Columns | {report.statistics.columns} |",

            f"| Applications | {report.statistics.unique_applications} |",

            f"| Service Classes | {report.statistics.unique_service_classes} |",

            f"| Service Types | {report.statistics.unique_service_types} |",

            "",

            "## Schema Validation",

            "",

            f"- Status: {'PASS' if report.schema.passed else 'FAIL'}",

            f"- Missing Columns: {len(report.schema.missing_columns)}",

            f"- Unexpected Columns: {len(report.schema.unexpected_columns)}",

            f"- Duplicate Flow IDs: {report.schema.duplicate_flow_ids}",

            "",

            "## QoS Validation",

            "",

            f"- Status: {'PASS' if report.qos.passed else 'FAIL'}",

            f"- Violations: {len(report.qos.violations)}",

            "",

            "## Correlation Validation",

            "",

            f"Passed: {sum(c.passed for c in report.correlations)} / {len(report.correlations)}",

            "",

            "| Feature X | Feature Y | Pearson | Spearman | Status |",

            "|-----------|-----------|--------:|---------:|:------:|",

        ]

        for correlation in report.correlations:

            lines.append(

                f"| {correlation.feature_x} "
                f"| {correlation.feature_y} "
                f"| {correlation.pearson:.3f} "
                f"| {correlation.spearman:.3f} "
                f"| {'PASS' if correlation.passed else 'FAIL'} |"

            )

        lines.extend(

            [

                "",

                "## Outlier Analysis",

                "",

                "| Feature | IQR Outliers | Z-Score Outliers |",

                "|---------|-------------:|-----------------:|",

            ]

        )

        for outlier in report.outliers:

            lines.append(

                f"| {outlier.feature} "
                f"| {outlier.iqr_outliers} "
                f"| {outlier.zscore_outliers} |"

            )

        lines.extend(

            [

                "",

                "## Score",

                "",

                f"- Overall Score: **{report.score:.2f}/100**",

                f"- Dataset Status: **{'PASS' if report.passed else 'FAIL'}**",

            ]

        )

        if report.recommendations:

            lines.extend(

                [

                    "",

                    "## Recommendations",

                    "",

                ]

            )

            for recommendation in report.recommendations:

                lines.append(

                    f"- {recommendation}"

                )

        output_path.write_text(

            "\n".join(lines),

            encoding="utf-8",

        )

    def to_text(
        self,
        report: ValidationReport,
        output_path: str | Path,
    ) -> None:

        output_path = Path(output_path)
        output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        lines = [

            "=" * 70,

            "RSNSD DATASET VALIDATION REPORT",

            "=" * 70,

            "",

            f"Rows                 : {report.statistics.rows}",

            f"Columns              : {report.statistics.columns}",

            f"Applications         : {report.statistics.unique_applications}",

            f"Service Classes      : {report.statistics.unique_service_classes}",

            f"Service Types        : {report.statistics.unique_service_types}",

            "",

            f"Schema               : {'PASS' if report.schema.passed else 'FAIL'}",

            f"QoS                  : {'PASS' if report.qos.passed else 'FAIL'}",

            f"Correlations         : {sum(c.passed for c in report.correlations)}/{len(report.correlations)}",

            f"QoS Violations       : {len(report.qos.violations)}",

            f"Outlier Metrics      : {len(report.outliers)}",

            "",

            f"Overall Score        : {report.score:.2f}/100",

            f"Dataset Status       : {'PASS' if report.passed else 'FAIL'}",

        ]

        if report.recommendations:

            lines.extend(

                [

                    "",

                    "Recommendations",

                    "-" * 70,

                ]

            )

            for recommendation in report.recommendations:

                lines.append(

                    f"• {recommendation}"

                )

        lines.append("")
        lines.append("=" * 70)

        output_path.write_text(

            "\n".join(lines),

            encoding="utf-8",

        )