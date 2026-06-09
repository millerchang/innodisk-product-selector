"""
Rule-based extractor using pdfplumber text extraction.
Handles all AIoT BU product types: SBC, Box PC, Embedded, Industrial Board, APEX.
Covers both Intel and NXP platforms.

Strategy:
  - Extract full text via pdfplumber
  - Apply regex patterns per field
  - Score completeness → if < threshold, caller falls back to Claude Vision
"""

import json
import re
import pdfplumber
from pathlib import Path
from product_catalog import classify_by_rule

# ── CPU Library (lazy-loaded) ────────────────────────────────────────────────
_CPU_LIB: dict | None = None

def _load_cpu_library() -> dict:
    global _CPU_LIB
    if _CPU_LIB is None:
        lib_path = Path(__file__).parent.parent / "output" / "cpu_library.json"
        if lib_path.exists():
            with open(lib_path, encoding="utf-8-sig") as f:  # utf-8-sig handles optional BOM
                _CPU_LIB = json.load(f)
        else:
            _CPU_LIB = {}
    return _CPU_LIB

def _normalize_model(s: str) -> str:
    """移除 ® ™ 符號、多餘空白，用於 library key 查詢。"""
    if not s:
        return ""
    s = re.sub(r"[®™]", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def _cpu_lib_lookup(model: str) -> dict:
    """
    查詢 cpu_library.json，回傳匹配的 entry dict（或 {}）。
    查詢順序：
      1. 直接命中（正規化後 key）
      2. _lookup_aliases 表
      3. 部分匹配（model number substring）
    """
    if not model:
        return {}
    lib = _load_cpu_library()
    norm = _normalize_model(model)

    # 1. 直接命中
    if norm in lib:
        return lib[norm]

    # 2. alias 表
    aliases = lib.get("_lookup_aliases", {})
    if norm in aliases:
        canonical = aliases[norm]
        return lib.get(canonical, {})
    if model in aliases:
        canonical = aliases[model]
        return lib.get(canonical, {})

    # 3. 部分匹配：去掉品牌前綴後比對
    short = re.sub(r"^(Intel\s+(Core\s+|Atom\s+|Celeron\s+)?|NXP\s+)", "", norm, flags=re.I).strip()
    if short:
        for key, entry in lib.items():
            if key.startswith("_"):
                continue
            if short.lower() in key.lower() or key.replace("Intel ", "").lower().startswith(short.lower()):
                return entry

    return {}


# ── Regex patterns ──────────────────────────────────────────────────────────

# Part number: e.g. ASBC-3150, ABOX-4020, AXMB-1130, AIPC-4120, APEX-X100
RE_PART_NO = re.compile(
    r'\b(A(?:SBC|BOX|XMB|IPC|RAK|PEX)-[A-Z0-9]{1,5}(?:-[A-Z0-9]{1,5})?)\b'
)

# IPA BU \ EP \ Computing part numbers: EXEC-Q911, EXMP-Q911, EXMU-X261, EXOU-X261
# Format: "EX" + 2 letters + "-" + 3-5 alphanumerics (Innodisk IPA computing prefix)
RE_PART_NO_IPA = re.compile(r'\b(EX[A-Z]{2}-[A-Z0-9]{3,5})\b')

# IPA BU \ EP module part numbers (Networking / Air Sensor / I/O).
#   Networking : EGPC-* (Innodisk PoE/GbE cards), FARO-* / GADN-* (Antzertech brands)
#   Air Sensor : IAG* (gas modules), ET3-IAERIS* (iAeris subsidiary)
#   I/O        : E + form-factor char {2,3,D,G,H,L,M,S,Y,Z} + 2 chars + -#### (EMSS-3201)
RE_PART_NO_NET    = re.compile(r'\b((?:EGPC|FARO|GADN)-[A-Z0-9]{2,6})\b')
RE_PART_NO_SENSOR = re.compile(r'\b(ET3-IAERIS[0-9]+|IAG[A-Z0-9]{1,6})\b')
RE_PART_NO_IO     = re.compile(r'\b(E[23DGHLMSYZ][A-Z0-9]{2}-[A-Z0-9]{2,6})\b')

# ── Subsidiary / OEM module part numbers (filed under Innodisk EP) ──────────
# These don't follow the E-code scheme, so they're matched from the filename
# stem in the module-routing block and tagged with a "sourcing" origin:
#   InnoEx-*  : subsidiary resale product (Virtual IO)        → io,         subsidiary
#   ANNA-*    : subsidiary GNSS product (subsidiary dissolved) → networking, subsidiary
#   5S######  : OEM-purchased WiFi modules (Intel AX/BE)       → networking, oem
_RE_PN_INNOEX = re.compile(r'^(InnoEx-[A-Za-z0-9]{3,8})', re.IGNORECASE)
_RE_PN_ANNA   = re.compile(r'^(ANNA-[A-Z][0-9]{2}[A-Z][0-9][A-Z]?)', re.IGNORECASE)
_RE_PN_WIFI   = re.compile(r'^(5S[A-Z]{0,2}[0-9]{6,10})')

# Form factor: first lines of document often contain it
RE_FORM_FACTOR = re.compile(
    r'\b(3\.5["\']?\s*SBC|Mini-ITX|Thin\s*Mini-ITX|Box\s*PC|Small\s*Box\s*PC|'
    r'Embedded\s*System|Industrial\s*Motherboard|'
    r'COM\s*Express|SMARC|Pico-ITX|uATX|ATX)\b',
    re.IGNORECASE
)

# Operating temperature — handles various formats:
#   "0°C~60°C", "-40°C ~85°C", "0°C to 60°C", "-20~70°C"
RE_OP_TEMP = re.compile(
    r'Operating\s+Temperature[^\n]{0,60}?(-?\d{1,3})\s*°?C?\s*[~\-–to]+\s*(-?\d{1,3})\s*°?C',
    re.IGNORECASE
)

# Some products list multiple temp ranges on same line (e.g. "0°C~60°C, -40°C~85°C")
RE_OP_TEMP_MULTI = re.compile(
    r'(-?\d{1,3})\s*°?C?\s*[~\-–]+\s*(-?\d{1,3})\s*°?C',
    re.IGNORECASE
)

# ── CPU regex patterns (4 formats found across AIoT product line) ───────────
#
# Format A — full Intel name with ® ™ (standard ABOX/ASBC):
#   "Intel® Core™ i7-13700E"  /  "Intel® Celeron® J6412"
RE_CPU_INTEL_FULL = re.compile(
    r'Intel[®™\s]*(?:Core[™\s]*(?:Ultra\s*\d+\s*)?(?:i[3579]-\d{4,5}[A-Z]{0,3}|'
    r'Ultra\s*[579]\s+\d{3}[A-Z]{0,3})|'
    r'Atom[®\s]*[\w]+|Celeron[®\s]*[\w]+|Pentium[®\s]*[\w]+)',
    re.IGNORECASE
)
# Format B — APEX/AXMB "Intel CPU Core iN-NNNNE" (with or without slash list):
#   "Intel CPU Core i7-13700E"
#   "CPU i9-13900E/ i7-13700E/ i5-13500E"
RE_CPU_MULTI_SKU = re.compile(
    r'(?:Intel\s+)?CPU\s+(?:Core\s+)?'
    r'((?:i[3579]-\d{4,5}[A-Z]{0,3}[\s/]*)+)',
    re.IGNORECASE
)
# Format C — APEX Core Ultra full form (HL/UL two-letter suffix, optional "Processor"):
#   "Intel CPU Core Ultra 7 165HL Core Ultra 5 135HL"
#   "Intel CPU Core Ultra 7 Processor 265H"
RE_CPU_ULTRA_FULL_APEX = re.compile(
    r'Intel\s+CPU\s+Core\s+Ultra\s+(\d)\s+(?:Processor\s+)?(\d{3}[A-Z]{0,3})',
    re.IGNORECASE
)
# Format D — bare short form (no brand prefix, 1-4 SKUs):
#   "Platform CPU 255U 225U 265H"
#   "CPU 155U 125U 165H"   ← ABOX-4140 style
RE_CPU_ULTRA_SHORT = re.compile(
    r'(?:Platform\s+)?CPU\s+((?:\d{3}[A-Z]{0,3}\s*){1,4})',
    re.IGNORECASE
)
# NXP
RE_CPU_NXP = re.compile(
    r'NXP\s+i\.MX\s+[\w\s.]+?(?=Quad|Dual|Octa|\n|$)',
    re.IGNORECASE
)

# CPU TDP
RE_TDP = re.compile(r'\bTDP\s+(\d+)\s*W', re.IGNORECASE)

# Memory capacity
RE_RAM = re.compile(
    r'Max\.\s*Capacity\s+(?:Up\s+to\s+)?(\d+)\s*GB',
    re.IGNORECASE
)

# AI TOPS (NPU or GPU)
RE_TOPS = re.compile(r'(\d+(?:\.\d+)?)\s*TOPS', re.IGNORECASE)

# Storage interfaces
RE_STORAGE = re.compile(
    r'\b(M\.2\s+(?:\d{4}\s+)?[MBE][\s-]?[Kk]ey|SATA\s*(?:III|3\.0|DOM)?|'
    r'NVMe|eMMC|mSATA|CFast)\b',
    re.IGNORECASE
)

# Expansion: PCIe, USB, COM, LAN counts
RE_LAN = re.compile(r'LAN[1-9~\s]*(?:Intel|Marvell|Realtek)[^\n]{0,60}?(\d+(?:\.\d+)?)\s*Gbps', re.IGNORECASE)
RE_USB_GEN2 = re.compile(r'USB\s+3\.2\s+Gen\.?2[^\n]{0,30}?(\d+)', re.IGNORECASE)
RE_COM = re.compile(r'COM(\d+)[\s~]*(?:COM)?(\d+)?', re.IGNORECASE)

# Display outputs
RE_HDMI = re.compile(r'(\d+)\s*x\s*HDMI|HDMI[^\n]{0,20}?(\d+)', re.IGNORECASE)
RE_DP = re.compile(r'(\d+)\s*x\s*DP\+{0,2}|DP\+{0,2}[^\n]{0,20}?(\d+)', re.IGNORECASE)
RE_EDP = re.compile(r'\beDP\b', re.IGNORECASE)

# OS support
RE_OS_WIN = re.compile(r'Windows[®\s]*(?:10|11|IoT)?', re.IGNORECASE)
RE_OS_LINUX = re.compile(r'Linux|Ubuntu\s*\d+\.\d+', re.IGNORECASE)
RE_OS_YOCTO = re.compile(r'Yocto', re.IGNORECASE)
RE_OS_ANDROID = re.compile(r'Android', re.IGNORECASE)

# Certifications
RE_CERT = re.compile(r'\b(CE|FCC|RoHS|UKCA|UL|CB|MIL-STD-\d+)\b')

# Dimensions — old single-group (kept for backward compat)
RE_DIM = re.compile(
    r'(?:Dimension|Size)[^\n]{0,30}?(\d{2,4}(?:\.\d+)?\s*[xX×]\s*\d{2,4}(?:\.\d+)?(?:\s*[xX×]\s*\d{2,4}(?:\.\d+)?)?)\s*mm',
    re.IGNORECASE
)
# Dimensions — three-group for structured parsing
# Handles both "225 x 139 x 44 mm" AND "225mm x 139mm x 44mm" (mm after each number)
RE_DIM3 = re.compile(
    r'(?:Dimension|Size|L\s*[xX×]\s*W\s*[xX×]\s*H)[^\n]{0,50}?'
    r'(\d{2,4}(?:\.\d+)?)\s*(?:mm)?\s*[xX×]\s*'
    r'(\d{2,4}(?:\.\d+)?)\s*(?:mm)?\s*[xX×]\s*'
    r'(\d{2,4}(?:\.\d+)?)\s*mm',
    re.IGNORECASE
)

# Power input
RE_POWER = re.compile(
    r'Power\s+Input\s+Voltage\s+([^\n]{5,60})',
    re.IGNORECASE
)

# OpenVINO
RE_OPENVINO = re.compile(r'OpenVINO', re.IGNORECASE)

# ── v3.0: Memory ─────────────────────────────────────────────────────────────
# Memory type — order matters: check LP variants first (more specific)
RE_MEM_TYPE = re.compile(r'\b(LPDDR5|LPDDR4|DDR5|DDR4)\b', re.IGNORECASE)
# Memory speed — "DDR5-5600" / "DDR5 5600" / "5600 MHz"
RE_MEM_SPEED = re.compile(
    r'(?:LPDDR5|LPDDR4|DDR5|DDR4)[^\n]{0,15}?(\d{4,5})\s*(?:MHz|MT/s)?'
    r'|(\d{4,5})\s*MHz',
    re.IGNORECASE
)
# Physical slot count: "2 x SO-DIMM" / "2 SO-DIMM slots"
# (?<![A-Za-z]) 防止誤抓 "DDR5 SO-DIMM" 中的 "5"
RE_MEM_SLOTS = re.compile(r'(?<![A-Za-z])(\d+)\s*[xX×]?\s*(?:SO-DIMM|DIMM)\b', re.IGNORECASE)
# Max capacity backup pattern
RE_MEM_MAX = re.compile(
    r'(?:Max\.?|Maximum)\s*(?:Memory\s*)?(?:Capacity\s*)?(?:Up\s*to\s*)?(\d+)\s*GB',
    re.IGNORECASE
)

# ── v3.0: PCIe expansion slots (full-size card slots) ────────────────────────
RE_PCIE_SLOT = re.compile(
    r'(\d+)\s*[xX×]\s*PCIe\s+[xX](\d+)(?:\s*Slot)?'
    r'(?:[^\n]{0,25}?Gen\.?\s*(\d))?',
    re.IGNORECASE
)
RE_MINIPCIE = re.compile(r'(\d+)\s*[xX×]\s*Mini[-\s]?PCIe', re.IGNORECASE)

# ── v3.0: M.2 slots ──────────────────────────────────────────────────────────
# Format A: "1 x M.2 B Key 3042 (PCIe x1/SATA)" — count before, size may follow key
# Groups: 1=count, 2=size_before_key, 3=key, 4=size_after_key, 5=interface
RE_M2_SLOT_A = re.compile(
    r'(\d+)\s*[xX×]\s*M\.2\s+'                          # "1 x M.2 "
    r'((?:\d{4,5}(?:[/,]\d{4,5})*)?)\s*'                # optional size(s) before key
    r'([A-Z][+&/A-Z]{0,4})\s*[-\s]?[Kk]ey'             # key type
    r'(?:\s*((?:\d{4,5}(?:[/,]\d{4,5})*)?))?'           # optional size(s) after key (group 4)
    r'(?:\s*\(([^)]{0,80})\))?',                         # optional interface in parens (group 5)
    re.IGNORECASE
)
# Format B: "M.2 2242/3042 B Key 1 (PCIe x1/SATA)" — size before key, count after key
# Count is 1-2 digits only (max 99) to avoid matching M.2 size numbers like 2242
RE_M2_SLOT_B = re.compile(
    r'\bM\.2\s+'
    r'((?:\d{4,5}(?:[/,]\d{4,5})*)?)\s*'                # optional size(s)
    r'([A-Z][+&/A-Z]{0,4})\s*[-\s]?[Kk]ey\s+'          # key type
    r'(\d{1,2})\b'                                       # count: 1-2 digits only
    r'(?:\s*\(([^)]{0,80})\))?',                         # optional interface in parens
    re.IGNORECASE
)
RE_M2_SLOT = RE_M2_SLOT_A   # kept for legacy reference
RE_M2_COUNT = re.compile(r'(\d+)\s*[xX×]\s*M\.2', re.IGNORECASE)

# ── v3.0: USB ports ───────────────────────────────────────────────────────────
# USB version token (reused in two patterns below)
_USB_VER = r'(4|3\.2\s*Gen\.?\s*[12]x?\d?|3\.1\s*Gen\s*[12]|3\.0|2\.0)'
_USB_CONN = r'(?:[^\n]{0,35}?(Type[-\s]?[AC]|Typ[-\s]?[AC]))?'
# Format A: "4 x USB 3.2 Gen.2 (Type-A)"  or  "4 USB 3.2 Gen.2"
RE_USB_PORT = re.compile(
    r'(\d+)\s*(?:[xX×]\s*)?' + r'USB\s+' + _USB_VER + _USB_CONN,
    re.IGNORECASE
)
# Format B: "USB 3.2 Gen.2 (Type A) 4"  or  "USB 2.0 (Type A) 4"
RE_USB_PORT_B = re.compile(
    r'USB\s+' + _USB_VER + r'[^\n]{0,35}?'
    r'(?:' + r'(?:Type[-\s]?[AC]|Typ[-\s]?[AC])' + r'[^\n]{0,20}?)?'
    r'(\d+)\s*$',
    re.IGNORECASE | re.MULTILINE
)

# ── v3.0: GbE ports ───────────────────────────────────────────────────────────
RE_GBE_PORT = re.compile(
    r'(\d+)\s*[xX×]\s*(?:(\d+(?:\.\d+)?)\s*G(?:bE|igabit)|GbE|Gigabit\s*Ethernet)',
    re.IGNORECASE
)
RE_POE = re.compile(r'\bPoE\b', re.IGNORECASE)

# ── v3.0: Serial ports ────────────────────────────────────────────────────────
RE_SERIAL_NX = re.compile(
    r'(\d+)\s*[xX×]\s*((?:RS[-\s]?232(?:/422)?(?:/485)?|COM))',
    re.IGNORECASE
)
RE_COM_RANGE = re.compile(r'COM(\d+)\s*[~\-]\s*(?:COM)?(\d+)', re.IGNORECASE)

# ── v3.0: GPIO / CAN / SIM ────────────────────────────────────────────────────
RE_GPIO_PINS = re.compile(
    r'(\d+)[-\s]?(?:[-\s]bit\s+)?(?:GPIO|Digital\s+I/?O\b|DIO\b)',
    re.IGNORECASE
)
RE_CAN_COUNT = re.compile(r'(\d+)\s*[xX×]\s*CAN', re.IGNORECASE)
RE_SIM_SLOT  = re.compile(r'(\d+)\s*[xX×]\s*(?:nano[-\s]?|micro[-\s]?)?SIM', re.IGNORECASE)

# Connectivity keywords
CONNECTIVITY_KEYWORDS = {
    "GbE":    re.compile(r'\b(?:1000Mbps|GbE|Gigabit\s*Ethernet|2500Mbps|10Gbps)\b', re.IGNORECASE),
    "USB3":   re.compile(r'USB\s*3\.', re.IGNORECASE),
    "HDMI":   re.compile(r'\bHDMI\b', re.IGNORECASE),
    "DP":     re.compile(r'\bDP\+{0,2}\b', re.IGNORECASE),
    "PCIe":   re.compile(r'\bPCIe\b', re.IGNORECASE),
    "CAN":    re.compile(r'\bCANBus\b|\bCAN\s*2\.0\b|\bCAN\s*FD\b', re.IGNORECASE),
    "GPIO":   re.compile(r'\bGPIO\b|\bDIO\b', re.IGNORECASE),
    "RS-232": re.compile(r'\bRS[-\s]?232\b', re.IGNORECASE),
    "RS-485": re.compile(r'\bRS[-\s]?485\b', re.IGNORECASE),
    "RS-422": re.compile(r'\bRS[-\s]?422\b', re.IGNORECASE),
    "MIPI":   re.compile(r'\bMIPI\b|\bCSI\b', re.IGNORECASE),
    "PoE":    re.compile(r'\bPoE\b', re.IGNORECASE),
    "eDP":    re.compile(r'\beDP\b', re.IGNORECASE),
    "M.2":    re.compile(r'\bM\.2\b', re.IGNORECASE),
    "SATA":   re.compile(r'\bSATA\b', re.IGNORECASE),
    "WiFi":   re.compile(r'\bWi[-\s]?Fi\b|\bWLAN\b|\bAX\d{3}\b', re.IGNORECASE),
    "OOB":    re.compile(r'\bInnoAgent\b|\bOOB\b|Out-of-band', re.IGNORECASE),
}

# ── Camera part number (EV* = camera module, EB* = capture card) ─────────────
# NOTE: avoid \b at end — part numbers like EV3F-ZSM1-RXCF-41 end with digits
# followed by '_' (word char), so \b never fires. Use negative lookahead instead.
RE_PART_NO_CAMERA = re.compile(
    r'(?<!\w)(E[VB][0-9A-Z]{1,4}(?:-[A-Z0-9]{2,6}){1,3})(?![A-Z0-9-])'
)

# ── Camera spec patterns ──────────────────────────────────────────────────────
# Resolution: "2 MP" / "2.0 Megapixel" / "1920 x 1080"
RE_CAM_MP   = re.compile(r'(\d+(?:\.\d+)?)\s*M\.?P\.?\b|(\d+(?:\.\d+)?)\s*Mega[-\s]?[Pp]ixels?', re.IGNORECASE)
RE_CAM_PX   = re.compile(r'(\d{3,4})\s*[xX×]\s*(\d{3,4})', re.IGNORECASE)
# FPS — take the maximum
RE_CAM_FPS  = re.compile(r'(?:Up\s+to\s+)?(\d+)\s*(?:fps|FPS|Hz)\b', re.IGNORECASE)
# Sensor
RE_CAM_SENSOR_TYPE = re.compile(r'\b(BSI[\s-]?CMOS|CMOS)\b', re.IGNORECASE)
RE_CAM_SENSOR_SIZE = re.compile(r'1/(\d+(?:\.\d+)?)["\']?\s*(?:inch|")?', re.IGNORECASE)
# FOV — handles "FOV: 90°", "HFOV: 80°", "120° D-FOV", etc.
RE_CAM_FOV  = re.compile(r'(?:[DHV]?[-\s]?FOV|Field\s+of\s+View)[^\n]{0,30}?(\d+)\s*°', re.IGNORECASE)
RE_CAM_FOV2 = re.compile(r'(\d{2,3})\s*°\s*(?:[DHV]?[-\s]?FOV)', re.IGNORECASE)
# Feature flags
RE_CAM_HDR  = re.compile(r'\bHDR\b|\bWDR\b|Wide\s+Dynamic\s+Range', re.IGNORECASE)
RE_CAM_IR   = re.compile(r'\bIR\s*[Cc]ut\b|\bIR\s*[Ff]ilter\b|Night\s+[Vv]ision', re.IGNORECASE)
RE_CAM_LL   = re.compile(r'Low[-\s]?[Ll]ight|[Ss]tarlight|F1\.[0-8]\b', re.IGNORECASE)
# Adapter/platform compatibility
RE_CAM_COMPAT = re.compile(
    r'(?:Compatible\s+with|Works\s+with|Support(?:ed)?\s+(?:Platform|Board)s?)[^\n]{0,120}',
    re.IGNORECASE
)
KNOWN_CAM_BOARDS = [
    "Jetson AGX Orin", "Jetson Orin NX", "Jetson Orin Nano",
    "Jetson AGX Xavier", "Jetson Xavier NX", "Jetson Nano",
    "NVIDIA Jetson", "Raspberry Pi",
    "ASBC", "ABOX", "AXMB",
]

# Application hints from features / product description
APP_KEYWORDS = {
    "manufacturing":    re.compile(r'manufactur|factory|industrial\s+automation|IIoT', re.IGNORECASE),
    "transportation":   re.compile(r'transport|vehicle|railway|fleet|in-vehicle', re.IGNORECASE),
    "medical":          re.compile(r'medical|healthcare|clinical', re.IGNORECASE),
    "surveillance":     re.compile(r'surveillance|security\s+camera|NVR|DVR', re.IGNORECASE),
    "retail":           re.compile(r'retail|kiosk|POS', re.IGNORECASE),
    "AI-inference":     re.compile(r'AI\s+infer|deep\s+learning|neural\s+network|LLM|SLM|TOPS', re.IGNORECASE),
    "edge-AI":          re.compile(r'edge\s*AI|edge\s*computing', re.IGNORECASE),
}


# ── Main extractor ──────────────────────────────────────────────────────────

def _extract_text(pdf_path: str) -> tuple[str, int]:
    """Return full concatenated text and page count."""
    pages_text = []
    with pdfplumber.open(pdf_path) as pdf:
        page_count = len(pdf.pages)
        for page in pdf.pages:
            t = page.extract_text() or ""
            pages_text.append(t)
    return "\n".join(pages_text), page_count


def _first_match(pattern: re.Pattern, text: str, group: int = 1) -> str | None:
    m = pattern.search(text)
    if m:
        try:
            return m.group(group).strip()
        except IndexError:
            return None
    return None


def _all_matches(pattern: re.Pattern, text: str, group: int = 1) -> list[str]:
    return list(dict.fromkeys(
        m.group(group).strip()
        for m in pattern.finditer(text)
        if m.group(group)
    ))


def _parse_temp(text: str) -> tuple[int | None, int | None]:
    """Extract (min_c, max_c) from operating temperature text."""
    # First look for the dedicated row
    m = RE_OP_TEMP.search(text)
    if m:
        return int(m.group(1)), int(m.group(2))
    # Fallback: find lowest min and highest max from any temp range in document
    temps = RE_OP_TEMP_MULTI.findall(text)
    if temps:
        mins = [int(t[0]) for t in temps]
        maxs = [int(t[1]) for t in temps]
        return min(mins), max(maxs)
    return None, None


def _infer_series(model_str: str) -> str | None:
    """Infer processor series name from model number string."""
    s = model_str.upper()
    if re.search(r'ULTRA', s):
        # Core Ultra 200 series = Arrow Lake / Lunar Lake
        # Core Ultra 100 series = Meteor Lake
        nums = re.findall(r'\d{3}', s)
        if nums and int(nums[0]) >= 200:
            return "Arrow Lake"
        return "Meteor Lake"
    if re.search(r'14[0-9]{3}[A-Z]?E?\b', s):
        return "Raptor Lake Refresh"
    if re.search(r'13[0-9]{3}[A-Z]?E?\b', s):
        return "Raptor Lake"
    if re.search(r'12[0-9]{3}[A-Z]?E?\b', s):
        return "Alder Lake"
    if re.search(r'X6[0-9]{3}|J6[0-9]{3}', s):
        return "Elkhart Lake"
    if re.search(r'\bN[0-9]{3,4}\b', s):
        return "Alder Lake-N"
    if re.search(r'I\.MX', s):
        return "i.MX 8M Plus"
    return None


def _parse_cpu(text: str) -> tuple[str | None, str | None]:
    """
    Return (processor_model, processor_series).
    Evaluation order (most-specific first):
      0. NXP
      1. Format C: "Intel CPU Core Ultra 7 [Processor] 265H[L]"  (APEX/AXMB-D style)
      2. Format A: "Intel® Core™ i7-13700E"                      (standard datasheets)
      3. Format B: "[Intel CPU] Core i9-13900E/ i7-13700E"       (APEX multi-slash)
      4. Format D: "[Platform] CPU 155U 125U 165H"               (bare short form)
    """
    # 0. NXP
    nxp = RE_CPU_NXP.search(text)
    if nxp:
        return nxp.group(0).strip().rstrip("/,"), "i.MX 8M Plus"

    # 1. APEX Core Ultra full: "Intel CPU Core Ultra 7 Processor 265H"
    apex_ultra = RE_CPU_ULTRA_FULL_APEX.search(text)
    if apex_ultra:
        tier  = apex_ultra.group(1)   # e.g. "7"
        model = apex_ultra.group(2)   # e.g. "265H" or "165HL"
        raw   = f"Intel Core Ultra {tier} {model}"
        return raw, _infer_series(model)

    # 2. Full Intel name (best quality — has ® or ™)
    full = RE_CPU_INTEL_FULL.search(text)
    if full:
        raw = full.group(0).strip()
        return raw, _infer_series(raw)

    # 3. Multi-SKU slash/space: "[Intel CPU] Core i9-13900E/ i7-13700E"
    multi = RE_CPU_MULTI_SKU.search(text)
    if multi:
        first = re.split(r'[/\s]+', multi.group(1).strip())[0]
        raw = f"Intel Core {first}"
        return raw, _infer_series(first)

    # 4. Bare short form: "CPU 155U 125U" or "Platform CPU 255U 225U 265H"
    ultra = RE_CPU_ULTRA_SHORT.search(text)
    if ultra:
        # Guard: skip if it matched an order-info table row (contains LAN/USB keywords)
        ctx_end = min(ultra.end() + 60, len(text))
        ctx = text[ultra.end():ctx_end]
        if re.search(r'\bLAN\b|\bUSB\b|\bDisplay\b', ctx, re.IGNORECASE):
            return None, None
        first = ultra.group(1).strip().split()[0]
        num_m = re.search(r'\d+', first)
        if not num_m:
            return None, None
        num = int(num_m.group())
        family = "Ultra 9" if num >= 280 else "Ultra 7" if num >= 250 else "Ultra 5"
        raw = f"Intel Core {family} {first}"
        return raw, _infer_series(first)

    return None, None


def _parse_cpu_ipa(text: str) -> tuple[str | None, str | None, int | None]:
    """
    Detect Qualcomm / AMD-Xilinx processor for IPA BU boards.
    Implements CLAUDE.md rules I-2 (Qualcomm), I-4 (AMD-Xilinx), I-7 (cores).
    Returns (processor_model, processor_series, cpu_cores). cpu_p/e_cores are
    always null for these non-hybrid SoCs (handled by caller).
    """
    # ── Qualcomm ─────────────────────────────────────────────────────────────
    if re.search(r'Qualcomm|Snapdragon|Dragonwing|\bQCS\d', text, re.I):
        m = re.search(r'\bQCS(\d{3,4})\b', text)
        if m:
            model, series = f"Qualcomm Dragonwing QCS{m.group(1)}", "Qualcomm Dragonwing"
        else:
            sm = re.search(r'Snapdragon[\w\s\-]+', text, re.I)
            model = _normalize_model(sm.group(0)) if sm else "Qualcomm"
            series = "Snapdragon"
        cores = None
        if re.search(r'Octa[-\s]?core|8x\s*Kryo', text, re.I):
            cores = 8
        elif re.search(r'Hexa[-\s]?core', text, re.I):
            cores = 6
        elif re.search(r'Quad[-\s]?core', text, re.I):
            cores = 4
        return model, series, cores

    # ── AMD-Xilinx ───────────────────────────────────────────────────────────
    if re.search(r'\bKria\b|\bZynq\b|\bVersal\b|\bXilinx\b', text, re.I):
        m = re.search(r'\bKria\s+(K\d{2})\b', text, re.I)
        if m:
            return f"AMD Kria {m.group(1)}", "Kria", 4   # K26 = quad Cortex-A53 (Rule I-7)
        m = re.search(r'\bZynq\s+UltraScale\+?\s*(?:MPSoC\s+)?([A-Z0-9]+)?', text, re.I)
        if m:
            sku = (m.group(1) or "").strip()
            return f"Zynq UltraScale+ {sku}".strip(), "Zynq UltraScale+", None
        m = re.search(r'\bVersal\b[\w\s]*?(VC\d{3,4})', text, re.I)
        if m:
            return f"Versal {m.group(1)}", "Versal", None
        return "AMD-Xilinx FPGA", None, None

    return None, None, None


def _parse_ram_gb(text: str) -> float | None:
    m = RE_RAM.search(text)
    if m:
        return float(m.group(1))
    return None


def _parse_tops(text: str) -> float | None:
    """Return AI TOPS — take highest value found."""
    matches = RE_TOPS.findall(text)
    if matches:
        return max(float(v) for v in matches)
    return None


def _parse_os(text: str) -> list[str]:
    os_list = []
    if RE_OS_WIN.search(text):
        os_list.append("Windows")
    if RE_OS_LINUX.search(text):
        os_list.append("Linux")
    if RE_OS_YOCTO.search(text):
        os_list.append("Yocto")
    if RE_OS_ANDROID.search(text):
        os_list.append("Android")
    return os_list


def _parse_connectivity(text: str) -> list[str]:
    return [label for label, pat in CONNECTIVITY_KEYWORDS.items() if pat.search(text)]


def _parse_display_outputs(text: str) -> list[str]:
    outputs = []
    if RE_HDMI.search(text):
        outputs.append("HDMI")
    if RE_DP.search(text):
        outputs.append("DP")
    if RE_EDP.search(text):
        outputs.append("eDP")
    return outputs


def _parse_storage_interfaces(text: str) -> list[str]:
    raw = _all_matches(RE_STORAGE, text)
    # Normalise
    norm = set()
    for r in raw:
        r_up = r.upper()
        if "M.2" in r_up:
            norm.add("M.2")
        elif "SATA" in r_up:
            norm.add("SATA")
        elif "NVME" in r_up:
            norm.add("NVMe")
        elif "EMMC" in r_up:
            norm.add("eMMC")
        elif "MSATA" in r_up:
            norm.add("mSATA")
        elif "CFAST" in r_up:
            norm.add("CFast")
    return sorted(norm)


def _parse_certs(text: str) -> list[str]:
    return sorted(set(RE_CERT.findall(text)))


def _parse_apps(text: str) -> list[str]:
    return [app for app, pat in APP_KEYWORDS.items() if pat.search(text)]


def _parse_key_features(text: str) -> list[str]:
    """Extract bullet points from FEATURES / HIGHLIGHT FEATURES section."""
    features_block = re.search(
        r'(?:HIGHLIGHT\s+)?FEATURES\s*\n(.*?)(?:SPECIFICATIONS|$)',
        text, re.DOTALL | re.IGNORECASE
    )
    if not features_block:
        return []
    block = features_block.group(1)
    # Bullets: ·  •  ◼  ─ or lines starting with ․ (special dot used by Innodisk)
    bullets = re.findall(r'[·•◼\-․]\s*(.+)', block)
    clean = []
    for b in bullets:
        b = b.strip().lstrip("․·•◼ ")
        # Skip very short, header-like, or truncated lines
        if len(b) < 15:
            continue
        if b.upper() == b:   # ALL CAPS → likely a section header, skip
            continue
        clean.append(b)
    return clean[:6]


# ── CPU Cores Lookup ────────────────────────────────────────────────────────
# Each entry: (compiled_pattern, (total, p_cores, e_cores))  — None = N/A
_CPU_CORES_TABLE = [
    # Intel Classic Core E-series 13th/14th gen
    (re.compile(r'i9-1[34]\d{3}[A-Z]{0,3}E?\b', re.I), (24, 8,  16)),
    (re.compile(r'i7-1[34]700[A-Z]{0,3}E?\b',   re.I), (16, 8,  8 )),
    (re.compile(r'i5-1[34]500[A-Z]{0,3}E?\b',   re.I), (14, 6,  8 )),
    (re.compile(r'i3-1[34]100[A-Z]{0,3}E?\b',   re.I), (4,  4,  0 )),
    # Intel Core Ultra 100 Meteor Lake — H/HL series
    (re.compile(r'Ultra\s+[79]\s+1[5-9][05][HL]{1,2}\b', re.I), (16, 6, 10)),
    (re.compile(r'Ultra\s+5\s+1[1-5][05][HL]{1,2}\b',    re.I), (14, 4, 10)),
    # Intel Core Ultra 100 Meteor Lake — U/UL series
    (re.compile(r'Ultra\s+7\s+1[5-9][05][UL]{1,2}\b', re.I), (12, 2, 10)),
    (re.compile(r'Ultra\s+5\s+1[1-5][05][UL]{1,2}\b',  re.I), (12, 2, 10)),
    # Intel Core Ultra 200 Arrow Lake — H series
    (re.compile(r'Ultra\s+9\s+28[05]H\b',  re.I), (24, 8, 16)),
    (re.compile(r'Ultra\s+7\s+26[05]H\b',  re.I), (20, 8, 12)),
    (re.compile(r'Ultra\s+5\s+24[05]H\b',  re.I), (18, 6, 12)),
    # Intel Core Ultra 200 Arrow Lake — U series
    (re.compile(r'Ultra\s+7\s+25[05]U\b',  re.I), (14, 2, 12)),
    (re.compile(r'Ultra\s+5\s+22[05]U\b',  re.I), (12, 2, 10)),
    # NXP i.MX
    (re.compile(r'i\.MX\s+8M\s+Plus',  re.I), (4, None, None)),
    (re.compile(r'i\.MX\s+8M\s+Nano',  re.I), (4, None, None)),
    (re.compile(r'i\.MX\s+8M\s+Mini',  re.I), (4, None, None)),
]


def _derive_cpu_cores(model: str | None) -> tuple[int | None, int | None, int | None]:
    """
    Return (total_cores, p_cores, e_cores) from processor_model string.
    查詢順序：
      1. 內建 Lookup Table（最快，完全離線）
      2. cpu_library.json（本地 JSON，覆蓋 Elkhart Lake / Alder Lake-N / NXP 等）
    """
    if not model:
        return None, None, None

    # 1. 內建 Lookup Table
    for pat, cores in _CPU_CORES_TABLE:
        if pat.search(model):
            return cores

    # 2. cpu_library.json fallback
    entry = _cpu_lib_lookup(model)
    if entry:
        c = entry.get("cores", {})
        total = c.get("cpu_cores")
        p     = c.get("cpu_p_cores")
        e     = c.get("cpu_e_cores")
        if total is not None:
            return total, p, e

    return None, None, None


# ── v3.0 Parsing functions ───────────────────────────────────────────────────

def _parse_memory_spec(text: str, ram_gb_fallback: float | None = None) -> dict:
    """Extract memory_spec sub-object (type, speed, slots, max capacity, form factor)."""
    # Memory type
    mem_type = None
    m = RE_MEM_TYPE.search(text)
    if m:
        mem_type = m.group(1).upper()   # e.g. "DDR5", "LPDDR4"

    # Speed
    speed_mhz = None
    m = RE_MEM_SPEED.search(text)
    if m:
        raw_speed = m.group(1) or m.group(2)
        if raw_speed:
            speed_mhz = int(raw_speed)

    # Physical slot count
    slots = None
    m = RE_MEM_SLOTS.search(text)
    if m:
        slots = int(m.group(1))
    elif mem_type and mem_type.startswith("LP"):
        slots = 0   # LPDDR = on-board soldered

    # Max capacity (prefer existing ram_gb parse, then backup)
    max_cap = ram_gb_fallback
    if max_cap is None:
        m = RE_MEM_MAX.search(text)
        if m:
            max_cap = float(m.group(1))

    # Form factor inference
    form_factor = None
    if mem_type and mem_type.startswith("LP"):
        form_factor = "on-board"
    elif slots is not None:
        # AXMB industrial motherboards typically use DIMM; others SO-DIMM
        form_factor = "DIMM" if re.search(r'\bDIMM\b', text) and not re.search(r'SO-DIMM', text) else "SO-DIMM"

    return {
        "type":            mem_type,
        "speed_mhz":       speed_mhz,
        "slots":           slots,
        "max_capacity_gb": max_cap,
        "form_factor":     form_factor,
        "ecc_support":     None,
    }


def _parse_dimensions_structured(text: str) -> dict:
    """Extract W×D×H dimensions as structured object (Rule 13)."""
    m = RE_DIM3.search(text)
    if not m:
        return {"width_mm": None, "depth_mm": None, "height_mm": None}
    a, b, c = float(m.group(1)), float(m.group(2)), float(m.group(3))
    # Rule: shorter of first two = width, larger = depth, third = height
    return {
        "width_mm":  min(a, b),
        "depth_mm":  max(a, b),
        "height_mm": c,
    }


def _parse_pcie_slots(text: str) -> list[dict]:
    """Extract full-size PCIe expansion card slots (Rule 14)."""
    slots = []
    seen = set()
    for m in RE_PCIE_SLOT.finditer(text):
        count = int(m.group(1))
        width = f"x{m.group(2)}"
        gen   = int(m.group(3)) if m.group(3) else None
        key   = (width, gen, count)
        if key in seen:
            continue
        seen.add(key)
        # Look for bandwidth-sharing note in surrounding 80 chars
        ctx = text[m.start(): min(m.end() + 80, len(text))]
        note_m = re.search(
            r'electrical\s*[xX]?\d+|shared\s+(?:bandwidth\s+)?with[^\n]{0,30}',
            ctx, re.IGNORECASE
        )
        note = note_m.group(0).strip() if note_m else None
        slots.append({"width": width, "gen": gen, "count": count, "note": note})

    for m in RE_MINIPCIE.finditer(text):
        slots.append({"width": "x1", "gen": None, "count": int(m.group(1)), "note": "Mini-PCIe"})

    return slots


def _normalize_m2_key(raw: str) -> str | None:
    """Normalize M.2 key type to canonical form."""
    k = raw.upper().strip()
    k = re.sub(r'[-\s]?KEY', '', k)
    k = k.replace(" ", "").replace("/", "+").replace("&", "+")
    # Known mappings
    if k in ("BM", "MB"):
        return "B+M"
    if k in ("AE", "EA"):
        return "A+E"
    if k in ("A", "B", "E", "M"):
        return k
    if "B+M" in k or "M+B" in k:
        return "B+M"
    if "A+E" in k or "E+A" in k:
        return "A+E"
    return k if k else None


def _parse_m2_interface(raw: str) -> list[str]:
    """Parse M.2 interface string into normalized list."""
    iface = []
    r = raw.upper()
    pcie_m = re.search(r'PCIE\s*[xX]?\s*(\d+)(?:\s*GEN\.?\s*(\d))?', r)
    if pcie_m:
        lanes = pcie_m.group(1)
        gen   = pcie_m.group(2)
        iface.append(f"PCIe x{lanes} Gen{gen}" if gen else f"PCIe x{lanes}")
    if "SATA" in r:
        iface.append("SATA")
    if "USB" in r:
        iface.append("USB3.0")
    return iface


def _parse_m2_slots(text: str) -> list[dict]:
    """
    Extract M.2 slot specifications (Rule 15).
    Handles two formats:
      A: "1 x M.2 B Key 3042 (PCIe x1/SATA)"  — count before key
      B: "M.2 2242/3042 B Key 1 (PCIe x1/SATA)" — count after key
    """
    slots = []
    seen_spans: list[int] = []

    def _add(count_str, sizes_raw, key_raw, iface_raw, span_start):
        if any(abs(span_start - s) < 5 for s in seen_spans):
            return
        seen_spans.append(span_start)
        count = int(count_str)
        size_nums = re.findall(r'\d{4,5}', sizes_raw or "")
        size = max(size_nums, key=int) if size_nums else None
        key  = _normalize_m2_key(key_raw or "")
        iface = _parse_m2_interface(iface_raw or "")
        if not iface:
            if key == "M":
                iface = ["PCIe x4", "SATA"]
            elif key in ("B", "B+M"):
                iface = ["SATA"]
        slots.append({"size": size, "key": key, "interface": iface, "count": count})

    # Format A: "1 x M.2 [size] KEY [size] (iface)"
    # Prefer pre-key size; fall back to post-key size (groups 2 and 4)
    for m in RE_M2_SLOT_A.finditer(text):
        sizes_raw = m.group(2) or m.group(4) or ""
        _add(m.group(1), sizes_raw, m.group(3), m.group(5), m.start())

    # Format B: "M.2 [size] KEY count (iface)" — only if Format A didn't already claim this span
    for m in RE_M2_SLOT_B.finditer(text):
        if any(abs(m.start() - s) < 5 for s in seen_spans):
            continue
        _add(m.group(3), m.group(1), m.group(2), m.group(4), m.start())

    return slots


def _normalize_usb_standard(raw: str) -> str:
    """Map various USB version strings to canonical standard."""
    # Strip spaces AND periods so "3.2 Gen.2" → "32GEN2", "3.2Gen.2x1" → "32GEN2X1"
    s = raw.upper().replace(" ", "").replace(".", "")
    if s == "4":
        return "USB4"
    if "32GEN2" in s or "31GEN2" in s or s == "10GBPS":
        return "USB3.2 Gen2"
    if "32GEN1" in s or "31GEN1" in s or s in ("30", "5GBPS"):
        return "USB3.2 Gen1"
    return "USB2.0"


def _parse_io_ports(text: str) -> dict:
    """Extract detailed I/O port specifications (Rule 16)."""

    # ── USB ──
    usb_seen: set[tuple] = set()
    usb = []

    def _add_usb(count: int, std_raw: str, conn_raw: str | None):
        std = _normalize_usb_standard(std_raw)
        connector = None
        if conn_raw:
            c = conn_raw.upper()
            connector = "Type-C" if "C" in c else "Type-A"
        key = (std, count, connector)
        if key in usb_seen:
            return
        usb_seen.add(key)
        usb.append({"standard": std, "count": count, "connector": connector})

    # Format A: "4 [x] USB 3.2 Gen.2 [Type-A]"  (count before standard)
    for m in RE_USB_PORT.finditer(text):
        count    = int(m.group(1))
        std_raw  = m.group(2)
        conn_raw = m.group(3) if m.lastindex >= 3 else None
        # Skip matches where count looks like a USB speed number (e.g. "4" from "x4" in PCIe)
        if count > 32:
            continue
        _add_usb(count, std_raw, conn_raw)

    # Format B: "USB 3.2 Gen.2 (Type A) 4"  (count at end of line)
    for m in RE_USB_PORT_B.finditer(text):
        std_raw  = m.group(1)
        count    = int(m.group(2))
        # Detect connector from text between standard and count
        ctx = text[m.start():m.end()]
        conn_raw = None
        conn_m = re.search(r'Type[-\s]?([AC])', ctx, re.I)
        if conn_m:
            conn_raw = "Type-" + conn_m.group(1).upper()
        if count > 32:
            continue
        _add_usb(count, std_raw, conn_raw)

    # ── GbE ──
    gbe = []
    seen_gbe: set[tuple] = set()

    def _add_gbe(count: int, speed: float, poe: bool = False):
        key = (speed, count)
        if key in seen_gbe:
            return
        seen_gbe.add(key)
        gbe.append({"speed_gbps": speed, "count": count, "poe_support": poe})

    for m in RE_GBE_PORT.finditer(text):
        count     = int(m.group(1))
        speed_str = m.group(2)
        speed     = float(speed_str) if speed_str else 1.0
        ctx = text[m.start(): min(m.end() + 80, len(text))]
        _add_gbe(count, speed, bool(RE_POE.search(ctx)))

    # Pattern: "LAN1~2: Intel i226, up to 2500Mbps" — range notation
    lan_range_re = re.compile(
        r'LAN\s*(\d+)\s*[~\-]\s*(?:LAN\s*)?(\d+)[^\n]{0,60}?(\d+(?:\.\d+)?)\s*(?:Gbps|Mbps)',
        re.IGNORECASE
    )
    for m in lan_range_re.finditer(text):
        n1, n2    = int(m.group(1)), int(m.group(2))
        count     = abs(n2 - n1) + 1
        raw_speed = float(m.group(3))
        speed     = raw_speed / 1000 if raw_speed >= 100 else raw_speed   # Mbps → Gbps
        _add_gbe(count, speed)

    # Fallback: text mentions GbE but no "N x" / range pattern found
    if not gbe and CONNECTIVITY_KEYWORDS["GbE"].search(text):
        speed = 2.5 if re.search(r'2\.5\s*G(?:bE|igabit)', text, re.I) else 1.0
        _add_gbe(1, speed)

    # ── Serial ──
    serial = []
    for m in RE_SERIAL_NX.finditer(text):
        count   = int(m.group(1))
        std_raw = m.group(2).upper()
        if "485" in std_raw or "422" in std_raw:
            std = "RS-232/422/485"
        elif "232" in std_raw:
            std = "RS-232"
        else:
            std = "RS-232"   # COM without qualifier → assume RS-232
        ctx  = text[m.start(): min(m.end() + 60, len(text))]
        note = "software selectable" if re.search(r'software\s+selectable', ctx, re.I) else None
        serial.append({"standard": std, "count": count, "note": note})
    # Fallback: "COM1~COM6" / "COM1~2" range notation
    if not serial:
        for m in RE_COM_RANGE.finditer(text):
            n1, n2 = int(m.group(1)), int(m.group(2))
            count  = abs(n2 - n1) + 1
            # Infer RS type from the same line (look forward 60 chars)
            ctx = text[m.start(): min(m.end() + 60, len(text))]
            if re.search(r'RS[-\s]?(?:232|422|485).*RS[-\s]?(?:422|485)', ctx, re.I):
                std = "RS-232/422/485"
            elif re.search(r'RS[-\s]?485', ctx, re.I):
                std = "RS-485"
            elif re.search(r'RS[-\s]?422', ctx, re.I):
                std = "RS-422"
            else:
                std = "RS-232"
            note = "software selectable" if re.search(r'selectable', ctx, re.I) else None
            serial.append({"standard": std, "count": count, "note": note})

    # ── GPIO ──
    gpio_pins = None
    m = RE_GPIO_PINS.search(text)
    if m:
        v = int(m.group(1))
        # Guard: RS-485 contains "485"; realistic GPIO counts are 1–128
        gpio_pins = v if 1 <= v <= 128 else None

    # ── CAN Bus ──
    can_count = None
    m = RE_CAN_COUNT.search(text)
    if m:
        can_count = int(m.group(1))
    elif CONNECTIVITY_KEYWORDS["CAN"].search(text):
        can_count = 1

    # ── SIM Slot ──
    sim_count = None
    m = RE_SIM_SLOT.search(text)
    if m:
        sim_count = int(m.group(1))

    # ── Audio ──
    line_out = 1 if re.search(r'Line[-\s]?Out', text, re.I) else None
    mic_in   = 1 if re.search(r'Mic[-\s]?In|Microphone', text, re.I) else None
    spk_out  = 1 if re.search(r'Speaker\s*Out', text, re.I) else None

    return {
        "usb":            usb,
        "gbe":            gbe,
        "serial":         serial,
        "gpio_pins":      gpio_pins,
        "can_bus_count":  can_count,
        "sim_slot_count": sim_count,
        "audio": {
            "line_out": line_out,
            "mic_in":   mic_in,
            "spk_out":  spk_out,
        },
    }


# ── Camera helpers ─────────────────────────────────────────────────────────

def _is_camera_product(part_no: str) -> bool:
    """Camera modules start with EV, capture cards start with EB."""
    return part_no.startswith(("EV", "EB"))


def _detect_cam_interface(text: str, pdf_path: str) -> str | None:
    """
    Detect camera interface_bus.
    Priority: folder/filename path string → text regex.
    """
    p = pdf_path.upper().replace("\\", "/")
    if "GMSL2" in p or "GMSL 2" in p:
        return "GMSL2"
    if "MIPI OVER TYPE-C" in p or "TYPE-C" in p or "TYPEC" in p:
        return "MIPI-TypeC"
    if "MIPI CSI" in p or "MIPI-CSI" in p:
        return "MIPI-CSI2"
    if "USB 2.0" in p or "USB2.0" in p:
        return "USB2.0"
    if "USB 3" in p or "USB3" in p:
        return "USB3.0"
    if "CAPTURE CARD" in p:
        return "PCIe"   # capture cards are PCIe-based

    # Text fallback
    if re.search(r'\bGMSL[-\s]?2\b', text, re.I):
        return "GMSL2"
    if re.search(r'MIPI.*Type[-\s]?C|Type[-\s]?C.*MIPI', text, re.I):
        return "MIPI-TypeC"
    if re.search(r'\bMIPI\b|\bCSI[-\s]?2\b', text, re.I):
        return "MIPI-CSI2"
    if re.search(r'\bUSB\s*3\b', text, re.I):
        return "USB3.0"
    if re.search(r'\bUSB\s*2\.0\b', text, re.I):
        return "USB2.0"
    return None


def _parse_camera_spec(text: str, pdf_path: str) -> dict:
    """Extract camera_spec fields from PDF text (Rule set: CAM-2 through CAM-7)."""
    interface_bus = _detect_cam_interface(text, pdf_path)

    # ── Resolution MP ──
    resolution_mp = None
    m = RE_CAM_MP.search(text)
    if m:
        val = m.group(1) or m.group(2)
        try:
            resolution_mp = float(val)
        except (TypeError, ValueError):
            pass

    # ── Resolution pixels (find largest px pair) ──
    resolution_px = None
    px_matches = RE_CAM_PX.findall(text)
    if px_matches:
        # Filter out obvious non-resolution numbers (timestamps, part_no components)
        valid = [(int(a), int(b)) for a, b in px_matches
                 if 320 <= int(a) <= 8000 and 200 <= int(b) <= 6000]
        if valid:
            best = max(valid, key=lambda r: r[0] * r[1])
            resolution_px = f"{best[0]}x{best[1]}"
            if resolution_mp is None:
                resolution_mp = round(best[0] * best[1] / 1_000_000, 1)

    # ── FPS — take maximum ──
    fps = None
    fps_vals = RE_CAM_FPS.findall(text)
    if fps_vals:
        candidates = [int(v) for v in fps_vals if 1 <= int(v) <= 960]
        fps = max(candidates) if candidates else None

    # ── Sensor type ──
    sensor_type = None
    m = RE_CAM_SENSOR_TYPE.search(text)
    if m:
        sensor_type = "BSI" if "BSI" in m.group(1).upper() else "CMOS"

    # ── Sensor size ──
    sensor_size = None
    m = RE_CAM_SENSOR_SIZE.search(text)
    if m:
        sensor_size = f"1/{m.group(1)}inch"

    # ── FOV ──
    fov = None
    m = RE_CAM_FOV.search(text)
    if not m:
        m = RE_CAM_FOV2.search(text)
    if m:
        try:
            fov = int(m.group(1))
        except (TypeError, ValueError):
            pass

    # ── Feature flags ──
    hdr      = bool(RE_CAM_HDR.search(text))
    ir_filter = bool(RE_CAM_IR.search(text))
    low_light = bool(RE_CAM_LL.search(text))

    # ── Adapter board compatibility ──
    adapter_boards: list[str] = []
    for m_compat in RE_CAM_COMPAT.finditer(text):
        ctx = m_compat.group(0)
        for board in KNOWN_CAM_BOARDS:
            if re.search(re.escape(board), ctx, re.I) and board not in adapter_boards:
                adapter_boards.append(board)

    return {
        "interface_bus":            interface_bus,
        "resolution_mp":            resolution_mp,
        "resolution_px":            resolution_px,
        "fps":                      fps,
        "sensor_type":              sensor_type,
        "sensor_size":              sensor_size,
        "hdr":                      hdr,
        "low_light":                low_light,
        "lens_fov_deg":             fov,
        "ir_filter":                ir_filter,
        "adapter_board_compatible": adapter_boards,
    }


def _score_completeness_camera(result: dict) -> float:
    """0.0–1.0 confidence score for camera products."""
    cam = result.get("camera_spec") or {}
    fields = {
        "part_no":       result.get("part_no") not in (None, "UNKNOWN"),
        "interface_bus": cam.get("interface_bus") is not None,
        "resolution":    cam.get("resolution_mp") is not None or cam.get("resolution_px") is not None,
        "fps":           cam.get("fps") is not None,
        "op_temp":       result.get("op_temp_min_c") is not None,
        "certs":         bool(result.get("certifications")),
    }
    return sum(1 for v in fields.values() if v) / len(fields)


def _score_completeness(result: dict) -> float:
    """0.0–1.0 confidence score based on how many key fields are populated."""
    key_fields = [
        "part_no", "processor_model", "op_temp_min_c", "op_temp_max_c",
        "os_support", "connectivity", "certifications",
    ]
    filled = sum(1 for f in key_fields if result.get(f))
    # Bonus weight for new v3.0 structured fields
    ms = result.get("memory_spec") or {}
    if ms.get("type"):
        filled += 0.5
    if result.get("m2_slots"):
        filled += 0.5
    if result.get("io_ports", {}).get("gbe"):
        filled += 0.25
    total_weight = len(key_fields) + 1.25
    return min(filled / total_weight, 1.0)


# ── IPA EP module extraction: I/O, Networking, Air Sensor ────────────────────

def _folder_product_line(pdf_path: str) -> str | None:
    """
    Infer product_line from the datasheet folder. The EP module part-number
    prefix (E + form-factor char) cannot separate io vs networking vs air_sensor
    — e.g. EGPL (LAN card) and EGPS (storage card) share 'EG' — so the folder,
    which the user organizes by product line, is the authoritative signal.
    """
    p = pdf_path.replace("/", "\\").lower()
    if "\\networking\\" in p:
        return "networking"
    if "\\io modules\\" in p or "\\io module\\" in p:
        return "io"
    if "\\air sensor\\" in p:
        return "air_sensor"
    return None


def _parse_host_iface(text: str) -> tuple[str | None, str | None, int | None]:
    """Return (host_interface, pcie_gen, pcie_lanes) for an expansion module."""
    low = text.lower()
    host = gen = None
    lanes = None
    if re.search(r'pci\s*express|\bpcie\b', low):
        host = "PCIe"
        g = re.search(r'(?:pcie\s*)?gen\s*([3-5])|pcie\s*([3-5])\.0', low)
        if g:
            gen = "Gen" + (g.group(1) or g.group(2))
        l = re.search(r'\bx\s*(1|2|4|8|16)\b', low)
        if l:
            lanes = int(l.group(1))
    elif re.search(r'\bm\.?2\b', low):
        host = "M.2"
    elif re.search(r'\busb\b', low):
        host = "USB"
    return host, gen, lanes


def _parse_io_spec(text: str) -> dict:
    """Best-effort io_spec extraction (subcategory, host iface, ports)."""
    low = text.lower()
    sub = None
    if re.search(r'storage expander|\braid\b|jbod', low):
        sub = "Storage"
    elif re.search(r'disk array|\bhba\b', low):
        sub = "DiskArray"
    elif re.search(r'display adapter|hdmi output|gpu-?less display', low):
        sub = "Display"
    elif re.search(r'out-?of-?band|\boob\b|\bipmi\b|\bbmc\b', low):
        sub = "OOB"
    elif re.search(r'innoex|virtual\s*i/?o|sr-?iov', low):
        sub = "InnoEx-VirtualIO"
    elif re.search(r'testing|diagnostic|signal generator', low):
        sub = "TestingTool"

    host, gen, lanes = _parse_host_iface(text)

    port_type = []
    for pat, label in (
        (r'\bsata\b', "SATA"), (r'\bnvme\b', "NVMe"), (r'\bhdmi\b', "HDMI"),
        (r'displayport|\bdp\b', "DP"), (r'\busb\b', "USB"),
        (r'\b(?:gbe|rj45|ethernet)\b', "GbE"), (r'\bm\.?2\b', "M.2"),
    ):
        if re.search(pat, low) and label not in port_type:
            port_type.append(label)

    display_output = bool(re.search(r'\bhdmi\b|displayport|\bdp\b|display output', low))
    driver_required = not bool(re.search(r'driver-?less|no driver required', low))
    return {
        "subcategory":     sub,
        "host_interface":  host,
        "pcie_gen":        gen,
        "pcie_lanes":      lanes,
        "port_type":       port_type,
        "port_count":      None,
        "supported_os":    _parse_os(text),
        "driver_required": driver_required,
        "display_output":  display_output,
    }


def _parse_networking_spec(text: str) -> dict:
    """Best-effort networking_spec extraction (LAN/CAN/Serial/PoE)."""
    low = text.lower()
    sub = None
    if re.search(r'power over ethernet|\bpoe\b', low):
        sub = "PoE"
    elif re.search(r'can\s*fd|can\s*bus|can\s*2\.0', low):
        sub = "CAN-Bus"
    elif re.search(r'rs-?232|rs-?422|rs-?485|\bserial\b|\bcom port', low):
        sub = "Serial"
    elif re.search(r'\blan\b|\bgbe\b|ethernet|\bnic\b', low):
        sub = "LAN"

    host, gen, _ = _parse_host_iface(text)

    speed = None
    for pat, val in (
        (r'100\s*gbe', 100), (r'25\s*gbe', 25), (r'10\s*gbe|10\s*g\b|10000\s*mbps', 10),
        (r'2\.5\s*gbe|2500\s*mbps', 2.5), (r'\b1\s*gbe|gigabit|1000\s*mbps', 1),
    ):
        if re.search(pat, low):
            speed = val
            break

    protocol = []
    if re.search(r'rs-?232/?-?422/?-?485|software selectable', low):
        protocol = ["RS-232", "RS-422", "RS-485"]
    else:
        if re.search(r'rs-?232', low):
            protocol.append("RS-232")
        if re.search(r'rs-?422', low):
            protocol.append("RS-422")
        if re.search(r'rs-?485', low):
            protocol.append("RS-485")

    poe_watt = None
    if re.search(r'802\.3bt|poe\+\+|\b90\s*w|\b60\s*w', low):
        poe_watt = 90 if re.search(r'\b90\s*w', low) else 60
    elif re.search(r'802\.3at|poe\+|\b30\s*w', low):
        poe_watt = 30
    elif re.search(r'802\.3af|\b15\.4\s*w|\b15\s*w', low):
        poe_watt = 15
    elif sub == "PoE":
        poe_watt = 15  # conservative default

    can_fd = bool(re.search(r'can\s*fd|iso\s*11898-1:2015|flexible data rate', low))
    isolation = bool(re.search(r'galvanic isolation|isolated|\d+\s*v\s*isolation', low))
    return {
        "subcategory":    sub,
        "host_interface": host,
        "pcie_gen":       gen,
        "port_count":     None,
        "speed_gbps":     speed,
        "protocol":       protocol,
        "poe_watt":       poe_watt,
        "can_fd_support": can_fd,
        "isolation":      isolation,
    }


# Pollutant keyword → canonical label
_POLLUTANT_MAP = [
    (r'pm\s*2\.5|pm2\.5', "PM2.5"), (r'pm\s*10|pm10', "PM10"),
    (r'\bco2\b|carbon dioxide', "CO2"),
    (r'\bco\b|carbon monoxide', "CO"), (r'\bvoc\b|tvoc|volatile organic', "VOC"),
    (r'\bno2\b|nitrogen dioxide', "NO2"), (r'\bso2\b|sulfur dioxide', "SO2"),
    (r'\bo3\b|ozone', "O3"), (r'hcho|formaldehyde', "HCHO"),
    (r'humidity', "Humidity"), (r'temperature', "Temp"),
]


def _parse_air_sensor_spec(text: str) -> dict:
    """Best-effort air_sensor_spec extraction (pollutants, interface, accuracy)."""
    low = text.lower()
    pollutants = []
    for pat, label in _POLLUTANT_MAP:
        if re.search(pat, low) and label not in pollutants:
            pollutants.append(label)

    iface = None
    if re.search(r'\bi2c\b', low):
        iface = "I2C"
    elif re.search(r'\buart\b', low):
        iface = "UART"
    elif re.search(r'\busb\b', low):
        iface = "USB"

    rng_m = re.search(r'(?:measurement|measuring)\s*range[:\s]*([^\n]{1,40})', text, re.I)
    measurement_range = rng_m.group(1).strip() if rng_m else None

    resp_m = re.search(r'response time[:\s]*(?:t90\s*)?[<≤]?\s*(\d+)\s*s', low)
    response_time = int(resp_m.group(1)) if resp_m else None

    icap = bool(re.search(r'icap|innodisk cloud', low))
    return {
        "detected_pollutants": pollutants,
        "interface_bus":       iface,
        "accuracy_pm25_ug":    None,
        "measurement_range":   measurement_range,
        "response_time_s":     response_time,
        "sdk_support":         ["iCAP"] if icap else [],
        "icap_compatible":     icap,
    }


def _score_completeness_module(result: dict, product_line: str) -> float:
    """0.0–1.0 confidence score for I/O / Networking / Air Sensor modules."""
    spec = result.get(f"{product_line}_spec") if product_line != "air_sensor" \
        else result.get("air_sensor_spec")
    spec = spec or {}
    checks = [result.get("part_no") not in (None, "UNKNOWN")]
    if product_line == "io":
        checks += [bool(spec.get("subcategory")), bool(spec.get("host_interface")),
                   bool(spec.get("port_type"))]
    elif product_line == "networking":
        checks += [bool(spec.get("subcategory")), spec.get("speed_gbps") is not None,
                   bool(spec.get("host_interface"))]
    else:  # air_sensor
        checks += [bool(spec.get("detected_pollutants")), bool(spec.get("interface_bus"))]
    checks += [bool(result.get("certifications")), result.get("op_temp_min_c") is not None]
    return sum(1 for c in checks if c) / len(checks)


def _extract_module(text: str, pdf_path: str, part_no: str, product_line: str) -> dict:
    """Extraction path for IPA EP modules: io / networking / air_sensor."""
    op_min, op_max = _parse_temp(text)
    result = {
        "part_no":             part_no,
        "product_name":        part_no,
        "op_temp_min_c":       op_min,
        "op_temp_max_c":       op_max,
        "temp_grade":          None,
        "certifications":      _parse_certs(text),
        "target_applications": _parse_apps(text),
        "key_features":        _parse_key_features(text),
    }
    if product_line == "io":
        result["io_spec"] = _parse_io_spec(text)
    elif product_line == "networking":
        result["networking_spec"] = _parse_networking_spec(text)
    elif product_line == "air_sensor":
        result["air_sensor_spec"] = _parse_air_sensor_spec(text)

    result["_confidence"] = _score_completeness_module(result, product_line)
    result["_method"]     = f"rule_based_{product_line}"
    return result


# ── Public API ──────────────────────────────────────────────────────────────

def extract(pdf_path: str) -> dict:
    """
    Rule-based extraction from a PDF.
    Returns a dict in the same shape as vision_extractor.extract().
    Includes a '_confidence' key (0.0–1.0) for the pipeline to decide fallback.

    Routing:
      - EV* / EB* part numbers           → camera extraction path
      - EGPC/FARO/GADN, IAG*, EP I/O      → module path (networking / air_sensor / io)
      - All others                        → computing (AIoT/IPA) extraction path
    """
    text, page_count = _extract_text(pdf_path)

    # ── Part number detection: AIoT → IPA (EX*) → EP modules → camera ──────────
    part_no = "UNKNOWN"
    for rx in (RE_PART_NO, RE_PART_NO_IPA, RE_PART_NO_NET,
               RE_PART_NO_SENSOR, RE_PART_NO_IO, RE_PART_NO_CAMERA):
        m = rx.search(text)
        if m:
            part_no = m.group(1)
            break

    # ── For camera products: prefer filename stem as part_no (most reliable) ──
    # Filenames follow convention "{PART_NO}_{rest}.pdf" — e.g. "EV3F-ZSM1-RXCF-41_Datasheet..."
    # PDF text often uses a shortened variant without the SKU suffix (-41).
    if _is_camera_product(part_no) or _is_camera_product(Path(pdf_path).stem.split('_')[0]):
        filename_pn = Path(pdf_path).stem.split('_')[0].strip()   # "EV3F-ZSM1-RXCF-41"
        if _is_camera_product(filename_pn) and len(filename_pn) >= len(part_no):
            part_no = filename_pn

    # ── Route camera products ──────────────────────────────────────────────────
    if _is_camera_product(part_no):
        cam_spec = _parse_camera_spec(text, pdf_path)
        op_temp_min_c, op_temp_max_c = _parse_temp(text)

        # Product name: "Camera Module {part_no}" or "Capture Card {part_no}"
        if "CAPTURE CARD" in pdf_path.upper():
            product_name = f"Capture Card {part_no}"
        else:
            product_name = f"Camera Module {part_no}"

        result = {
            "part_no":             part_no,
            "product_name":        product_name,
            "camera_spec":         cam_spec,
            "op_temp_min_c":       op_temp_min_c,
            "op_temp_max_c":       op_temp_max_c,
            "temp_grade":          None,
            "certifications":      _parse_certs(text),
            "target_applications": _parse_apps(text),
            "key_features":        _parse_key_features(text),
        }
        result["_confidence"] = _score_completeness_camera(result)
        result["_page_count"]  = page_count
        result["_method"]      = "rule_based_camera"
        return result

    # ── Route IPA EP modules (I/O / Networking / Air Sensor) ──────────────────
    # Folder is authoritative (prefix can't separate io/networking); fall back
    # to the part-no rule when scanning outside the known module folders.
    folder_pl = _folder_product_line(pdf_path)
    module_pl = folder_pl if folder_pl in ("io", "networking", "air_sensor") \
        else classify_by_rule(part_no).get("product_line")
    if module_pl in ("io", "networking", "air_sensor"):
        # Filename stem "{PART_NO}_Datasheet.pdf" is the most reliable part_no
        stem = Path(pdf_path).stem.split('_')[0].strip()
        sourcing = "in-house"
        subcat_hint = None
        source_vendor = None
        # Subsidiary / OEM part numbers that don't follow the E-code scheme.
        if _RE_PN_INNOEX.match(stem):
            part_no, sourcing, subcat_hint = _RE_PN_INNOEX.match(stem).group(1), "subsidiary", "Virtual IO"
            source_vendor = "Millitronic"        # 巽晨國際 (resale)
        elif _RE_PN_ANNA.match(stem):
            part_no, sourcing, subcat_hint = _RE_PN_ANNA.match(stem).group(1), "subsidiary", "GNSS"
            source_vendor = "Antzertech"          # 安捷科 (dissolved subsidiary)
        elif _RE_PN_WIFI.match(stem):
            part_no, sourcing, subcat_hint = _RE_PN_WIFI.match(stem).group(1), "oem", "WiFi"
            source_vendor = None                  # OEM purchase (Intel AX/BE)
        elif re.match(r'^(E[0-9A-Z]{2,3}-|EGPC-|FARO-|GADN-|IAG|ET3-)', stem.upper()) \
                and (part_no == "UNKNOWN" or len(stem) >= len(part_no)):
            part_no = stem
        result = _extract_module(text, pdf_path, part_no, module_pl)
        # Subcategory is unreliable for 3rd-party GNSS/WiFi datasheets — force it.
        spec_key = f"{module_pl}_spec"
        if subcat_hint and spec_key in result:
            result[spec_key]["subcategory"] = subcat_hint
        result["_product_line"] = module_pl
        result["_sourcing"] = sourcing
        result["_source_vendor"] = source_vendor
        result["_page_count"] = page_count
        return result

    # ── Computing (AIoT / IPA) path ────────────────────────────────────────────
    # Existing fields ────────────────────────────────────────────────────────

    ff_match = RE_FORM_FACTOR.search(text)
    form_factor = ff_match.group(0).strip() if ff_match else None

    processor_model, processor_series = _parse_cpu(text)
    # IPA BU fallback: Intel/NXP patterns missed → try Qualcomm / AMD-Xilinx
    ipa_cpu_cores = None
    if processor_model is None:
        processor_model, processor_series, ipa_cpu_cores = _parse_cpu_ipa(text)

    tdp_matches = RE_TDP.findall(text)
    tdp_watt = max(int(v) for v in tdp_matches) if tdp_matches else None

    ram_gb         = _parse_ram_gb(text)
    ai_tops        = _parse_tops(text)
    op_temp_min_c, op_temp_max_c = _parse_temp(text)
    power_input    = _first_match(RE_POWER, text)
    display_outputs     = _parse_display_outputs(text)
    os_support          = _parse_os(text)
    certifications      = _parse_certs(text)
    connectivity        = _parse_connectivity(text)
    storage_interfaces  = _parse_storage_interfaces(text)
    openvino_support    = bool(RE_OPENVINO.search(text))
    target_applications = _parse_apps(text)
    key_features        = _parse_key_features(text)

    product_name_match = re.search(
        r'((?:SBC|Box\s*PC|Small\s*Box\s*PC|Embedded\s*System|'
        r'Industrial\s*(?:Motherboard|Board)|APEX\s*SERIES?)[^\n]{0,40})\n',
        text, re.IGNORECASE
    )
    product_name = product_name_match.group(1).strip() if product_name_match else part_no

    # ── v3.0 new fields ────────────────────────────────────────────────────────
    cpu_cores, cpu_p_cores, cpu_e_cores = _derive_cpu_cores(processor_model)
    # IPA SoCs aren't in the Intel/NXP cores table — use count parsed from datasheet
    if cpu_cores is None and ipa_cpu_cores is not None:
        cpu_cores = ipa_cpu_cores
    memory_spec  = _parse_memory_spec(text, ram_gb_fallback=ram_gb)
    dimensions   = _parse_dimensions_structured(text)
    pcie_slots   = _parse_pcie_slots(text)
    m2_slots     = _parse_m2_slots(text)
    io_ports     = _parse_io_ports(text)

    result = {
        "part_no":            part_no,
        "product_name":       product_name,
        "processor_model":    processor_model,
        "processor_series":   processor_series,
        "cpu_cores":          cpu_cores,
        "cpu_p_cores":        cpu_p_cores,
        "cpu_e_cores":        cpu_e_cores,
        "tdp_watt":           tdp_watt,
        "ai_tops":            ai_tops,
        "ram_gb":             ram_gb,
        "storage_gb":         None,
        "form_factor":        form_factor,
        "os_support":         os_support,
        "sdk":                ["OpenVINO"] if openvino_support else [],
        "openvino_support":   openvino_support if openvino_support else None,
        "connectivity":       connectivity,
        "display_outputs":    display_outputs,
        "storage_interfaces": storage_interfaces,
        "dimensions":         dimensions,
        "power_input":        power_input,
        "memory_spec":        memory_spec,
        "pcie_slots":         pcie_slots,
        "m2_slots":           m2_slots,
        "io_ports":           io_ports,
        "op_temp_min_c":      op_temp_min_c,
        "op_temp_max_c":      op_temp_max_c,
        "temp_grade":         None,   # derived in schema_builder
        "certifications":     certifications,
        "target_applications": target_applications,
        "key_features":       key_features,
    }

    result["_confidence"] = _score_completeness(result)
    result["_page_count"]  = page_count
    result["_method"]      = "rule_based"
    return result
