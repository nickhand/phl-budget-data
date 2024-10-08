"""Load the processed QCMR data."""

from pathlib import Path
from typing import Iterator, Tuple, Type

import numpy as np
import pandas as pd
from pydantic import validate_arguments

from ..utils.misc import fiscal_year_quarter_from_path
from . import cash, obligations, personal_services, positions
from .base import ETLPipelineQCMR
from .cash.core import CASH_DATA_TYPE

__all__ = [
    "load_cash_reports",
    "load_department_obligations",
    "load_fulltime_positions",
    "load_personal_services_summary",
]


def _load_processed_results(
    cls: Type[ETLPipelineQCMR],
) -> Iterator[Tuple[Path, int, int]]:
    """Internal helper function for loading processed results."""

    # Get the files
    dirname = cls.get_data_directory("processed")
    files = sorted(dirname.glob("*.csv"), reverse=True)

    # Loop over each file
    for f in files:

        # Get fiscal year and quarter
        fiscal_year, quarter = fiscal_year_quarter_from_path(f)

        # Yield
        yield f, fiscal_year, quarter


def _load_department_reports(cls: Type[ETLPipelineQCMR]) -> pd.DataFrame:
    """Internal function to load department-based QCMR reports."""

    all_df = []
    fiscal_years = set()
    report_fiscal_years = set()

    for f, fiscal_year, quarter in _load_processed_results(cls):

        # Get fiscal year and quarter
        fiscal_year, quarter = fiscal_year_quarter_from_path(f)

        # Load
        df = pd.read_csv(f, dtype={"dept_code": str})

        # Get historical actuals
        historical_actuals = df.query(
            f"variable == 'Actual' and time_period == 'Full Year'"
        )
        duplicates = historical_actuals.query("fiscal_year in @fiscal_years")

        # Update the fiscal years
        fiscal_years.update(set(historical_actuals["fiscal_year"]))

        # Remove duplicates
        df = df.drop(duplicates.index)

        # Also remove adopted budget duplicates
        adopted_budget = df.query(
            f"variable == 'Adopted Budget' and time_period == 'Full Year'"
        )
        duplicates = adopted_budget.query("fiscal_year in @report_fiscal_years")

        # Update the fiscal years
        report_fiscal_years.update([fiscal_year])

        # Remove duplicates
        df = df.drop(duplicates.index)

        # Add report fiscal year and quarter
        df["report_quarter"] = quarter
        df["report_fiscal_year"] = fiscal_year

        # Save
        all_df.append(df)

    # Combine them!
    out = pd.concat(all_df, ignore_index=True)

    # Make into a date
    out["as_of_date"] = pd.to_datetime(out["as_of_date"])

    # Dept major code
    out["dept_major_code"] = out["dept_code"].str.slice(0, 2)

    return out.sort_values(
        ["report_fiscal_year", "report_quarter"], ascending=False
    ).reset_index(drop=True)


def load_personal_services_summary() -> pd.DataFrame:
    """
    Load data from the QCMR Personal Services Summary.

    Notes
    -----
    See raw PDF files in data/raw/qcmr/personal-services/ folder.
    """
    return _load_department_reports(personal_services.PersonalServices)


def load_fulltime_positions() -> pd.DataFrame:
    """
    Load data from the QCMR Full-Time Position Report.

    Notes
    -----
    See raw PDF files in the "data/raw/qcmr/positions/" folder.
    """
    df = _load_department_reports(positions.FullTimePositions)

    # Remove duplicates of YTD and full year for Q4 data
    actuals = df.query("variable == 'Actual'")
    duplicates = actuals.loc[
        actuals.duplicated(subset=["as_of_date", "fund", "dept_code"])
    ]
    df = df.drop(duplicates.index)

    latest_report_fy = df["report_fiscal_year"].max()

    # Remove duplicates for end-of-year actuals
    # But keep latest no matter what
    sel = (
        (df["as_of_date"].dt.month == 6)
        & (df["time_period"] == "YTD")
        & (df["report_fiscal_year"] != latest_report_fy)
    )
    df = df.loc[~sel]  # Dont keep the YTD values

    return df


def load_department_obligations() -> pd.DataFrame:
    """
    Load data from the QCMR department obligation reports.

    Notes
    -----
    See raw PDF files in the "data/raw/qcmr/obligations/" folder.
    """
    return _load_department_reports(obligations.DepartmentObligations)


