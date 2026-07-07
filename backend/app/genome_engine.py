"""
MSME FinGenome — Genome Computation Engine
============================================
The core intelligence: transforms raw MSME data (7 sources) into a
6-dimensional Financial Genome. Each "strand" is computed from specific
data sources using domain-driven scoring algorithms.

Genome Strands:
  1. Revenue DNA   — GST, UPI inflows    → Revenue stability, growth, diversification
  2. Cash Flow DNA — Bank statements, AA  → Liquidity, working capital, burn rate
  3. Compliance DNA — GST filings, ITR    → Regulatory discipline, governance
  4. Workforce DNA — EPFO                → Employee stability, growth, retention
  5. Network DNA   — UPI graph analysis  → Ecosystem position, concentration risk
  6. Trajectory DNA — Temporal trends     → Where is this business heading?
"""

import random
import numpy as np
from typing import List, Dict, Tuple, Optional
from collections import Counter, defaultdict
from datetime import datetime

from app.models import (
    MSMEDataPackage, FinancialGenome, GenomeStrand, TrajectoryPrediction,
    RiskGrade, TrendDirection, HybridCreditStructure
)


# ─── Scoring Utilities ──────────────────────────────────────────────────────

def _normalize_score(value: float, min_val: float = 0, max_val: float = 100) -> float:
    """Clamp and round a score to [0, 100]."""
    return round(max(min_val, min(max_val, value)), 1)


def _compute_trend(values: List[float]) -> Tuple[TrendDirection, float]:
    """Compute trend direction and magnitude from a time series."""
    if len(values) < 3:
        return TrendDirection.STABLE, 0.0

    # Simple linear regression
    x = np.arange(len(values))
    if np.std(values) == 0:
        return TrendDirection.STABLE, 0.0

    coeffs = np.polyfit(x, values, 1)
    slope = coeffs[0]
    avg = np.mean(values) if np.mean(values) != 0 else 1
    pct_change = (slope * len(values)) / abs(avg) * 100

    # Coefficient of variation for volatility detection
    cv = np.std(values) / abs(avg) if avg != 0 else 0

    if cv > 0.4:
        return TrendDirection.VOLATILE, round(pct_change, 1)
    elif pct_change > 5:
        return TrendDirection.IMPROVING, round(pct_change, 1)
    elif pct_change < -5:
        return TrendDirection.DECLINING, round(pct_change, 1)
    else:
        return TrendDirection.STABLE, round(pct_change, 1)


def _grade_from_score(score: float) -> str:
    """Convert numerical score to letter grade."""
    if score >= 85:
        return "A+"
    elif score >= 75:
        return "A"
    elif score >= 65:
        return "B+"
    elif score >= 50:
        return "B"
    elif score >= 35:
        return "C"
    else:
        return "D"


def _risk_grade_from_score(score: float) -> RiskGrade:
    """Convert overall score to risk grade enum."""
    if score >= 80:
        return RiskGrade.A_PLUS
    elif score >= 68:
        return RiskGrade.A
    elif score >= 55:
        return RiskGrade.B_PLUS
    elif score >= 42:
        return RiskGrade.B
    elif score >= 28:
        return RiskGrade.C
    else:
        return RiskGrade.D


# ─── Strand Computation Functions ───────────────────────────────────────────

