#!/usr/bin/env python3
"""Debug script to see what's in the PDF."""

import pdfplumber

pdf_path = "/data/test-sample.pdf"

print("=" * 80)
print("RAW TEXT:")
print("=" * 80)

with pdfplumber.open(pdf_path) as pdf:
    for page_num, page in enumerate(pdf.pages, 1):
        print(f"\n--- PAGE {page_num} ---")
        text = page.extract_text()
        print(text)
        
        print(f"\n--- TABLES ON PAGE {page_num} ---")
        tables = page.extract_tables()
        if tables:
            for table_num, table in enumerate(tables, 1):
                print(f"\nTable {table_num}:")
                for row_num, row in enumerate(table):
                    print(f"  Row {row_num}: {row}")
        else:
            print("No tables found")

