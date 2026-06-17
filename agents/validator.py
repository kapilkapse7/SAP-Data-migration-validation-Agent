"""Validation Agent — applies extracted rules against preload Excel records."""

import logging
import re
from typing import Any

import pandas as pd

from state import MigrationState

logger = logging.getLogger(__name__)

# Column used to identify material/record in reports
MATERIAL_COLUMN_CANDIDATES = ("Material", "MATNR", "material", "matnr", "Material Number")


def _resolve_material_column(df: pd.DataFrame) -> str:
    """Find the material identifier column in the preload DataFrame."""
    for candidate in MATERIAL_COLUMN_CANDIDATES:
        if candidate in df.columns:
            return candidate
    return df.columns[0] if len(df.columns) > 0 else "Row"


def _is_blank(value: Any) -> bool:
    """Check if a cell value is considered blank."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return True
    return str(value).strip() == ""


def _expected_value_for_rule(rule: dict[str, Any]) -> str:
    """Human-readable expected value for reporting."""
    rule_type = rule.get("type", "")
    if rule_type == "equals":
        return str(rule.get("value", ""))
    if rule_type == "not_blank":
        return "Not blank"
    if rule_type == "in_list":
        return ", ".join(str(v) for v in rule.get("values", []))
    if rule_type == "regex":
        return f"Match pattern: {rule.get('pattern', '')}"
    if rule_type == "max_length":
        return f"Max length {rule.get('max_length', '')}"
    if rule_type == "min_length":
        return f"Min length {rule.get('min_length', '')}"
    if rule_type == "numeric":
        return "Numeric value"
    if rule_type == "date_format":
        return f"Date format: {rule.get('format', '')}"
    return str(rule)


def _validate_cell(value: Any, rule: dict[str, Any]) -> tuple[bool, str]:
    """
    Validate a single cell value against a rule.
    Returns (passed, error_description).
    """
    rule_type = rule.get("type", "")

    if rule_type == "not_blank":
        if _is_blank(value):
            return False, "Value is blank but field cannot be blank"
        return True, ""

    if _is_blank(value):
        return False, "Missing value"

    str_value = str(value).strip()

    if rule_type == "equals":
        expected = str(rule.get("value", "")).strip()
        if str_value.upper() != expected.upper():
            return False, f"Value must equal '{expected}'"
        return True, ""

    if rule_type == "in_list":
        allowed = [str(v).strip().upper() for v in rule.get("values", [])]
        if str_value.upper() not in allowed:
            return False, f"Value must be one of: {', '.join(allowed)}"
        return True, ""

    if rule_type == "regex":
        pattern = rule.get("pattern", "")
        if not re.fullmatch(pattern, str_value):
            return False, f"Value does not match required pattern"
        return True, ""

    if rule_type == "max_length":
        max_len = int(rule.get("max_length", 0))
        if len(str_value) > max_len:
            return False, f"Value exceeds maximum length of {max_len}"
        return True, ""

    if rule_type == "min_length":
        min_len = int(rule.get("min_length", 0))
        if len(str_value) < min_len:
            return False, f"Value is shorter than minimum length of {min_len}"
        return True, ""

    if rule_type == "numeric":
        try:
            float(str_value.replace(",", ""))
        except ValueError:
            return False, "Value must be numeric"
        return True, ""

    if rule_type == "date_format":
        fmt = rule.get("format", "YYYY-MM-DD")
        if fmt == "YYYY-MM-DD" and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str_value):
            return False, "Value must be in YYYY-MM-DD format"
        return True, ""

    return False, f"Unknown rule type: {rule_type}"


def validate_preload_data(state: MigrationState) -> MigrationState:
    """
    Validation Agent node.
    Applies extracted rules to each row in the preload DataFrame.
    """
    rules = state.get("rules", {})
    preload_df = state.get("preload_df")

    if preload_df is None or preload_df.empty:
        logger.error("Preload DataFrame is empty or missing")
        return {
            **state,
            "validation_results": [],
            "total_records": 0,
            "passed_records": 0,
            "failed_records": 0,
            "error": "Preload Excel data is empty or could not be loaded",
        }

    if not rules:
        logger.error("No validation rules available")
        return {
            **state,
            "validation_results": [],
            "total_records": len(preload_df),
            "passed_records": 0,
            "failed_records": len(preload_df),
            "error": "No validation rules were extracted",
        }

    material_col = _resolve_material_column(preload_df)
    results: list[dict[str, Any]] = []
    failed_materials: set[str] = set()

    logger.info(
        "Validating %d records against %d rules (material column: %s)",
        len(preload_df),
        len(rules),
        material_col,
    )

    for _, row in preload_df.iterrows():
        material_id = str(row.get(material_col, "Unknown"))

        for field_name, rule in rules.items():
            actual_value = row.get(field_name, row.get(field_name.upper(), row.get(field_name.lower(), None)))
            passed, error_desc = _validate_cell(actual_value, rule)

            status = "PASS" if passed else "FAIL"
            if not passed:
                failed_materials.add(material_id)

            results.append(
                {
                    "Material": material_id,
                    "Field": field_name,
                    "Expected Value": _expected_value_for_rule(rule),
                    "Actual Value": "" if _is_blank(actual_value) else str(actual_value),
                    "Status": status,
                    "Error Description": error_desc if not passed else "",
                }
            )

    total_records = len(preload_df)
    failed_records = len(failed_materials)
    passed_records = total_records - failed_records

    logger.info(
        "Validation complete: %d total, %d passed, %d failed",
        total_records,
        passed_records,
        failed_records,
    )

    return {
        **state,
        "validation_results": results,
        "total_records": total_records,
        "passed_records": passed_records,
        "failed_records": failed_records,
        "error": "",
    }
