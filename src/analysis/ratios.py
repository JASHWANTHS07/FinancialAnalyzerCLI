import logging
import pandas as pd
from typing import Dict, Optional, Any, Union

logger = logging.getLogger(__name__)

def _safe_division(numerator: Optional[float], denominator: Optional[float]) -> Optional[float]:
    """
    Helper function for safe division.

    Handles None inputs and division by zero, returning None in these cases.
    Ensures inputs are treated as floats before division.

    Args:
        numerator: The numerator value (or None).
        denominator: The denominator value (or None).

    Returns:
        The result of the division as a float, or None if division cannot be performed safely.
    """
    if numerator is None or denominator is None:
        return None
    try:
        num_f = float(numerator)
        den_f = float(denominator)

        if den_f == 0:
            return None
        return num_f / den_f
    except (ValueError, TypeError):
        logger.debug(f"Could not convert numerator ({numerator}) or denominator ({denominator}) to float for division.")
        return None

def calculate_single_period_ratios(period_data: Union[pd.Series, Dict[str, float]]) -> Dict[str, Optional[float]]:
    """
    Calculates key financial ratios for a SINGLE period's standardized data.

    This function assumes the input contains financial items that have already been
    standardized (e.g., using the mapper).

    Args:
        period_data: A pandas Series or dictionary containing standardized financial items
                     as floats for one specific period. Index/keys are standard item names
                     (e.g., 'revenue', 'net_income', 'total_assets').

    Returns:
        A dictionary where keys are ratio names (e.g., 'Net Margin', 'Current Ratio')
        and values are the calculated ratios (float) or None if the ratio could not
        be calculated due to missing data or division by zero.
    """
    ratios: Dict[str, Optional[float]] = {}

    def _get(key: str) -> Optional[float]:
        """Safely retrieves and converts a value to float, returning None on failure or NaN."""
        try:
            val = period_data.get(key)
            if pd.isna(val):
                return None
            return float(val)
        except (TypeError, ValueError):
            logger.warning(f"Could not convert value for key '{key}' to float. Value: {period_data.get(key)}")
            return None
        except KeyError:
            return None


    # Profitability
    gp = _get('gross_profit')
    rev = _get('revenue')
    ni = _get('net_income')
    oi = _get('operating_income')

    # Liquidity
    ca = _get('current_assets')
    cl = _get('current_liabilities')
    cash = _get('cash') # Although not used in current ratios, often useful
    inv = _get('inventory')

    # Leverage
    std = _get('short_term_debt')
    ltd = _get('long_term_debt')
    equity = _get('total_equity')
    liab = _get('total_liabilities')
    assets = _get('total_assets')

    # Activity / Efficiency related
    cogs = _get('cost_of_revenue')
    ar = _get('accounts_receivable')

    # Profitability Ratios
    ratios['Gross Margin'] = _safe_division(gp, rev)
    ratios['Net Margin'] = _safe_division(ni, rev)
    ratios['Operating Margin'] = _safe_division(oi, rev)

    # Liquidity Ratios
    ratios['Current Ratio'] = _safe_division(ca, cl)
    # Quick Ratio = (Current Assets - Inventory) / Current Liabilities
    # Calculate numerator first, handling potential Nones
    quick_assets_numerator = None
    if ca is not None and inv is not None:
        quick_assets_numerator = ca - inv
    elif ca is not None and inv is None: # If inventory is missing, assume quick assets = current assets? Or None? Let's assume None.
        quick_assets_numerator = None # Or maybe ca, depending on convention needed? Defaulting to safer None.
    ratios['Quick Ratio'] = _safe_division(quick_assets_numerator, cl)

    # Leverage Ratios
    # Calculate Total Debt safely
    total_debt: Optional[float] = None
    if std is not None or ltd is not None:
         total_debt = (std or 0.0) + (ltd or 0.0) # Treat missing component as 0 if the other exists

    ratios['Debt to Equity'] = _safe_division(total_debt, equity)
    ratios['Liabilities to Equity'] = _safe_division(liab, equity)
    ratios['Debt Ratio'] = _safe_division(total_debt, assets) # Total Debt / Total Assets

    # Return Ratios
    # Note: These use end-of-period balances as approximations for average balances.
    # More accurate calculations would require data from the prior period for averaging.
    ratios['Return on Equity (ROE)'] = _safe_division(ni, equity)
    ratios['Return on Assets (ROA)'] = _safe_division(ni, assets)

    # Return on Capital Employed (ROCE) = Operating Income / (Total Assets - Current Liabilities)
    capital_employed_denominator = None
    if assets is not None and cl is not None:
        capital_employed_denominator = assets - cl
    ratios['Return on Capital Employed (ROCE)'] = _safe_division(oi, capital_employed_denominator)

    # Activity / Efficiency Ratios
    # Note: Using end-of-period values as approximation for average inventory/assets/receivables.
    ratios['Inventory Turnover'] = _safe_division(cogs, inv)
    ratios['Asset Turnover'] = _safe_division(rev, assets)
    ratios['Receivable Turnover'] = _safe_division(rev, ar)


    # --- Final Cleanup (Optional but recommended) ---

    cleaned_ratios = {k: (v if pd.notna(v) and isinstance(v, (int, float)) else None) for k, v in ratios.items()}

    # Log calculated ratios for this period (optional)
    logger.debug(f"Calculated ratios for period: {cleaned_ratios}")

    return cleaned_ratios


