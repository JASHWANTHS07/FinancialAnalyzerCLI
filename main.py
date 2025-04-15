import click
import pandas as pd
from typing import Literal
import logging
import os
import sys

from src.data_extraction.extractor import get_financial_statements, get_company_info
from src.data_extraction.mapper import standardize_statements
from src.analysis.ratios import (
    calculate_historical_ratios,
    calculate_sector_ratios,
    calculate_single_period_ratios
)
from src.analysis.verifier import verify_financial_consistency
from src.utils.helpers import load_sector_map

try:
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    plt = None
    mdates = None

try:
    import plotext as pltx
    PLOTEXT_AVAILABLE = True
except ImportError:
    PLOTEXT_AVAILABLE = False
    pltx = None


logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
# Silence overly verbose logs from libraries like matplotlib
logging.getLogger("matplotlib").setLevel(logging.WARNING)


pd.set_option('display.max_columns', 15)
pd.set_option('display.max_rows', 50)
pd.set_option('display.width', 150)
pd.set_option('display.float_format', '{:,.2f}'.format)


@click.group()
def cli():
    """
    FinancialAnalysisCLI: Fetch, analyze, and visualize financial data.

    Provides commands to analyze individual companies or compare companies
    within a specific sector using data from Yahoo Finance.
    """
    pass

@cli.command()
@click.argument('ticker')
@click.option('--period',
              type=click.Choice(['annual', 'quarterly'], case_sensitive=False),
              default='annual', show_default=True,
              help='Specify whether to analyze annual or quarterly data.')
@click.option('--years', type=int, default=5, show_default=True,
              help='Number of recent periods (years/quarters) to display in tables.')
@click.option('--plot', is_flag=True, default=False,
              help='Generate and save graphical plots for key ratio trends (requires matplotlib).')
@click.option('--term-plot', is_flag=True, default=False,
              help='Display simple trend plots directly in the terminal (requires plotext).')
@click.option('--output-dir', type=click.Path(file_okay=False, dir_okay=True, writable=True, resolve_path=True),
              default='output', show_default=True,
              help='Directory to save generated plots.')
@click.option('--show', is_flag=True, default=False,
              help='Attempt to automatically open the generated graphical plot (if --plot is used).')