@validate_arguments
def load_cash_reports(kind: CASH_DATA_TYPE) -> pd.DataFrame:
    """
    Load data from the QCMR cash reports.

    Parameters
    ----------
    kind : str
        the kind of data to load, one of "fund-balances",
        "net-cash-flow", "revenue", or "spending"


    Notes
    -----
    See raw PDF files in the "data/raw/qcmr/cash/" folder.
    """
    classes = {
        "fund-balances": cash.CashReportFundBalances,
        "net-cash-flow": cash.CashReportNetCashFlow,
        "revenue": cash.CashReportRevenue,
        "spending": cash.CashReportSpending,
    }
    cls = classes[kind]

    # Formatting
    formatting = {
        "spending": {
            "payroll": "Payroll",
            "employee_benefits": "Employee Benefits",
            "pension": "Pension",
            "purchases_of_services": "Contracts / Leases",
            "materials_equipment": "Materials / Equipment",
            "contributions_indemnities": "Contributions / Indemnities",
            "advances_misc_payments": "Advances / Labor Obligations",
            "debt_service_long": "Long-Term Debt Service",
            "debt_service_short": "Short-Term Debt Service",
            "current_year_appropriation": "Current Year Appropriation",
            "total_disbursements": "Total Disbursements",
            "prior_year_encumbrances": "Prior Year Encumbrances",
            "prior_year_vouchers_payable": "Prior Year Vouchers Payable",
            "interfund_charges": "Interfund Charges",
        },
        "revenue": {
            "real_estate_tax": "Real Estate Tax",
            "wage_earnings_net_profits": "Wage, Earnings, Net Profits",
            "total_wage_earnings_net_profits": "Wage, Earnings, Net Profits",
            "realty_transfer_tax": "Realty Transfer Tax",
            "sales_tax": "Sales Tax",
            "business_income_and_receipts_tax": "BIRT",
            "beverage_tax": "Beverage Tax",
            "total_pica_other_governments": "PICA Other Governments",
            "total_other_governments": "Other Governments",
            "total_cash_receipts": "Total Cash Receipts",
            "locally_generated_nontax": "Locally Generated Non-Tax",
            "other_taxes": "Other Taxes",
            "collection_of_prior_year_revenue": "Prior Year Revenue",
            "interfund_transfers": "Interfund Transfers",
            "other_fund_balance_adjustments": "Other Adjustments",
            "total_current_revenue": "Total Current Revenue",
        },
        "fund-balances": {
            "general": "General Fund",
            "community_development": "Community Development",
            "hospital_assessment_fund": "Hospital Assessment Fund",
            "housing_trust_fund": "Housing Trust Fund",
            "budget_stabilization_fund": "Budget Stabilization Fund",
            "other_funds": "Other Funds",
            "total_operating_funds": "Total Operating Funds",
            "capital_improvement": "Capital Improvement",
            "industrial_and_commercial_dev": "Industrial and Commercial Development",
            "total_capital_funds": "Total Capital Funds",
            "grants_revenue": "Grants Fund",
            "total_fund_equity": "Consolidated Cash",
            "vehicle_rental_tax": "Vehicle Rental Tax",
            "transportation_fund": "Transportation Fund",
        },
        "net-cash-flow": {
            "tran": "TRAN",
            "closing_balance": "Closing Balance",
            "excess_of_receipts_over_disbursements": "Receipts - Disbursements",
            "opening_balance": "Opening Balance",
        },
    }

    # Loop over all files
    out = []
    for f, fiscal_year, quarter in _load_processed_results(cls):  # type: ignore

        # Load the CSV data
        df = pd.read_csv(f)

        # Drop month = 13 (total)
        df = df.query("fiscal_month != 13")

        df = df.assign(
            fiscal_year=fiscal_year,
            quarter=quarter,
            month=lambda df: np.where(
                df.fiscal_month < 7, df.fiscal_month + 6, df.fiscal_month - 6
            ),
        )

        categories = df["category"].drop_duplicates()
        missing = ~categories.isin(formatting[kind])
        if missing.sum():
            missing = categories.loc[missing]
            raise ValueError(f"Missing category replacements: {missing.tolist()}")
        df["category"] = df["category"].replace(formatting[kind])

        out.append(df)

    return pd.concat(out, ignore_index=True).sort_values(
        ["fiscal_year", "quarter"], ascending=False, ignore_index=True
    )
