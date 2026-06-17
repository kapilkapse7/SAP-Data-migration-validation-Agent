"""Report Generation Agent — creates Validation_Report.xlsx from validation results."""

import logging
from datetime import datetime
from pathlib import Path

import pandas as pd

from state import MigrationState

logger = logging.getLogger(__name__)

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "outputs"
REPORT_FILENAME = "Validation_Report.xlsx"

REPORT_COLUMNS = [
    "Material",
    "Field",
    "Expected Value",
    "Actual Value",
    "Status",
    "Error Description",
]


def generate_validation_report(state: MigrationState) -> MigrationState:
    """
    Report Generation Agent node.
    Writes validation results to an Excel report in the outputs directory.
    """
    validation_results = state.get("validation_results", [])

    try:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        report_path = OUTPUT_DIR / REPORT_FILENAME

        if validation_results:
            df = pd.DataFrame(validation_results, columns=REPORT_COLUMNS)
        else:
            df = pd.DataFrame(columns=REPORT_COLUMNS)

        # Summary sheet with run metadata
        summary_df = pd.DataFrame(
            [
                {"Metric": "Report Generated", "Value": datetime.now().strftime("%Y-%m-%d %H:%M:%S")},
                {"Metric": "Total Records", "Value": state.get("total_records", 0)},
                {"Metric": "Passed Records", "Value": state.get("passed_records", 0)},
                {"Metric": "Failed Records", "Value": state.get("failed_records", 0)},
                {"Metric": "Total Checks", "Value": len(validation_results)},
                {
                    "Metric": "Failed Checks",
                    "Value": sum(1 for r in validation_results if r.get("Status") == "FAIL"),
                },
            ]
        )

        with pd.ExcelWriter(report_path, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name="Validation Results", index=False)
            summary_df.to_excel(writer, sheet_name="Summary", index=False)

        logger.info("Validation report written to %s", report_path)

        return {**state, "report_path": str(report_path), "error": ""}

    except Exception as exc:
        logger.exception("Failed to generate validation report: %s", exc)
        return {**state, "report_path": "", "error": f"Report generation failed: {exc}"}
