"""
Claude Vision extractor: converts PDF pages to images and asks Claude
to extract structured computing_spec fields.
"""

import base64
import json
import re
import os
import anthropic
import pymupdf

SYSTEM_PROMPT = """You are a hardware datasheet parser for Innodisk industrial computing products.
Extract structured JSON from the provided datasheet page images.
Return ONLY valid JSON, no markdown fences, no explanation."""

EXTRACTION_PROMPT = """Extract the following fields from this Innodisk product datasheet (schema v3.0).
Return ONLY a valid JSON object with exactly these keys (use null for missing scalar fields,
empty arrays [] for missing array fields):

{
  "product_name": "full product name string",
  "part_no": "model number e.g. ABOX-4020",
  "processor_model": "exact CPU model string",
  "processor_series": "CPU family e.g. Alder Lake-N, Elkhart Lake, Meteor Lake, Arrow Lake",
  "cpu_cores":   <integer or null — total physical cores>,
  "cpu_p_cores": <integer or null — Performance cores, Intel hybrid only; null for NXP/Qualcomm>,
  "cpu_e_cores": <integer or null — Efficiency cores incl. LP-E, Intel hybrid only>,
  "tdp_watt":    <number or null>,
  "ai_tops":     <number or null — take MAXIMUM value if multiple TOPS figures listed>,
  "memory_spec": {
    "type":            "DDR5|DDR4|LPDDR5|LPDDR4|null",
    "speed_mhz":       <integer or null — e.g. 5600 for DDR5-5600>,
    "slots":           <integer or null — physical SO-DIMM/DIMM slot count; 0 for on-board soldered>,
    "max_capacity_gb": <number or null>,
    "form_factor":     "SO-DIMM|DIMM|on-board|null",
    "ecc_support":     <true|false|null>
  },
  "form_factor": "e.g. Box PC, SBC, 3.5\\\" SBC, Mini-ITX, Industrial Motherboard, Embedded System",
  "os_support":  ["Windows", "Linux", "Yocto", "Android"],
  "sdk":         ["OpenVINO", "SNPE", "QNN", "Vitis-AI"],
  "openvino_support": <true|false|null>,
  "dimensions": {
    "width_mm":  <number or null — shorter horizontal dimension>,
    "depth_mm":  <number or null — longer horizontal dimension>,
    "height_mm": <number or null — vertical / thickness>
  },
  "power_input": "power input voltage/connector description or null",
  "pcie_slots": [
    {
      "width": "x1|x4|x8|x16",
      "gen":   <integer or null — PCIe generation: 3|4|5>,
      "count": <integer>,
      "note":  "e.g. electrical x4, shared with x1 slot — or null"
    }
  ],
  "m2_slots": [
    {
      "size":      "2230|2242|2260|2280|22110|3052 — use largest if range given",
      "key":       "A|B|E|M|B+M|A+E",
      "interface": ["PCIe x4 Gen4", "SATA"],
      "count":     <integer>
    }
  ],
  "io_ports": {
    "usb": [
      {
        "standard":  "USB4|USB3.2 Gen2|USB3.2 Gen1|USB2.0",
        "count":     <integer>,
        "connector": "Type-A|Type-C|Internal|null"
      }
    ],
    "gbe": [
      {
        "speed_gbps":  <number — 1|2.5|10>,
        "count":       <integer>,
        "poe_support": <true|false>
      }
    ],
    "serial": [
      {
        "standard": "RS-232|RS-422|RS-485|RS-232/422/485",
        "count":    <integer>,
        "note":     "software selectable — or null"
      }
    ],
    "gpio_pins":      <integer or null>,
    "can_bus_count":  <integer or null>,
    "sim_slot_count": <integer or null>,
    "audio": {
      "line_out": <integer or null>,
      "mic_in":   <integer or null>,
      "spk_out":  <integer or null>
    }
  },
  "display_outputs":    ["HDMI", "DP", "eDP", "VGA"],
  "storage_interfaces": ["M.2", "SATA", "NVMe", "eMMC", "mSATA"],
  "op_temp_min_c": <integer or null>,
  "op_temp_max_c": <integer or null>,
  "temp_grade": "Commercial|Industrial|Wide|Military|null",
  "certifications": ["CE", "FCC", "RoHS", "UKCA"],
  "target_applications": ["manufacturing", "transportation", "medical", "surveillance", "retail", "automation"],
  "key_features": ["short bullet strings — max 6 items"]
}

Extraction rules:
- pcie_slots: full-size PCIe card expansion slots ONLY — do NOT include M.2 slots here
- m2_slots: list every distinct M.2 slot group; if size range (e.g. 2230/2242/2280), use largest ("2280")
- io_ports.usb: one entry per distinct (standard × connector) combination
- io_ports.gbe: one entry per speed tier; if plain "GbE" or "LAN" without speed = 1 Gbps
- io_ports.serial: RS-232/422/485 on same port → standard = "RS-232/422/485", note = "software selectable"
- memory_spec.slots: physical slot count; on-board LPDDR = 0 slots
- ai_tops: if NPU alone + CPU+GPU+NPU total both listed, take the larger (total system AI performance)
- dimensions: width_mm < depth_mm (shorter side = width)
- temp_grade: if not stated, infer from op_temp (0~70 → Commercial; -20~60 or wider → Industrial; -40~85 or wider → Wide)
"""

def _pdf_to_images(pdf_path: str, dpi: int = 150) -> list[bytes]:
    """Convert each PDF page to PNG bytes."""
    doc = pymupdf.open(pdf_path)
    images = []
    mat = pymupdf.Matrix(dpi / 72, dpi / 72)
    for page in doc:
        pix = page.get_pixmap(matrix=mat, alpha=False)
        images.append(pix.tobytes("png"))
    doc.close()
    return images


def _build_image_blocks(images: list[bytes]) -> list[dict]:
    """Build Anthropic content blocks for image pages."""
    blocks = []
    for i, img_bytes in enumerate(images):
        b64 = base64.standard_b64encode(img_bytes).decode()
        blocks.append({
            "type": "text",
            "text": f"--- Page {i+1} ---"
        })
        blocks.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/png",
                "data": b64,
            }
        })
    return blocks


def extract(pdf_path: str, client: anthropic.Anthropic) -> dict:
    """
    Extract computing_spec fields from a PDF using Claude Vision.
    Returns raw extracted dict (not yet mapped to full schema).
    """
    images = _pdf_to_images(pdf_path)
    # Limit to first 6 pages — spec tables are almost always in first 2-3 pages
    images = images[:6]

    content = _build_image_blocks(images)
    content.append({"type": "text", "text": EXTRACTION_PROMPT})

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": content}],
    )

    raw_text = response.content[0].text.strip()

    # Strip markdown fences if Claude adds them despite instructions
    raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
    raw_text = re.sub(r"\s*```$", "", raw_text)

    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        # Return what we have with a parse error flag
        return {"_parse_error": raw_text[:500]}