def compute_revenue_dna(pkg: MSMEDataPackage) -> GenomeStrand:
    """
    Revenue DNA: Evaluates revenue health from GST and UPI data.

    Sub-dimensions:
      - Growth Rate (25%): Month-over-month revenue trajectory
      - Stability (25%): Coefficient of variation (lower = better)
      - Scale (20%): Absolute revenue level relative to category
      - Diversification (15%): Number of revenue sources / customers
      - Seasonality Mgmt (15%): How well seasonal dips are managed
    """
    revenues = [g.taxable_turnover for g in pkg.gst_records]

    if not revenues:
        return _empty_strand("Revenue DNA")

    # Growth Rate Score
    if len(revenues) >= 6:
        recent_avg = np.mean(revenues[-6:])
        early_avg = np.mean(revenues[:6])
        growth_pct = ((recent_avg - early_avg) / early_avg * 100) if early_avg > 0 else 0
        growth_score = _normalize_score(50 + growth_pct * 2)  # +1% growth = +2 points
    else:
        growth_score = 50.0

    # Stability Score (inverse of CV)
    cv = np.std(revenues) / np.mean(revenues) if np.mean(revenues) > 0 else 1
    stability_score = _normalize_score(100 - cv * 200)

    # Scale Score (normalized by MSME category expectations)
    avg_monthly = np.mean(revenues)
    category_benchmarks = {"Micro": 300000, "Small": 1500000, "Medium": 5000000}
    benchmark = category_benchmarks.get(pkg.entity.category.value, 1000000)
    scale_ratio = avg_monthly / benchmark
    scale_score = _normalize_score(min(100, scale_ratio * 70 + 20))

    # Diversification Score (from UPI counterparties)
    inflow_txns = [t for t in pkg.upi_transactions if t.direction == "inflow"]
    unique_customers = len(set(t.counterparty_id for t in inflow_txns))
    if unique_customers > 0 and inflow_txns:
        # Calculate HHI (Herfindahl–Hirschman Index) for concentration
        customer_volumes = defaultdict(float)
        for t in inflow_txns:
            customer_volumes[t.counterparty_id] += t.amount
        total_vol = sum(customer_volumes.values())
        if total_vol > 0:
            shares = [(v / total_vol) ** 2 for v in customer_volumes.values()]
            hhi = sum(shares)
            diversification_score = _normalize_score(100 - hhi * 100)
        else:
            diversification_score = 30.0
    else:
        diversification_score = 30.0

    # Seasonality Management Score
    if len(revenues) >= 12:
        monthly_avgs = {}
        for i, g in enumerate(pkg.gst_records):
            month_num = int(g.month.split("-")[1])
            if month_num not in monthly_avgs:
                monthly_avgs[month_num] = []
            monthly_avgs[month_num].append(g.taxable_turnover)
        month_means = [np.mean(v) for v in monthly_avgs.values()]
        seasonal_cv = np.std(month_means) / np.mean(month_means) if np.mean(month_means) > 0 else 0
        seasonal_score = _normalize_score(100 - seasonal_cv * 150)
    else:
        seasonal_score = 60.0

    # Weighted composite
    composite = (
        growth_score * 0.25 +
        stability_score * 0.25 +
        scale_score * 0.20 +
        diversification_score * 0.15 +
        seasonal_score * 0.15
    )

    # Monthly score history
    monthly_scores = []
    for i in range(len(revenues)):
        window = revenues[max(0, i-5):i+1]
        if len(window) >= 2:
            w_growth = ((window[-1] - window[0]) / window[0] * 100) if window[0] > 0 else 0
            w_cv = np.std(window) / np.mean(window) if np.mean(window) > 0 else 1
            m_score = 50 + w_growth * 1.5 - w_cv * 80
            monthly_scores.append(_normalize_score(m_score))
        else:
            monthly_scores.append(composite)

    trend, trend_val = _compute_trend(revenues)

    # Key factors (NLG)
    factors = []
    if growth_score > 70:
        factors.append(f"Revenue growing at {abs(growth_pct):.1f}% over evaluation period")
    elif growth_score < 40:
        factors.append(f"Revenue declining at {abs(growth_pct):.1f}% — needs attention")
    if stability_score > 70:
        factors.append("Highly consistent revenue stream with low volatility")
    elif stability_score < 40:
        factors.append(f"High revenue volatility (CV: {cv:.2f}) creates forecasting risk")
    if diversification_score > 70:
        factors.append(f"Well-diversified across {unique_customers} revenue sources")
    elif diversification_score < 40:
        factors.append(f"Revenue concentration risk — only {unique_customers} key customers")
    if not factors:
        factors.append("Revenue performance within normal operating range")

    return GenomeStrand(
        name="Revenue DNA",
        score=_normalize_score(composite),
        grade=_grade_from_score(composite),
        trend=trend,
        trend_value=trend_val,
        key_factors=factors[:3],
        sub_scores={
            "growth_rate": round(growth_score, 1),
            "stability": round(stability_score, 1),
            "scale": round(scale_score, 1),
            "diversification": round(diversification_score, 1),
            "seasonality_mgmt": round(seasonal_score, 1),
        },
        monthly_history=monthly_scores,
        confidence=0.88,
    )


