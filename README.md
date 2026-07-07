# 🧬 MSME FinGenome
### *India's First Living Loan Intelligence Platform*

[![Tech Stack: FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![Frontend: Vanilla JS + D3.js](https://img.shields.io/badge/Frontend-Vanilla_JS_%26_D3.js-F9A03C)](https://d3js.org)
[![Charts: Chart.js](https://img.shields.io/badge/Charts-Chart.js-FF6384?logo=chartdotjs)](https://chartjs.org)

> **Problem:** 80% of India's 63 million MSMEs are financially invisible — no audited statements, no credit history, no collateral. Banks guess. They guess wrong. ₹89,000 Cr in MSME NPAs prove it.
>
> **Solution:** Stop guessing. Read their **Financial DNA**.

---

## 🌟 What Makes This Different

MSME FinGenome is not a dashboard. It is a **Financial Truth Terminal** — a two-phase system that reconstructs what a business truly is from raw transactional behaviour, then watches it breathe in real-time after a loan is issued.

### Phase 1 — Loan Origination: The Genome Engine
Before lending a single rupee, FinGenome sequences the MSME's **6-dimensional financial DNA**:

| Strand | What it measures |
|--------|-----------------|
| 💰 Revenue DNA | Real inferred revenue from UPI/NACH inflows — not what they declared |
| 🌊 Cash Flow DNA | Liquidity rhythm, working capital pressure, payroll regularity |
| 📋 Compliance DNA | GST filing consistency, TDS regularity, regulatory reliability |
| 👥 Workforce DNA | Employee count stability, payroll-to-revenue ratio |
| 🕸️ Network DNA | Supply chain centrality, buyer/supplier dependency, contagion risk |
| 📈 Trajectory DNA | 24-month projection with XGBoost — where is this business going? |

**The result:** A single Genome Score (0–100), a credit grade (A+ → D), and a suggested credit limit — all derived from **zero audited documents**.

### Phase 2 — Living Loan Monitor: Post-Disbursement Intelligence
After the loan is issued, the system doesn't walk away. It watches every transaction:

- **💓 Genome Heartbeat** — 12-month score pulse. The moment a business starts declining, we know — 92 days before a traditional bank would notice.
- **⚡ Transactional Sweep** — 3.5% of every incoming transaction auto-repaid via NACH across multiple linked bank accounts.
- **🚨 Intervention Timeline** — Automated Yellow/Orange/Red alerts with AI-driven responses (payment holidays, CFO advisories, rate adjustments).
- **🛡️ NPA Prevention Engine** — Quantifies exactly how much capital was saved vs the traditional "discover at 90-days-overdue" approach.
- **🪪 Behavioral Credit Passport** — Dynamic interest rate (starts 14%, drops to 11% for Gold tier) earned through responsible behaviour. Non-transferable — switches banks, resets passport.

---

## 🛠️ Tech Stack

### Backend (Python)
- **FastAPI** — High-performance async REST API
- **NetworkX** — Graph-based supply chain contagion analysis
- **Scikit-Learn + XGBoost** — 24-month trajectory prediction
- **Pydantic v2** — Strict data ontology and validation
- **NumPy / Pandas** — Financial genome computation

### Frontend (Vanilla JS)
- **Zero framework** — Pure HTML/CSS/JS for maximum speed
- **D3.js** — Radar polygon genome map + force-directed network graph
- **Chart.js** — Heartbeat pulse chart, sweep bar chart, trajectory forecast
- **Multi-page SPA** — Home portfolio grid + full-page MSME profile

---

## 🚀 Running Locally

### Prerequisites
- Python 3.10+

### 1. Install dependencies
```bash
git clone https://github.com/sid-code04/msme-fingenome.git
cd msme-fingenome
pip install -r backend/requirements.txt
```

### 2. Start the engine
```bash
cd backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 3. Open in browser
```
http://localhost:8000
```

The engine will synthesize **55 MSMEs** with 24-month relational histories on startup (~2–5 seconds).

---

## 📁 Project Structure

```
msme-fingenome/
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI routes + lifecycle API
│   │   ├── models.py        # Pydantic data models
│   │   ├── genome_engine.py # 6-strand genome computation
│   │   ├── graph_engine.py  # NetworkX supply chain analysis
│   │   └── data_generator.py# Synthetic MSME data factory
│   └── requirements.txt
└── frontend/
    ├── index.html           # Multi-page SPA structure
    └── assets/
        ├── css/styles.css   # Design system (dark, spacious)
        └── js/app.js        # Full SPA logic + D3/Chart.js renders
```

---

## 🔑 Key API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/msmes` | Portfolio list with filters |
| GET | `/api/msmes/{id}/genome` | Full 6-strand genome analysis |
| GET | `/api/msmes/{id}/network` | Supply chain graph data |
| POST | `/api/msmes/{id}/simulate` | Stress test: revenue/cashflow shock |
| GET | `/api/loan-lifecycle/{id}` | Living Loan Monitor data |
| POST | `/api/msmes/onboard` | Mock ULI/AA new MSME connection |

---

*Built to solve a ₹89,000 Cr problem — one genome at a time.*
