"""
Known product catalog: BU ownership, platform, product line mapping.
Derived from datasheet folder analysis + confirmed by Miller.
"""

# Maps part_no prefix/exact → (product_line, bu_owner, platform_brand)
PRODUCT_CATALOG = {
    # ── APEX series ─────────────────────────────────────────────────────────
    "APEX-A100": ("computing_ipa",  "IPA",   "Qualcomm"),

    # ── IPA BU \ EP \ Computing — Qualcomm single boards (COM-HPC Mini) ──────
    "EXEC-Q911": ("computing_ipa",  "IPA",   "Qualcomm"),     # Dragonwing QCS9075
    "EXMP-Q911": ("computing_ipa",  "IPA",   "Qualcomm"),     # Dragonwing QCS9075
    # ── IPA BU \ EP \ Computing — AMD-Xilinx FPGA (Kria K26 SOM) ─────────────
    "EXMU-X261": ("computing_ipa",  "IPA",   "AMD-Xilinx"),   # FPGA Machine Vision Kit
    "EXOU-X261": ("computing_ipa",  "IPA",   "AMD-Xilinx"),   # FPGA Machine Vision Box


    "APEX-E100": ("computing_aiot", "AIoT",  "Intel"),
    "APEX-E400": ("computing_aiot", "AIoT",  "Intel"),
    "APEX-P100": ("computing_aiot", "AIoT",  "Intel"),
    "APEX-P200": ("computing_aiot", "AIoT",  "Intel"),
    "APEX-S100": ("computing_aiot", "AIoT",  "Intel"),
    "APEX-X100": ("computing_aiot", "AIoT",  "Intel"),
    "APEX-X100-Q": ("computing_aiot", "AIoT", "Intel"),   # Qualcomm Cloud AI100 是外購加速卡，整機仍 AIoT 負責
    "APEX-X200": ("computing_aiot", "AIoT",  "Intel"),

    # ── Box PC (ABOX) ────────────────────────────────────────────────────────
    "ABOX-1M80": ("computing_aiot", "AIoT",  "NXP"),
    "ABOX-2020": ("computing_aiot", "AIoT",  "Intel"),
    "ABOX-3020": ("computing_aiot", "AIoT",  "Intel"),
    "ABOX-4020": ("computing_aiot", "AIoT",  "Intel"),
    "ABOX-4021": ("computing_aiot", "AIoT",  "Intel"),
    "ABOX-4120": ("computing_aiot", "AIoT",  "Intel"),
    "ABOX-4130": ("computing_aiot", "AIoT",  "Intel"),
    "ABOX-4140": ("computing_aiot", "AIoT",  "Intel"),
    "ABOX-4150": ("computing_aiot", "AIoT",  "Intel"),
    "ABOX-5020": ("computing_aiot", "AIoT",  "Intel"),
    "ABOX-5021": ("computing_aiot", "AIoT",  "Intel"),
    "ABOX-5120": ("computing_aiot", "AIoT",  "Intel"),
    "ABOX-5130": ("computing_aiot", "AIoT",  "Intel"),
    "ABOX-R020": ("computing_aiot", "AIoT",  "Intel"),
    "ABOX-R030": ("computing_aiot", "AIoT",  "Intel"),
    "ABOX-R040": ("computing_aiot", "AIoT",  "Intel"),
    "ABOX-V140": ("computing_aiot", "AIoT",  "Intel"),

    # ── Embedded System ──────────────────────────────────────────────────────
    "AIPC-4120": ("computing_aiot", "AIoT",  "Intel"),
    "AIPC-4150": ("computing_aiot", "AIoT",  "Intel"),
    "AIPC-6120": ("computing_aiot", "AIoT",  "Intel"),
    "ARAK-1120": ("computing_aiot", "AIoT",  "Intel"),
    "ARAK-2120": ("computing_aiot", "AIoT",  "Intel"),
    "ARAK-4120": ("computing_aiot", "AIoT",  "Intel"),

    # ── Industrial Board (AXMB) ──────────────────────────────────────────────
    "AXMB-1030": ("computing_aiot", "AIoT",  "Intel"),
    "AXMB-1130": ("computing_aiot", "AIoT",  "Intel"),
    "AXMB-1150": ("computing_aiot", "AIoT",  "Intel"),
    "AXMB-3120": ("computing_aiot", "AIoT",  "Intel"),
    "AXMB-3150": ("computing_aiot", "AIoT",  "Intel"),
    "AXMB-5120": ("computing_aiot", "AIoT",  "Intel"),
    "AXMB-D150": ("computing_aiot", "AIoT",  "Intel"),
    "AXMB-D160": ("computing_aiot", "AIoT",  "Intel"),
    "AXMB-L120": ("computing_aiot", "AIoT",  "Intel"),

    # ── SBC (ASBC) ───────────────────────────────────────────────────────────
    "ASBC-2020": ("computing_aiot", "AIoT",  "Intel"),
    "ASBC-2021": ("computing_aiot", "AIoT",  "Intel"),
    "ASBC-3020": ("computing_aiot", "AIoT",  "Intel"),
    "ASBC-3021": ("computing_aiot", "AIoT",  "Intel"),
    "ASBC-3030": ("computing_aiot", "AIoT",  "Intel"),
    "ASBC-3040": ("computing_aiot", "AIoT",  "Intel"),
    "ASBC-3120": ("computing_aiot", "AIoT",  "Intel"),
    "ASBC-3130": ("computing_aiot", "AIoT",  "Intel"),
    "ASBC-3140": ("computing_aiot", "AIoT",  "Intel"),
    "ASBC-3150": ("computing_aiot", "AIoT",  "Intel"),
    "ASBC-3M80": ("computing_aiot", "AIoT",  "NXP"),
    "ASBC-D130": ("computing_aiot", "AIoT",  "Intel"),

    # ── Camera Module — USB 2.0 ─────────────────────────────────────────────
    # bu_owner=None (Camera BU, not IPA/AIoT); platform_brand=None
    "EV2U-LOM1-RHCF": ("camera", None, None),
    "EV2U-RMR1-UMCB": ("camera", None, None),
    "EV2U-RMR2-MMC1": ("camera", None, None),
    "EV2U-SGR1-MMC1": ("camera", None, None),
    "EV2U-SSM1-RLCF": ("camera", None, None),
    "EV8U-LSM1-RLCF": ("camera", None, None),
    "EV8U-LSN1-RSCA": ("camera", None, None),

    # ── Camera Module — MIPI CSI-2 ──────────────────────────────────────────
    "EV2M-CSM1-RHCF": ("camera", None, None),
    "EV2M-OOM1-UHCA": ("camera", None, None),
    "EV2M-ZOM1-GSCV": ("camera", None, None),
    "EV5M-CSM1-RTCF": ("camera", None, None),
    "EV8M-CSM1-RTCF": ("camera", None, None),
    "EV8M-OOM1-RHCF": ("camera", None, None),
    "EVDM-OOM1-RHCF": ("camera", None, None),

    # ── Camera Module — MIPI over Type-C ────────────────────────────────────
    "EV8C-OOM1-RHCF": ("camera", None, None),

    # ── Camera Module — GMSL2 ───────────────────────────────────────────────
    "EV2F-OOM3-RHCF":    ("camera", None, None),
    "EV3F-ZSM1-RXCF-41": ("camera", None, None),
    "EVDF-OOM1-RHCF":    ("camera", None, None),

    # ── Capture Card ────────────────────────────────────────────────────────
    # PCIe-based video capture cards; placed in Camera folder by Camera BU
    "EB022-2M4F": ("camera", None, None),
    "EB120-1S4F": ("camera", None, None),
    "EB120-1S4M": ("camera", None, None),
}