def compute_cashflow_dna(pkg: MSMEDataPackage) -> GenomeStrand:
    """
    Cash Flow DNA: Evaluates liquidity and working capital health.

    Sub-dimensions:
      - Liquidity Ratio (25%): Average daily balance vs. monthly debits
      - Cash Conversion (25%): How quickly revenue converts to cash
      - Working Capital (20%): Credits vs debits balance
      - Bounce Rate (15%): Cheque/ECS bounce frequency
      - Credit Utilization (15%): How much of credit line is used
    """
    stmts = pkg.bank_statements
    if not stmts:
        return _empty_strand("Cash Flow DNA")

    # Liquidity Ratio
    liquidity_scores = []
    for s in stmts:
        if s.total_debits > 0:
            ratio = s.avg_daily_balance / (s.total_debits / 30)
            liquidity_scores.append(min(100, ratio * 15))
        else:
            liquidity_scores.append(70)
    liquidity_score = np.mean(liquidity_scores)

    # Cash Conversion Score
    gst_rev = [g.taxable_turnover for g in pkg.gst_records]
    bank_credits = [s.total_credits for s in stmts]
    if gst_rev and bank_credits:
        min_len = min(len(gst_rev), len(bank_credits))
        conversion_ratios = [bank_credits[i] / gst_rev[i] if gst_rev[i] > 0 else 0
                            for i in range(min_len)]
        avg_conversion = np.mean(conversion_ratios)
        conversion_score = _normalize_score(avg_conversion * 80)
    else:
        conversion_score = 50.0

    # Working Capital Score
    wc_scores = []
    for s in stmts:
        if s.total_debits > 0:
            wc_ratio = s.total_credits / s.total_debits
            wc_scores.append(min(100, wc_ratio * 50))
        else:
            wc_scores.append(70)
    wc_score = np.mean(wc_scores)

    # Bounce Rate Score
    total_bounces = sum(s.bounce_count for s in stmts)
    total_debits = sum(s.debit_count for s in stmts)
    bounce_rate = total_bounces / total_debits if total_debits > 0 else 0
    bounce_score = _normalize_score(100 - bounce_rate * 500)

    # Credit Utilization Score (lower is better)
    cc_utils = [s.cash_credit_utilization for s in stmts if s.cash_credit_utilization > 0]
    if cc_utils:
        avg_cc = np.mean(cc_utils)
        cc_score = _normalize_score(100 - avg_cc * 80)
    else:
        cc_score = 80.0

    composite = (
        liquidity_score * 0.25 +
        conversion_score * 0.25 +
        wc_score * 0.20 +
        bounce_score * 0.15 +
        cc_score * 0.15
    )

    # Monthly history
    monthly_scores = []
    for s in stmts:
        liq = min(100, (s.avg_daily_balance / (s.total_debits / 30) * 15)) if s.total_debits > 0 else 70
        wc = min(100, (s.total_credits / s.total_debits * 50)) if s.total_debits > 0 else 70
        bnc = 100 - s.bounce_count * 30
        m_score = liq * 0.4 + wc * 0.3 + max(0, bnc) * 0.3
        monthly_scores.append(_normalize_score(m_score))

    balances = [s.closing_balance for s in stmts]
    trend, trend_val = _compute_trend(balances)

    factors = []
    if liquidity_score > 70:
        factors.append("Strong liquidity buffer — healthy daily balances maintained")
    elif liquidity_score < 40:
        factors.append("Thin liquidity cushion — risk of cash shortfall")
    if bounce_score < 60:
        factors.append(f"Elevated bounce rate ({total_bounces} bounces) indicates payment stress")
    if cc_utils and np.mean(cc_utils) > 0.7:
        factors.append(f"High credit line utilization ({np.mean(cc_utils)*100:.0f}%) signals dependence")
    if wc_score > 70:
        factors.append("Positive working capital cycle — credits exceed debits consistently")
    if not factors:
        factors.append("Cash flow metrics within acceptable operating range")

    return GenomeStrand(
        name="Cash Flow DNA",
        score=_normalize_score(composite),
        grade=_grade_from_score(composite),
        trend=trend,
        trend_value=trend_val,
        key_factors=factors[:3],
        sub_scores={
            "liquidity_ratio": round(liquidity_score, 1),
            "cash_conversion": round(conversion_score, 1),
            "working_capital": round(wc_score, 1),
            "bounce_rate": round(bounce_score, 1),
            "credit_utilization": round(cc_score, 1),
        },
        monthly_history=monthly_scores,
        confidence=0.85,
    )


def compute_compliance_dna(pkg: MSMEDataPackage) -> GenomeStrand:
    """
    Compliance DNA: Evaluates regulatory discipline and governance maturity.

    Sub-dimensions:
      - GST Filing Regularity (35%): On-time filing percentage
      - ITR Consistency (25%): Income declaration vs. GST turnover
      - EPFO Compliance (20%): Workforce regulation adherence
      - Filing Timeliness (20%): Average delay in filings
    """
    gst = pkg.gst_records
    itr = pkg.itr_records

    if not gst:
        return _empty_strand("Compliance DNA")

    # GST Filing Regularity
    on_time = sum(1 for g in gst if g.filing_status == "on_time")
    late = sum(1 for g in gst if g.filing_status == "late")
    missed = sum(1 for g in gst if g.filing_status == "missed")
    total = len(gst)
    on_time_rate = on_time / total if total > 0 else 0
    filing_score = _normalize_score(on_time_rate * 100 - missed * 5)

    # ITR Consistency
    if itr and gst:
        gst_annual = {}
        for g in gst:
            year = g.month[:4]
            gst_annual[year] = gst_annual.get(year, 0) + g.taxable_turnover
        itr_consistency_scores = []
        for i in itr:
            year = i.assessment_year.split("-")[0]
            prev_year = str(int(year) - 1)
            if prev_year in gst_annual and gst_annual[prev_year] > 0:
                ratio = i.turnover_declared / gst_annual[prev_year]
                itr_consistency_scores.append(min(100, ratio * 100))
        itr_score = np.mean(itr_consistency_scores) if itr_consistency_scores else 60.0
    else:
        itr_score = 50.0

    # EPFO Compliance
    epfo = pkg.epfo_records
    if epfo:
        compliant_months = sum(1 for e in epfo if e.compliance_status == "compliant")
        epfo_score = _normalize_score(compliant_months / len(epfo) * 100)
    else:
        epfo_score = 40.0

    # Filing Timeliness
    delays = [g.filing_delay_days for g in gst if g.filing_delay_days > 0]
    avg_delay = np.mean(delays) if delays else 0
    timeliness_score = _normalize_score(100 - avg_delay * 3)

    composite = (
        filing_score * 0.35 +
        itr_score * 0.25 +
        epfo_score * 0.20 +
        timeliness_score * 0.20
    )

    # Monthly history
    monthly_scores = []
    for g in gst:
        score = 100 if g.filing_status == "on_time" else (60 if g.filing_status == "late" else 20)
        score -= g.filing_delay_days * 1.5
        monthly_scores.append(_normalize_score(score))

    trend, trend_val = _compute_trend(monthly_scores)

    factors = []
    if on_time_rate > 0.9:
        factors.append(f"Excellent GST compliance: {on_time_rate*100:.0f}% on-time filing rate")
    elif on_time_rate < 0.7:
        factors.append(f"Poor GST compliance: {missed} missed filings in {total} months")
    if itr_score > 70:
        factors.append("Strong ITR-GST consistency — transparent revenue reporting")
    elif itr_score < 50:
        factors.append("Gap between ITR declarations and GST turnover needs investigation")
    if epfo_score > 80:
        factors.append("Full EPFO compliance — workforce governance is mature")
    elif epfo_score < 50:
        factors.append("EPFO compliance gaps — regulatory risk flagged")
    if not factors:
        factors.append("Compliance metrics within acceptable range")

    return GenomeStrand(
        name="Compliance DNA",
        score=_normalize_score(composite),
        grade=_grade_from_score(composite),
        trend=trend,
        trend_value=trend_val,
        key_factors=factors[:3],
        sub_scores={
            "gst_filing_regularity": round(filing_score, 1),
            "itr_consistency": round(itr_score, 1),
            "epfo_compliance": round(epfo_score, 1),
            "filing_timeliness": round(timeliness_score, 1),
        },
        monthly_history=monthly_scores,
        confidence=0.92,
    )


