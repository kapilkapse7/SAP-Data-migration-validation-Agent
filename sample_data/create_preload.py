"""
Sample preload Excel generator for SAP Data Migration Validation Agent.

Run from the project root:
    python sample_data/create_preload.py

Creates sample_data/preload.xlsx with a mix of valid and invalid records
for demonstration and testing purposes.
"""

from pathlib import Path

import pandas as pd

OUTPUT_PATH = Path(__file__).resolve().parent / "preload.xlsx"

# Sample records: some pass all rules, some have intentional violations
SAMPLE_RECORDS = [
    {
        "Material": "MAT-10001",
        "MATNR": "MAT-10001",
        "MTART": "FERT",
        "MEINS": "EA",
        "MATKL": "001",
        "BRGEW": "1.25",
        "VKORG": "1000",
        "VTWEG": "10",
        "DWERK": "1000",
        "WERKS": "1000",
        "DISMM": "PD",
        "BESKZ": "E",
        "MAKTX": "Finished Product Alpha",
        "EAN11": "4006381333931",
        "ERSDA": "2024-01-15",
    },
    {
        "Material": "MAT-10002",
        "MATNR": "MAT-10002",
        "MTART": "FERT",
        "MEINS": "KG",
        "MATKL": "002",
        "BRGEW": "5.0",
        "VKORG": "2000",
        "VTWEG": "10",
        "DWERK": "2000",
        "WERKS": "2000",
        "DISMM": "PD",
        "BESKZ": "F",
        "MAKTX": "Finished Product Beta",
        "EAN11": "5901234123457",
        "ERSDA": "2024-03-22",
    },
    {
        "Material": "MAT-10003",
        "MATNR": "MAT-10003",
        "MTART": "HALB",  # FAIL: must equal FERT
        "MEINS": "EA",
        "MATKL": "001",
        "BRGEW": "2.1",
        "VKORG": "",  # FAIL: cannot be blank
        "VTWEG": "10",
        "DWERK": "1000",
        "WERKS": "1000",
        "DISMM": "PD",
        "BESKZ": "E",
        "MAKTX": "Semi-Finished Component",
        "EAN11": "12345",  # FAIL: invalid EAN pattern
        "ERSDA": "15-01-2024",  # FAIL: wrong date format
    },
    {
        "Material": "MAT-10004",
        "MATNR": "MAT-10004",
        "MTART": "FERT",
        "MEINS": "XX",  # FAIL: not in allowed list
        "MATKL": "",  # FAIL: cannot be blank
        "BRGEW": "N/A",  # FAIL: must be numeric
        "VKORG": "1000",
        "VTWEG": "20",  # FAIL: must equal 10
        "DWERK": "1000",
        "WERKS": "9999",  # FAIL: not in allowed plants
        "DISMM": "ND",  # FAIL: must equal PD
        "BESKZ": "X",  # FAIL: not in allowed list
        "MAKTX": "This material description exceeds the maximum allowed forty characters limit",
        "EAN11": "4006381333931",
        "ERSDA": "2024-06-01",
    },
    {
        "Material": "MAT-10005",
        "MATNR": "MAT-10005",
        "MTART": "FERT",
        "MEINS": "L",
        "MATKL": "003",
        "BRGEW": "0.75",
        "VKORG": "3000",
        "VTWEG": "10",
        "DWERK": "3000",
        "WERKS": "3000",
        "DISMM": "PD",
        "BESKZ": "E",
        "MAKTX": "Liquid Product Gamma",
        "EAN11": "9780201379624",
        "ERSDA": "2024-11-30",
    },
]


def main() -> None:
    """Generate the sample preload Excel file."""
    df = pd.DataFrame(SAMPLE_RECORDS)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_excel(OUTPUT_PATH, index=False, engine="openpyxl")
    print(f"Sample preload Excel created: {OUTPUT_PATH}")
    print(f"Records: {len(df)} (mix of valid and invalid data for testing)")


if __name__ == "__main__":
    main()