def analyze_company(ticker: str, period: Literal['annual', 'quarterly'], years: int, plot: bool, term_plot: bool, output_dir: str, show: bool):
    """
    Analyzes historical financial data for a specific company Ticker.

    Fetches data, standardizes it, verifies the latest period, calculates
    historical ratios, and optionally generates trend plots.
    """
    ticker = ticker.upper()
    click.echo(f"--- Analyzing {ticker} ({period.capitalize()} Data) ---")


    statements = get_financial_statements(ticker, period=period)
    info = get_company_info(ticker) # Get info for context (name, sector, etc.)

    if statements is None or not statements or all(df is None or df.empty for df in statements.values()):
        click.secho(f"ERROR: Could not retrieve sufficient {period} financial data for {ticker}.", fg='red')
        sys.exit(1) # Exit with error code


    standard_df = standardize_statements(statements)

    if standard_df is None or standard_df.empty:
        click.secho(f"ERROR: Could not standardize {period} data for {ticker}.", fg='red')
        sys.exit(1)

    num_periods_available = len(standard_df.columns)
    periods_to_display = min(years, num_periods_available)
    click.echo(f"\n--- Standardized Data ({periods_to_display} Most Recent Periods) ---")
    # Use specific float format for financial statements (e.g., no decimals or 2)
    with pd.option_context('display.float_format', '{:,.0f}'.format): # No decimals for large statement numbers
        click.echo(standard_df.iloc[:, :periods_to_display])

    if num_periods_available > 0:
        latest_period_data = standard_df.iloc[:, 0] # Get the first column (latest period Series)
        latest_period_date = latest_period_data.name # This should be a Timestamp
        latest_period_date_str = latest_period_date.strftime('%Y-%m-%d') if isinstance(latest_period_date, pd.Timestamp) else "Unknown Date"

        click.echo(f"\n--- Data Verification (Latest Period: {latest_period_date_str}) ---")
        verification_results = verify_financial_consistency(latest_period_data)
        has_failures = False
        for check, result in verification_results.items():
            if result is True:
                click.secho(f"  {check}: Passed", fg='green')
            elif isinstance(result, str) and result.startswith("Skipped"):
                click.secho(f"  {check}: {result}", fg='yellow')
            else: # Failed or other string message
                click.secho(f"  {check}: {result}", fg='red')
                has_failures = True
        if has_failures:
             click.secho("  NOTE: Verification failures may indicate data quality issues or mapping problems.", fg='yellow')
    else:
        click.echo("\n--- Data Verification ---")
        click.secho("  Skipped: No data periods available for verification.", fg='yellow')


    ratio_df = calculate_historical_ratios(standard_df)

    if ratio_df is None or ratio_df.empty:
         click.echo("\n--- Ratios ---")
         click.secho("  Could not calculate ratios.", fg='yellow')
    else:
        num_ratio_periods = len(ratio_df.columns)
        ratio_periods_to_display = min(years, num_ratio_periods)
        click.echo(f"\n--- Calculated Ratios ({ratio_periods_to_display} Most Recent Periods) ---")
        # Use specific float format for ratios (e.g., 4 decimal places)
        with pd.option_context('display.float_format', '{:,.4f}'.format):
            click.echo(ratio_df.iloc[:, :ratio_periods_to_display])

        if plot or term_plot:
            try:
                os.makedirs(output_dir, exist_ok=True)
            except OSError as e:
                 click.secho(f"ERROR: Could not create output directory '{output_dir}': {e}", fg='red')
                 plot = False
                 term_plot = False

        if plot:
            if not MATPLOTLIB_AVAILABLE:
                click.secho("\nWARN: Graphical plotting skipped. --plot requires `matplotlib`. Install it (`pip install matplotlib`).", fg='yellow')
            else:
                click.echo("\n--- Generating Graphical Plot (Matplotlib) ---")
                try:
                    plot_ratios_keys = ['Return on Equity (ROE)', 'Return on Assets (ROA)',
                                        'Net Margin', 'Operating Margin', 'Asset Turnover', 'Current Ratio']
                    plot_df = ratio_df.loc[ratio_df.index.intersection(plot_ratios_keys)].dropna(axis=1, how='all').sort_index(axis=1).T

                    if not plot_df.empty:
                        fig, ax = plt.subplots(figsize=(12, 7))
                        plot_df.plot(ax=ax, marker='.', linestyle='-')

                        ax.set_title(f'{ticker} Key Ratio Trends ({period.capitalize()})', fontsize=14)
                        ax.set_ylabel('Ratio Value', fontsize=10)
                        ax.set_xlabel('Period Ending', fontsize=10)
                        ax.grid(True, axis='y', linestyle='--', alpha=0.6)
                        ax.tick_params(axis='x', rotation=45)
                        ax.tick_params(axis='both', labelsize=9)

                        if period == 'quarterly' and len(plot_df.index) > 1:
                            ax.xaxis.set_major_locator(mdates.YearLocator())
                            ax.xaxis.set_minor_locator(mdates.MonthLocator(interval=3))
                            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
                        else:
                             ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))

                        ax.legend(title='Ratio', fontsize=9, bbox_to_anchor=(1.02, 1), loc='upper left')
                        plt.subplots_adjust(right=0.85)
                        plt.tight_layout(rect=[0, 0, 0.85, 1])

                        filename = os.path.join(output_dir, f"{ticker}_{period}_ratios_trend.png")
                        plt.savefig(filename, dpi=150)
                        plt.close(fig)
                        click.secho(f"  Chart saved to: {filename}", fg='cyan')

                        if show:
                            try:
                                if sys.platform == "win32":
                                    os.startfile(filename)
                                elif sys.platform == "darwin":
                                    os.system(f"open '{filename}'")
                                else:
                                    os.system(f"xdg-open '{filename}'")
                                click.echo("  Attempting to open the chart...")
                            except Exception as e:
                                click.secho(f"  WARN: Could not automatically open the chart: {e}", fg='yellow')

                    else:
                        click.secho("  No data available for plotting the selected key ratios.", fg='yellow')

                except Exception as e:
                    click.secho(f"  ERROR generating matplotlib plot: {e}", fg='red')
                    logging.exception("Matplotlib plotting error details:")

        if term_plot:
            if not PLOTEXT_AVAILABLE:
                click.secho(
                    "\nWARN: Terminal plotting skipped. --term-plot requires `plotext`. Install it (`pip install plotext`).",
                    fg='yellow')
            else:
                click.echo("\n--- Generating Terminal Plots (Plotext) ---")
                term_plot_ratios = ['Return on Equity (ROE)', 'Current Ratio']
                for ratio_name in term_plot_ratios:
                    try:
                        if ratio_name in ratio_df.index:
                            ratio_series = ratio_df.loc[ratio_name].dropna().sort_index(ascending=True)
                            if not ratio_series.empty:
                                x_values = list(range(len(ratio_series)))
                                values = ratio_series.values

                                x_labels = [d.strftime('%Y-%m') for d in ratio_series.index]

                                pltx.clear_figure()
                                pltx.plot_size(min(100, os.get_terminal_size().columns - 10), 20)

                                pltx.plot(x_values, values, marker='braille')

                                pltx.title(f"{ticker} - {ratio_name} ({period.capitalize()})")
                                pltx.xlabel("Period")
                                pltx.ylabel(ratio_name)

                                ticks_step = max(1, len(x_values) // 5)
                                tick_positions = [i for i in x_values if i % ticks_step == 0]
                                tick_labels = [x_labels[i] for i in tick_positions]
                                pltx.xticks(tick_positions, tick_labels)

                                pltx.show()
                                click.echo("-" * 40)
                            else:
                                click.secho(f"  No data available for terminal plot of {ratio_name}.", fg='yellow')
                        else:
                            click.secho(f"  Ratio '{ratio_name}' not found for terminal plot.", fg='yellow')
                    except Exception as e:
                        click.secho(f"  ERROR generating plotext plot for {ratio_name}: {e}", fg='red')
                        logging.exception(f"Plotext plotting error details for {ratio_name}:")


    if info:
         click.echo("\n--- Company Information ---")
         click.echo(f"  Name:     {info.get('shortName', 'N/A')}")
         click.echo(f"  Sector:   {info.get('sector', 'N/A')}")
         click.echo(f"  Industry: {info.get('industry', 'N/A')}")
         click.echo(f"  Website:  {info.get('website', 'N/A')}")
         market_cap = info.get('marketCap')
         if market_cap: click.echo(f"  Market Cap: {market_cap:,.0f}")
        # Add more info fields if desired (e.g., marketCap, employees)

    click.echo("\n--- Analysis Complete ---")


@cli.command()
@click.argument('sector_name')
@click.option('--map-file', type=click.Path(exists=True, dir_okay=False, readable=True),
              default='data/ticker_sector_map.csv', show_default=True,
              help='Path to the CSV file mapping tickers to sectors.')
@click.option('--period', type=click.Choice(['annual', 'quarterly'], case_sensitive=False),
              default='annual', show_default=True,
              help='Analyze latest annual or quarterly data for sector comparison.')
def analyze_sector(sector_name: str, map_file: str, period: Literal['annual', 'quarterly']):
    """
    Compares the LATEST period ratios for companies within a specific sector.

    Uses the ticker-sector map file to identify companies. Calculates aggregate
    statistics (Avg, Median, Min, Max) and displays a comparative table.
    """
    click.echo(f"--- Analyzing Sector: {sector_name} (Latest {period.capitalize()} Data) ---")

    sector_map_df = load_sector_map(map_file)
    if sector_map_df is None:
        click.secho(f"ERROR: Failed to load or validate sector map file: {map_file}", fg='red')
        sys.exit(1)

    sector_tickers = sector_map_df[sector_map_df['Sector'].str.lower() == sector_name.lower()].index.tolist()

    if not sector_tickers:
        click.secho(f"No tickers found for sector '{sector_name}' in the map file '{map_file}'.", fg='yellow')
        known_sectors = sorted(sector_map_df['Sector'].dropna().unique())
        if known_sectors:
             click.echo(f"Available sectors in map: {', '.join(known_sectors)}")
        else:
             click.echo("No sectors found in the map file.")
        sys.exit(0)

    click.echo(f"Found {len(sector_tickers)} tickers for sector '{sector_name}'. Processing...")

    all_company_latest_ratios = {} # {ticker: {ratio_name: value}}
    processed_count = 0
    skipped_count = 0
    skipped_reasons = {'no_data': 0, 'standardize_fail': 0, 'ratio_fail': 0}

    for ticker in sector_tickers:
        click.echo(f"  Processing {ticker.upper()}...", nl=False) # Keep cursor on same line

        statements = get_financial_statements(ticker, period=period)
        if not statements or all(df is None or df.empty for df in statements.values()):
            click.secho(" Skipped (No data)", fg='yellow')
            skipped_count += 1
            skipped_reasons['no_data'] += 1
            continue

        standard_df = standardize_statements(statements)
        if standard_df is None or standard_df.empty:
             click.secho(" Skipped (Standardization failed)", fg='yellow')
             skipped_count += 1
             skipped_reasons['standardize_fail'] += 1
             continue

        if standard_df.shape[1] == 0:
             click.secho(" Skipped (No periods after standardization)", fg='yellow')
             skipped_count += 1
             skipped_reasons['standardize_fail'] += 1
             continue

        latest_period_data = standard_df.iloc[:, 0]

        latest_ratios = calculate_single_period_ratios(latest_period_data)

        if latest_ratios and any(v is not None for v in latest_ratios.values()):
             all_company_latest_ratios[ticker.upper()] = latest_ratios
             click.secho(" Done.", fg='green')
             processed_count += 1
        else:
            click.secho(" Skipped (Ratio calculation failed or yielded no results)", fg='yellow')
            skipped_count += 1
            skipped_reasons['ratio_fail'] += 1


    click.echo(f"\n--- Sector Processing Summary ---")
    click.echo(f"  Successfully processed: {processed_count}")
    click.echo(f"  Skipped: {skipped_count} (No Data: {skipped_reasons['no_data']}, Standardize Fail: {skipped_reasons['standardize_fail']}, Ratio Fail: {skipped_reasons['ratio_fail']})")

    if not all_company_latest_ratios:
         click.secho("\nNo company ratios could be calculated for comparison in this sector.", fg='yellow')
         sys.exit(0)

    click.echo(f"\n--- Sector Aggregate Ratios ({processed_count} Companies, Latest {period.capitalize()} Period) ---")
    sector_agg_ratios = calculate_sector_ratios(all_company_latest_ratios) # Expects {ticker: {ratio: value}}

    if sector_agg_ratios:
         try:
             agg_df = pd.DataFrame.from_dict(sector_agg_ratios, orient='index', columns=['Value'])
             agg_df[['Ratio', 'Stat']] = agg_df.index.str.rsplit('_', n=1, expand=True)
             agg_pivot = agg_df.pivot(index='Ratio', columns='Stat', values='Value')
             display_stats = ['Avg', 'Median', 'Min', 'Max']
             agg_pivot = agg_pivot[[col for col in display_stats if col in agg_pivot.columns]] # Handle missing stats if all data was NaN

             with pd.option_context('display.float_format', '{:,.4f}'.format):
                  click.echo(agg_pivot)
         except Exception as e:
              click.secho(f"  Error formatting aggregate ratios: {e}", fg='red')
              for name, value in sector_agg_ratios.items():
                   click.echo(f"  {name}: {value:.4f}" if value is not None else f"  {name}: N/A")
    else:
        click.secho("  Could not calculate aggregate sector ratios.", fg='yellow')

    click.echo(f"\n--- Comparative Ratios (Individual Companies - Latest {period.capitalize()} Period) ---")
    try:
        comp_df = pd.DataFrame.from_dict(all_company_latest_ratios, orient='index')
        with pd.option_context('display.float_format', '{:,.4f}'.format):
             click.echo(comp_df)
    except Exception as e:
        click.secho(f"  Error creating comparative DataFrame: {e}", fg='red')

    click.echo("\n--- Analysis Complete ---")

if __name__ == '__main__':
    pd.reset_option('display.float_format')
    cli()