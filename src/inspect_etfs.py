#!/usr/bin/env python3
"""
Utility to inspect downloaded ETF Excel files and understand their structure.
"""

import sys
import pandas as pd
from pathlib import Path


def inspect_etf_file(filepath: Path):
    """Inspect an ETF Excel file and show its structure."""
    print(f"\n=== Inspecting {filepath.name} ===")
    
    try:
        # Try different engines for reading Excel files
        engines = ['openpyxl', 'xlrd', None]
        df = None
        
        for engine in engines:
            try:
                excel_file = pd.ExcelFile(filepath, engine=engine)
                print(f"Sheet names: {excel_file.sheet_names}")
                
                # Read the first sheet
                df = pd.read_excel(filepath, sheet_name=0, engine=engine)
                break
            except Exception as e:
                if engine is None:
                    # If it's XML format, try reading as CSV with tab separator
                    try:
                        print("Trying to read as tab-separated file...")
                        with open(filepath, 'r', encoding='utf-8') as f:
                            content = f.read()
                            if '<?xml' in content:
                                print("File is in XML format (Excel XML)")
                                # For now, just show the first few lines
                                lines = content.split('\n')[:10]
                                for line in lines:
                                    print(line)
                                return
                    except Exception:
                        pass
                print(f"Engine {engine} failed: {e}")
                continue
        
        if df is not None:
            print(f"Shape: {df.shape}")
            print(f"Columns: {list(df.columns)}")
            print("First few rows:")
            print(df.head(3))
        else:
            print("Could not read file with any engine")
            
    except Exception as e:
        print(f"Error reading {filepath}: {e}")


def main():
    """Main function to inspect all ETF files."""
    data_dir = Path("data/etf")
    
    if not data_dir.exists():
        print(f"Data directory {data_dir} does not exist")
        sys.exit(1)
    
    etf_files = list(data_dir.glob("*.xls"))
    
    if not etf_files:
        print("No ETF files found")
        sys.exit(1)
    
    print(f"Found {len(etf_files)} ETF files")
    
    for filepath in etf_files:
        inspect_etf_file(filepath)


if __name__ == "__main__":
    main()