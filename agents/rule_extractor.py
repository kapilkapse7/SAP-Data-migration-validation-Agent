"""Rule Extraction Agent — extracts field validation rules from MDM Functional Specification."""

import json
import logging
import os
import re
from typing import Any

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from state import MigrationState

load_dotenv()

logger = logging.getLogger(__name__)

RULE_EXTRACTION_SYSTEM_PROMPT = """You are an SAP MDM (Master Data Management) functional analyst.
Your task is to read an MDM Functional Specification document and extract field-level validation rules.

Return ONLY valid JSON (no markdown, no explanation) with this structure:
{
  "FIELD_NAME": {
    "type": "<rule_type>",
    ...additional keys depending on type...
  }
}

Supported rule types:
- "equals": field must equal a specific value. Include "value": "<expected>".
- "not_blank": field cannot be empty or whitespace. No extra keys.
- "in_list": field must be one of allowed values. Include "values": ["A", "B"].
- "regex": field must match pattern. Include "pattern": "<regex>".
- "max_length": maximum character length. Include "max_length": <integer>.
- "min_length": minimum character length. Include "min_length": <integer>.
- "numeric": field must be numeric. No extra keys.
- "date_format": field must match date format. Include "format": "YYYY-MM-DD" or similar.

Use SAP field names exactly as written in the specification (e.g., MTART, VKORG, MATNR).
Extract every validation rule you can identify from the document.
"""


def _get_llm() -> ChatGoogleGenerativeAI:
    """Create Gemini LLM instance from environment configuration."""
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    return ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        temperature=0,
        google_api_key=api_key,
    )


def _parse_json_from_response(text: str) -> dict[str, Any]:
    """Extract and parse JSON from LLM response, handling markdown fences."""
    cleaned = text.strip()
    fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned)
    if fence_match:
        cleaned = fence_match.group(1).strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        brace_match = re.search(r"\{[\s\S]*\}", cleaned)
        if brace_match:
            return json.loads(brace_match.group(0))
        raise


def _fallback_rule_extraction(fs_content: str) -> dict[str, dict[str, Any]]:
    """
    Deterministic fallback parser for common MDM FS patterns when LLM output fails.
    Parses lines like: 'Field: MTART' followed by 'Rule: Must equal FERT'.
    """
    logger.warning("Using fallback rule extraction parser")
    rules: dict[str, dict[str, Any]] = {}
    current_field: str | None = None

    for raw_line in fs_content.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        field_match = re.match(r"^Field:\s*(\w+)", line, re.IGNORECASE)
        if field_match:
            current_field = field_match.group(1).upper()
            continue

        rule_match = re.match(r"^Rule:\s*(.+)", line, re.IGNORECASE)
        if rule_match and current_field:
            rule_text = rule_match.group(1).strip()
            rule = _interpret_rule_text(rule_text)
            if rule:
                rules[current_field] = rule
            current_field = None

    return rules


def _interpret_rule_text(rule_text: str) -> dict[str, Any] | None:
    """Map natural-language rule text to structured rule dict."""
    lower = rule_text.lower()

    if "cannot be blank" in lower or "must not be blank" in lower or "not blank" in lower:
        return {"type": "not_blank"}

    equals_match = re.search(r"must equal\s+(\S+)", lower)
    if equals_match:
        return {"type": "equals", "value": equals_match.group(1).upper()}

    in_list_match = re.search(r"must be one of[:\s]+(.+)", lower)
    if in_list_match:
        values = [v.strip().upper() for v in re.split(r"[,|]", in_list_match.group(1)) if v.strip()]
        return {"type": "in_list", "values": values}

    max_len_match = re.search(r"max(?:imum)?\s+length\s+(\d+)", lower)
    if max_len_match:
        return {"type": "max_length", "max_length": int(max_len_match.group(1))}

    min_len_match = re.search(r"min(?:imum)?\s+length\s+(\d+)", lower)
    if min_len_match:
        return {"type": "min_length", "min_length": int(min_len_match.group(1))}

    regex_match = re.search(r"match pattern\s+(.+)", lower)
    if regex_match:
        return {"type": "regex", "pattern": regex_match.group(1).strip()}

    if "yyyy-mm-dd" in lower or "date format" in lower:
        return {"type": "date_format", "format": "YYYY-MM-DD"}

    if "must be numeric" in lower or "numeric only" in lower:
        return {"type": "numeric"}

    return None


def extract_validation_rules(state: MigrationState) -> MigrationState:
    """
    Rule Extraction Agent node.
    Reads MDM Functional Specification content and returns structured validation rules.
    """
    fs_content = state.get("fs_content", "")
    if not fs_content or not fs_content.strip():
        logger.error("MDM Functional Specification content is empty")
        return {**state, "rules": {}, "error": "MDM Functional Specification content is empty"}

    rules: dict[str, dict[str, Any]] = {}

    try:
        llm = _get_llm()
        messages = [
            SystemMessage(content=RULE_EXTRACTION_SYSTEM_PROMPT),
            HumanMessage(
                content=(
                    "Extract all field validation rules from this MDM Functional "
                    f"Specification document:\n\n{fs_content}"
                )
            ),
        ]
        response = llm.invoke(messages)
        raw_rules = _parse_json_from_response(response.content)

        if not isinstance(raw_rules, dict):
            raise ValueError("LLM returned non-dict JSON for rules")

        for field_name, rule_data in raw_rules.items():
            if isinstance(rule_data, dict) and "type" in rule_data:
                rules[field_name.upper()] = rule_data

        logger.info("Extracted %d rules via Gemini", len(rules))

    except Exception as exc:
        logger.exception("Gemini rule extraction failed: %s", exc)
        rules = _fallback_rule_extraction(fs_content)
        if not rules:
            return {
                **state,
                "rules": {},
                "error": f"Rule extraction failed: {exc}",
            }
        logger.info("Fallback extracted %d rules", len(rules))

    return {**state, "rules": rules, "error": ""}
