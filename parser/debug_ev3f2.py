"""Find all occurrences of EV3F in the PDF text and show context."""
import sys, re
sys.path.insert(0, r'D:\Claude\Miller_Workspace\Work\Innodisk_Product_Selector\parser')
import pdfplumber

PDF = r'D:\Claude\Miller_Workspace\Work\Innodisk_Product_Selector\Camera\1.0 Datasheet\4.0 GMSL2\EV3F-ZSM1-RXCF-41_Datasheet_2025_Q4.pdf'

full_text = ""
with pdfplumber.open(PDF) as pdf:
    for page in pdf.pages:
        full_text += (page.extract_text() or "") + "\n"

# Show every occurrence of EV3F with 20 chars of context
for m in re.finditer(r'EV3F.{0,30}', full_text):
    raw = repr(m.group(0))
    print(f"pos={m.start():4d}  {raw}")

# Also test the regex directly
RE = re.compile(r'(?<!\w)(E[VB][0-9A-Z]{1,4}(?:-[A-Z0-9]{2,6}){1,3})(?![A-Z0-9-])')
print("\n=== Regex matches ===")
for m in RE.finditer(full_text):
    print(f"  match={m.group(1)!r}  (context: {full_text[m.start()-3:m.end()+10]!r})")