# Preliminary products — new / in-development parts whose datasheet is still
# marked "Preliminary". These get lifecycle_status "Preview" (NOT "NRND";
# NRND means a mature part near end-of-life — the opposite of a new product).
PRELIMINARY_PARTS = {
    "APEX-A100", "APEX-E400", "APEX-S100", "ARAK-4120",
    "EXEC-Q911", "EXMP-Q911",
    # ABOX-V140 removed 2026-06-11 — promoted to Active release (20260608 datasheet)
}

# ── Rule-based classifier ────────────────────────────────────────────────────
# Auto-classify by part-no prefix using the official Innodisk naming rules
# (see ../part_number_rules/*.md). Used as a fallback when PRODUCT_CATALOG has
# no exact entry, so new part numbers don't need manual catalog maintenance.
import re

# EP Platform main-chip code (chars after the dash) → platform_brand
#   first char  X → AMD-Xilinx,  Q → Qualcomm
_EP_PLATFORM_RE = re.compile(r"^EX[A-Z]{2}-([A-Z])", re.IGNORECASE)

# AIoT series: A + 3-letter series code (ABOX/ASBC/ASOM/AXMB/AIPC/APPC/ARAK/APEX/APAC)
_AIOT_RE = re.compile(r"^A[A-Z]{3}-", re.IGNORECASE)

