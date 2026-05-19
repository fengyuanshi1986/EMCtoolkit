
import pandas as pd
import os
from fuzzywuzzy import process

class RateProcessor:
    def __init__(self, finance_path, usage_path, equip_path):
        self.finance_path = finance_path
        self.usage_path = usage_path
        self.equip_path = equip_path
        
        self.salaries = None
        self.salaries_summary = None
        self.expenses_summary = None
        self.expenses_detail = None
        self.service_contracts = None
        self.dep_full = None
        self.depreciation = None
        self.usage = None
        
    def load_data(self):
        # 1. Salaries (EXCLUDE Robert Klie)
        df_sal_det = pd.read_excel(self.finance_path, sheet_name='Salaries Detail', header=1)
        df_sal_det = df_sal_det[df_sal_det['Employee UIN'] != 'Employee UIN']
        df_sal_det = df_sal_det[~df_sal_det['Employee Name'].str.contains('Klie, Robert', case=False, na=False)]
        self.salaries = df_sal_det.groupby(['Employee Name', 'Position Title'])['Payroll Expense Amount'].sum().reset_index()
        
        self.salaries_summary = pd.read_excel(self.finance_path, sheet_name='Salaries Summary', header=1)
        self.salaries_summary = self.salaries_summary.dropna(subset=['Employee Name', '3E Fund Expense Amount'])
        self.salaries_summary = self.salaries_summary[~self.salaries_summary['Employee Name'].str.contains('Klie, Robert', case=False, na=False)]

        # 2. Depreciation (Grouped for App Speed)
        df_equip = pd.read_excel(self.equip_path, header=3)
        df_equip = df_equip.dropna(subset=['Asset Description'])
        df_equip['Depreciation Amount'] = pd.to_numeric(df_equip['Depreciation Amount'], errors='coerce').fillna(0)
        df_equip['Fund Type'] = df_equip['Fin Fund Type Code'].apply(lambda x: '3E' if str(x) == '3E' else 'Non-3E')
        self.dep_full = df_equip
        # GROUP BY Description so the mapping list isn't 500 lines long
        self.depreciation = df_equip.groupby('Asset Description')['Depreciation Amount'].sum().reset_index()
        
        # 3. Expenditures Summary (Strict Filtering)
        df_exp_sum = pd.read_excel(self.finance_path, sheet_name='Exp Summary', header=1)
        exclude_codes = [142100, 153809, 186100, 211300, 211400, 211960, 147400]
        mask_summary = (
            (df_exp_sum['Financial Account Code'].isin(exclude_codes)) |
            (df_exp_sum['Expense Amount'] <= 0) | 
            (df_exp_sum['Financial Account Title'].str.contains('Total|Sum|Salary|Bad Debt|Facilities Management', case=False, na=False))
        )
        self.expenses_summary = df_exp_sum[~mask_summary].copy()
        
        # App View uses Summary Level (Concise)
        self.expenses_detail = self.expenses_summary[['Financial Account Code', 'Financial Account Title', 'Expense Amount']].copy()
        self.expenses_detail.columns = ['Account', 'Description', 'Amount']

        # 4. Service Contracts (Isolated from Detail)
        df_exp_detail = pd.read_excel(self.finance_path, sheet_name='Exp Detail', header=2)
        mask_contracts = (
            (df_exp_detail['Financial Account Code'] == 147400) | 
            (df_exp_detail['Financial Account Title'].str.contains('Repair/Maint|Annual R/M', case=False, na=False))
        )
        self.service_contracts = df_exp_detail[mask_contracts & (df_exp_detail['OL Detail Expense Amt'] > 0)][['Financial Account Title', 'OL Detail Descriptive Text', 'OL Detail Expense Amt']].copy()
        self.service_contracts.columns = ['Account', 'Description', 'Amount']

        # 5. iLab Usage
        df_usage = pd.read_excel(self.usage_path, header=3)
        self.usage = df_usage[['Service', 'Total']].dropna()
        self.usage.columns = ['Instrument', 'Hours']
        self.usage = self.usage[~self.usage['Instrument'].str.contains('Total', case=False)]

    def suggest_mapping(self, asset_desc, instruments):
        if not instruments: return "Skip"
        match, score = process.extractOne(asset_desc, instruments)
        return match if score > 70 else "Skip"

    def get_allocation_percentages(self):
        total_hours = self.usage['Hours'].sum()
        if total_hours == 0: return self.usage.copy()
        df = self.usage.copy()
        df['Percentage'] = df['Hours'] / total_hours
        return df
