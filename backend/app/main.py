"""
MSME FinGenome — FastAPI Application
======================================
Main application serving the FinGenome API and static frontend.
Endpoints provide genome data, network analysis, and MSME exploration.
"""

import os
import json
import time
from typing import List, Dict, Optional
from datetime import datetime

from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.models import (
    MSMEDataPackage, FinancialGenome, MSMENetwork,
    MSMEListItem, DashboardSummary
)
from app.data_generator import generate_ecosystem
from app.genome_engine import compute_genome
from app.graph_engine import EconomicGraphEngine
from pydantic import BaseModel
import copy

class OnboardRequest(BaseModel):
    gstin: str
    name: str = "New MSME Connection"

class SimulateRequest(BaseModel):
    revenue_shock: float = 0.0      # percentage change (e.g. -30 for -30%)
    cashflow_shock: float = 0.0


# ─── Application Setup ──────────────────────────────────────────────────────

app = FastAPI(
    title="MSME FinGenome",
    description="Financial Digital Twin Platform for MSMEs — Mapping the Financial DNA of India's Small Businesses",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Global State (initialized on startup) ──────────────────────────────────

class AppState:
    packages: List[MSMEDataPackage] = []
    genomes: Dict[str, FinancialGenome] = {}
    graph_engine: EconomicGraphEngine = EconomicGraphEngine()
    initialized: bool = False
    init_time: float = 0.0


state = AppState()


@app.on_event("startup")
async def startup():
    """Initialize the FinGenome system with synthetic data."""
    print("🧬 MSME FinGenome — Initializing...")
    start = time.time()

    # Step 1: Generate synthetic ecosystem
    print("   📊 Generating synthetic MSME ecosystem (55 businesses, 24 months)...")
    state.packages = generate_ecosystem(num_msmes=55, months=24, seed=42)
    print(f"   ✅ Generated {len(state.packages)} MSMEs")

    # Step 2: Compute Financial Genomes
    print("   🧬 Computing Financial Genomes...")
    for pkg in state.packages:
        genome = compute_genome(pkg)
        state.genomes[pkg.entity.business_id] = genome
    print(f"   ✅ Computed {len(state.genomes)} genomes")

    # Step 3: Build economic network graph
    print("   🕸️  Building economic network graph...")
    genome_data = {
        bid: {"overall_score": g.overall_score, "risk_grade": g.risk_grade.value}
        for bid, g in state.genomes.items()
    }
    state.graph_engine.build_graph(state.packages, genome_data)
    print(f"   ✅ Network built with {state.graph_engine.graph.number_of_nodes()} nodes, "
          f"{state.graph_engine.graph.number_of_edges()} edges")

    state.init_time = time.time() - start
    state.initialized = True
    print(f"\n🚀 FinGenome ready in {state.init_time:.1f}s — Serving at http://localhost:8000")


# ─── API Endpoints ──────────────────────────────────────────────────────────

@app.get("/api/health")
async def health_check():
    """System health check."""
    return {
        "status": "operational",
        "initialized": state.initialized,
        "msme_count": len(state.genomes),
        "init_time_seconds": round(state.init_time, 2),
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/api/dashboard/summary", response_model=DashboardSummary)
async def get_dashboard_summary():
    """Get aggregate statistics for the dashboard header."""
    if not state.initialized:
        raise HTTPException(503, "System initializing")

    genomes = list(state.genomes.values())
    scores = [g.overall_score for g in genomes]

    grade_dist = {}
    for g in genomes:
        grade = g.risk_grade.value
        grade_dist[grade] = grade_dist.get(grade, 0) + 1

    industry_dist = {}
    for g in genomes:
        ind = g.industry
        industry_dist[ind] = industry_dist.get(ind, 0) + 1

    return DashboardSummary(
        total_msmes=len(genomes),
        avg_health_score=round(sum(scores) / len(scores), 1) if scores else 0,
        grade_distribution=grade_dist,
        industry_distribution=industry_dist,
        credit_worthy_count=sum(1 for g in genomes if g.credit_recommendation in ["approve", "conditional"]),
        at_risk_count=sum(1 for g in genomes if g.overall_score < 40),
        newly_onboarded=sum(1 for p in state.packages if p.entity.profile_type.value == "new_business"),
    )


@app.get("/api/msmes", response_model=List[MSMEListItem])
async def list_msmes(
    industry: Optional[str] = Query(None, description="Filter by industry"),
    risk_grade: Optional[str] = Query(None, description="Filter by risk grade"),
    sort_by: str = Query("score", description="Sort by: score, name, industry"),
    sort_order: str = Query("desc", description="Sort order: asc, desc"),
    search: Optional[str] = Query(None, description="Search by name"),
):
    """List all MSMEs with summary data for the sidebar explorer."""
    if not state.initialized:
        raise HTTPException(503, "System initializing")

    items = []
    for bid, genome in state.genomes.items():
        # Find matching package for city
        pkg = next((p for p in state.packages if p.entity.business_id == bid), None)
        city = pkg.entity.city if pkg else ""

        item = MSMEListItem(
            business_id=bid,
            name=genome.business_name,
            industry=genome.industry,
            category=genome.category,
            city=city,
            overall_score=genome.overall_score,
            risk_grade=genome.risk_grade.value,
            trend=genome.trajectory_dna.trend.value,
        )

        # Apply filters
        if industry and genome.industry != industry:
            continue
        if risk_grade and genome.risk_grade.value != risk_grade:
            continue
        if search and search.lower() not in genome.business_name.lower():
            continue

        items.append(item)

    # Sort
    reverse = sort_order == "desc"
    if sort_by == "score":
        items.sort(key=lambda x: x.overall_score, reverse=reverse)
    elif sort_by == "name":
        items.sort(key=lambda x: x.name, reverse=reverse)
    elif sort_by == "industry":
        items.sort(key=lambda x: x.industry, reverse=reverse)

    return items


@app.post("/api/msmes/onboard")
async def onboard_msme(req: OnboardRequest):
    """Mock an Account Aggregator / ULI fetch to onboard a new MSME."""
    if not state.initialized:
        raise HTTPException(503, "System initializing")
        
    from app.data_generator import SyntheticDataGenerator
    generator = SyntheticDataGenerator(num_msmes=0)  # We don't need it to generate standard 55
    new_pkg = generator.generate_single(custom_gstin=req.gstin, custom_name=req.name)
    
    # Compute the new genome
    new_genome = compute_genome(new_pkg)
    
    # Add to global state
    state.packages.append(new_pkg)
    state.genomes[new_genome.business_id] = new_genome
    
    # Add node to the graph network
    from app.models import NetworkNode
    state.graph_engine.add_node(NetworkNode(
        id=new_genome.business_id,
        name=new_genome.business_name,
        industry=new_genome.industry,
        health_score=new_genome.overall_score,
        risk_grade=new_genome.risk_grade.value
    ))
    
    return {"message": "success", "business_id": new_genome.business_id}


@app.post("/api/msmes/{business_id}/simulate")
async def simulate_genome(business_id: str, req: SimulateRequest):
    """Run a What-If scenario (Stress Test) by temporarily mutating the data."""
    if business_id not in state.genomes:
        raise HTTPException(404, "MSME not found")
        
    pkg = next((p for p in state.packages if p.entity.business_id == business_id), None)
    if not pkg:
        raise HTTPException(404, "Data package not found")
        
    # Deep copy the package to not mutate the global state
    mutated_pkg = copy.deepcopy(pkg)
    
    # Apply Revenue Shock (e.g., -30% means we multiply all turnover by 0.70)
    if req.revenue_shock != 0:
        multiplier = 1 + (req.revenue_shock / 100.0)
        for g in mutated_pkg.gst_records:
            g.taxable_turnover *= multiplier
            
    # Apply Cashflow Shock
    if req.cashflow_shock != 0:
        multiplier = 1 + (req.cashflow_shock / 100.0)
        for b in mutated_pkg.bank_statements:
            b.end_balance *= multiplier
            b.inflow *= multiplier
            
    # Recalculate genome on the fly
    simulated_genome = compute_genome(mutated_pkg)
    return simulated_genome



@app.get("/api/msmes/{business_id}/genome")
async def get_genome(business_id: str):
    """Get the complete Financial Genome for a specific MSME."""
    if not state.initialized:
        raise HTTPException(503, "System initializing")

    genome = state.genomes.get(business_id)
    if not genome:
        raise HTTPException(404, f"MSME {business_id} not found")

    return genome.model_dump()


@app.get("/api/msmes/{business_id}/network")
async def get_network(business_id: str, depth: int = Query(1, ge=1, le=2)):
    """Get the economic network graph centered on a specific MSME."""
    if not state.initialized:
        raise HTTPException(503, "System initializing")

    if business_id not in state.genomes:
        raise HTTPException(404, f"MSME {business_id} not found")

    network = state.graph_engine.get_msme_network(business_id, depth=depth)
    return network.model_dump()


@app.get("/api/msmes/{business_id}/raw-data")
async def get_raw_data(business_id: str):
    """Get the raw data sources for a specific MSME (for transparency/explainability)."""
    if not state.initialized:
        raise HTTPException(503, "System initializing")

    pkg = next((p for p in state.packages if p.entity.business_id == business_id), None)
    if not pkg:
        raise HTTPException(404, f"MSME {business_id} not found")

    return {
        "entity": pkg.entity.model_dump(),
        "gst_summary": {
            "total_months": len(pkg.gst_records),
            "avg_monthly_turnover": round(
                sum(g.taxable_turnover for g in pkg.gst_records) / len(pkg.gst_records), 2
            ) if pkg.gst_records else 0,
            "total_turnover": round(sum(g.taxable_turnover for g in pkg.gst_records), 2),
            "on_time_filings": sum(1 for g in pkg.gst_records if g.filing_status.value == "on_time"),
            "records": [g.model_dump() for g in pkg.gst_records[-6:]],  # Last 6 months
        },
        "bank_summary": {
            "total_months": len(pkg.bank_statements),
            "avg_daily_balance": round(
                sum(b.avg_daily_balance for b in pkg.bank_statements) / len(pkg.bank_statements), 2
            ) if pkg.bank_statements else 0,
            "total_bounces": sum(b.bounce_count for b in pkg.bank_statements),
            "records": [b.model_dump() for b in pkg.bank_statements[-6:]],
        },
        "epfo_summary": {
            "total_months": len(pkg.epfo_records),
            "current_employees": pkg.epfo_records[-1].active_employees if pkg.epfo_records else 0,
            "records": [e.model_dump() for e in pkg.epfo_records[-6:]],
        },
        "upi_summary": {
            "total_transactions": len(pkg.upi_transactions),
            "total_inflow": round(sum(t.amount for t in pkg.upi_transactions if t.direction == "inflow"), 2),
            "total_outflow": round(sum(t.amount for t in pkg.upi_transactions if t.direction == "outflow"), 2),
            "unique_counterparties": len(set(t.counterparty_id for t in pkg.upi_transactions)),
        },
        "itr_records": [i.model_dump() for i in pkg.itr_records],
        "alternate_signals": [a.model_dump() for a in pkg.alternate_signals],
    }


@app.get("/api/network/full")
async def get_full_network():
    """Get the complete economic network for the ecosystem visualization."""
    if not state.initialized:
        raise HTTPException(503, "System initializing")
    return state.graph_engine.get_full_graph_data()


@app.get("/api/analytics/distribution")
async def get_score_distribution():
    """Get score distribution data for analytics charts."""
    if not state.initialized:
        raise HTTPException(503, "System initializing")

    genomes = list(state.genomes.values())

    # Score histogram (bins of 10)
    bins = {f"{i}-{i+10}": 0 for i in range(0, 100, 10)}
    for g in genomes:
        bin_key = f"{int(g.overall_score // 10) * 10}-{int(g.overall_score // 10) * 10 + 10}"
        if bin_key in bins:
            bins[bin_key] += 1

    # Strand averages
    strand_avgs = {
        "Revenue DNA": round(sum(g.revenue_dna.score for g in genomes) / len(genomes), 1),
        "Cash Flow DNA": round(sum(g.cashflow_dna.score for g in genomes) / len(genomes), 1),
        "Compliance DNA": round(sum(g.compliance_dna.score for g in genomes) / len(genomes), 1),
        "Workforce DNA": round(sum(g.workforce_dna.score for g in genomes) / len(genomes), 1),
        "Network DNA": round(sum(g.network_dna.score for g in genomes) / len(genomes), 1),
        "Trajectory DNA": round(sum(g.trajectory_dna.score for g in genomes) / len(genomes), 1),
    }

    # Credit recommendation distribution
    credit_dist = {}
    for g in genomes:
        cr = g.credit_recommendation
        credit_dist[cr] = credit_dist.get(cr, 0) + 1

    return {
        "score_histogram": bins,
        "strand_averages": strand_avgs,
        "credit_distribution": credit_dist,
        "total_suggested_credit": round(sum(g.suggested_credit_limit for g in genomes), 2),
    }


@app.get("/api/industries")
async def list_industries():
    """List all industries present in the ecosystem."""
    if not state.initialized:
        raise HTTPException(503, "System initializing")
    industries = list(set(g.industry for g in state.genomes.values()))
    return sorted(industries)


@app.get("/api/compare")
async def compare_msmes(ids: str = Query(..., description="Comma-separated business IDs")):
    """Compare multiple MSMEs side by side."""
    if not state.initialized:
        raise HTTPException(503, "System initializing")

    business_ids = [bid.strip() for bid in ids.split(",")]
    results = []
    for bid in business_ids:
        genome = state.genomes.get(bid)
        if genome:
            results.append({
                "business_id": bid,
                "name": genome.business_name,
                "overall_score": genome.overall_score,
                "risk_grade": genome.risk_grade.value,
                "revenue_dna": genome.revenue_dna.score,
                "cashflow_dna": genome.cashflow_dna.score,
                "compliance_dna": genome.compliance_dna.score,
                "workforce_dna": genome.workforce_dna.score,
                "network_dna": genome.network_dna.score,
                "trajectory_dna": genome.trajectory_dna.score,
                "credit_recommendation": genome.credit_recommendation,
                "suggested_credit_limit": genome.suggested_credit_limit,
            })

    return results


# ─── Phase 2: Living Loan Lifecycle Endpoint ─────────────────────────────────

import random as _random

@app.get("/api/loan-lifecycle/{business_id}")
async def get_loan_lifecycle(business_id: str):
    """
    Returns the Living Loan lifecycle data for an MSME.
    Simulates 12 months of post-disbursement monitoring data:
    - Daily genome heartbeat (30-day rolling average per month)
    - Monthly sweep amounts (revenue-linked repayment)
    - Alert history (Yellow/Orange/Red interventions)
    - NPA prevention stats
    - Behavioral Credit Passport summary
    """
    if not state.initialized:
        raise HTTPException(503, "System initializing")

    genome = state.genomes.get(business_id)
    if not genome:
        raise HTTPException(404, f"MSME {business_id} not found")

    pkg = next((p for p in state.packages if p.entity.business_id == business_id), None)

    # Seed random with business_id for consistent results per MSME
    seed = sum(ord(c) for c in business_id)
    rng = _random.Random(seed)

    base_score = genome.overall_score
    avg_revenue = genome.inferred_annual_revenue / 12 if genome.inferred_annual_revenue else 500000

    # ── 1. Generate 12-month genome heartbeat ──────────────────────────────
    months = ["Jul'24","Aug'24","Sep'24","Oct'24","Nov'24","Dec'24",
              "Jan'25","Feb'25","Mar'25","Apr'25","May'25","Jun'25"]
    heartbeat = []
    current_score = base_score
    for i, month in enumerate(months):
        # Simulate realistic score fluctuation
        shock = rng.uniform(-8, 6)
        if i == 3:  shock = -18   # simulate a stress event in month 4
        if i == 4:  shock = -8    # continued stress
        if i == 5:  shock = +5    # recovery after intervention
        current_score = max(20, min(98, current_score + shock))
        heartbeat.append({"month": month, "score": round(current_score, 1)})

    # ── 2. Generate monthly sweep amounts ──────────────────────────────────
    sweep_rate = 0.035  # 3.5% of incoming transactions
    sweep_data = []
    for i, month in enumerate(months):
        seasonal_factor = 1.0 + rng.uniform(-0.2, 0.25)
        if i == 3: seasonal_factor = 0.6   # stress month — low revenue
        if i == 4: seasonal_factor = 0.7
        monthly_rev = avg_revenue * seasonal_factor
        swept = monthly_rev * sweep_rate
        sweep_data.append({
            "month": month,
            "revenue": round(monthly_rev),
            "swept": round(swept),
            "cumulative_repaid": round(swept * (i + 1) * rng.uniform(0.85, 1.05))
        })

    # ── 3. Alert history ───────────────────────────────────────────────────
    alerts = [
        {
            "month": "Oct'24",
            "type": "YELLOW",
            "trigger": "Revenue dropped 18% vs prior month. Top buyer payment delayed 12 days.",
            "action": "Auto-advisory sent to MSME: 'Your receivables from Buyer A are 12 days overdue. Draft payment reminder sent.'",
            "resolved": True,
            "days_to_resolve": 8
        },
        {
            "month": "Nov'24",
            "type": "ORANGE",
            "trigger": "Score dropped 26%. Payroll delay detected. 2 supplier payments missed.",
            "action": "30-day repayment holiday auto-activated. Sweep rate reduced from 3.5% to 1% for November.",
            "resolved": True,
            "days_to_resolve": 30
        },
        {
            "month": "Dec'24",
            "type": "YELLOW",
            "trigger": "Recovery underway but receivables still elevated.",
            "action": "CFO advisory: 'Negotiate 7-day early payment discount with top 3 buyers to accelerate receivable recovery.'",
            "resolved": True,
            "days_to_resolve": 12
        }
    ]

    # ── 4. NPA Prevention Counter ──────────────────────────────────────────
    loan_amount = genome.suggested_credit_limit or 2500000
    estimated_npa_loss = loan_amount * 0.65   # banks typically recover 35 paise on rupee
    interest_saved = loan_amount * 0.12 * (2/12)  # 2 months interest on restructured tenure

    npa_prevention = {
        "yellow_alerts_sent": 2,
        "orange_alerts_sent": 1,
        "red_alerts_sent": 0,
        "payment_holidays_granted": 1,
        "npa_prevented": True,
        "traditional_bank_discovery_month": "Jan'25",  # when traditional bank would have found out
        "living_loan_detection_month": "Oct'24",       # when we detected it
        "detection_advantage_days": 92,
        "estimated_capital_saved": round(estimated_npa_loss),
        "interest_revenue_preserved": round(interest_saved),
        "total_value_protected": round(estimated_npa_loss + interest_saved)
    }

    # ── 5. Behavioral Credit Passport ─────────────────────────────────────
    avg_heartbeat = sum(h["score"] for h in heartbeat) / len(heartbeat)
    if avg_heartbeat > 80:
        current_rate = 10.5
        rate_tier = "Gold"
    elif avg_heartbeat > 65:
        current_rate = 12.0
        rate_tier = "Silver"
    else:
        current_rate = 14.0
        rate_tier = "Standard"

    passport = {
        "months_on_platform": 12,
        "avg_genome_score": round(avg_heartbeat, 1),
        "rate_tier": rate_tier,
        "original_rate": 14.0,
        "current_rate": current_rate,
        "rate_saved": round(14.0 - current_rate, 1),
        "annual_interest_saving": round(loan_amount * (14.0 - current_rate) / 100),
        "next_review": "Sep'25",
        "alerts_responded_to": "3/3",
        "passport_score": round(avg_heartbeat * 0.7 + (100 - len(alerts) * 5) * 0.3, 1)
    }

    # ── 6. Multi-account sweep summary ────────────────────────────────────
    accounts = [
        {"bank": "Primary Bank", "type": "Primary", "sweep_share": 60, "status": "Active"},
        {"bank": "HDFC Bank", "type": "Secondary (AA Linked)", "sweep_share": 30, "status": "NACH Active"},
        {"bank": "Axis Bank", "type": "Operational (AA Linked)", "sweep_share": 10, "status": "NACH Active"},
    ]

    total_swept = sum(s["swept"] for s in sweep_data)

    return {
        "business_id": business_id,
        "business_name": genome.business_name,
        "loan_amount": loan_amount,
        "disbursement_date": "Jul'24",
        "sweep_rate": round(sweep_rate * 100, 1),
        "current_zone": "GREEN" if base_score > 75 else "YELLOW" if base_score > 55 else "ORANGE",
        "current_genome_score": base_score,
        "total_swept_to_date": round(total_swept),
        "loan_repaid_percent": round((total_swept / loan_amount) * 100, 1),
        "projected_months_to_full_repayment": round((loan_amount - total_swept) / (total_swept / 12)),
        "heartbeat": heartbeat,
        "sweep_data": sweep_data,
        "alerts": alerts,
        "npa_prevention": npa_prevention,
        "passport": passport,
        "linked_accounts": accounts
    }



# Determine frontend path
# __file__ = backend/app/main.py → go up to backend/ → then up to project root → then into frontend/
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "frontend")
print(f"   📁 Frontend directory: {FRONTEND_DIR} (exists: {os.path.exists(FRONTEND_DIR)})")

if os.path.exists(FRONTEND_DIR):
    app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIR, "assets")), name="assets")

    @app.get("/")
    async def serve_index():
        """Serve the main dashboard."""
        return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

    @app.get("/{full_path:path}")
    async def serve_static(full_path: str):
        """Serve static files."""
        file_path = os.path.join(FRONTEND_DIR, full_path)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))
