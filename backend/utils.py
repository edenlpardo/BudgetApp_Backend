# utils.py by Eden Pardo
from constants import VALID_PERIODS
from pyf_budget_routes import pyf_allocation_calculation, pyf_purchase_calculation
from ftt_budget_routes import ftt_allocation_calculation, ftt_purchase_calculation

# Helper function to convert amounts to weekly equivalent
def normalize_to_weekly(amount, frequency, periods):
    frequency.lower()
    if frequency not in periods:
        raise ValueError(f"Invalid frequency: {frequency}")
    return amount / periods[frequency]

# Helper function to reduce redundant code
def trigger_allocation_recalculation(budget):
    method = budget.method.lower()
    if method == "pay-yourself-first":
        return pyf_allocation_calculation(budget.id)
    elif method == "50-30-20":
        return ftt_allocation_calculation(budget.id)
    return None, 200

# Helper function to reduce redundant code
def trigger_purchase_recalculation(budget):
    method = budget.method.lower()
    if method == "pay-yourself-first":
        return pyf_purchase_calculation(budget.id)
    elif method == "50-30-20":
        return ftt_purchase_calculation(budget.id)
    return None, 200