def calculate_historical_ratios(standardized_data: Optional[pd.DataFrame]) -> Optional[pd.DataFrame]:
    """
    Calculates ratios for each period available in the standardized data DataFrame.

    Args:
        standardized_data: DataFrame where index represents standardized financial items
                           (e.g., 'revenue', 'net_income') and columns represent distinct
                           time periods (datetime objects), typically sorted latest first.
                           This is usually the output from `mapper.standardize_statements`.

    Returns:
        A pandas DataFrame where the index contains the names of the calculated ratios
        (e.g., 'Net Margin', 'Current Ratio') and the columns are the time periods
        (datetime objects, sorted consistently with the input DataFrame). Returns None
        if the input is invalid or if no ratios could be calculated for any period.
    """
    if standardized_data is None or not isinstance(standardized_data, pd.DataFrame) or standardized_data.empty:
        logger.warning("Cannot calculate historical ratios: Input standardized_data is None, not a DataFrame, or empty.")
        return None

    all_ratios_by_period = {} # Dictionary to hold {period_column: {ratio_name: value}}

    for period_col in standardized_data.columns:
        period_series = standardized_data[period_col]

        period_ratios = calculate_single_period_ratios(period_series)

        if period_ratios:
             all_ratios_by_period[period_col] = period_ratios

    if not all_ratios_by_period:
        logger.warning("No ratios could be calculated for any period in the provided data.")
        return None

    try:
        ratio_df = pd.DataFrame.from_dict(all_ratios_by_period, orient='columns')

        ratio_df = ratio_df.reindex(columns=standardized_data.columns)

        logger.info(f"Successfully calculated historical ratios for {len(ratio_df.columns)} periods.")
        return ratio_df
    except Exception as e:
         # Catch potential errors during DataFrame creation or reindexing
         logger.error(f"Failed to create final historical ratio DataFrame: {e}", exc_info=True)
         return None

# --- Sector / Comparative Ratio Analysis ---
# This function remains unchanged as it's designed to work on a dictionary
# where keys are tickers and values are dictionaries of *latest* ratios.
# The logic in main.py is responsible for preparing this input dictionary.

def calculate_sector_ratios(all_company_latest_ratios: Dict[str, Dict[str, Optional[float]]]) -> Dict[str, Optional[float]]:
    """
    Calculates aggregated statistics (Avg, Median, Min, Max) for each ratio across a sector,
    based on the latest period data provided for each company.

    Args:
        all_company_latest_ratios: A nested dictionary where outer keys are tickers and inner
                                   keys are ratio names, mapping to the calculated ratio value
                                   (float or None) for the latest analyzed period for that company.
                                   Example: {'AAPL': {'Gross Margin': 0.4, ...}, 'MSFT': {...}}

    Returns:
        A dictionary where keys indicate the ratio and aggregation type (e.g., 'Gross Margin_Avg',
        'Net Margin_Median') and values are the aggregated results (float or None). Returns an empty
        dictionary if the input is empty or if aggregation fails.
    """
    if not all_company_latest_ratios:
        logger.warning("Cannot calculate sector ratios: Input 'all_company_latest_ratios' is empty.")
        return {}

    try:
        # Combine all latest ratios into a DataFrame for easy aggregation
        # Rows = Tickers, Columns = Ratios
        df = pd.DataFrame.from_dict(all_company_latest_ratios, orient='index')

        if df.empty:
            logger.warning("Cannot calculate sector ratios: DataFrame created from input is empty.")
            return {}

        # Calculate statistics, ignoring NaNs present in individual company ratios
        sector_stats: Dict[str, Optional[float]] = {} # Ensure type hint consistency
        for ratio_name in df.columns:
            # Select the column (Series) for the current ratio
            ratio_column = df[ratio_name]

            # Ensure the column contains numeric data before calculating stats
            # Coerce errors to NaN, then check if *any* valid number exists
            numeric_column = pd.to_numeric(ratio_column, errors='coerce')

            if not numeric_column.empty and not numeric_column.isna().all(): # Check if there's any valid data
                 # skipna=True is the default for pandas aggregations but good to be explicit
                 sector_stats[f"{ratio_name}_Avg"] = numeric_column.mean(skipna=True)
                 sector_stats[f"{ratio_name}_Median"] = numeric_column.median(skipna=True)
                 sector_stats[f"{ratio_name}_Min"] = numeric_column.min(skipna=True)
                 sector_stats[f"{ratio_name}_Max"] = numeric_column.max(skipna=True)
            else:
                 # If column is all NaN or non-numeric after coercion, set stats to None
                 logger.debug(f"Skipping stats for ratio '{ratio_name}' as no valid numeric data was found.")
                 sector_stats[f"{ratio_name}_Avg"] = None
                 sector_stats[f"{ratio_name}_Median"] = None
                 sector_stats[f"{ratio_name}_Min"] = None
                 sector_stats[f"{ratio_name}_Max"] = None


        # Filter out any potential NaN/inf values from the aggregation results themselves
        # (This is a safeguard; mean/median/min/max should handle NaNs correctly with skipna=True)
        cleaned_stats = {k: (v if pd.notna(v) and isinstance(v, (int, float)) else None) for k, v in sector_stats.items()}

        logger.info(f"Calculated sector statistics for {len(df.columns)} base ratios across {len(df.index)} companies.")
        return cleaned_stats

    except Exception as e:
        logger.error(f"Error calculating sector ratios: {e}", exc_info=True)
        # Return empty dict on unexpected error during processing
        return {}