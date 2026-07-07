"""
MSME FinGenome — Synthetic Data Generator
==========================================
Generates realistic MSME financial data across 7 data sources for 50+ businesses.
Each MSME has a distinct "profile archetype" that drives realistic patterns:
  - Thriving: Strong across all dimensions
  - Growing: Rapid expansion, some cash flow tension
  - Stable: Steady, predictable, lower growth
  - Seasonal: Cyclical patterns (agriculture, tourism, etc.)
  - Struggling: Revenue decline, compliance issues
  - Declining: Past peak, contracting
  - New Business: Limited history, high variance

The generator creates interconnected businesses (UPI transactions between them)
to build a realistic economic network graph.
"""

import random
import string
import uuid
import math
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
import numpy as np

from app.models import (
    MSMEEntity, GSTRecord, UPITransaction, BankStatement,
    EPFORecord, ITRRecord, AlternateSignal, MSMEDataPackage,
    IndustryType, MSMECategory, BusinessProfile, FilingStatus
)


# ─── Constants ───────────────────────────────────────────────────────────────

INDIAN_CITIES = [
    ("Mumbai", "Maharashtra"), ("Delhi", "Delhi"), ("Bengaluru", "Karnataka"),
    ("Hyderabad", "Telangana"), ("Chennai", "Tamil Nadu"), ("Kolkata", "West Bengal"),
    ("Pune", "Maharashtra"), ("Ahmedabad", "Gujarat"), ("Jaipur", "Rajasthan"),
    ("Lucknow", "Uttar Pradesh"), ("Surat", "Gujarat"), ("Coimbatore", "Tamil Nadu"),
    ("Indore", "Madhya Pradesh"), ("Nagpur", "Maharashtra"), ("Kochi", "Kerala"),
    ("Vadodara", "Gujarat"), ("Ludhiana", "Punjab"), ("Visakhapatnam", "Andhra Pradesh"),
    ("Thiruvananthapuram", "Kerala"), ("Rajkot", "Gujarat"),
]

BUSINESS_NAMES = {
    IndustryType.MANUFACTURING: [
        "Precision Auto Components", "Shree Krishna Steels", "NovaTech Plastics",
        "Durable Forge Industries", "BharatMech Engineering", "Apex Metal Works",
        "Indo-Pacific Castings", "Sunrise Polymers", "Everest Machine Tools",
    ],
    IndustryType.RETAIL: [
        "Urban Bazaar Retail", "MegaMart Express", "FreshPick Groceries",
        "Trendy Threads Fashion", "ElectroHub Retail", "HomeStyle Furnishings",
        "QuickBuy Supermarket", "Sparkle Jewellers",
    ],
    IndustryType.SERVICES: [
        "Pinnacle Consulting Group", "ClearView Auditors", "TrustBridge Legal",
        "SwiftHR Solutions", "ProManage Advisory", "StratEdge Partners",
    ],
    IndustryType.FOOD_BEVERAGE: [
        "Spice Route Kitchen", "FreshBrew Beverages", "Golden Grain Foods",
        "Royal Biryani House", "PureJuice India", "DailyBite Catering",
        "AnnapurnaFoods", "TasteBud Snacks",
    ],
    IndustryType.TEXTILES: [
        "Priya's Handloom Creations", "SilkRoute Fabrics", "VasthraWeave Textiles",
        "IndoThread Exports", "KalaCraft Garments", "Heritage Weaves",
    ],
    IndustryType.IT_SERVICES: [
        "CodeNova Technologies", "PixelPerfect Solutions", "CloudBridge Systems",
        "DataMind Analytics", "InnoSoft Labs", "QuantumByte Tech",
        "NexGen Digital", "SwiftStack Solutions",
    ],
    IndustryType.CONSTRUCTION: [
        "BuildRight Infrastructure", "UrbanEdge Constructions", "SolidBase Projects",
        "SkyScraper Developers", "GreenBuild Corp", "Foundation First Builders",
    ],
    IndustryType.AGRICULTURE: [
        "Green Harvest Agro", "KisanFirst FarmTech", "OrganicRoot Produce",
        "SeedTech Bioagri", "HarvestGold Exports", "FarmFresh Collective",
    ],
    IndustryType.HEALTHCARE: [
        "MedLife Diagnostics", "CareFirst Clinics", "VitalHealth Labs",
        "PharmaPoint Distributors", "WellBeing Healthcare", "CureTech Medical",
    ],
    IndustryType.LOGISTICS: [
        "QuickMove Logistics", "TransIndia Freight", "SwiftShip Couriers",
        "CargoLink Express", "RouteOptima Transport", "AllIndia Logistics",
    ],
    IndustryType.EDUCATION: [
        "BrightMinds Academy", "SkillForge Institute", "LearnPath EdTech",
        "FutureReady Training", "MindSpark Education",
    ],
    IndustryType.RENEWABLE_ENERGY: [
        "SolarPeak Energy", "WindForce Solutions", "GreenVolt Power",
        "EcoWatt Systems", "SunHarvest Renewables",
    ],
}

