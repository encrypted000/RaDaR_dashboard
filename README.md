# RaDaR Dashboard

Internal analytics dashboard for the UK Kidney Association's Rare Disease Registry (RaDaR). Built with Streamlit, it connects to the RaDaR PostgreSQL database over an SSH tunnel and presents clinical tracking data across eight pages.

---

## Pages

| Page | What it shows |
|------|--------------|
| **Home** | Registry overview — total patients, cohort breakdown, sex distribution |
| **Biopsy Tracking** | Biopsy completeness by site and cohort, weekly KPI trend |
| **Genetics Tracking** | Genetics sample upload status, missing/resolved over time |
| **Diagnoses Tracking** | Diagnosis record completeness, new vs still-missing per week |
| **Kidney Failure Events** | RRT modality events per cohort, eGFR progression |
| **Children Dashboard** | Paediatric patient completeness across 13 BAPN sites |
| **Children Data Quality** | Out-of-range flag detection for paediatric measurements |
| **Adult Data Quality** | Out-of-range flag detection for adult measurements |

---

## How it works

The dashboard does not query the database live on every page load. Instead:

1. **Backend scripts** (`scripts/`) connect to the database, run the heavy SQL queries, and write snapshot CSVs and weekly KPI files into `outputs/`.
2. **The Streamlit app** reads from those files and caches the results for one hour. The database is only queried live for the interactive patient lookup and kidney failure event pages.

This means the dashboard stays fast even on slow connections, and the `outputs/` folder acts as a lightweight data layer between the database and the UI.

---

## Prerequisites

- Python 3.12
- SSH access to `db.radar.nhs.uk` with your private key
- The `RADAR_DB_PASS` environment variable set to the `radar_ro` database password

---

## Local setup

```bash
# 1. Create and activate a virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS / Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set the database password
set RADAR_DB_PASS=your_password_here   # Windows CMD
# export RADAR_DB_PASS=your_password   # bash

# 4. Run the backend scripts to populate outputs/
python scripts/run_all_backends.py

# 5. Launch the dashboard
streamlit run Home.py
```

The app will be available at **http://localhost:8501**.

---

## Docker

Copy the example env file and fill it in:

```bash
cp .env.example .env
```

Edit `.env`:

```
RADAR_DB_PASS=your_password_here
SSH_KEY_FILE=C:/Users/you/.ssh/id_rsa
SSH_USER=bidhanp
```

Then build and start:

```bash
docker compose up --build
```

The dashboard runs on **http://localhost:8501**. The `outputs/` folder is mounted as a volume so generated files persist across restarts. The SSH key is mounted read-only inside the container — it is never copied into the image.

To stop:

```bash
docker compose down
```

---

## Updating the data

The backend scripts pull fresh data from the database and overwrite the snapshots in `outputs/`. Run them manually whenever you want to refresh:

```bash
# All modules at once
python scripts/run_all_backends.py

# Or individually
python scripts/run_biopsy_backend.py
python scripts/run_genetics_backend.py
python scripts/run_diagnoses_backend.py
python scripts/run_children_backend.py
python scripts/run_home_backend.py
```

Each run keeps the last 12 snapshots and deletes older ones automatically.

---

## Environment variables

| Variable | Required | Description |
|----------|----------|-------------|
| `RADAR_DB_PASS` | Yes | Password for the `radar_ro` PostgreSQL user |
| `SSH_USER` | No | SSH username for `db.radar.nhs.uk` (default: `bidhanp`) |
| `SSH_KEY_PATH` | No | Path to SSH private key inside the container (default: `/run/secrets/ssh_key`) |
| `SSH_HOST` | No | SSH host (default: `db.radar.nhs.uk`) |
| `SSH_PORT` | No | SSH port (default: `22`) |

---

## Project structure

```
RaDaR_dashboard/
├── Home.py                  # App entry point — page config, global CSS, navigation
├── pages/                   # Streamlit page stubs (each delegates to app_pages/)
├── app_pages/               # Page logic and UI components
│   ├── home_page.py
│   ├── biopsy_page.py
│   ├── genetics_page.py
│   ├── diagnoses_page.py
│   ├── kidney_failure_page.py
│   ├── children_page.py
│   ├── children_quality_page.py
│   └── adult_quality_page.py
├── lib/                     # Shared library
│   ├── db.py                # Database connection via SSH tunnel
│   ├── queries.py           # All SQL queries
│   ├── outputs_reader.py    # Reads snapshot CSVs from outputs/
│   ├── home_backend.py
│   ├── biopsy_backend.py
│   ├── genetics_backend.py
│   ├── diagnoses_backend.py
│   └── children_backend.py
├── scripts/                 # Data refresh scripts (run manually or on a schedule)
├── assets/                  # Logo and static files
├── outputs/                 # Generated snapshots and reports (git-ignored)
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

---

## Notes

- `outputs/` contains CSVs with patient identifiers. It is git-ignored and must never be committed.
- The `.streamlit/secrets.toml` file (if used) is also git-ignored. Keep database credentials out of source control.
- The adult and children data quality pages flag values outside physiologically plausible ranges. Those ranges require sign-off from the clinical team before being treated as definitive.
