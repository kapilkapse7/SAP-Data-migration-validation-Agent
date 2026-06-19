# SAP Data Migration Governance Platform

A **Role-Based** Agentic AI platform that governs SAP Master Data Migration
validation. Built on the existing multi-agent LangGraph pipeline (Rule Extraction
→ Validation → Report → Email), now extended with authentication, RBAC, a
versioned MDM Functional Specification repository, validation history, and
Plotly analytics dashboards.

## Roles

| Role | Capabilities |
|------|--------------|
| **Admin** | Create streams & migration objects, upload/version MDM Functional Specs (auto rule extraction + storage), view governance dashboard, audit trail |
| **Functional Consultant (FC)** | Ad-hoc workspace: upload FS + preload, run validation, view rules/summary, download report & email draft (workflow unchanged) |
| **Business Analyst (BA)** | Select Stream → Object → auto-load latest approved rules → upload preload → validate → view results & dashboards. **Cannot upload FS.** |

## Architecture

```
Stream
 └── Migration Object
      └── MDM Functional Specification (versioned)
           └── Validation Rules (JSON)
                └── Validation History (runs)
```

### Role-aware LangGraph workflow

```
Admin:  START → Rule Extraction → Store Rules → END
FC:     START → Rule Extraction → Validation → Report → Email → END
BA:     START → Load Stored Rules → Validation → Report → Email → END
```

A single compiled graph routes by `state["mode"]` (see `graph.py`).

## Project Structure

```
Agent/
├── app.py                      # Entry point: login + role routing
├── config.py                   # Paths, DB URL, roles, API-key helpers
├── graph.py                    # Role-aware LangGraph workflow
├── state.py                    # Shared pipeline state (extended)
├── requirements.txt
├── .env.example
├── agents/
│   ├── rule_extractor.py       # (existing) Gemini rule extraction
│   ├── validator.py            # (existing) rule application
│   ├── report_generator.py     # (existing) Excel report
│   ├── email_generator.py      # (existing) email draft
│   ├── rule_store.py           # NEW — Admin: persist FS version + rules
│   └── rule_loader.py          # NEW — BA: load latest approved rules
├── auth/
│   ├── security.py             # PBKDF2 password hashing (stdlib)
│   └── auth_service.py         # login / user management
├── database/
│   ├── models.py               # SQLAlchemy ORM models
│   ├── session.py              # engine + session
│   └── seed.py                 # seed users, streams, objects
├── services/
│   ├── file_parser.py          # (existing)
│   ├── stream_service.py       # streams & objects CRUD
│   ├── fs_service.py           # FS versioning + rule persistence
│   ├── validation_service.py   # run persistence + analytics
│   └── audit_service.py        # audit trail
├── ui/
│   ├── login.py  sidebar.py  common.py
│   ├── admin_view.py  fc_view.py  ba_view.py
│   └── dashboards.py           # Plotly dashboards
├── sample_data/                # sample FS + preload
├── data/                       # SQLite DB + stored FS documents (auto-created)
└── outputs/                    # Validation_Report.xlsx
```

## Database Schema

`users`, `streams`, `objects`, `functional_specs` (versioned), `validation_rules`,
`validation_runs`, plus `audit_logs` for the audit trail. See `database/models.py`.

## Setup

### 1. Navigate to the project
```powershell
cd C:\new2\Agent\Agent
```

### 2. (Recommended) Create a virtual environment
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 3. Install dependencies
```powershell
py -m pip install -r requirements.txt
```

### 4. Configure environment
```powershell
copy .env.example .env
```
Edit `.env` and set your Gemini key (optional — fallback parser works without it):
```
GOOGLE_API_KEY=your_actual_api_key_here
```

### 5. Initialize and seed the database
```powershell
py -m database.seed
```
This creates `data/governance.db`, the default users, and the O2C / P2P / R2R /
MDG / SCM streams with their objects.

**Default logins:**

| Role | Username | Password |
|------|----------|----------|
| Admin | `admin` | `admin123` |
| Functional Consultant | `consultant` | `fc123` |
| Business Analyst | `analyst` | `ba123` |

> Change these credentials before any real use.

### 6. (Optional) Generate sample preload data
```powershell
py sample_data\create_preload.py
```

## Run

```powershell
py -m streamlit run app.py
```
Open http://localhost:8501 and log in.

### Typical end-to-end flow
1. **Admin** logs in → *Manage Streams* (or use seeded ones) → *Manage Objects*
   → *Upload / Edit FS* (select stream + object, upload FS, click **Extract Rules
   & Store Version**). Rules are now stored and versioned.
2. **Business Analyst** logs in → *Run Validation* → select Stream → Object →
   rules auto-load → upload preload Excel → **Run Validation** → review summary,
   failures, report, email. Then visit *Global Dashboard* for analytics.
3. **Functional Consultant** logs in → upload FS + preload → **Run Validation**
   (ad-hoc, no stored objects needed).

## Notes
- SQLite is used by default; override with the `DATABASE_URL` env var for another
  SQLAlchemy-supported database.
- Passwords are hashed with PBKDF2-HMAC-SHA256 (stdlib, no extra dependency).
- All key actions (login, create stream/object, FS upload, validation runs) are
  written to the audit trail and `migration_agent.log`.

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `no such table` | Run `py -m database.seed` first |
| Login fails | Re-run the seed; verify credentials above |
| `No Gemini API key found` | Set `GOOGLE_API_KEY` in `.env`; fallback parser still works |
| BA sees "no approved rules" | An Admin must upload an FS for that object first |
| Port in use | `py -m streamlit run app.py --server.port 8502` |