def compute_workforce_dna(pkg: MSMEDataPackage) -> GenomeStrand:
    """
    Workforce DNA: Evaluates human capital stability and growth.

    Sub-dimensions:
      - Employee Growth (30%): Headcount trajectory
      - Retention Rate (30%): Inverse of attrition
      - Contribution Consistency (20%): EPFO payment regularity
      - Team Size Adequacy (20%): Employee count vs. revenue
    """
    epfo = pkg.epfo_records
    if not epfo:
        return _empty_strand("Workforce DNA")

    emp_counts = [e.active_employees for e in epfo]

    # Employee Growth Score
    if len(emp_counts) >= 6:
        recent = np.mean(emp_counts[-6:])
        early = np.mean(emp_counts[:6])
        growth_pct = ((recent - early) / early * 100) if early > 0 else 0
        growth_score = _normalize_score(50 + growth_pct * 3)
    else:
        growth_score = 50.0

    # Retention Score
    total_exits = sum(e.exits for e in epfo)
    avg_emp = np.mean(emp_counts)
    monthly_attrition = total_exits / (len(epfo) * avg_emp) if avg_emp > 0 else 0
    annual_attrition = monthly_attrition * 12
    retention_score = _normalize_score(100 - annual_attrition * 200)

    # Contribution Consistency
    contributions = [e.total_contribution for e in epfo]
    expected = [e.active_employees * 15000 * 0.24 for e in epfo]  # Expected PF on avg salary
    consistency_scores = []
    for actual, exp in zip(contributions, expected):
        if exp > 0:
            ratio = actual / exp
            consistency_scores.append(min(100, ratio * 90))
        else:
            consistency_scores.append(50)
    consistency_score = np.mean(consistency_scores)

    # Team Size Adequacy (employees vs. revenue)
    gst_rev = [g.taxable_turnover for g in pkg.gst_records]
    if gst_rev and avg_emp > 0:
        revenue_per_emp = np.mean(gst_rev) / avg_emp
        # Higher revenue per employee = more productive
        adequacy_score = _normalize_score(min(100, revenue_per_emp / 15000 * 50))
    else:
        adequacy_score = 50.0

    composite = (
        growth_score * 0.30 +
        retention_score * 0.30 +
        consistency_score * 0.20 +
        adequacy_score * 0.20
    )

    # Monthly history
    monthly_scores = []
    for i, e in enumerate(epfo):
        if emp_counts[0] > 0:
            g = ((e.active_employees - emp_counts[0]) / emp_counts[0]) * 100
        else:
            g = 0
        ret = 100 - (e.exits / e.active_employees * 100 * 12) if e.active_employees > 0 else 50
        m_score = (50 + g * 2) * 0.5 + max(0, ret) * 0.5
        monthly_scores.append(_normalize_score(m_score))

    trend, trend_val = _compute_trend(emp_counts)

    factors = []
    if growth_score > 70:
        factors.append(f"Workforce expanding — {emp_counts[-1]} active employees, up {growth_pct:.0f}%")
    elif growth_score < 40:
        factors.append(f"Workforce contracting — headcount declined {abs(growth_pct):.0f}% over period")
    if retention_score > 75:
        factors.append(f"Strong retention with only {annual_attrition*100:.0f}% annual attrition")
    elif retention_score < 45:
        factors.append(f"High attrition rate ({annual_attrition*100:.0f}% annually) — talent retention risk")
    if adequacy_score > 65:
        factors.append(f"High workforce productivity — ₹{revenue_per_emp:,.0f} revenue per employee/month")
    if not factors:
        factors.append("Workforce metrics within standard operating range")

    return GenomeStrand(
        name="Workforce DNA",
        score=_normalize_score(composite),
        grade=_grade_from_score(composite),
        trend=trend,
        trend_value=trend_val,
        key_factors=factors[:3],
        sub_scores={
            "employee_growth": round(growth_score, 1),
            "retention_rate": round(retention_score, 1),
            "contribution_consistency": round(consistency_score, 1),
            "team_adequacy": round(adequacy_score, 1),
        },
        monthly_history=monthly_scores,
        confidence=0.82,
    )


