FINANCIAL_ITEM_MAPPING= {
    # Income Statement
    'revenue': ['Total Revenue', 'Revenue', 'totalRevenue'],
    'cost_of_revenue': ['Cost Of Revenue', 'Cost of Revenue', 'costOfRevenue'],
    'gross_profit': ['Gross Profit', 'grossProfit'],
    'research_development': ['Research Development', 'researchDevelopmentExpense'],
    'selling_general_administrative': ['Selling General Administrative', 'Selling General and Administrative', 'sellingGeneralAdministrative', 'sellingGeneralAndAdministrative'],
    'operating_expenses': ['Operating Expenses', 'Total Operating Expenses', 'totalOperatingExpenses', 'OperatingExpenditures', 'Total Operating Expenditures'],
    'operating_income': ['Operating Income', 'Operating Income or Loss', 'operatingIncome'],
    'interest_expense': ['Interest Expense', 'interestExpense'],
    'income_before_tax': ['Income Before Tax', 'Pretax Income', 'incomeBeforeTax'],
    'income_tax_expense': ['Income Tax Expense', 'Tax Provision', 'incomeTaxExpense'],
    'net_income': ['Net Income', 'Net Income Applicable To Common Shares', 'netIncome', 'netIncomeApplicableToCommonShares'],

    # Balance Sheet
    'cash': ['Cash', 'Cash And Cash Equivalents', 'cashAndCashEquivalents'],
    'accounts_receivable': ['Net Receivables', 'Accounts Receivable'],
    'inventory': ['Inventory', 'inventory'],
    'current_assets': ['Total Current Assets', 'Current Assets', 'totalCurrentAssets'],
    'property_plant_equipment': ['Property Plant Equipment Net', 'Total Property Plant Equipment', 'Property plant and equipment net'], # Added variation
    'total_assets': ['Total Assets', 'totalAssets'],
    'accounts_payable': ['Accounts Payable'],
    'short_term_debt': ['Short Long Term Debt', 'Short Term Debt', 'Current Debt', 'Current Liabilities And Long Term Debt'], # Check specific names
    'current_liabilities': ['Total Current Liabilities', 'Current Liabilities', 'totalCurrentLiabilities'],
    'long_term_debt': ['Long Term Debt', 'longTermDebt'],
    'total_liabilities': ['Total Liab', 'Total Liabilities', 'totalLiab', 'Total Liabilities Net Minority Interest'], # Added variation - CHECK THIS ONE CAREFULLY
    'common_stock': ['Common Stock', 'commonStock'],
    'retained_earnings': ['Retained Earnings', 'retainedEarnings'],
    'total_equity': ['Total Stockholder Equity', 'Stockholders Equity', 'Total Equity', 'totalStockholderEquity'],

    # Cash Flow Statement
    'depreciation_amortization': ['Depreciation And Amortization', 'Depreciation & Amortization', 'Depreciation'], # Check specific names
    'operating_cash_flow': ['Total Cash From Operating Activities', 'Cash Flow From Operating Activities', 'totalCashFromOperatingActivities'],
    'capital_expenditures': ['Capital Expenditures', 'capex'],
    'investing_cash_flow': ['Total Cashflows From Investing Activities', 'Cash Flow From Investing Activities', 'totalCashflowsFromInvestingActivities'],
    'dividends_paid': ['Dividends Paid', 'dividendsPaid'],
    'issuance_of_stock': ['Issuance Of Stock', 'Issuance of Common Stock'], # Check names
    'repurchase_of_stock': ['Repurchase Of Stock', 'Repurchase of Common Stock', 'Treasury Stock'], # Added variation
    'financing_cash_flow': ['Total Cash From Financing Activities', 'Cash Flow From Financing Activities', 'totalCashFromFinancingActivities'],
    'change_in_cash': ['Change In Cash', 'Net Change In Cash', 'changeInCash'],

    # Verification specific (often derived or redundant)
    'liabilities_and_equity': ['Total Liabilities And Stockholders Equity'], # Often same as Total Assets
}