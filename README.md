# SAP Data Migration Validation Agent

Production-ready Agentic AI application that automates SAP Master Data Migration preload validation using business rules defined in an MDM Functional Specification document.

## Features

- **Multi-agent LangGraph workflow** with four specialized agents:
  1. **Rule Extraction Agent** — extracts field validation rules from MDM FS using Gemini
  2. **Validation Agent** — validates preload Excel records against extracted rules
  3. **Report Generation Agent** — creates `Validation_Report.xlsx`
  4. **Email Generation Agent** — drafts a business-ready summary email

- **Streamlit UI** for file uploads, validation execution, and result download
- **Fallback parsers** when Gemini API is unavailable
- **Structured logging** to console and `migration_agent.log`

## Project Structure

```
migration_agent/
├── app.py                      # Streamlit application
├── graph.py                    # LangGraph workflow
├── state.py                    # Shared pipeline state
├── requirements.txt
├── .env.example
├── agents/
│   ├── rule_extractor.py
│   ├── validator.py
│   ├── report_generator.py
│   └── email_generator.py
├── sample_data/
│   ├── mdm_fs.txt              # Sample MDM Functional Specification
│   ├── create_preload.py       # Script to generate sample preload Excel
│   └── preload.xlsx            # Generated sample data (run create_preload.py)
└── outputs/
    └── Validation_Report.xlsx  # Generated after validation run
```

## Prerequisites

- Python 3.11 or higher
- Google Gemini API key (optional but recommended for AI features)

## Setup Instructions

### 1. Clone or navigate to the project

```powershell
cd C:\Users\kapil\migration_agent
```

### 2. Create a virtual environment (recommended)

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```powershell
py -m pip install -r requirements.txt
```

> On Windows, use `py` if `python` is not on your PATH.

### 4. Configure environment variables

```powershell
copy .env.example .env
```

Edit `.env` and set your Google Gemini API key:

```
GOOGLE_API_KEY=your_actual_api_key_here
```

Get a free API key at: https://aistudio.google.com/apikey

### 5. Generate sample preload data

```powershell
py sample_data\create_preload.py
```

## Run Instructions

Start the Streamlit application:

```powershell
py -m streamlit run app.py
```

The app opens in your browser (default: http://localhost:8501).

### Using the Application

1. **Upload MDM Functional Specification** — `.txt`, `.md`, `.csv`, or `.xlsx`
2. **Upload Preload Excel** — `.xlsx` or `.xls`
3. Click **Run Validation**
4. Review extracted rules, validation summary, and failed records
5. **Download** `Validation_Report.xlsx` and the email draft

### Testing with Sample Data

1. Expand **"Use sample data (for testing)"**
2. Check both sample data options
3. Click **Run Validation**

The sample preload contains 5 records with intentional violations for demonstration.

## Validation Rule Types

| Rule Type    | Description                          | Example                          |
|-------------|--------------------------------------|----------------------------------|
| `equals`    | Field must equal a value             | MTART must equal FERT            |
| `not_blank` | Field cannot be empty                | VKORG cannot be blank            |
| `in_list`   | Field must be in allowed values      | WERKS must be 1000, 2000, 3000   |
| `regex`     | Field must match a pattern           | EAN11 must match 13-digit EAN    |
| `max_length`| Maximum character length             | MAKTX max length 40              |
| `min_length`| Minimum character length             |                                  |
| `numeric`   | Field must be numeric                | BRGEW must be numeric            |
| `date_format`| Date format validation              | ERSDA in YYYY-MM-DD              |

## LangGraph Workflow

```
START
  ↓
Rule Extraction Agent
  ↓
Validation Agent
  ↓
Report Generation Agent
  ↓
Email Generation Agent
  ↓
END
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `No Gemini API key found` | Copy `.env.example` to `.env` and set `GOOGLE_API_KEY` |
| Fallback rules used | Check API key; fallback parser still extracts basic rules from FS |
| Excel read error | Ensure preload file is valid `.xlsx` with expected SAP field columns |
| Port in use | Run `streamlit run app.py --server.port 8502` |

## License

Internal use — SAP Data Migration project tooling.
# SAP-Data-migration-validation-Agent
