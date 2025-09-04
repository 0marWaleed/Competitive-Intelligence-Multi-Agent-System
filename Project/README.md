# Competitive Intelligence Monitor & Strategist

A Streamlit application that tracks competitor news, classifies events, analyzes trends and impact, and generates focused strategic recommendations. Includes professional PDF export of the daily brief and all action recommendations.

## Features
- Sidebar configuration for competitors, regions, timeframe, and recommendation focus
- Ingests and classifies events, computes trends and impact scores
- Strategy insights and action recommendations with clear prioritization
- Modern, readable UI with tabs and card-based actions
- PDF export:
  - Full Report: Daily Brief + Action Recommendations
  - Actions-only PDF (from the Actions tab)

## Quickstart

### 1) Environment
Ensure Python 3.10+ is installed. Create and activate a virtual environment.

```bash
python -m venv .venv
. .venv/Scripts/activate  # Windows PowerShell
# or
source .venv/bin/activate  # macOS/Linux
```

### 2) Install dependencies

```bash
pip install -r requirements.txt
```

Key deps: `streamlit`, `fpdf2`, `pandas`, `plotly`, `langchain`.

### 3) Run the app

```bash
streamlit run competitive_intel/ui.py
```

Open the URL shown in the terminal (typically `http://localhost:8501`).

## Usage
1. In the left sidebar, select competitors, regions, timeframe, and optionally describe a "Recommendation focus".
2. Click "Run Pipeline".
3. Navigate tabs:
   - Overview: Classified events
   - Trends: Aggregated trends table
   - Impact: Impact scoring output
   - Strategy: Strategic context per event
   - Actions: Action recommendations as cards + "Download All Actions (PDF)"
   - Report: KPIs, companies, and "Download Full Report (PDF)"

## PDF Export
- Full Report combines the Daily Brief and all actions in one professional layout (centered titles, clear spacing, readable sections).
- Actions PDF lists every action with priority, context, urgency, and steps.

If you see PDF errors:
- Verify `fpdf2` is installed (not legacy `fpdf`).
- Confirm Streamlit uses the same Python environment where deps were installed.

## Configuration & Extensibility
- The pipeline is orchestrated via `competitive_intel/main.py` and related agents.
- UI code lives in `competitive_intel/ui.py`.
- PDF generation helpers are in `competitive_intel/agents/report_generator_agent.py`:
  - `export_pdf(daily_brief)` – brief only
  - `export_actions_pdf(final_events)` – actions only
  - `export_full_pdf(daily_brief, final_events)` – full report
- Pass additional knobs through the `config` object inside `run_pipeline()` in the UI.

## Project Structure
```
.
├─ competitive_intel/
│  ├─ ui.py                      # Streamlit UI
│  ├─ agents/
│  │  └─ report_generator_agent.py  # PDF export utilities
│  └─ ...
├─ action_recommender_agent.py   
├─ data_retrieval_&_cleaning_agent_.py
├─ event_classification_agent.py
├─ impact_scoring_agent.py
├─ report_generator_agent.py     # Original Colab source (reference)
├─ strategic_analyst_agent.py
├─ trend_analysis_agent.py
├─ requirements.txt
└─ README.md
```

## Troubleshooting
- "PDF export not available": Ensure `fpdf2>=2.7` installed, restart Streamlit.
- "Invalid binary data format": You may have an older `fpdf2`; upgrade and restart.
- Tables not rendering: Ensure `pandas` is installed and up to date.

## License
Specify your preferred license here (e.g., MIT). If none, all rights reserved.
