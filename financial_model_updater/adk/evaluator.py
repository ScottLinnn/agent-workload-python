import sys
import os


import openpyxl

def evaluate():
    base_path = os.path.abspath(os.path.dirname(__file__))
    excel_path = os.path.join(base_path, 'mock_model_updated.xlsx')
    summary_path = os.path.join(base_path, 'summary.md')
    
    # Check if files exist
    if not os.path.exists(excel_path):
        print(f"FAILED: {excel_path} does not exist.")
        return False
    if not os.path.exists(summary_path):
        print(f"FAILED: {summary_path} does not exist.")
        return False
    
    # Check Excel content
    wb = openpyxl.load_workbook(excel_path, data_only=True)
    ws = wb['DCF Model']
    year_5_revenue = ws['F2'].value
    
    # Expected revenue from q4_data.txt was 1500000
    if year_5_revenue != 1500000:
        print(f"FAILED: Expected Year 5 revenue 1500000, got {year_5_revenue}")
        return False
    
    # Check IRR in summary.md
    with open(summary_path, 'r') as f:
        summary_content = f.read()
    
    # Reference IRR for 1.5M revenue is 12.37%
    if "12.37%" not in summary_content:
        print(f"FAILED: IRR (12.37%) not found in {summary_path}")
        print(f"Summary content: {summary_content}")
        return False
    
    print("PASSED: Financial Model Updater evaluation successful (Revenue and IRR verified).")
    return True

if __name__ == "__main__":
    if evaluate():
        sys.exit(0)
    else:
        sys.exit(1)