COUNTERPARTY_NAMES = [
    "Reliance Retail", "Tata Motors", "Hindustan Unilever", "ITC Limited",
    "Mahindra & Mahindra", "Bajaj Auto", "Asian Paints", "Britannia Industries",
    "Marico Ltd", "Godrej Consumer", "Dabur India", "Titan Company",
    "Page Industries", "Berger Paints", "Havells India", "Voltas Ltd",
    "Blue Star", "Crompton Greaves", "Supreme Industries", "Astral Poly",
    "Local Supplier A", "Local Supplier B", "Regional Distributor X",
    "State Warehouse Corp", "Municipal Water Board", "Power Grid Office",
    "Telecom Service Provider", "Cloud Hosting India", "Fleet Fuel Agency",
    "Raw Material Depot", "Packaging Solutions Ltd", "Labour Contractor Agency",
]

UPI_CATEGORIES = ["sales", "supplier_payment", "salary", "utilities", "rent",
                   "equipment", "raw_materials", "maintenance", "insurance",
                   "marketing", "logistics", "other"]


# ─── Profile Configuration ──────────────────────────────────────────────────

PROFILE_CONFIGS = {
    BusinessProfile.THRIVING: {
        "base_revenue_range": (800000, 3000000),
        "growth_rate": (0.03, 0.07),  # monthly
        "volatility": 0.08,
        "compliance_rate": 0.95,
        "employee_range": (25, 150),
        "employee_growth": 0.02,
        "cash_ratio": 1.3,  # credits / debits
        "bounce_prob": 0.01,
    },
    BusinessProfile.GROWING: {
        "base_revenue_range": (300000, 1200000),
        "growth_rate": (0.05, 0.12),
        "volatility": 0.15,
        "compliance_rate": 0.85,
        "employee_range": (10, 60),
        "employee_growth": 0.05,
        "cash_ratio": 1.05,
        "bounce_prob": 0.05,
    },
    BusinessProfile.STABLE: {
        "base_revenue_range": (500000, 1500000),
        "growth_rate": (0.0, 0.015),
        "volatility": 0.05,
        "compliance_rate": 0.92,
        "employee_range": (15, 80),
        "employee_growth": 0.005,
        "cash_ratio": 1.2,
        "bounce_prob": 0.02,
    },
    BusinessProfile.SEASONAL: {
        "base_revenue_range": (200000, 1000000),
        "growth_rate": (0.01, 0.03),
        "volatility": 0.25,
        "compliance_rate": 0.88,
        "employee_range": (8, 40),
        "employee_growth": 0.01,
        "cash_ratio": 1.1,
        "bounce_prob": 0.04,
    },
    BusinessProfile.STRUGGLING: {
        "base_revenue_range": (150000, 600000),
        "growth_rate": (-0.04, -0.01),
        "volatility": 0.20,
        "compliance_rate": 0.65,
        "employee_range": (5, 30),
        "employee_growth": -0.02,
        "cash_ratio": 0.85,
        "bounce_prob": 0.12,
    },
    BusinessProfile.DECLINING: {
        "base_revenue_range": (400000, 1200000),
        "growth_rate": (-0.06, -0.02),
        "volatility": 0.18,
        "compliance_rate": 0.55,
        "employee_range": (10, 50),
        "employee_growth": -0.04,
        "cash_ratio": 0.75,
        "bounce_prob": 0.18,
    },
    BusinessProfile.NEW_BUSINESS: {
        "base_revenue_range": (50000, 300000),
        "growth_rate": (0.08, 0.20),
        "volatility": 0.30,
        "compliance_rate": 0.80,
        "employee_range": (2, 12),
        "employee_growth": 0.08,
        "cash_ratio": 0.95,
        "bounce_prob": 0.08,
    },
}

