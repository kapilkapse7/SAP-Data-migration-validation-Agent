"""Email Generation Agent — drafts a business-ready summary email of validation findings."""

import logging
import os
from collections import Counter
from typing import Any

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from state import MigrationState

load_dotenv()

logger = logging.getLogger(__name__)

EMAIL_SYSTEM_PROMPT = """You are an SAP Data Migration project manager writing a professional
email to business stakeholders about MDM preload validation results.

Write a clear, concise, business-friendly email that:
- Uses a professional tone suitable for SAP project communications
- Summarizes validation outcomes (total, passed, failed records)
- Highlights the most critical issues found
- Provides actionable recommended next steps
- Does NOT use overly technical jargon

Format the email with:
- Subject line (prefix with "Subject: ")
- Greeting
- Executive summary paragraph
- Key findings (bullet points)
- Recommended actions (numbered list)
- Professional closing

Do not invent statistics — use only the data provided in the prompt.
"""


def _build_issue_summary(validation_results: list[dict[str, Any]], top_n: int = 5) -> str:
    """Build a text summary of top validation failures for the LLM prompt."""
    failures = [r for r in validation_results if r.get("Status") == "FAIL"]
    if not failures:
        return "No validation failures detected."

    field_counts = Counter(r.get("Field", "Unknown") for r in failures)
    lines = [f"- {field}: {count} failure(s)" for field, count in field_counts.most_common(top_n)]

    sample_failures = failures[:3]
    for item in sample_failures:
        lines.append(
            f"  Example: Material {item.get('Material')} — {item.get('Field')} "
            f"(expected: {item.get('Expected Value')}, actual: {item.get('Actual Value') or 'blank'})"
        )

    return "\n".join(lines)


def _fallback_email_draft(state: MigrationState) -> str:
    """Generate a template email when Gemini is unavailable."""
    total = state.get("total_records", 0)
    passed = state.get("passed_records", 0)
    failed = state.get("failed_records", 0)
    issue_summary = _build_issue_summary(state.get("validation_results", []))

    return f"""Subject: SAP MDM Preload Validation Results — Action Required

Dear Team,

The SAP Master Data Migration preload validation has been completed. Please find the summary below.

Executive Summary:
A total of {total} material records were validated against the MDM Functional Specification rules.
{passed} record(s) passed all checks and {failed} record(s) failed one or more validations.

Key Findings:
{issue_summary}

Recommended Actions:
1. Review the attached Validation_Report.xlsx for detailed failure information.
2. Correct failed records in the source system and regenerate the preload file.
3. Re-run validation after corrections before proceeding to SAP load.

Please let us know if you need support resolving the identified data quality issues.

Best regards,
Kapil Kapse
"""


def generate_email_draft(state: MigrationState) -> MigrationState:
    """
    Email Generation Agent node.
    Uses Gemini to produce a business-ready email summarizing validation findings.
    """
    total = state.get("total_records", 0)
    passed = state.get("passed_records", 0)
    failed = state.get("failed_records", 0)
    validation_results = state.get("validation_results", [])
    issue_summary = _build_issue_summary(validation_results)

    prompt_context = f"""
Validation Statistics:
- Total Records: {total}
- Passed Records: {passed}
- Failed Records: {failed}
- Total Field Checks: {len(validation_results)}
- Failed Field Checks: {sum(1 for r in validation_results if r.get('Status') == 'FAIL')}

Issue Summary:
{issue_summary}

Report Location: {state.get('report_path', 'Validation_Report.xlsx')}
"""

    try:
        api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            temperature=0.3,
            google_api_key=api_key,
        )
        messages = [
            SystemMessage(content=EMAIL_SYSTEM_PROMPT),
            HumanMessage(content=f"Draft the validation summary email using this data:\n{prompt_context}"),
        ]
        response = llm.invoke(messages)
        email_draft = response.content.strip()
        logger.info("Email draft generated via Gemini")

    except Exception as exc:
        logger.exception("Gemini email generation failed, using fallback: %s", exc)
        email_draft = _fallback_email_draft(state)

    return {**state, "email_draft": email_draft, "error": ""}
