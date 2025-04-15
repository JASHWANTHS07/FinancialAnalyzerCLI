import logging
import math # For floating point comparisons (math.isclose)
from typing import Dict, Any, Optional, Union # To handle both Dict and Series input
import pandas as pd # To check for pd.NA/NaN and handle Series

logger = logging.getLogger(__name__)

def verify_financial_consistency(period_data: Optional[Union[pd.Series, Dict[str, Any]]]) -> Dict[str, Union[bool, str]]:
    """
    Performs internal consistency checks on standardized financial data for ONE specific period.

    Checks fundamental accounting equations and relationships using the provided data.

    Args:
        period_data: A pandas Series or a dictionary containing standardized financial items
                     (keys) and their corresponding float values for a single time period.
                     Can be None or empty.

    Returns:
        A dictionary where keys are the names of the consistency checks performed
        (e.g., 'BalanceSheetEq', 'CashCheck') and values indicate the result:
          - True: The check passed within tolerance.
          - str: The check failed or was skipped, with a reason provided in the string.
                 (e.g., "Failed (Mismatch: ...)", "Skipped: Missing components (...)").
    """
    results: Dict[str, Union[bool, str]] = {}

    # --- Input Validation ---
    if period_data is None:
        logger.warning("Verifier received None for period_data.")
        results['InputValidation'] = "Failed: No data received for period."
        return results
    # Check for empty structures after ensuring it's not None
    if isinstance(period_data, dict) and not period_data:
         logger.warning("Verifier received empty dictionary for period_data.")
         results['InputValidation'] = "Failed: Empty data dictionary received."
         return results
    if isinstance(period_data, pd.Series) and period_data.empty:
         logger.warning("Verifier received empty Series for period_data.")
         results['InputValidation'] = "Failed: Empty data Series received."
         return results
    # -----------------------

    # --- Helper Function to Safely Get and Convert to Float ---
    def _get_float(key: str) -> Optional[float]:
        """
        Safely retrieves a value by key from period_data, handles missing keys,
        checks for NaN/NA, attempts conversion to float, and returns None on any failure.
        """
        try:
            # .get works for both dict and Series, returning None if key is absent
            val = period_data.get(key)

            # Check for None or pandas/numpy NA/NaN values
            if val is None or pd.isna(val):
                 return None

            # Attempt conversion to float
            return float(val)
        except (TypeError, ValueError):
            # Log if conversion fails for an existing non-NA value
            # logger.warning(f"Verifier: Could not convert value for key '{key}' to float. Value: {period_data.get(key)}")
            return None
        except Exception as e:
            # Catch any other unexpected errors during retrieval/conversion
            logger.error(f"Verifier: Unexpected error getting key '{key}': {e}")
            return None
    # ---------------------------------------------------------

    # --- 1. Balance Sheet Equation (Assets = Liabilities + Equity) ---
    assets = _get_float('total_assets')
    liabs = _get_float('total_liabilities')
    equity = _get_float('total_equity')

    # Check if all necessary components were successfully retrieved as floats
    required_keys_bs = {'Total Assets': assets, 'Total Liabilities': liabs, 'Total Equity': equity}
    missing_keys_bs = [k for k, v in required_keys_bs.items() if v is None]

    if not missing_keys_bs:
        # Perform the check using math.isclose for robust float comparison
        # rel_tol allows for small percentage differences often found in real data
        if math.isclose(assets, liabs + equity, rel_tol=0.015): # Allow 1.5% tolerance
            results['BalanceSheetEq'] = True
        else:
            # Provide context if the check fails
            calculated_le = liabs + equity
            diff = assets - calculated_le
            mismatch_str = f"Mismatch: A={assets:,.2f}, L+E={calculated_le:,.2f}, Diff={diff:,.2f}"
            results['BalanceSheetEq'] = f"Failed ({mismatch_str})"
    else:
        # Report missing components if the check couldn't be performed
        results['BalanceSheetEq'] = f"Skipped: Missing components ({', '.join(missing_keys_bs)})"

    # --- 2. Cash Check (Cash >= 0) ---
    cash = _get_float('cash')
    if cash is not None:
        if cash >= -1e-6: # Allow for very small negative numbers due to float precision
            results['CashCheck'] = True
        else:
            results['CashCheck'] = f"Failed (Negative cash: {cash:,.2f})"
    else:
         results['CashCheck'] = "Skipped: Missing 'Cash'" # Use standard key 'cash'

    # --- 3. Gross Profit Check (Gross Profit = Revenue - Cost of Revenue) ---
    revenue = _get_float('revenue')
    cogs = _get_float('cost_of_revenue')
    gp = _get_float('gross_profit')

    required_keys_gp = {'Revenue': revenue, 'Cost of Revenue': cogs, 'Gross Profit': gp}
    missing_keys_gp = [k for k, v in required_keys_gp.items() if v is None]

    if not missing_keys_gp:
        calculated_gp = revenue - cogs
        if math.isclose(gp, calculated_gp, rel_tol=0.01): # Allow 1% tolerance
            results['GrossProfitCheck'] = True
        else:
             diff = gp - calculated_gp
             mismatch_gp = f"Mismatch: GP={gp:,.2f}, Rev-CoGS={calculated_gp:,.2f}, Diff={diff:,.2f}"
             results['GrossProfitCheck'] = f"Failed ({mismatch_gp})"
    else:
        results['GrossProfitCheck'] = f"Skipped: Missing components ({', '.join(missing_keys_gp)})"

    # --- 4. Operating Income Check (Operating Income ≈ Gross Profit - Operating Expenses) ---
    # This is often an approximation as 'Operating Expenses' might not include *all* relevant items
    # depending on the source data mapping.
    op_inc = _get_float('operating_income')
    # Gross Profit (gp) already retrieved above

    # Try to get total operating expenses first
    op_ex_total = _get_float('operating_expenses')

    # If total OpEx isn't available, try summing components (R&D + SG&A)
    if op_ex_total is None:
        rd = _get_float('research_development')
        sga = _get_float('selling_general_administrative')
        # Sum only if at least one component exists, treating missing ones as zero
        if rd is not None or sga is not None:
             op_ex_total = (rd or 0.0) + (sga or 0.0)

    required_keys_oi = {'Gross Profit': gp, 'Operating Income': op_inc, 'Operating Expenses': op_ex_total}
    missing_keys_oi = [k for k, v in required_keys_oi.items() if v is None]

    if not missing_keys_oi:
         calculated_oi = gp - op_ex_total
         # Use a larger tolerance due to potential variations in OpEx definitions
         if math.isclose(op_inc, calculated_oi, rel_tol=0.05): # Allow 5% tolerance
            results['OperatingIncomeCheck'] = True
         else:
             diff = op_inc - calculated_oi
             mismatch_oi = f"Mismatch: OpInc={op_inc:,.2f}, GP-OpEx={calculated_oi:,.2f}, Diff={diff:,.2f}"
             results['OperatingIncomeCheck'] = f"Failed ({mismatch_oi})"
    else:
        # Specify which component was missing (GP, OpInc, or usable OpEx)
        missing_oi_detail = [k for k, v in {'Gross Profit': gp, 'Operating Income': op_inc}.items() if v is None]
        if op_ex_total is None:
            missing_oi_detail.append("Operating Expenses (Total or Components)")
        results['OperatingIncomeCheck'] = f"Skipped: Missing components ({', '.join(missing_oi_detail)})"

    # --- 5. Net Income Check (Net Income ≈ Income Before Tax - Income Tax Expense) ---
    ni = _get_float('net_income')
    ibt = _get_float('income_before_tax')
    tax = _get_float('income_tax_expense')

    required_keys_ni = {'Net Income': ni, 'Income Before Tax': ibt, 'Income Tax Expense': tax}
    missing_keys_ni = [k for k, v in required_keys_ni.items() if v is None]

    if not missing_keys_ni:
        calculated_ni = ibt - tax
        if math.isclose(ni, calculated_ni, rel_tol=0.015): # Allow 1.5% tolerance
            results['NetIncomeCheck'] = True
        else:
             diff = ni - calculated_ni
             mismatch_ni = f"Mismatch: NetInc={ni:,.2f}, IBT-Tax={calculated_ni:,.2f}, Diff={diff:,.2f}"
             results['NetIncomeCheck'] = f"Failed ({mismatch_ni})"
    else:
        results['NetIncomeCheck'] = f"Skipped: Missing components ({', '.join(missing_keys_ni)})"

    # --- 6. Cash Flow Sum Check (Change in Cash ≈ Op CF + Inv CF + Fin CF) ---
    change_cash = _get_float('change_in_cash')
    op_cf = _get_float('operating_cash_flow')
    inv_cf = _get_float('investing_cash_flow')
    fin_cf = _get_float('financing_cash_flow')

    required_keys_cf = {'Change in Cash': change_cash, 'Operating CF': op_cf,
                       'Investing CF': inv_cf, 'Financing CF': fin_cf}
    missing_keys_cf = [k for k, v in required_keys_cf.items() if v is None]

    if not missing_keys_cf:
        sum_cf = op_cf + inv_cf + fin_cf
        # Cash flow statements can sometimes have small discrepancies due to rounding or minor items
        if math.isclose(change_cash, sum_cf, rel_tol=0.02, abs_tol=1000): # Allow 2% relative or 1000 absolute tolerance
            results['CashFlowSumCheck'] = True
        else:
             diff = change_cash - sum_cf
             mismatch_cf = f"Mismatch: ChangeCash={change_cash:,.2f}, SumCF={sum_cf:,.2f}, Diff={diff:,.2f}"
             results['CashFlowSumCheck'] = f"Failed ({mismatch_cf})"
    else:
        results['CashFlowSumCheck'] = f"Skipped: Missing components ({', '.join(missing_keys_cf)})"


    logger.info(f"Verification results for period: {results}")

    return results