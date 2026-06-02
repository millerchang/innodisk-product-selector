"""
Known product catalog: BU ownership, platform, product line mapping.
Derived from datasheet folder analysis + confirmed by Miller.
"""

# Maps part_no prefix/exact → (product_line, bu_owner, platform_brand)
PRODUCT_CATALOG = {
    # ── APEX series ─────────────────────────────────────────────────────────
    "APEX-A100": ("computing_ipa",  "IPA",   "Qualcomm"),

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

# Preliminary products (lifecycle_status → "NRND")
PRELIMINARY_PARTS = {
    "APEX-A100", "APEX-E400", "APEX-S100", "ABOX-V140", "ARAK-4120",
}

def lookup(part_no: str) -> dict:
    """Return catalog metadata for a given part_no."""
    entry = PRODUCT_CATALOG.get(part_no)
    if not entry:
        return {}
    product_line, bu_owner, platform_brand = entry
    return {
        "product_line": product_line,
        "bu_owner": bu_owner if bu_owner != "null" else None,
        "platform_brand": platform_brand,
        "lifecycle_status": "NRND" if part_no in PRELIMINARY_PARTS else "Active",
    }
