# src/data_extraction/mapper.py
import pandas as pd
import logging
from typing import Dict, List, Any, Optional, Union
# Make sure to import from the correct location based on your structure
from src.utils.constants import FINANCIAL_ITEM_MAPPING

logger = logging.getLogger(__name__)

def standardize_statements(statements: Optional[Dict[str, Optional[pd.DataFrame]]]) -> Optional[pd.DataFrame]:
    """
    Extracts data from all available periods in financial statements, combines them,
    and standardizes the keys into a single DataFrame using FINANCIAL_ITEM_MAPPING.

    Rows of the DataFrame are the standardized financial items, columns are the periods (datetime).

    Args:
        statements: A dictionary where keys are statement types ('income', 'balance', 'cashflow')
                    and values are pandas DataFrames from yfinance (with periods as columns),
                    or None if a statement couldn't be fetched.

    Returns:
        A pandas DataFrame containing standardized financial items (index) across all
        available valid periods (columns, sorted descending), or None if essential data
        is missing or cannot be processed.
    """
    if statements is None or not statements or all(df is None or df.empty for df in statements.values()):
        logger.warning("Mapper received empty or invalid statements dictionary.")
        return None

    all_period_data = {} # {period_col: {standard_key: value}}
    processed_periods = set()
    raw_item_names = set() # Keep track of all raw item names encountered

    # --- Iterate through each statement type ---
    for stmt_type, df in statements.items():
        if df is None or df.empty:
            logger.debug(f"Skipping empty/None statement: {stmt_type}")
            continue

        if not isinstance(df.columns, pd.DatetimeIndex):
            logger.warning(f"Columns for {stmt_type} are not DatetimeIndex. Attempting conversion.")
            try:
                 df.columns = pd.to_datetime(df.columns, errors='coerce')
                 df = df.dropna(axis=1, how='all') # Drop columns that failed conversion
                 if df.empty:
                      logger.warning(f"No valid date columns remain for {stmt_type} after conversion.")
                      continue
            except Exception as e:
                 logger.error(f"Failed to convert columns to datetime for {stmt_type}: {e}. Skipping statement.")
                 continue

        raw_item_names.update(df.index) # Add raw names from this statement

        # --- Iterate through each period (column) in the statement ---
        for period_col in df.columns:
            if not isinstance(period_col, pd.Timestamp): # Skip if somehow not a timestamp after conversion
                logger.debug(f"Skipping non-timestamp column in {stmt_type}: {period_col}")
                continue

            period_str = period_col.strftime('%Y-%m-%d') # Consistent key format
            processed_periods.add(period_col)

            if period_str not in all_period_data:
                all_period_data[period_str] = {} # Initialize dict for this period

            period_series = df[period_col]

            # --- Iterate through each item (row) for the current period ---
            for yf_key, value_raw in period_series.items():
                 # Store the raw value for potential mapping later
                 # We store it keyed by the yf_key first within the period
                 if pd.notna(value_raw): # Only store non-NaN values initially
                    # Use a temporary dict to avoid overwriting if multiple statements have same raw key
                    # (though this shouldn't happen with yf structure)
                    if 'raw' not in all_period_data[period_str]:
                        all_period_data[period_str]['raw'] = {}
                    all_period_data[period_str]['raw'][yf_key] = value_raw


    if not all_period_data:
        logger.warning("No period data could be extracted from statements.")
        return None

    # --- Now, map raw keys to standard keys for each period ---
    standardized_data_by_period = {} # {period_str: {standard_key: float_value}}

    for period_str, period_contents in all_period_data.items():
        raw_data_for_period = period_contents.get('raw', {})
        if not raw_data_for_period:
            continue # Skip if no raw data for this period

        standardized_dict_for_period: Dict[str, float] = {}
        mapped_yfinance_keys_for_period = set()

        for standard_key, potential_yf_keys in FINANCIAL_ITEM_MAPPING.items():
            found_value_raw = None
            used_yfinance_key = None

            for yf_key in potential_yf_keys:
                if yf_key in raw_data_for_period:
                    value_raw = raw_data_for_period[yf_key]
                    # Value should already be non-NA here based on previous check
                    found_value_raw = value_raw
                    used_yfinance_key = yf_key
                    mapped_yfinance_keys_for_period.add(yf_key)
                    break # Use the first valid value found

            if found_value_raw is not None and used_yfinance_key is not None:
                try:
                    float_value = float(found_value_raw)
                    standardized_dict_for_period[standard_key] = float_value
                except (ValueError, TypeError) as e:
                    logger.warning(
                        f"Period {period_str}: Could not convert value for '{standard_key}' "
                        f"(from yf key: '{used_yfinance_key}', value: '{found_value_raw}') to float: {e}. Skipping."
                    )
            # else: Log missing keys if needed (can be very verbose)
                 # logger.debug(f"Period {period_str}: Standard key '{standard_key}' not found or value was NaN.")

        if standardized_dict_for_period:
            standardized_data_by_period[period_str] = standardized_dict_for_period

        # --- Log unmapped keys (optional, potentially verbose) ---
        # unmapped_raw = set(raw_data_for_period.keys()) - mapped_yfinance_keys_for_period
        # if unmapped_raw:
        #     logger.debug(f"Period {period_str}: Unmapped raw keys: {', '.join(sorted(unmapped_raw))}")

    if not standardized_data_by_period:
        logger.error("Standardization resulted in no data across all periods.")
        return None

    try:
        final_df = pd.DataFrame.from_dict(standardized_data_by_period, orient='index')
        final_df.index = pd.to_datetime(final_df.index)
        final_df = final_df.sort_index(ascending=False)
        final_df = final_df.T
        logger.info(f"Successfully standardized {len(final_df.index)} items across {len(final_df.columns)} periods.")
        return final_df
    except Exception as e:
        logger.error(f"Failed to create final DataFrame from standardized data: {e}", exc_info=True)
        return None