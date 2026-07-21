# Forecasting Financial Inclusion in Ethiopia

This project analyzes Ethiopia's financial inclusion transformation, focusing on:

- Access: account ownership
- Usage: digital-payment adoption

## Interim Submission

The interim submission contains:

- Task 1: data exploration and enrichment
- Task 2: exploratory data analysis
- Data-quality assessment
- Five evidence-supported insights
- Preliminary event-indicator relationships
- Interim report

## Project Structure

- `data/raw/`: original source files
- `data/processed/`: enriched analysis-ready data
- `data/enrichment/`: newly collected records
- `notebooks/`: Task 1 and Task 2 analysis
- `reports/figures/`: generated visualizations
- `reports/`: interim report
- `src/`: reusable Python code
- `tests/`: project tests

## Installation

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
## Interactive Streamlit Dashboard

The project includes an interactive dashboard for exploring Ethiopia's
financial-inclusion indicators, event-impact relationships, and Access and
Usage forecasts for 2025–2027.

### Dashboard sections

- **Overview:** Key metrics, account-ownership growth, P2P/ATM crossover,
  and ecosystem scale indicators
- **Trends:** Interactive indicator selection, date filtering,
  normalization, and channel comparison
- **Event Impacts:** Event-indicator association matrix and strongest
  modeled relationships
- **Forecasts:** Conservative, baseline, and optimistic Access and Usage
  projections with 90% uncertainty intervals
- **Inclusion Projections:** Progress toward the 60% Access target and
  answers to the consortium's key questions

### Run locally

Clone the repository and enter the project directory:

```bash
git clone https://github.com/rediet-Shewarega/ethiopia-financial-inclusion-interim.git
cd ethiopia-financial-inclusion-interim