PROFILE_DISTRIBUTION = [
    (BusinessProfile.THRIVING, 0.12),
    (BusinessProfile.GROWING, 0.18),
    (BusinessProfile.STABLE, 0.25),
    (BusinessProfile.SEASONAL, 0.15),
    (BusinessProfile.STRUGGLING, 0.15),
    (BusinessProfile.DECLINING, 0.08),
    (BusinessProfile.NEW_BUSINESS, 0.07),
]


# ─── Utility Functions ──────────────────────────────────────────────────────

def _generate_gstin(state_code: str) -> str:
    """Generate a realistic-looking GSTIN."""
    state_codes = {
        "Maharashtra": "27", "Delhi": "07", "Karnataka": "29",
        "Telangana": "36", "Tamil Nadu": "33", "West Bengal": "19",
        "Gujarat": "24", "Rajasthan": "08", "Uttar Pradesh": "09",
        "Madhya Pradesh": "23", "Kerala": "32", "Punjab": "03",
        "Andhra Pradesh": "37",
    }
    sc = state_codes.get(state_code, "27")
    pan = ''.join(random.choices(string.ascii_uppercase, k=5)) + \
          ''.join(random.choices(string.digits, k=4)) + \
          random.choice(string.ascii_uppercase)
    return f"{sc}{pan}1Z{random.choice(string.digits)}"


def _generate_udyam() -> str:
    """Generate a realistic Udyam registration number."""
    state = random.choice(["MH", "DL", "KA", "TN", "GJ", "RJ", "UP", "KL", "WB"])
    return f"UDYAM-{state}-00-{random.randint(1000000, 9999999)}"


def _generate_pan() -> str:
    return ''.join(random.choices(string.ascii_uppercase, k=5)) + \
           ''.join(random.choices(string.digits, k=4)) + \
           random.choice(string.ascii_uppercase)


def _seasonal_factor(month: int, industry: IndustryType) -> float:
    """Returns a seasonal multiplier based on industry and month."""
    seasonal_patterns = {
        IndustryType.AGRICULTURE: [0.6, 0.5, 0.7, 0.9, 1.0, 0.8, 0.7, 0.8, 1.1, 1.4, 1.5, 1.3],
        IndustryType.TEXTILES: [1.0, 0.8, 0.9, 0.7, 0.6, 0.7, 0.8, 0.9, 1.1, 1.3, 1.5, 1.2],
        IndustryType.RETAIL: [0.9, 0.8, 0.9, 0.8, 0.7, 0.8, 0.9, 0.9, 1.0, 1.2, 1.4, 1.3],
        IndustryType.FOOD_BEVERAGE: [1.0, 0.9, 1.0, 1.1, 1.2, 1.0, 0.9, 0.9, 1.0, 1.1, 1.2, 1.1],
        IndustryType.CONSTRUCTION: [0.7, 0.8, 1.0, 1.1, 1.2, 0.6, 0.5, 0.5, 0.9, 1.1, 1.2, 1.0],
    }
    default_pattern = [1.0, 0.95, 1.0, 0.98, 0.95, 0.97, 1.0, 0.98, 1.02, 1.05, 1.08, 1.03]
    pattern = seasonal_patterns.get(industry, default_pattern)
    return pattern[month - 1]


# ─── Main Generator ─────────────────────────────────────────────────────────

