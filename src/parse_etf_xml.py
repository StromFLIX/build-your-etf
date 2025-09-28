#!/usr/bin/env python3
"""
Utility to parse iShares Excel XML files and extract ETF holdings data.
"""

import xml.etree.ElementTree as ET
import pandas as pd
from pathlib import Path
import sys
import re


def parse_excel_xml(filepath: Path) -> pd.DataFrame:
    """Parse an Excel XML file and extract table data."""
    print(f"Parsing {filepath.name}...")
    
    try:
        # Read the file content
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Remove BOM if present
        content = content.lstrip('\ufeff')
        
        # Parse XML
        root = ET.fromstring(content)
        
        # Define namespace
        ns = {'ss': 'urn:schemas-microsoft-com:office:spreadsheet'}
        
        # Find all worksheets
        worksheets = root.findall('.//ss:Worksheet', ns)
        
        all_data = {}
        
        for ws in worksheets:
            ws_name = ws.get('{urn:schemas-microsoft-com:office:spreadsheet}Name', 'Unnamed')
            print(f"  Found worksheet: {ws_name}")
            
            # Find table in this worksheet
            table = ws.find('.//ss:Table', ns)
            if table is None:
                continue
                
            rows_data = []
            rows = table.findall('.//ss:Row', ns)
            
            for row in rows:
                cells = row.findall('.//ss:Cell', ns)
                row_data = []
                
                for cell in cells:
                    data_elem = cell.find('.//ss:Data', ns)
                    if data_elem is not None:
                        row_data.append(data_elem.text or '')
                    else:
                        row_data.append('')
                
                if any(row_data):  # Only add non-empty rows
                    rows_data.append(row_data)
            
            if rows_data:
                # Convert to DataFrame
                max_cols = max(len(row) for row in rows_data) if rows_data else 0
                # Pad short rows
                for row in rows_data:
                    while len(row) < max_cols:
                        row.append('')
                
                df = pd.DataFrame(rows_data[1:] if len(rows_data) > 1 else [], 
                                columns=rows_data[0] if rows_data else [])
                all_data[ws_name] = df
                
                print(f"    Shape: {df.shape}")
                if not df.empty:
                    print(f"    Columns: {list(df.columns)[:5]}...")  # Show first 5 columns
                    print(f"    Sample data:")
                    print(df.head(3))
                    print()
        
        return all_data
        
    except Exception as e:
        print(f"Error parsing {filepath}: {e}")
        return {}


def main():
    """Main function to parse all ETF files."""
    data_dir = Path("data/etf")
    
    if not data_dir.exists():
        print(f"Data directory {data_dir} does not exist")
        sys.exit(1)
    
    etf_files = list(data_dir.glob("*.xls"))
    
    if not etf_files:
        print("No ETF files found")
        sys.exit(1)
    
    print(f"Found {len(etf_files)} ETF files to parse\n")
    
    for filepath in etf_files:
        parsed_data = parse_excel_xml(filepath)
        
        if parsed_data:
            print(f"✅ Successfully parsed {filepath.name}")
            print(f"   Found {len(parsed_data)} worksheets: {list(parsed_data.keys())}")
        else:
            print(f"❌ Failed to parse {filepath.name}")
        print("-" * 60)


if __name__ == "__main__":
    main()