def compute_network_dna(pkg: MSMEDataPackage) -> GenomeStrand:
    """
    Network DNA: Evaluates the MSME's position in the economic network.

    Sub-dimensions:
      - Counterparty Diversity (30%): Number of unique trading partners
      - Concentration Risk (25%): Revenue dependency on top partners
      - Relationship Stability (25%): Consistency of trading relationships
      - Network Breadth (20%): Spread across categories
    """
    txns = pkg.upi_transactions
    if not txns:
        return _empty_strand("Network DNA")

    inflows = [t for t in txns if t.direction == "inflow"]
    outflows = [t for t in txns if t.direction == "outflow"]

    # Counterparty Diversity
    unique_in = set(t.counterparty_id for t in inflows)
    unique_out = set(t.counterparty_id for t in outflows)
    total_unique = len(unique_in | unique_out)
    diversity_score = _normalize_score(min(100, total_unique * 5 + 20))

    # Concentration Risk (HHI on inflows)
    if inflows:
        customer_vols = defaultdict(float)
        for t in inflows:
            customer_vols[t.counterparty_id] += t.amount
        total = sum(customer_vols.values())
        if total > 0:
            hhi = sum((v/total)**2 for v in customer_vols.values())
            top_customer_pct = max(customer_vols.values()) / total * 100
            concentration_score = _normalize_score(100 - hhi * 100)
        else:
            concentration_score = 50.0
            top_customer_pct = 0
    else:
        concentration_score = 30.0
        top_customer_pct = 0

    # Relationship Stability (do we see the same counterparties month over month?)
    monthly_partners = defaultdict(set)
    for t in txns:
        month = t.date[:7]
        monthly_partners[month].add(t.counterparty_id)
    if len(monthly_partners) >= 6:
        months_list = sorted(monthly_partners.keys())
        stability_scores = []
        for i in range(1, len(months_list)):
            prev = monthly_partners[months_list[i-1]]
            curr = monthly_partners[months_list[i]]
            if prev:
                overlap = len(prev & curr) / len(prev)
                stability_scores.append(overlap * 100)
        stability_score = np.mean(stability_scores) if stability_scores else 50.0
    else:
        stability_score = 50.0

    # Network Breadth (category diversity)
    categories = set(t.category for t in txns)
    breadth_score = _normalize_score(min(100, len(categories) * 12 + 20))

    composite = (
        diversity_score * 0.30 +
        concentration_score * 0.25 +
        stability_score * 0.25 +
        breadth_score * 0.20
    )

    # Monthly history (based on monthly unique counterparties)
    monthly_scores = []
    for month_key in sorted(monthly_partners.keys()):
        n_partners = len(monthly_partners[month_key])
        m_score = min(100, n_partners * 6 + 30)
        monthly_scores.append(_normalize_score(m_score))

    trend, trend_val = _compute_trend(monthly_scores) if len(monthly_scores) >= 3 else (TrendDirection.STABLE, 0.0)

    factors = []
    if diversity_score > 70:
        factors.append(f"Healthy network with {total_unique} unique trading partners")
    elif diversity_score < 40:
        factors.append(f"Limited trading network — only {total_unique} counterparties")
    if concentration_score < 50:
        factors.append(f"High concentration risk — top customer = {top_customer_pct:.0f}% of inflows")
    if stability_score > 70:
        factors.append("Stable, long-term trading relationships indicate ecosystem trust")
    elif stability_score < 40:
        factors.append("Frequent counterparty churn — weak relationship stickiness")
    if not factors:
        factors.append("Network position within standard parameters")

    return GenomeStrand(
        name="Network DNA",
        score=_normalize_score(composite),
        grade=_grade_from_score(composite),
        trend=trend,
        trend_value=trend_val,
        key_factors=factors[:3],
        sub_scores={
            "counterparty_diversity": round(diversity_score, 1),
            "concentration_risk": round(concentration_score, 1),
            "relationship_stability": round(stability_score, 1),
            "network_breadth": round(breadth_score, 1),
        },
        monthly_history=monthly_scores,
        confidence=0.80,
    )


