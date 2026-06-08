"""
Quick inspection script: extract raw text from representative PDFs.
Run: python inspect_pdfs.py
"""
import pdfplumber
import os
import sys
# Force UTF-8 output on Windows console
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

files = {
    "SBC":      r"D:\Claude\Miller_Workspace\Work\Innodisk_Product_Selector\AIoT\1.Datasheet\SBC\ASBC-3150\ASBC-3150_251003.pdf",
    "BoxPC":    r"D:\Claude\Miller_Workspace\Work\Innodisk_Product_Selector\AIoT\1.Datasheet\Box PC\ABOX-4020\ABOX-4020.pdf",
    "APEX":     r"D:\Claude\Miller_Workspace\Work\Innodisk_Product_Selector\AIoT\1.Datasheet\APEX series\APEX-X100\Datasheet_APEX-X100_20260213.pdf",
    "IndBoard": r"D:\Claude\Miller_Workspace\Work\Innodisk_Product_Selector\AIoT\1.Datasheet\Industrial Board\AXMB-1130\AXMB-1130_20250807.pdf",
    "Embedded": r"D:\Claude\Miller_Workspace\Work\Innodisk_Product_Selector\AIoT\1.Datasheet\Embedded System\AIPC-4120\AIPC-4120 Datasheet_1209.pdf",
    "NXP_SBC":  r"D:\Claude\Miller_Workspace\Work\Innodisk_Product_Selector\AIoT\1.Datasheet\SBC\ASBC-3M80\ASBC-3M80_251014.pdf",
}

for label, path in files.items():
    print(f"\n{'='*65}")
    print(f"[{label}] {os.path.basename(path)}")
    print("=" * 65)
    with pdfplumber.open(path) as pdf:
        total = len(pdf.pages)
        print(f"Total pages: {total}")
        for i, page in enumerate(pdf.pages[:3]):
            text = page.extract_text() or ""
            tables = page.extract_tables()
            print(f"\n--- Page {i+1} | tables={len(tables)} ---")
            print(text[:2000])
            if tables:
                print(f"  [TABLE SAMPLE] {tables[0][:4]}")
