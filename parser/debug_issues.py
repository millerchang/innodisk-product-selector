"""
Debug script: inspect ai_tops and processor_model issues in specific PDFs.
"""
import sys, re
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import pdfplumber

TARGETS = {
    "ABOX-4140 (ai_tops=22.4?)":
        r"D:\Claude\Miller_Workspace\Work\Innodisk_Product_Selector\AIoT\1.Datasheet\Box PC\ABOX-4140\ABOX-4140_251205.pdf",
    "APEX-X100-Q (ai_tops=870?)":
        r"D:\Claude\Miller_Workspace\Work\Innodisk_Product_Selector\AIoT\1.Datasheet\APEX series\APEX-X100-Q\Datasheet_APEX-X100-Q_20250903.pdf",
    "APEX-E100 (cpu=?)":
        r"D:\Claude\Miller_Workspace\Work\Innodisk_Product_Selector\AIoT\1.Datasheet\APEX series\APEX-E100\Datasheet_APEX-E100_20250814.pdf",
    "AXMB-D150 (ai_tops=97?)":
        r"D:\Claude\Miller_Workspace\Work\Innodisk_Product_Selector\AIoT\1.Datasheet\Industrial Board\AXMB-D150_Mini ITX\Datasheet_AXMB-D150_20251008.pdf",
}

RE_TOPS = re.compile(r'(\d+(?:\.\d+)?)\s*TOPS', re.IGNORECASE)
RE_CPU  = re.compile(r'(?:Intel\s+)?CPU\s+(.{10,80})', re.IGNORECASE)

for label, path in TARGETS.items():
    print(f"\n{'='*60}")
    print(f"  {label}")
    print("=" * 60)
    with pdfplumber.open(path) as pdf:
        text = "\n".join(p.extract_text() or "" for p in pdf.pages)

    # Show all TOPS hits with 60 chars of context
    print("\n[TOPS hits]")
    for m in RE_TOPS.finditer(text):
        start = max(0, m.start() - 60)
        end   = min(len(text), m.end() + 60)
        ctx   = text[start:end].replace("\n", "↵")
        print(f"  value={m.group(1):>8}  ctx: ...{ctx}...")

    # Show CPU line context
    print("\n[CPU line hits]")
    for m in RE_CPU.finditer(text):
        print(f"  → {m.group(0)[:100]}")
