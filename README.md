# Urban Mobility Data Explorer

A full-stack web application for exploring NYC yellow taxi trips. A Python pipeline cleans the raw TLC data and loads it into a normalized SQLite database, a Flask API serves it, and a browser dashboard lets you filter, sort and visualize urban mobility patterns.

- **Video walkthrough (5 min):** TODO: paste video link
- **Team participation sheet:** TODO: paste sheet link
- **GitHub repository:** TODO: paste repo link

> Items marked `TODO` are details only the team knows. Fill them in and delete this note before submitting.

---

## Features

- Data pipeline that cleans trips, logs every excluded record with its reason, and engineers derived features: **trip duration**, **average speed**, **tip percentage** and a **pickup hour bucket**
- Normalized SQLite schema (zones, rate codes, payment types, trips) with indexes matched to dashboard filters
- Flask REST API with filtering, sorting and pagination
- Dashboard with filters, a sortable trips table, summary statistics and charts
- A hand-written algorithm (no built-in sort/heap/counter helpers) used by the API: TODO name the algorithm and the endpoint that uses it

---

## Project Structure

```
.
├── README.md
├── requirements.txt
├── .gitignore
├── backend/
│   ├── app.py              # Flask app and routes
│   ├── db.py               # SQLite connection helper
│   └── algorithms.py       # Custom algorithm implementation
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── app.js
├── db/
│   └── schema.sql          # Database schema (tables, keys, indexes)
├── data/                   # Raw data files go here (not committed)
├── logs/
│   └── excluded_records.csv  # Log of removed/suspicious records
├── scripts/                # Exploration and pipeline scripts
└── docs/                   # Notes and the PDF report
```

> TODO: adjust this tree to match your actual folders (for example, where `pipeline.py` lives).

---

## Prerequisites

- Python 3.10 or newer (TODO: state the version you used)
- Git
- A modern web browser

No database server is needed. The project uses SQLite, which ships with Python.

---

## Setup

### 1. Clone the repository

```bash
git clone TODO-repo-url
cd TODO-project-folder
```

### 2. Create and activate a virtual environment

**Windows (PowerShell):**
```powershell
python -m venv venv
venv\Scripts\Activate.ps1
```

**Windows (Command Prompt):**
```cmd
python -m venv venv
venv\Scripts\activate.bat
```

**macOS / Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

If PowerShell blocks activation, run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once and try again.

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Download the data

The raw data files are too large for Git, so download them and place them in the `data/` folder:

| File | Where it goes | Source |
|---|---|---|
| Yellow taxi trip records (`.parquet`), TODO: month and year used | `data/` | NYC TLC Trip Record Data page, or the link on the assignment page |
| `taxi_zone_lookup.csv` | `data/` | NYC TLC Trip Record Data page |
| Taxi zone boundaries (GeoJSON, converted from the TLC shapefile) | TODO: path | TLC taxi zone shapefile, converted to GeoJSON with EPSG:4326 coordinates |

Download the TLC data from: https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page

> TODO: list the exact filenames the pipeline expects, since a wrong filename is the most common setup failure.

### 5. Build the database

This runs the cleaning pipeline, writes the exclusion log, and loads the data into `db/taxi.db`:

```bash
python TODO-path/pipeline.py
```

When it finishes it prints a summary of rows loaded and rows excluded per rule. The excluded records are saved to `logs/excluded_records.csv`.

The database structure is defined in `db/schema.sql`. SQLite foreign keys are enabled on every connection by the application code.

---

## Running the Application

You need two terminals, both with the virtual environment active and opened at the project root.

### Terminal 1: Backend API

```bash
python backend/app.py
```

The API starts at `http://127.0.0.1:5000` (TODO: confirm the port). Check it by opening `http://127.0.0.1:5000/TODO-health-route` in a browser.

### Terminal 2: Frontend

```bash
cd frontend
python -m http.server 8000
```

Open `http://localhost:8000` in your browser. Serving the files this way avoids browser restrictions that appear when opening `index.html` directly from disk.

If you change the API port, update the base URL constant at the top of `frontend/app.js`.

---

## API Reference

> TODO: update this table to match the routes you actually built.

| Method | Endpoint | Description |
|---|---|---|
| GET | `/TODO-health` | Health check |
| GET | `/TODO-trips` | Paginated trips. Supports filters (time/hour, distance, fare, zone/borough), sorting, and `page` / `page_size` |
| GET | `/TODO-summary` | Summary statistics for the current filters |
| GET | `/TODO-trips-by-hour` | Trip counts and averages grouped by pickup hour |
| GET | `/TODO-zones` | Zone list and per-zone trip counts |
| GET | `/TODO-top` | Top-N results computed with the custom algorithm |

---

## Data Cleaning Summary

The pipeline removes records that are missing, duplicated, or physically or logically implausible, and records each exclusion in `logs/excluded_records.csv` with the original row index, the rule that removed it, and the offending value.

| Rule | Threshold | Rows removed |
|---|---|---|
| TODO (for example: dropoff not after pickup) | TODO | TODO |
| TODO (for example: distance out of range) | TODO | TODO |
| TODO (for example: speed above ceiling) | TODO | TODO |

Derived features:

- **Trip duration:** dropoff time minus pickup time, in minutes
- **Average speed:** trip distance divided by duration in hours
- **Tip percentage:** tip amount divided by fare amount, times 100 (TODO: state whether it covers card payments only)
- **Pickup hour bucket:** the hour of day taken from the pickup timestamp

---

## Database Schema

The schema is normalized: zones, rate codes and payment types live in their own dimension tables, and the `trips` fact table references them through foreign keys. Indexes cover the columns the dashboard filters and sorts on. See `db/schema.sql` for the full definition.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `ModuleNotFoundError` | The virtual environment isn't active, or dependencies weren't installed. Activate it and rerun `pip install -r requirements.txt`. |
| `FileNotFoundError` when running the pipeline | A data file is missing or misnamed in `data/`. Check the filenames in step 4. |
| `unable to open database file` | The `db/` folder is missing, or the command was run from the wrong directory. Run everything from the project root. |
| `Address already in use` | Another program holds the port. Stop it, or start the app on a different port and update `frontend/app.js`. |
| CORS error in the browser console | The backend isn't running, or the frontend is calling the wrong URL or port. |
| Dashboard shows no data | The database is empty. Rerun the pipeline and confirm it reported rows loaded. |

---

## Team

TODO: list team members and their roles. The full participation record is in the team participation sheet linked at the top.

## Data Source

NYC Taxi & Limousine Commission (TLC) Trip Record Data: yellow taxi trip records, taxi zone lookup table, and taxi zone boundaries.