class SyntheticDataGenerator:
    """Generates a complete synthetic MSME ecosystem with interconnected businesses."""

    def __init__(self, num_msmes: int = 55, months: int = 24, seed: int = 42):
        self.num_msmes = num_msmes
        self.months = months
        self.rng = np.random.RandomState(seed)
        random.seed(seed)
        self.start_date = datetime(2024, 7, 1)
        self.msme_ids: List[str] = []
        self.msme_names: Dict[str, str] = {}

    def generate_all(self) -> List[MSMEDataPackage]:
        """Generate complete data packages for all MSMEs."""
        packages = []

        # Assign profiles based on distribution
        profiles = self._assign_profiles()

        # Generate MSMEs
        used_names: set = set()
        for i in range(self.num_msmes):
            profile = profiles[i]
            industry = random.choice(list(IndustryType))
            entity = self._generate_entity(i, industry, profile, used_names)
            self.msme_ids.append(entity.business_id)
            self.msme_names[entity.business_id] = entity.name
            used_names.add(entity.name)

        # Generate data packages with cross-references (network)
        for i, msme_id in enumerate(self.msme_ids):
            profile = profiles[i]
            entity = self._generate_entity_by_id(i, profile)
            if entity is None:
                continue

            config = PROFILE_CONFIGS[profile]
            pkg = self._generate_data_package(entity, config, profile)
            packages.append(pkg)

        return packages

    def generate_single(self, custom_gstin: str, custom_name: str = "New MSME Connection") -> MSMEDataPackage:
        """Generate a single MSME data package dynamically on the fly."""
        profile = random.choice([BusinessProfile.THRIVING, BusinessProfile.STABLE, BusinessProfile.NEW_BUSINESS])
        industry = random.choice(list(IndustryType))
        
        # Manually create the entity
        city, state = random.choice(INDIAN_CITIES)
        config = PROFILE_CONFIGS[profile]
        emp_lo, emp_hi = config["employee_range"]
        
        category = MSMECategory.MICRO
        if emp_hi > 50:
            category = random.choice([MSMECategory.SMALL, MSMECategory.MEDIUM])
        elif emp_hi > 20:
            category = random.choice([MSMECategory.MICRO, MSMECategory.SMALL])

        business_id = f"MSME_{self.rng.randint(1000, 9999)}"
        
        entity = MSMEEntity(
            business_id=business_id,
            name=custom_name,
            industry=industry,
            category=category,
            city=city,
            state=state,
            gstin=custom_gstin,
            udyam_number=_generate_udyam(),
            registration_date=(datetime.now() - timedelta(days=700)).strftime("%Y-%m-%d"),
            pan=_generate_pan(),
            contact_email=f"info@{custom_name.lower().replace(' ', '').replace('&', '')[:15]}.in",
            description=f"A freshly onboarded {category.value.lower()} enterprise.",
            profile_type=profile,
        )
        
        # We don't cache this entity since it's just a simulation/on-the-fly
        # It won't have inbound network links initially, but we can generate outbound ones via _generate_upi_transactions
        
        pkg = self._generate_data_package(entity, config, profile)
        return pkg

    def _assign_profiles(self) -> List[BusinessProfile]:
        """Assign business profiles based on target distribution."""
        profiles = []
        for profile, ratio in PROFILE_DISTRIBUTION:
            count = max(1, int(self.num_msmes * ratio))
            profiles.extend([profile] * count)

        # Pad or trim to exact count
        while len(profiles) < self.num_msmes:
            profiles.append(random.choice([p for p, _ in PROFILE_DISTRIBUTION]))
        profiles = profiles[:self.num_msmes]
        random.shuffle(profiles)
        return profiles

    def _generate_entity(self, idx: int, industry: IndustryType,
                         profile: BusinessProfile, used_names: set) -> MSMEEntity:
        """Generate a single MSME entity."""
        city, state = random.choice(INDIAN_CITIES)

        # Pick a unique name
        name_pool = BUSINESS_NAMES.get(industry, ["Enterprise"])
        name = random.choice(name_pool)
        suffix = ""
        while (name + suffix) in used_names:
            suffix = f" {random.choice(['Pvt Ltd', 'LLP', 'Corp', 'India', 'Group'])}"
        name = name + suffix

        config = PROFILE_CONFIGS[profile]
        emp_lo, emp_hi = config["employee_range"]

        category = MSMECategory.MICRO
        if emp_hi > 50:
            category = random.choice([MSMECategory.SMALL, MSMECategory.MEDIUM])
        elif emp_hi > 20:
            category = random.choice([MSMECategory.MICRO, MSMECategory.SMALL])

        reg_years_ago = random.uniform(1, 12) if profile != BusinessProfile.NEW_BUSINESS else random.uniform(0.3, 1.5)
        reg_date = datetime.now() - timedelta(days=int(reg_years_ago * 365))

        business_id = f"MSME_{idx + 1:03d}"

        entity = MSMEEntity(
            business_id=business_id,
            name=name,
            industry=industry,
            category=category,
            city=city,
            state=state,
            gstin=_generate_gstin(state),
            udyam_number=_generate_udyam(),
            registration_date=reg_date.strftime("%Y-%m-%d"),
            pan=_generate_pan(),
            contact_email=f"info@{name.lower().replace(' ', '').replace('&', '')[:15]}.in",
            description=f"A {category.value.lower()} enterprise in {industry.value} based in {city}.",
            profile_type=profile,
        )

        # Cache for later retrieval
        if not hasattr(self, '_entity_cache'):
            self._entity_cache: Dict[int, MSMEEntity] = {}
        self._entity_cache[idx] = entity

        return entity

    def _generate_entity_by_id(self, idx: int, profile: BusinessProfile) -> MSMEEntity:
        """Retrieve cached entity."""
        return self._entity_cache.get(idx)

    def _generate_data_package(self, entity: MSMEEntity,
                                config: dict, profile: BusinessProfile) -> MSMEDataPackage:
        """Generate complete data package for one MSME."""
        gst = self._generate_gst(entity, config, profile)
        bank = self._generate_bank_statements(entity, config, profile, gst)
        epfo = self._generate_epfo(entity, config, profile)
        upi = self._generate_upi_transactions(entity, config, profile, gst)
        itr = self._generate_itr(entity, config, profile, gst)
        alt = self._generate_alternate_signals(entity, profile)

        return MSMEDataPackage(
            entity=entity,
            gst_records=gst,
            bank_statements=bank,
            epfo_records=epfo,
            upi_transactions=upi,
            itr_records=itr,
            alternate_signals=alt,
        )

    def _generate_gst(self, entity: MSMEEntity, config: dict,
                       profile: BusinessProfile) -> List[GSTRecord]:
        """Generate monthly GST records with realistic revenue patterns."""
        records = []
        base_rev_lo, base_rev_hi = config["base_revenue_range"]
        base_revenue = self.rng.uniform(base_rev_lo, base_rev_hi)
        growth_lo, growth_hi = config["growth_rate"]
        monthly_growth = self.rng.uniform(growth_lo, growth_hi)
        volatility = config["volatility"]
        compliance_rate = config["compliance_rate"]

        for m in range(self.months):
            dt = self.start_date + timedelta(days=30 * m)
            month_str = dt.strftime("%Y-%m")
            month_num = dt.month

            # Revenue with growth + seasonality + noise
            growth_factor = (1 + monthly_growth) ** m
            seasonal = _seasonal_factor(month_num, entity.industry)
            noise = self.rng.normal(1.0, volatility)
            noise = max(0.3, noise)

            turnover = base_revenue * growth_factor * seasonal * noise
            turnover = max(10000, turnover)

            # GST calculations
            gst_rate = random.choice([0.05, 0.12, 0.18])
            output_liability = turnover * gst_rate
            input_credit = output_liability * self.rng.uniform(0.4, 0.75)
            tax_paid = max(0, output_liability - input_credit)

            # Filing compliance
            roll = self.rng.random()
            if roll < compliance_rate:
                filing_status = FilingStatus.ON_TIME
                delay = 0
            elif roll < compliance_rate + (1 - compliance_rate) * 0.6:
                filing_status = FilingStatus.LATE
                delay = int(self.rng.uniform(1, 30))
            else:
                filing_status = FilingStatus.MISSED
                delay = int(self.rng.uniform(30, 90))

            b2b = int(turnover / self.rng.uniform(20000, 80000))
            b2c = int(turnover / self.rng.uniform(500, 5000))

            records.append(GSTRecord(
                month=month_str,
                taxable_turnover=round(turnover, 2),
                tax_paid=round(tax_paid, 2),
                filing_status=filing_status,
                filing_delay_days=delay,
                input_credit=round(input_credit, 2),
                output_liability=round(output_liability, 2),
                b2b_invoices=max(1, b2b),
                b2c_invoices=max(0, b2c),
            ))

        return records

    def _generate_bank_statements(self, entity: MSMEEntity, config: dict,
                                   profile: BusinessProfile,
                                   gst_records: List[GSTRecord]) -> List[BankStatement]:
        """Generate bank statements correlated with GST revenue."""
        records = []
        cash_ratio = config["cash_ratio"]
        bounce_prob = config["bounce_prob"]
        balance = self.rng.uniform(100000, 500000)

        for m, gst in enumerate(gst_records):
            dt = self.start_date + timedelta(days=30 * m)
            month_str = dt.strftime("%Y-%m")

            # Credits correlate with GST turnover (with some UPI/cash additions)
            total_credits = gst.taxable_turnover * self.rng.uniform(0.9, 1.2)
            total_debits = total_credits / cash_ratio * self.rng.uniform(0.85, 1.15)

            opening = balance
            closing = opening + total_credits - total_debits
            closing = max(5000, closing)

            credit_count = int(total_credits / self.rng.uniform(10000, 50000))
            debit_count = int(total_debits / self.rng.uniform(8000, 40000))

            avg_daily = (opening + closing) / 2 * self.rng.uniform(0.8, 1.2)
            min_bal = min(opening, closing) * self.rng.uniform(0.3, 0.7)
            max_bal = max(opening, closing) * self.rng.uniform(1.1, 1.5)

            emi = total_debits * self.rng.uniform(0.05, 0.20) if profile != BusinessProfile.NEW_BUSINESS else 0
            bounces = 1 if self.rng.random() < bounce_prob else 0
            cc_util = self.rng.uniform(0.2, 0.9) if profile in [
                BusinessProfile.STRUGGLING, BusinessProfile.DECLINING
            ] else self.rng.uniform(0.0, 0.5)

            records.append(BankStatement(
                month=month_str,
                opening_balance=round(opening, 2),
                closing_balance=round(closing, 2),
                total_credits=round(total_credits, 2),
                total_debits=round(total_debits, 2),
                credit_count=max(1, credit_count),
                debit_count=max(1, debit_count),
                avg_daily_balance=round(max(1000, avg_daily), 2),
                min_balance=round(max(0, min_bal), 2),
                max_balance=round(max_bal, 2),
                cash_credit_utilization=round(cc_util, 2),
                emi_outflows=round(emi, 2),
                bounce_count=bounces,
            ))

            balance = closing

        return records

    def _generate_epfo(self, entity: MSMEEntity, config: dict,
                        profile: BusinessProfile) -> List[EPFORecord]:
        """Generate EPFO records showing workforce dynamics."""
        records = []
        emp_lo, emp_hi = config["employee_range"]
        base_employees = int(self.rng.uniform(emp_lo, emp_hi))
        emp_growth = config["employee_growth"]

        for m in range(self.months):
            dt = self.start_date + timedelta(days=30 * m)
            month_str = dt.strftime("%Y-%m")

            # Employee count with growth + noise
            emp_count = int(base_employees * (1 + emp_growth) ** m)
            emp_count += int(self.rng.normal(0, max(1, emp_count * 0.05)))
            emp_count = max(1, emp_count)

            # Joins and exits
            new_joins = max(0, int(self.rng.poisson(max(0.5, emp_count * abs(emp_growth) * 1.5))))
            exit_rate = 0.02 if profile in [BusinessProfile.THRIVING, BusinessProfile.STABLE] else 0.05
            exits = max(0, int(self.rng.poisson(emp_count * exit_rate)))

            avg_salary = self.rng.uniform(15000, 45000)
            employer_contrib = emp_count * avg_salary * 0.12
            employee_contrib = emp_count * avg_salary * 0.12
            total = employer_contrib + employee_contrib

            compliance = "compliant"
            if profile == BusinessProfile.STRUGGLING and self.rng.random() < 0.2:
                compliance = "delayed"
            elif profile == BusinessProfile.DECLINING and self.rng.random() < 0.3:
                compliance = random.choice(["delayed", "defaulted"])

            records.append(EPFORecord(
                month=month_str,
                active_employees=emp_count,
                new_joins=new_joins,
                exits=exits,
                total_contribution=round(total, 2),
                employer_contribution=round(employer_contrib, 2),
                employee_contribution=round(employee_contrib, 2),
                compliance_status=compliance,
            ))

        return records

    def _generate_upi_transactions(self, entity: MSMEEntity, config: dict,
                                     profile: BusinessProfile,
                                     gst_records: List[GSTRecord]) -> List[UPITransaction]:
        """Generate UPI transactions creating network edges."""
        transactions = []

        # Create a set of counterparties for this MSME
        num_customers = self.rng.randint(3, 12)
        num_suppliers = self.rng.randint(2, 8)

        # Some counterparties are OTHER MSMEs in our ecosystem (creates network!)
        other_msmes = [mid for mid in self.msme_ids if mid != entity.business_id]
        msme_counterparties = random.sample(other_msmes, min(len(other_msmes), self.rng.randint(2, 6))) if other_msmes else []

        # External counterparties
        ext_counterparties = random.sample(COUNTERPARTY_NAMES, min(len(COUNTERPARTY_NAMES), num_customers + num_suppliers))

        all_customers = msme_counterparties[:len(msme_counterparties)//2] + ext_counterparties[:num_customers]
        all_suppliers = msme_counterparties[len(msme_counterparties)//2:] + ext_counterparties[num_customers:]

        # Assign concentration (some counterparties are bigger than others)
        customer_weights = self.rng.dirichlet(np.ones(len(all_customers)) * 0.5)
        supplier_weights = self.rng.dirichlet(np.ones(len(all_suppliers)) * 0.5) if all_suppliers else []

        for m, gst in enumerate(gst_records):
            dt_base = self.start_date + timedelta(days=30 * m)
            monthly_inflow = gst.taxable_turnover
            monthly_outflow = monthly_inflow * self.rng.uniform(0.55, 0.85)

            # Inflow transactions (from customers)
            num_txns_in = self.rng.randint(5, 30)
            for t in range(num_txns_in):
                cust_idx = self.rng.choice(len(all_customers), p=customer_weights)
                cust_id = all_customers[cust_idx]
                cust_name = self.msme_names.get(cust_id, cust_id)
                amount = monthly_inflow * customer_weights[cust_idx] * self.rng.uniform(0.5, 1.5) / max(1, num_txns_in // len(all_customers))
                day = self.rng.randint(1, 28)
                txn_date = dt_base.replace(day=day)

                transactions.append(UPITransaction(
                    transaction_id=f"UPI{uuid.uuid4().hex[:12].upper()}",
                    date=txn_date.strftime("%Y-%m-%d"),
                    amount=round(max(100, amount), 2),
                    direction="inflow",
                    counterparty_id=cust_id,
                    counterparty_name=cust_name,
                    category=random.choice(["sales", "sales", "sales", "other"]),
                ))

            # Outflow transactions (to suppliers)
            if len(all_suppliers) > 0:
                num_txns_out = self.rng.randint(3, 20)
                for t in range(num_txns_out):
                    sup_idx = self.rng.choice(len(all_suppliers), p=supplier_weights)
                    sup_id = all_suppliers[sup_idx]
                    sup_name = self.msme_names.get(sup_id, sup_id)
                    amount = monthly_outflow * supplier_weights[sup_idx] * self.rng.uniform(0.5, 1.5) / max(1, num_txns_out // len(all_suppliers))
                    day = self.rng.randint(1, 28)
                    txn_date = dt_base.replace(day=day)
                    cat = random.choice(["supplier_payment", "raw_materials", "logistics",
                                         "utilities", "rent", "salary", "equipment", "maintenance"])

                    transactions.append(UPITransaction(
                        transaction_id=f"UPI{uuid.uuid4().hex[:12].upper()}",
                        date=txn_date.strftime("%Y-%m-%d"),
                        amount=round(max(100, amount), 2),
                        direction="outflow",
                        counterparty_id=sup_id,
                        counterparty_name=sup_name,
                        category=cat,
                    ))

        return transactions

    def _generate_itr(self, entity: MSMEEntity, config: dict,
                       profile: BusinessProfile,
                       gst_records: List[GSTRecord]) -> List[ITRRecord]:
        """Generate annual ITR records aligned with GST data."""
        records = []
        years = set()
        for gst in gst_records:
            year = int(gst.month[:4])
            years.add(year)

        for year in sorted(years):
            # Annual revenue from GST
            annual_rev = sum(g.taxable_turnover for g in gst_records if g.month.startswith(str(year)))
            if annual_rev == 0:
                continue

            declared_ratio = self.rng.uniform(0.85, 1.0) if profile != BusinessProfile.STRUGGLING else self.rng.uniform(0.6, 0.85)
            income_from_biz = annual_rev * self.rng.uniform(0.08, 0.25)
            declared_income = income_from_biz * declared_ratio
            depreciation = annual_rev * self.rng.uniform(0.02, 0.08)
            tax_paid = max(0, declared_income * self.rng.uniform(0.15, 0.30))

            filing_month = self.rng.randint(7, 12) if profile != BusinessProfile.DECLINING else self.rng.randint(10, 15)
            filing_month = min(filing_month, 12)

            records.append(ITRRecord(
                assessment_year=f"{year + 1}-{str(year + 2)[-2:]}",
                declared_income=round(declared_income, 2),
                income_from_business=round(income_from_biz, 2),
                depreciation=round(depreciation, 2),
                tax_paid=round(tax_paid, 2),
                filing_date=f"{year + 1}-{filing_month:02d}-{self.rng.randint(1, 28):02d}",
                audit_required=annual_rev > 10000000,
                turnover_declared=round(annual_rev * declared_ratio, 2),
            ))

        return records

    def _generate_alternate_signals(self, entity: MSMEEntity,
                                     profile: BusinessProfile) -> List[AlternateSignal]:
        """Generate alternate data signals (Google reviews, utility payments, etc.)."""
        signals = []

        # Google Reviews signal
        if profile in [BusinessProfile.THRIVING, BusinessProfile.GROWING]:
            rating = round(self.rng.uniform(3.8, 4.8), 1)
            sentiment = "positive"
        elif profile in [BusinessProfile.STABLE, BusinessProfile.SEASONAL]:
            rating = round(self.rng.uniform(3.2, 4.2), 1)
            sentiment = "neutral"
        else:
            rating = round(self.rng.uniform(2.0, 3.5), 1)
            sentiment = "negative"

        signals.append(AlternateSignal(
            source="google_reviews",
            date=datetime.now().strftime("%Y-%m-%d"),
            signal_type=sentiment,
            value=rating,
            description=f"Average Google rating: {rating}/5 based on {self.rng.randint(10, 500)} reviews",
        ))

        # Utility payment consistency
        utility_score = self.rng.uniform(0.7, 1.0) if profile in [
            BusinessProfile.THRIVING, BusinessProfile.STABLE, BusinessProfile.GROWING
        ] else self.rng.uniform(0.3, 0.7)

        signals.append(AlternateSignal(
            source="utility_payments",
            date=datetime.now().strftime("%Y-%m-%d"),
            signal_type="positive" if utility_score > 0.7 else "negative",
            value=round(utility_score * 100, 1),
            description=f"Utility payment consistency score: {round(utility_score * 100, 1)}%",
        ))

        # Trade references
        trade_score = self.rng.uniform(0.6, 1.0) if profile != BusinessProfile.DECLINING else self.rng.uniform(0.2, 0.5)
        signals.append(AlternateSignal(
            source="trade_references",
            date=datetime.now().strftime("%Y-%m-%d"),
            signal_type="positive" if trade_score > 0.6 else "negative",
            value=round(trade_score * 100, 1),
            description=f"Trade reference score: {round(trade_score * 100, 1)}% positive from {self.rng.randint(3, 15)} references",
        ))

        return signals


# ─── Convenience Function ───────────────────────────────────────────────────

def generate_ecosystem(num_msmes: int = 55, months: int = 24, seed: int = 42) -> List[MSMEDataPackage]:
    """Generate a complete MSME ecosystem. Entry point for the application."""
    generator = SyntheticDataGenerator(num_msmes=num_msmes, months=months, seed=seed)
    return generator.generate_all()
