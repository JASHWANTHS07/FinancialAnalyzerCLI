import pandas as pd
import os
import logging

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'data')

def load_sector_map(filepath=os.path.join(DATA_DIR, 'ticker_sector_map.csv')) -> pd.DataFrame | None:
    """Loads the ticker-to-sector mapping file."""
    try:
        if not os.path.exists(filepath):
            logging.error(f"Sector map file not found at: {filepath}")

            print(f"Error: Please create a sector map file at '{filepath}'")
            print("Example format: Ticker,Sector,NAICS_Code,CompanyName")
            print("AAPL,Technology,334111,Apple Inc.")
            return None
        df = pd.read_csv(filepath)

        required_cols = ['Ticker', 'Sector']
        if not all(col in df.columns for col in required_cols):
             logging.error(f"Sector map CSV missing required columns: {required_cols}")
             return None
        logging.info(f"Loaded sector map with {len(df)} entries.")
        return df.set_index('Ticker') # Set Ticker as index for easy lookup
    except Exception as e:
        logging.error(f"Error loading sector map from {filepath}: {e}")