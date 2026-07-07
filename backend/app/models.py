"""
MSME FinGenome — Data Models
============================
Pydantic schemas defining the complete data ontology for the Financial Genome system.
Every MSME is modeled as a multi-dimensional entity with 7+ data source inputs
converging into a 6-strand Financial Genome.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from enum import Enum
from datetime import date


# ─── Enumerations ────────────────────────────────────────────────────────────

class IndustryType(str, Enum):
    MANUFACTURING = "Manufacturing"
    RETAIL = "Retail & Trade"
    SERVICES = "Professional Services"
    FOOD_BEVERAGE = "Food & Beverage"
    TEXTILES = "Textiles & Apparel"
    IT_SERVICES = "IT & Software Services"
    CONSTRUCTION = "Construction & Infrastructure"
    AGRICULTURE = "Agriculture & Allied"
    HEALTHCARE = "Healthcare & Pharma"
    LOGISTICS = "Logistics & Transport"
    EDUCATION = "Education & Training"
    RENEWABLE_ENERGY = "Renewable Energy"


class RiskGrade(str, Enum):
    A_PLUS = "A+"
    A = "A"
    B_PLUS = "B+"
    B = "B"
    C = "C"
    D = "D"


class TrendDirection(str, Enum):
    IMPROVING = "improving"
    STABLE = "stable"
    DECLINING = "declining"
    VOLATILE = "volatile"


class FilingStatus(str, Enum):
    ON_TIME = "on_time"
    LATE = "late"
    MISSED = "missed"


class MSMECategory(str, Enum):
    MICRO = "Micro"
    SMALL = "Small"
    MEDIUM = "Medium"


class BusinessProfile(str, Enum):
    """Archetype profiles for synthetic data generation."""
    THRIVING = "thriving"
    GROWING = "growing"
    STABLE = "stable"
    SEASONAL = "seasonal"
    STRUGGLING = "struggling"
    DECLINING = "declining"
    NEW_BUSINESS = "new_business"


# ─── Input Data Models (7 Data Sources) ─────────────────────────────────────

class MSMEEntity(BaseModel):
    """Core MSME identity and metadata."""
    business_id: str
    name: str
    industry: IndustryType
    category: MSMECategory
    city: str
    state: str
    gstin: str
    udyam_number: str
    registration_date: str
    pan: str
    contact_email: str
    description: str
    profile_type: BusinessProfile


class GSTRecord(BaseModel):
    """Monthly GST filing data — captures revenue patterns and compliance."""
    month: str  # YYYY-MM
    taxable_turnover: float
    tax_paid: float
    filing_status: FilingStatus
    filing_delay_days: int = 0
    input_credit: float
    output_liability: float
    b2b_invoices: int
    b2c_invoices: int


class UPITransaction(BaseModel):
    """Individual UPI transaction — builds the network graph."""
    transaction_id: str
    date: str  # YYYY-MM-DD
    amount: float
    direction: str  # "inflow" or "outflow"
    counterparty_id: str
    counterparty_name: str
    category: str  # "sales", "supplier", "salary", "utilities", "rent", "other"


class BankStatement(BaseModel):
    """Monthly aggregated bank statement via Account Aggregator."""
    month: str  # YYYY-MM
    opening_balance: float
    closing_balance: float
    total_credits: float
    total_debits: float
    credit_count: int
    debit_count: int
    avg_daily_balance: float
    min_balance: float
    max_balance: float
    cash_credit_utilization: float = 0.0  # % of limit used
    emi_outflows: float = 0.0
    bounce_count: int = 0


class EPFORecord(BaseModel):
    """Monthly EPFO contribution data — workforce stability signals."""
    month: str  # YYYY-MM
    active_employees: int
    new_joins: int
    exits: int
    total_contribution: float
    employer_contribution: float
    employee_contribution: float
    compliance_status: str  # "compliant", "delayed", "defaulted"


class ITRRecord(BaseModel):
    """Annual Income Tax Return data."""
    assessment_year: str  # e.g., "2025-26"
    declared_income: float
    income_from_business: float
    depreciation: float
    tax_paid: float
    filing_date: str
    audit_required: bool = False
    turnover_declared: float = 0.0


class AlternateSignal(BaseModel):
    """Alternate / non-traditional data signals."""
    source: str  # "google_reviews", "utility_payments", "trade_references"
    date: str
    signal_type: str  # "positive", "negative", "neutral"
    value: float
    description: str


# ─── Complete MSME Data Package ──────────────────────────────────────────────

class MSMEDataPackage(BaseModel):
    """All data for a single MSME — the input to the Genome Engine."""
    entity: MSMEEntity
    gst_records: List[GSTRecord]
    upi_transactions: List[UPITransaction]
    bank_statements: List[BankStatement]
    epfo_records: List[EPFORecord]
    itr_records: List[ITRRecord]
    alternate_signals: List[AlternateSignal] = []


# ─── Genome Output Models ───────────────────────────────────────────────────

class GenomeStrand(BaseModel):
    """Single dimension of the Financial Genome (one of 6 strands)."""
    name: str
    score: float = Field(ge=0, le=100, description="Score from 0-100")
    grade: str  # A+, A, B+, B, C, D
    trend: TrendDirection
    trend_value: float = 0.0  # % change
    key_factors: List[str]  # Top 3 contributing factors (NLG)
    sub_scores: Dict[str, float]  # Detailed sub-dimension scores
    monthly_history: List[float] = []  # Score over last 24 months
    confidence: float = Field(ge=0, le=1, default=0.85)


class TrajectoryPrediction(BaseModel):
    """Forward-looking prediction for a genome strand."""
    months_ahead: int
    predicted_score: float
    confidence_lower: float
    confidence_upper: float
    key_drivers: List[str]

class HybridCreditStructure(BaseModel):
    total_credit_limit: float
    programmable_limit_80: float
    open_liquidity_20: float
    recommendation_narrative: str

class FinancialGenome(BaseModel):
    """The complete Financial Genome — the OUTPUT of the engine.
    This is the core deliverable: a multi-dimensional, temporal,
    explainable financial identity for an MSME."""
    business_id: str
    business_name: str
    industry: str
    category: str
    computed_at: str

    # The 6 Genome Strands
    revenue_dna: GenomeStrand
    cashflow_dna: GenomeStrand
    compliance_dna: GenomeStrand
    workforce_dna: GenomeStrand
    network_dna: GenomeStrand
    trajectory_dna: GenomeStrand

    # Aggregate Metrics
    overall_score: float = Field(ge=0, le=100)
    risk_grade: RiskGrade
    percentile_rank: float = Field(ge=0, le=100, description="Percentile vs. industry peers")

    # Predictions
    predictions: Dict[str, TrajectoryPrediction]  # "6m", "12m", "24m"

    # Explainability
    health_summary: str  # 2-3 sentence NLG summary
    strengths: List[str]  # Top 3 strengths
    risks: List[str]  # Top 3 risk factors
    recommendations: List[str]  # Actionable recommendations
    
    # Phase 5: Prototype AI Features
    monopoly_index: Optional[float] = None
    hybrid_credit: Optional[HybridCreditStructure] = None
    contagion_risk_warning: Optional[str] = None
    virtual_cfo_roadmap: Optional[str] = None
    
    # Phase 7: Invisible CFO Prototype AI Features
    loan_readiness: Optional[str] = None
    suggested_products: Optional[List[str]] = None
    
    # Phase 8: Financial Truth Engine Features
    truth_confidence: Optional[str] = None
    inferred_annual_revenue: Optional[float] = None
    working_capital_pressure: Optional[str] = None
    sector_benchmark: Optional[str] = None
    
    credit_recommendation: str  # "approve", "conditional", "decline", "review"
    suggested_credit_limit: float = 0.0


# ─── Network / Graph Models ─────────────────────────────────────────────────

class NetworkNode(BaseModel):
    """A node in the MSME economic network graph."""
    id: str
    name: str
    industry: str
    health_score: float
    risk_grade: str
    is_primary: bool = False  # Is this the MSME being analyzed?
    category: str = "msme"  # "msme", "customer", "supplier"
    size: float = 1.0  # For visualization scaling


class NetworkEdge(BaseModel):
    """An edge in the economic network — represents financial relationship."""
    source: str
    target: str
    transaction_volume: float  # Total ₹ value
    transaction_count: int
    direction: str  # "inflow", "outflow", "bidirectional"
    strength: float = Field(ge=0, le=1, description="Normalized relationship strength")
    is_critical: bool = False  # True if >30% of revenue/cost


class MSMENetwork(BaseModel):
    """Complete network graph for an MSME and its economic relationships."""
    primary_msme_id: str
    nodes: List[NetworkNode]
    edges: List[NetworkEdge]
    metrics: Dict[str, float]  # degree_centrality, concentration_risk, etc.
    risk_narrative: str  # NLG summary of network risks


# ─── API Response Models ─────────────────────────────────────────────────────

class MSMEListItem(BaseModel):
    """Summary item for the MSME explorer sidebar."""
    business_id: str
    name: str
    industry: str
    category: str
    city: str
    overall_score: float
    risk_grade: str
    trend: str


class DashboardSummary(BaseModel):
    """Aggregate statistics for the dashboard header."""
    total_msmes: int
    avg_health_score: float
    grade_distribution: Dict[str, int]
    industry_distribution: Dict[str, int]
    credit_worthy_count: int
    at_risk_count: int
    newly_onboarded: int
