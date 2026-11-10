# RouteWise — student transportation planning

RouteWise is a synthetic-data prototype for assigning students to bus routes and stops, tracking daily attendance, and surfacing operational exceptions. It includes an interactive Streamlit dashboard, a deterministic data generator, CSV/JSON/SQL exports, a data dictionary, and documented decision rules.

## Run locally

Python 3.10 or newer is required.

```bash
python -m venv .venv
# Windows: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

The dashboard creates a small demo dataset on first launch. To generate the full challenge baseline (5,000 students, 100 buses, 300 stops, 200 school days):

```bash
python generate.py --out data --seed 20261022
```

To create a small reproducibility fixture:

```bash
python generate.py --out demo_data --students 120 --buses 12 --stops 36 --days 20 --seed 20261022
```

The generator exports one CSV per entity, `ground_truth.json`, `validation_summary.json`, `manifest.json` with SHA-256 checksums, and a SQLite-compatible SQL seed. Ground truth is a separate scoring artifact and must not be used as model input.

## Product flow

1. Review service attendance, seat utilization, and open issue fixtures.
2. Inspect a student's zone and accessibility need; see candidate approved stops and routes that have capacity.
3. Review attendance-driven guardian notification records using synthetic contact IDs and minimal message codes.
4. Triage labeled negative scenarios with their expected decision policy.
5. Browse or download generated data tables for further evaluation.

The planner is a decision-support prototype: it presents candidates and does not persist edits. Travel times and coordinates are synthetic estimates, not road-network navigation. See [SCHEMA.md](SCHEMA.md) for lifecycle, relationships, and rules, and [DATA_DICTIONARY.md](DATA_DICTIONARY.md) for the field definitions.

## Data provenance

All names, contacts, addresses, routes, coordinates and events are synthetic. No real student information or external data is used. Email addresses use `example.invalid`; telephone values use a fictional reserved range.