# EP I/O modules: E + form-factor char in {2,3,D,G,H,L,M,S,Y,Z}
_EP_IO_RE = re.compile(r"^E[23DGHLMSYZ]", re.IGNORECASE)

# EP Camera/Vision/Adapter: E + {V (Vision), I (Image sensor), B (Adapter board)}
_EP_CAMERA_RE = re.compile(r"^E[VIB]", re.IGNORECASE)

# Flash (EM BU): D (Disk) + series char in {C,E,G,H,R,S,T,U,V}
_FLASH_RE = re.compile(r"^D[CEGHRSTUV][A-Z0-9]", re.IGNORECASE)


def classify_by_rule(part_no: str) -> dict:
    """
    Classify a part number by prefix rules derived from the official naming
    conventions. Returns the same dict shape as lookup(), or {} if no rule
    matches (caller then falls back to its own default).
    """
    if not part_no:
        return {}
    pn = part_no.strip().upper()

    def _result(product_line, bu_owner, platform_brand):
        return {
            "product_line": product_line,
            "bu_owner": bu_owner,
            "platform_brand": platform_brand,
            "lifecycle_status": "Active",
            "_classified_by": "rule",
        }

    # 1. Networking — Innodisk EGPC cards + Antzertech subsidiary brands
    if pn.startswith(("EGPC-", "FARO-", "GADN-")):
        return _result("networking", "IPA", None)

    # 2. Air Sensor — Innodisk gas modules (IAG*) + iAeris subsidiary (ET3-IAERIS*)
    if pn.startswith("IAG") or pn.startswith("ET3-IAERIS"):
        return _result("air_sensor", "IPA", None)

    # 3. EP Platform (computing_ipa) — brand from main-chip code
    m = _EP_PLATFORM_RE.match(pn)
    if m:
        chip = m.group(1).upper()
        brand = "AMD-Xilinx" if chip == "X" else "Qualcomm" if chip == "Q" else None
        return _result("computing_ipa", "IPA", brand)

    # 4. EP Camera / Vision / Adapter board
    if _EP_CAMERA_RE.match(pn):
        return _result("camera", None, None)

    # 5. EP I/O modules
    if _EP_IO_RE.match(pn):
        return _result("io", "IPA", None)

    # 6. AIoT system boards — Intel/NXP not derivable from part_no (default Intel)
    if _AIOT_RE.match(pn):
        return _result("computing_aiot", "AIoT", None)

    # 7. Flash (EM BU)
    if _FLASH_RE.match(pn):
        return _result("flash", "EM", None)

    return {}


def lookup(part_no: str) -> dict:
    """
    Return catalog metadata for a given part_no.
    Strategy: exact PRODUCT_CATALOG first (hand-verified, highest trust);
    fall back to classify_by_rule() for new/unlisted parts.
    """
    entry = PRODUCT_CATALOG.get(part_no)
    if entry:
        product_line, bu_owner, platform_brand = entry
        return {
            "product_line": product_line,
            "bu_owner": bu_owner if bu_owner != "null" else None,
            "platform_brand": platform_brand,
            "lifecycle_status": "Preview" if part_no in PRELIMINARY_PARTS else "Active",
            "_classified_by": "catalog",
        }

    # No exact entry → try the prefix-rule classifier
    return classify_by_rule(part_no)
