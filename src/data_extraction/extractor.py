import yfinance as yf
import pandas as pd
import logging
from typing import Literal

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_financial_statements(
    ticker_symbol: str,
    period: Literal['annual', 'quarterly'] = 'annual'
) -> dict[str, pd.DataFrame | None]:
    """
    Fetches financial statements for a given ticker, for either annual or quarterly periods.

    Args:
        ticker_symbol: The stock ticker symbol.
        period: The type of period to fetch ('annual' or 'quarterly'). Defaults to 'annual'.

    Returns:
        A dictionary containing pandas DataFrames for 'income', 'balance', and 'cashflow' statements,
        or None for a statement if it couldn't be fetched. Returns DataFrames with multiple periods as columns.
    """
    logging.info(f"Fetching {period} financial statements for {ticker_symbol}...")
    statements = {'income': None, 'balance': None, 'cashflow': None}
    try:
        ticker = yf.Ticker(ticker_symbol)

        if period == 'annual':
            statements['income'] = ticker.financials
            statements['balance'] = ticker.balance_sheet
            statements['cashflow'] = ticker.cashflow
        elif period == 'quarterly':
            statements['income'] = ticker.quarterly_financials
            statements['balance'] = ticker.quarterly_balance_sheet
            statements['cashflow'] = ticker.quarterly_cashflow
        else:
            logging.error(f"Invalid period type specified: {period}. Use 'annual' or 'quarterly'.")
            return statements

        fetched_count = 0
        for name, df in statements.items():
            if df is None or df.empty:
                logging.warning(f"Could not retrieve {period} {name} statement for {ticker_symbol}")
                statements[name] = None # Ensure None if empty/failed
            else:
                 # Ensure columns are DatetimeIndex for reliable sorting/selection
                 try:
                     if not isinstance(df.columns, pd.DatetimeIndex):
                         df.columns = pd.to_datetime(df.columns, errors='coerce')
                         # Drop columns that couldn't be parsed (shouldn't happen often with yf)
                         df = df.dropna(axis=1, how='all')
                         statements[name] = df # Update the dict
                 except Exception as e:
                     logging.warning(f"Could not convert columns to datetime for {name} statement: {e}")
                 fetched_count += 1

        if fetched_count > 0:
            logging.info(f"Successfully fetched {fetched_count}/3 {period} statements for {ticker_symbol}")
        else:
            logging.warning(f"Could not fetch any valid {period} statements for {ticker_symbol}")

        return statements
    except Exception as e:
        logging.error(f"Error fetching {period} statements for {ticker_symbol}: {e}")
        return {'income': None, 'balance': None, 'cashflow': None}

def get_company_info(ticker_symbol: str) -> dict | None:
    logging.info(f"Fetching company info for {ticker_symbol}...")
    try:
        ticker = yf.Ticker(ticker_symbol)
        info = ticker.info
        if not info:
            logging.warning(f"Could not retrieve info for {ticker_symbol}")
            return None
        logging.info(f"Successfully fetched info for {ticker_symbol}")
        return info
    except Exception as e:
        logging.error(f"Error fetching info for {ticker_symbol}: {e}")
        return None