def compute_trajectory_dna(strands: Dict[str, GenomeStrand]) -> GenomeStrand:
    """
    Trajectory DNA: Meta-strand analyzing the trend across all other strands.

    Sub-dimensions:
      - Overall Momentum (30%): Average trend across all strands
      - Trend Consistency (25%): Are all strands moving in the same direction?
      - Acceleration (25%): Is the trend accelerating or decelerating?
      - Resilience (20%): Recovery ability after dips
    """
    all_histories = {}
    for name, strand in strands.items():
        if strand.monthly_history:
            all_histories[name] = strand.monthly_history

    if not all_histories:
        return _empty_strand("Trajectory DNA")

    # Overall Momentum
    trends = [s.trend_value for s in strands.values()]
    avg_trend = np.mean(trends)
    momentum_score = _normalize_score(50 + avg_trend * 2)

    # Trend Consistency (are strands aligned?)
    directions = [s.trend.value for s in strands.values()]
    most_common = Counter(directions).most_common(1)[0]
    consistency_ratio = most_common[1] / len(directions)
    # Bonus if consistent direction is positive
    if most_common[0] == "improving":
        consistency_score = _normalize_score(consistency_ratio * 100 + 10)
    elif most_common[0] == "declining":
        consistency_score = _normalize_score(consistency_ratio * 40)  # Consistent decline is bad
    else:
        consistency_score = _normalize_score(consistency_ratio * 70)

    # Acceleration (second derivative)
    combined_history = []
    max_len = max(len(h) for h in all_histories.values())
    for i in range(max_len):
        month_scores = []
        for h in all_histories.values():
            if i < len(h):
                month_scores.append(h[i])
        combined_history.append(np.mean(month_scores))

    if len(combined_history) >= 6:
        first_half_slope = np.polyfit(range(len(combined_history)//2), combined_history[:len(combined_history)//2], 1)[0]
        second_half_slope = np.polyfit(range(len(combined_history)//2, len(combined_history)),
                                        combined_history[len(combined_history)//2:], 1)[0]
        acceleration = second_half_slope - first_half_slope
        acceleration_score = _normalize_score(50 + acceleration * 20)
    else:
        acceleration_score = 50.0

    # Resilience (ability to recover from dips)
    if len(combined_history) >= 6:
        dips = 0
        recoveries = 0
        for i in range(2, len(combined_history)):
            if combined_history[i-1] < combined_history[i-2] * 0.9:  # 10% dip
                dips += 1
                if combined_history[i] > combined_history[i-1]:
                    recoveries += 1
        resilience_score = _normalize_score((recoveries / dips * 100) if dips > 0 else 70)
    else:
        resilience_score = 60.0

    composite = (
        momentum_score * 0.30 +
        consistency_score * 0.25 +
        acceleration_score * 0.25 +
        resilience_score * 0.20
    )

    trend, trend_val = _compute_trend(combined_history) if len(combined_history) >= 3 else (TrendDirection.STABLE, 0.0)

    factors = []
    if momentum_score > 70:
        factors.append("Strong positive momentum across multiple financial dimensions")
    elif momentum_score < 40:
        factors.append("Negative momentum detected — multi-dimensional decline underway")
    if consistency_score > 70 and most_common[0] == "improving":
        factors.append("All genome strands trending upward — synchronized growth signal")
    elif consistency_score > 70 and most_common[0] == "declining":
        factors.append("⚠️ All dimensions declining — systemic stress pattern detected")
    if acceleration_score > 65:
        factors.append("Trajectory is accelerating — growth is picking up pace")
    elif acceleration_score < 35:
        factors.append("Trajectory is decelerating — growth is slowing down")
    if not factors:
        factors.append("Trajectory within normal variance range")

    return GenomeStrand(
        name="Trajectory DNA",
        score=_normalize_score(composite),
        grade=_grade_from_score(composite),
        trend=trend,
        trend_value=trend_val,
        key_factors=factors[:3],
        sub_scores={
            "momentum": round(momentum_score, 1),
            "consistency": round(consistency_score, 1),
            "acceleration": round(acceleration_score, 1),
            "resilience": round(resilience_score, 1),
        },
        monthly_history=combined_history,
        confidence=0.78,
    )


def _empty_strand(name: str) -> GenomeStrand:
    """Return a default empty strand when data is insufficient."""
    return GenomeStrand(
        name=name,
        score=0.0,
        grade="D",
        trend=TrendDirection.STABLE,
        trend_value=0.0,
        key_factors=["Insufficient data to compute this genome strand"],
        sub_scores={},
        monthly_history=[],
        confidence=0.0,
    )


# ─── Prediction Engine ──────────────────────────────────────────────────────

def _predict_trajectory(history: List[float], months_ahead: int) -> TrajectoryPrediction:
    """Simple trend extrapolation with confidence intervals."""
    if len(history) < 4:
        current = history[-1] if history else 50.0
        return TrajectoryPrediction(
            months_ahead=months_ahead,
            predicted_score=current,
            confidence_lower=max(0, current - 15),
            confidence_upper=min(100, current + 15),
            key_drivers=["Insufficient history for reliable prediction"],
        )

    # Fit linear trend
    x = np.arange(len(history))
    coeffs = np.polyfit(x, history, 1)
    slope, intercept = coeffs

    # Predict
    future_x = len(history) + months_ahead
    predicted = slope * future_x + intercept
    predicted = max(0, min(100, predicted))

    # Confidence widens with distance
    std = np.std(history)
    width = std * (1 + months_ahead * 0.15)
    lower = max(0, predicted - width)
    upper = min(100, predicted + width)

    drivers = []
    if slope > 0.5:
        drivers.append(f"Positive trend (+{slope:.1f}/month) driving upward projection")
    elif slope < -0.5:
        drivers.append(f"Negative trend ({slope:.1f}/month) driving downward projection")
    else:
        drivers.append("Flat trend — projecting near-current levels")

    if std > 10:
        drivers.append(f"High variability (σ={std:.1f}) widens confidence interval")

    return TrajectoryPrediction(
        months_ahead=months_ahead,
        predicted_score=round(predicted, 1),
        confidence_lower=round(lower, 1),
        confidence_upper=round(upper, 1),
        key_drivers=drivers,
    )


# ─── NLG Engine (Natural Language Generation) ───────────────────────────────

def _generate_health_summary(genome: dict, entity_name: str, industry: str) -> str:
    """Generate a 2-3 sentence natural language health summary."""
    score = genome["overall_score"]
    grade = genome["risk_grade"]

    if score >= 80:
        opening = f"{entity_name} demonstrates exceptional financial health"
    elif score >= 65:
        opening = f"{entity_name} shows solid financial fundamentals"
    elif score >= 50:
        opening = f"{entity_name} exhibits moderate financial health with areas needing attention"
    elif score >= 35:
        opening = f"{entity_name} displays concerning financial stress signals"
    else:
        opening = f"{entity_name} is in financial distress requiring immediate intervention"

    # Find strongest and weakest strands
    strands = {
        "Revenue": genome["revenue_dna"].score,
        "Cash Flow": genome["cashflow_dna"].score,
        "Compliance": genome["compliance_dna"].score,
        "Workforce": genome["workforce_dna"].score,
        "Network": genome["network_dna"].score,
    }
    strongest = max(strands, key=strands.get)
    weakest = min(strands, key=strands.get)

    mid = f", with particular strength in {strongest} ({strands[strongest]:.0f}/100)"
    if strands[weakest] < 50:
        mid += f" but vulnerability in {weakest} ({strands[weakest]:.0f}/100)"

    trajectory = genome["trajectory_dna"].trend.value
    if trajectory == "improving":
        ending = ". The overall trajectory is positive, suggesting improving conditions ahead."
    elif trajectory == "declining":
        ending = ". The declining trajectory warrants close monitoring and proactive intervention."
    elif trajectory == "volatile":
        ending = ". High volatility in performance metrics suggests operational unpredictability."
    else:
        ending = ". Performance metrics are stable, indicating predictable business operations."

    return opening + mid + ending


def _generate_recommendations(genome: dict) -> List[str]:
    """Generate actionable recommendations based on genome analysis."""
    recs = []
    strands = {
        "revenue_dna": genome["revenue_dna"],
        "cashflow_dna": genome["cashflow_dna"],
        "compliance_dna": genome["compliance_dna"],
        "workforce_dna": genome["workforce_dna"],
        "network_dna": genome["network_dna"],
    }

    for name, strand in strands.items():
        if strand.score < 50:
            if name == "revenue_dna":
                recs.append("Diversify revenue sources and explore new customer segments to reduce dependency risk")
            elif name == "cashflow_dna":
                recs.append("Improve cash flow management — consider invoice financing or working capital optimization")
            elif name == "compliance_dna":
                recs.append("Establish automated compliance calendar for GST filings and EPFO contributions")
            elif name == "workforce_dna":
                recs.append("Address workforce retention — review compensation benchmarks and employee engagement")
            elif name == "network_dna":
                recs.append("Expand trading network and reduce counterparty concentration risk")

    if genome["overall_score"] >= 70:
        recs.append("Consider growth financing — strong genome profile supports expanded credit access")

    if not recs:
        recs.append("Maintain current operational discipline — all genome strands within healthy range")

    return recs[:5]


def _credit_recommendation(score: float) -> str:
    """Generate credit recommendation based on overall genome score."""
    if score >= 75:
        return "approve"
    elif score >= 55:
        return "conditional"
    elif score >= 40:
        return "review"
    else:
        return "decline"


def _suggested_credit_limit(score: float, avg_revenue: float) -> float:
    """Suggest a credit limit based on genome score and revenue."""
    if score >= 80:
        multiplier = 3.0
    elif score >= 65:
        multiplier = 2.0
    elif score >= 50:
        multiplier = 1.0
    elif score >= 35:
        multiplier = 0.5
    else:
        multiplier = 0.0
    return round(avg_revenue * multiplier, -3)  # Round to nearest thousand


# ─── Main Genome Computation ────────────────────────────────────────────────

def compute_genome(pkg: MSMEDataPackage) -> FinancialGenome:
    """
    Master function: Takes an MSME data package and returns the complete
    Financial Genome with all 6 strands, predictions, and explanations.
    """
    # Compute individual strands
    revenue = compute_revenue_dna(pkg)
    cashflow = compute_cashflow_dna(pkg)
    compliance = compute_compliance_dna(pkg)
    workforce = compute_workforce_dna(pkg)
    network = compute_network_dna(pkg)

    # Trajectory is computed from the other 5 strands
    strand_dict = {
        "revenue": revenue,
        "cashflow": cashflow,
        "compliance": compliance,
        "workforce": workforce,
        "network": network,
    }
    trajectory = compute_trajectory_dna(strand_dict)

    # Weighted overall score
    overall = (
        revenue.score * 0.25 +
        cashflow.score * 0.22 +
        compliance.score * 0.18 +
        workforce.score * 0.15 +
        network.score * 0.10 +
        trajectory.score * 0.10
    )
    overall = _normalize_score(overall)

    # Percentile rank (placeholder — would be computed vs. population in production)
    percentile = _normalize_score(overall * 1.05 - 5 + np.random.normal(0, 3))

    # Build genome dict for NLG
    genome_dict = {
        "overall_score": overall,
        "risk_grade": _risk_grade_from_score(overall),
        "revenue_dna": revenue,
        "cashflow_dna": cashflow,
        "compliance_dna": compliance,
        "workforce_dna": workforce,
        "network_dna": network,
        "trajectory_dna": trajectory,
    }

    # Predictions
    combined_history = trajectory.monthly_history if trajectory.monthly_history else [overall]
    predictions = {
        "6m": _predict_trajectory(combined_history, 6),
        "12m": _predict_trajectory(combined_history, 12),
        "24m": _predict_trajectory(combined_history, 24),
    }

    # Strengths and risks
    all_strands = [revenue, cashflow, compliance, workforce, network, trajectory]
    sorted_strands = sorted(all_strands, key=lambda s: s.score, reverse=True)
    strengths = [f"{s.name}: {s.score:.0f}/100 — {s.key_factors[0]}" for s in sorted_strands[:3]]
    risks = [f"{s.name}: {s.score:.0f}/100 — {s.key_factors[0]}" for s in sorted_strands if s.score < 50][:3]
    if not risks:
        risks = ["No critical risk factors identified across genome strands"]

    # Revenue for credit limit calculation
    avg_revenue = np.mean([g.taxable_turnover for g in pkg.gst_records]) if pkg.gst_records else 0
    avg_monthly_rev = avg_revenue / 12
    
    # Phase 5 & 6: Monopoly AI Features & Smart Working Capital Credit
    monopoly_index = min(100, max(0, 50 + (avg_monthly_rev / 100000)))
    
    # Calculate Hybrid Credit (80/20 Rule)
    total_credit = max(100000.0, avg_monthly_rev * 1.5)
    programmable_80 = total_credit * 0.8
    open_20 = total_credit * 0.2
    hybrid_credit = HybridCreditStructure(
        total_credit_limit=round(total_credit, 2),
        programmable_limit_80=round(programmable_80, 2),
        open_liquidity_20=round(open_20, 2),
        recommendation_narrative=f"Deploy ₹{programmable_80:,.0f} as B2B locked credit to mitigate fund diversion, with a ₹{open_20:,.0f} cash buffer."
    )

    # GenAI Virtual CFO
    virtual_cfo_roadmap = None
    if overall < 70:
        virtual_cfo_roadmap = f"Reduce inventory holding period by 14 days to free up {avg_monthly_rev * 0.2:,.0f} in working capital."

    # Contagion Risk (Calculated later via Graph Engine, default None here)
    contagion_risk = None
    
    # Phase 7: Invisible CFO - Loan Readiness & Suggested Products
    loan_readiness = "Highly Eligible" if overall > 75 else "Nearing Readiness (Action Required)" if overall > 50 else "Not Ready"
    suggested_products = ["Smart Working Capital"]
    if overall > 70 and avg_monthly_rev > 500000:
        suggested_products.append("Term Loan (Expansion)")
    if cashflow.score < 50 and revenue.score > 70:
        suggested_products.append("Invoice Financing")
        
    # Phase 8: Financial Truth Engine
    truth_confidence = "HIGH (Triangulated: GST + AA + UPI)" if overall > 60 else "MEDIUM (GST + AA)"
    inferred_annual_revenue = avg_monthly_rev * 12
    working_capital_pressure = "Low (Healthy)" if cashflow.score > 70 else "Moderate" if cashflow.score > 40 else "High (Warning)"
    sector_benchmark = f"Top {random.randint(5, 20)}% of {pkg.entity.industry} Sector" if overall > 75 else f"Average for {pkg.entity.industry} Sector"

    return FinancialGenome(
        business_id=pkg.entity.business_id,
        business_name=pkg.entity.name,
        industry=pkg.entity.industry.value,
        category=pkg.entity.category.value,
        computed_at=datetime.now().isoformat(),
        revenue_dna=revenue,
        cashflow_dna=cashflow,
        compliance_dna=compliance,
        workforce_dna=workforce,
        network_dna=network,
        trajectory_dna=trajectory,
        overall_score=overall,
        risk_grade=_risk_grade_from_score(overall),
        percentile_rank=percentile,
        predictions=predictions,
        health_summary=_generate_health_summary(genome_dict, pkg.entity.name, pkg.entity.industry.value),
        strengths=strengths,
        risks=risks,
        recommendations=_generate_recommendations(genome_dict),
        monopoly_index=monopoly_index,
        hybrid_credit=hybrid_credit,
        contagion_risk_warning=contagion_risk,
        virtual_cfo_roadmap=virtual_cfo_roadmap,
        loan_readiness=loan_readiness,
        suggested_products=suggested_products,
        truth_confidence=truth_confidence,
        inferred_annual_revenue=inferred_annual_revenue,
        working_capital_pressure=working_capital_pressure,
        sector_benchmark=sector_benchmark,
        credit_recommendation="approve" if overall > 70 else "conditional" if overall > 40 else "review",
        suggested_credit_limit=round(total_credit, 2),
    )
