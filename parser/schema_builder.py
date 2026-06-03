"""
Maps raw vision/rule extraction output → spec_matrix.json schema record (v3.0).

v3.0 changes vs v2.0:
  - cpu_p_cores / cpu_e_cores added
  - memory_spec sub-object replaces bare ram_gb (ram_gb kept for filter compat)
  - dimensions object replaces dimensions_mm string
  - pcie_slots array replaces expansion_slots string
  - m2_slots array added
  - io_ports sub-object added
  - connectivity flat list is now AUTO-GENERATED from structured fields
"""

import hashlib
import json
import os
import re
from datetime import date
from pathlib import Path
from product_catalog import lookup

SCHEMA_VERSION = "3.0"

# ── CPU Library integration ──────────────────────────────────────────────────

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
    if not s:
        return ""
    s = re.sub(r"[®™]", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _cpu_lib_lookup(model: str) -> dict:
    """查詢 cpu_library，回傳匹配 entry 或 {}。"""
    if not model:
        return {}
    lib = _load_cpu_library()
    norm = _normalize_model(model)

    if norm in lib:
        return lib[norm]

    aliases = lib.get("_lookup_aliases", {})
    for raw_key in (norm, model):
        if raw_key in aliases:
            return lib.get(aliases[raw_key], {})

    short = re.sub(r"^(Intel\s+(Core\s+|Atom\s+|Celeron\s+)?|NXP\s+)", "", norm, flags=re.I).strip()
    if short:
        for key, entry in lib.items():
            if key.startswith("_"):
                continue
            if short.lower() in key.lower():
                return entry
    return {}


def _enrich_from_cpu_library(raw: dict) -> dict:
    """
    用 cpu_library.json 填補 raw dict 裡缺少的欄位（setdefault 邏輯：
    只補 null/None 值，不覆蓋 PDF 已成功解析到的資料）。

    補充欄位：
      - cpu_cores / cpu_p_cores / cpu_e_cores
      - tdp_watt
      - memory_spec.type / speed_mhz / ecc_support / max_capacity_gb
      - processor_series (若 rule extractor 沒抓到)
      - ai_tops (NPU TOPS，若 library 有且 PDF 沒有)

    _part_no_overrides 優先級最高：
      - 無論 PDF 是否有抓到 processor_model，_part_no_overrides 永遠優先
      - 適用情境：wrong extraction（如 AXMB-1030 誤抓 "Intel Atom i3"）
        或 H suffix 遺漏（APEX-X200 抓到 "Core Ultra 9 285" 但實際是 285H）
    """
    part_no = raw.get("part_no", "")
    lib     = _load_cpu_library()
    overrides = lib.get("_part_no_overrides", {})

    # ── _part_no_overrides：無條件優先 ──────────────────────────────────────
    # 若此 part_no 在 override 表中，強制取代 PDF 抓到的值。
    # 同時 reset 所有由舊錯誤型號衍生的 CPU 欄位，讓 library 重新填入正確數值。
    if part_no in overrides:
        old_model = raw.get("processor_model", "")
        model     = overrides[part_no]
        raw["processor_model"]      = model
        raw["_model_from_override"] = True   # 標記來源，供 debug 用
        # 若原本抓到的型號與 override 不同，清除可能來自錯誤型號的衍生欄位
        if old_model != model:
            for stale_field in ("cpu_cores", "cpu_p_cores", "cpu_e_cores", "tdp_watt"):
                raw[stale_field] = None
    else:
        model = raw.get("processor_model")

    if not model:
        return raw

    entry = _cpu_lib_lookup(model)
    if not entry:
        return raw

    cores_data  = entry.get("cores",  {})
    power_data  = entry.get("power",  {})
    mem_data    = entry.get("memory", {})
    id_data     = entry.get("identity", {})
    ai_data     = entry.get("ai",     {})

    # ── CPU cores ──────────────────────────────────────────────────────────
    if raw.get("cpu_cores") is None and cores_data.get("cpu_cores") is not None:
        raw["cpu_cores"]   = cores_data["cpu_cores"]
        raw["cpu_p_cores"] = cores_data.get("cpu_p_cores")
        raw["cpu_e_cores"] = cores_data.get("cpu_e_cores")

    # ── TDP ────────────────────────────────────────────────────────────────
    if raw.get("tdp_watt") is None and power_data.get("tdp_watt") is not None:
        raw["tdp_watt"] = power_data["tdp_watt"]

    # ── processor_series ───────────────────────────────────────────────────
    if not raw.get("processor_series") and id_data.get("processor_series"):
        raw["processor_series"] = id_data["processor_series"]

    # ── memory_spec (補充 type / speed / ecc) ─────────────────────────────
    ms = raw.get("memory_spec") or {}
    if not ms.get("type") and mem_data.get("type"):
        ms["type"] = mem_data["type"][0] if len(mem_data["type"]) == 1 else mem_data["type"][0]
    if not ms.get("speed_mhz") and mem_data.get("max_speed_mhz"):
        ms["speed_mhz"] = mem_data["max_speed_mhz"]
    if ms.get("ecc_support") is None and mem_data.get("ecc_support") is not None:
        ms["ecc_support"] = mem_data["ecc_support"]
    if not ms.get("max_capacity_gb") and mem_data.get("max_capacity_gb"):
        ms["max_capacity_gb"] = mem_data["max_capacity_gb"]
    if ms:
        raw["memory_spec"] = ms

    # ── AI TOPS (只補 NPU 資料，不覆蓋 PDF 的 TOPS 數值) ──────────────────
    if raw.get("ai_tops") is None and ai_data.get("ai_tops") is not None:
        raw["ai_tops"] = ai_data["ai_tops"]

    return raw


# ── Scalar helpers ───────────────────────────────────────────────────────────

def _md5(path: str) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _infer_temp_grade(raw: dict) -> str | None:
    grade = raw.get("temp_grade")
    if grade and grade not in ("null", "None"):
        return grade
    mn = raw.get("op_temp_min_c")
    mx = raw.get("op_temp_max_c")
    if mn is None or mx is None:
        return None
    if mn <= -40 and mx >= 70:
        return "Wide"
    if mn <= -20 and mx >= 60:
        return "Industrial"
    if mn >= 0 and mx <= 70:
        return "Commercial"
    return "Industrial"


def _clean_list(val) -> list:
    if isinstance(val, list):
        return [v for v in val if v]
    return []


def _int_or_null(val):
    try:
        return int(val) if val is not None else None
    except (ValueError, TypeError):
        return None


def _float_or_null(val):
    try:
        return float(val) if val is not None else None
    except (ValueError, TypeError):
        return None


# ── Sub-object builders ──────────────────────────────────────────────────────

def _build_memory_spec(raw: dict) -> dict:
    """
    Prefer structured memory_spec from extractor; fall back to scalar fields.
    Ensures max_capacity_gb is always populated from ram_gb if available.
    """
    ms = raw.get("memory_spec") or {}
    max_cap = ms.get("max_capacity_gb") or _float_or_null(raw.get("ram_gb"))

    return {
        "type":            ms.get("type"),
        "speed_mhz":       _int_or_null(ms.get("speed_mhz")),
        "slots":           _int_or_null(ms.get("slots")),
        "max_capacity_gb": max_cap,
        "form_factor":     ms.get("form_factor"),
        "ecc_support":     ms.get("ecc_support"),
    }


def _build_dimensions(raw: dict) -> dict:
    """Build structured dimensions object."""
    d = raw.get("dimensions") or {}
    return {
        "width_mm":  _float_or_null(d.get("width_mm")),
        "depth_mm":  _float_or_null(d.get("depth_mm")),
        "height_mm": _float_or_null(d.get("height_mm")),
    }


def _build_pcie_slots(raw: dict) -> list:
    """Validate and clean pcie_slots list."""
    slots = raw.get("pcie_slots") or []
    clean = []
    for s in slots:
        if not isinstance(s, dict):
            continue
        clean.append({
            "width": s.get("width"),
            "gen":   _int_or_null(s.get("gen")),
            "count": _int_or_null(s.get("count")) or 1,
            "note":  s.get("note"),
        })
    return clean


def _build_m2_slots(raw: dict) -> list:
    """Validate and clean m2_slots list."""
    slots = raw.get("m2_slots") or []
    clean = []
    for s in slots:
        if not isinstance(s, dict):
            continue
        iface = s.get("interface")
        if isinstance(iface, str):
            iface = [iface]
        clean.append({
            "size":      s.get("size"),
            "key":       s.get("key"),
            "interface": iface or [],
            "count":     _int_or_null(s.get("count")) or 1,
        })
    return clean


def _build_io_ports(raw: dict) -> dict:
    """Validate and clean io_ports dict."""
    io = raw.get("io_ports") or {}

    def clean_usb(lst):
        out = []
        for u in (lst or []):
            if not isinstance(u, dict):
                continue
            out.append({
                "standard":  u.get("standard"),
                "count":     _int_or_null(u.get("count")) or 1,
                "connector": u.get("connector"),
            })
        return out

    def clean_gbe(lst):
        out = []
        for g in (lst or []):
            if not isinstance(g, dict):
                continue
            out.append({
                "speed_gbps":  _float_or_null(g.get("speed_gbps")) or 1.0,
                "count":       _int_or_null(g.get("count")) or 1,
                "poe_support": bool(g.get("poe_support")),
            })
        return out

    def clean_serial(lst):
        out = []
        for s in (lst or []):
            if not isinstance(s, dict):
                continue
            out.append({
                "standard": s.get("standard"),
                "count":    _int_or_null(s.get("count")) or 1,
                "note":     s.get("note"),
            })
        return out

    audio = io.get("audio") or {}

    return {
        "usb":            clean_usb(io.get("usb")),
        "gbe":            clean_gbe(io.get("gbe")),
        "serial":         clean_serial(io.get("serial")),
        "gpio_pins":      _int_or_null(io.get("gpio_pins")),
        "can_bus_count":  _int_or_null(io.get("can_bus_count")),
        "sim_slot_count": _int_or_null(io.get("sim_slot_count")),
        "audio": {
            "line_out": _int_or_null(audio.get("line_out")),
            "mic_in":   _int_or_null(audio.get("mic_in")),
            "spk_out":  _int_or_null(audio.get("spk_out")),
        },
    }


def _build_connectivity(raw: dict, io_ports: dict, pcie_slots: list, m2_slots: list) -> list[str]:
    """
    Auto-generate the backward-compat flat connectivity list from v3.0 structured fields.
    This is the single source of truth for the flat list — never edit manually.
    """
    conn: set[str] = set()

    # USB
    for u in (io_ports.get("usb") or []):
        std = (u.get("standard") or "").upper()
        if "USB4" in std:
            conn.add("USB4")
        elif "3." in std or "GEN" in std:
            conn.add("USB3")
        else:
            conn.add("USB2")

    # GbE
    for g in (io_ports.get("gbe") or []):
        speed = g.get("speed_gbps", 1)
        conn.add("GbE")
        if speed >= 10:
            conn.add("10GbE")
        elif speed >= 2:
            conn.add("2.5GbE")
        if g.get("poe_support"):
            conn.add("PoE")

    # Serial
    for s in (io_ports.get("serial") or []):
        std = s.get("standard") or ""
        if "485" in std:
            conn.add("RS-485")
        if "422" in std:
            conn.add("RS-422")
        if "232" in std or "COM" in std.upper():
            conn.add("RS-232")

    # GPIO / CAN / SIM
    if io_ports.get("gpio_pins"):
        conn.add("GPIO")
    if io_ports.get("can_bus_count"):
        conn.add("CAN")
    if io_ports.get("sim_slot_count"):
        conn.add("SIM")

    # PCIe expansion slots
    if pcie_slots:
        conn.add("PCIe")

    # M.2 → add to M.2 and also surface PCIe/SATA/NVMe based on interface
    if m2_slots:
        conn.add("M.2")
        for slot in m2_slots:
            for ifc in (slot.get("interface") or []):
                if "PCIE" in ifc.upper():
                    conn.add("PCIe")
                if "SATA" in ifc.upper():
                    conn.add("SATA")
                if "NVME" in ifc.upper():
                    conn.add("NVMe")

    # Display outputs
    for d in (raw.get("display_outputs") or []):
        if d:
            conn.add(d)

    # Pass-through: WiFi, OOB, MIPI, eDP from old flat list (rule extractor detects these)
    passthrough = {"WiFi", "OOB", "MIPI", "eDP", "SATA", "NVMe"}
    for c in (raw.get("connectivity") or []):
        if c in passthrough:
            conn.add(c)

    return sorted(conn)


# ── Text summary builder ─────────────────────────────────────────────────────

def _build_text_summary(raw: dict, part_no: str, platform: str,
                         io_ports: dict, m2_slots: list, pcie_slots: list) -> str:
    """Build rich text_summary for embedding (more detail than v2.0)."""
    parts = [
        f"{part_no} {raw.get('product_name', '')}",
        f"Platform: {platform} {raw.get('processor_model', '')}",
    ]

    # I/O summary
    io_items = []
    for u in (io_ports.get("usb") or []):
        conn = f" {u['connector']}" if u.get("connector") else ""
        io_items.append(f"{u['count']}x {u['standard']}{conn}")
    for g in (io_ports.get("gbe") or []):
        io_items.append(f"{g['count']}x {g['speed_gbps']}GbE")
    for s in (io_ports.get("serial") or []):
        io_items.append(f"{s['count']}x {s['standard']}")
    if io_ports.get("gpio_pins"):
        io_items.append(f"{io_ports['gpio_pins']}-pin GPIO")
    if io_ports.get("can_bus_count"):
        io_items.append(f"{io_ports['can_bus_count']}x CAN Bus")
    if io_items:
        parts.append("I/O: " + ", ".join(io_items))

    # M.2 / PCIe summary
    exp_items = []
    for slot in m2_slots:
        ifc_str = "/".join(slot.get("interface") or [])
        exp_items.append(f"{slot['count']}x M.2 {slot.get('size','')} {slot.get('key','')} ({ifc_str})")
    for slot in pcie_slots:
        note = f" {slot['note']}" if slot.get("note") else ""
        gen  = f" Gen{slot['gen']}" if slot.get("gen") else ""
        exp_items.append(f"{slot['count']}x PCIe {slot['width']}{gen}{note}")
    if exp_items:
        parts.append("Expansion: " + ", ".join(exp_items))

    os_list = _clean_list(raw.get("os_support", []))
    if os_list:
        parts.append(f"OS: {', '.join(os_list)}")

    op_min = raw.get("op_temp_min_c")
    op_max = raw.get("op_temp_max_c")
    if op_min is not None and op_max is not None:
        parts.append(f"Op temp: {op_min}°C ~ {op_max}°C")

    features = _clean_list(raw.get("key_features", []))
    if features:
        parts.append("Features: " + "; ".join(features))

    return " | ".join(parts)


# ── Camera spec builder ──────────────────────────────────────────────────────

def _build_camera_spec(raw: dict) -> dict:
    """Build camera_spec sub-object from raw extractor output."""
    cam = raw.get("camera_spec") or {}
    return {
        "interface_bus":            cam.get("interface_bus"),
        "resolution_mp":            _float_or_null(cam.get("resolution_mp")),
        "resolution_px":            cam.get("resolution_px"),
        "fps":                      _int_or_null(cam.get("fps")),
        "sensor_type":              cam.get("sensor_type"),
        "sensor_size":              cam.get("sensor_size"),
        "hdr":                      bool(cam.get("hdr", False)),
        "low_light":                bool(cam.get("low_light", False)),
        "lens_fov_deg":             _int_or_null(cam.get("lens_fov_deg")),
        "ir_filter":                bool(cam.get("ir_filter", False)),
        "adapter_board_compatible": _clean_list(cam.get("adapter_board_compatible", [])),
    }


def _build_camera_text_summary(raw: dict, part_no: str, cam_spec: dict) -> str:
    """Build text_summary for camera product embedding."""
    parts = [f"{part_no} {raw.get('product_name', '')}"]

    iface = cam_spec.get("interface_bus")
    if iface:
        parts.append(f"Interface: {iface}")

    res_mp = cam_spec.get("resolution_mp")
    res_px = cam_spec.get("resolution_px")
    if res_mp:
        parts.append(f"Resolution: {res_mp} MP{(' (' + res_px + ')') if res_px else ''}")
    elif res_px:
        parts.append(f"Resolution: {res_px}")

    fps = cam_spec.get("fps")
    if fps:
        parts.append(f"Frame rate: {fps} fps")

    sensor_type = cam_spec.get("sensor_type")
    sensor_size = cam_spec.get("sensor_size")
    if sensor_type or sensor_size:
        sensor_str = " ".join(filter(None, [sensor_type, sensor_size]))
        parts.append(f"Sensor: {sensor_str}")

    fov = cam_spec.get("lens_fov_deg")
    if fov:
        parts.append(f"FOV: {fov}°")

    flags = []
    if cam_spec.get("hdr"):
        flags.append("HDR")
    if cam_spec.get("low_light"):
        flags.append("Low-light")
    if cam_spec.get("ir_filter"):
        flags.append("IR-filter")
    if flags:
        parts.append("Features: " + ", ".join(flags))

    compat = cam_spec.get("adapter_board_compatible") or []
    if compat:
        parts.append("Compatible: " + ", ".join(compat))

    op_min = raw.get("op_temp_min_c")
    op_max = raw.get("op_temp_max_c")
    if op_min is not None and op_max is not None:
        parts.append(f"Op temp: {op_min}°C ~ {op_max}°C")

    features = _clean_list(raw.get("key_features", []))
    if features:
        parts.append("Features: " + "; ".join(features))

    return " | ".join(parts)


# ── IPA EP module spec builders: I/O, Networking, Air Sensor ─────────────────

def _build_io_spec(raw: dict) -> dict:
    """Build io_spec sub-object from raw extractor output."""
    s = raw.get("io_spec") or {}
    return {
        "subcategory":     s.get("subcategory"),
        "host_interface":  s.get("host_interface"),
        "pcie_gen":        s.get("pcie_gen"),
        "pcie_lanes":      _int_or_null(s.get("pcie_lanes")),
        "port_type":       _clean_list(s.get("port_type", [])),
        "port_count":      _int_or_null(s.get("port_count")),
        "supported_os":    _clean_list(s.get("supported_os", [])),
        "driver_required": bool(s.get("driver_required", True)),
        "display_output":  bool(s.get("display_output", False)),
    }


def _build_networking_spec(raw: dict) -> dict:
    """Build networking_spec sub-object from raw extractor output."""
    s = raw.get("networking_spec") or {}
    return {
        "subcategory":    s.get("subcategory"),
        "host_interface": s.get("host_interface"),
        "pcie_gen":       s.get("pcie_gen"),
        "port_count":     _int_or_null(s.get("port_count")),
        "speed_gbps":     _float_or_null(s.get("speed_gbps")),
        "protocol":       _clean_list(s.get("protocol", [])),
        "poe_watt":       _int_or_null(s.get("poe_watt")),
        "can_fd_support": bool(s.get("can_fd_support", False)),
        "isolation":      bool(s.get("isolation", False)),
    }


def _build_air_sensor_spec(raw: dict) -> dict:
    """Build air_sensor_spec sub-object from raw extractor output."""
    s = raw.get("air_sensor_spec") or {}
    return {
        "detected_pollutants": _clean_list(s.get("detected_pollutants", [])),
        "interface_bus":       s.get("interface_bus"),
        "accuracy_pm25_ug":    _float_or_null(s.get("accuracy_pm25_ug")),
        "measurement_range":   s.get("measurement_range"),
        "response_time_s":     _int_or_null(s.get("response_time_s")),
        "sdk_support":         _clean_list(s.get("sdk_support", [])),
        "icap_compatible":     bool(s.get("icap_compatible", False)),
    }


_MODULE_SPEC_KEY = {
    "io":          "io_spec",
    "networking":  "networking_spec",
    "air_sensor":  "air_sensor_spec",
}
_MODULE_BUILDER = {
    "io":          _build_io_spec,
    "networking":  _build_networking_spec,
    "air_sensor":  _build_air_sensor_spec,
}


def _build_module_tags(product_line: str, spec: dict, op_min) -> list:
    """searchable_tags for an IPA EP module record."""
    tags = ["industrial", "IPA", product_line]
    if op_min is not None and op_min <= -40:
        tags.append("wide-temp")
    sub = spec.get("subcategory")
    if sub:
        tags.append(sub)
    if product_line == "networking":
        if spec.get("speed_gbps"):
            tags.append(f"{spec['speed_gbps']}GbE")
        if spec.get("poe_watt"):
            tags.append("PoE")
        if spec.get("can_fd_support"):
            tags.append("CAN-FD")
    elif product_line == "io" and spec.get("host_interface"):
        tags.append(spec["host_interface"])
    elif product_line == "air_sensor":
        tags.extend(spec.get("detected_pollutants", []))
    return tags


def _build_module_text_summary(raw: dict, part_no: str, product_line: str, spec: dict) -> str:
    """text_summary for an IPA EP module embedding."""
    name = raw.get("product_name", "")
    head = part_no if not name or name == part_no else f"{part_no} {name}"
    parts = [head.strip()]
    if product_line == "io":
        if spec.get("subcategory"):
            parts.append(f"I/O type: {spec['subcategory']}")
        if spec.get("host_interface"):
            hi = spec["host_interface"]
            if spec.get("pcie_gen"):
                hi += f" {spec['pcie_gen']}"
            parts.append(f"Host: {hi}")
        if spec.get("port_type"):
            parts.append("Ports: " + ", ".join(spec["port_type"]))
    elif product_line == "networking":
        if spec.get("subcategory"):
            parts.append(f"Network type: {spec['subcategory']}")
        if spec.get("speed_gbps"):
            parts.append(f"Speed: {spec['speed_gbps']} Gbps")
        if spec.get("protocol"):
            parts.append("Serial: " + ", ".join(spec["protocol"]))
        if spec.get("poe_watt"):
            parts.append(f"PoE: {spec['poe_watt']}W")
    elif product_line == "air_sensor":
        if spec.get("detected_pollutants"):
            parts.append("Detects: " + ", ".join(spec["detected_pollutants"]))
        if spec.get("interface_bus"):
            parts.append(f"Interface: {spec['interface_bus']}")
        if spec.get("measurement_range"):
            parts.append(f"Range: {spec['measurement_range']}")
    op_min = raw.get("op_temp_min_c")
    op_max = raw.get("op_temp_max_c")
    if op_min is not None and op_max is not None:
        parts.append(f"Op temp: {op_min}°C ~ {op_max}°C")
    features = _clean_list(raw.get("key_features", []))
    if features:
        parts.append("Features: " + "; ".join(features))
    return " | ".join(parts)


# ── Main builder ─────────────────────────────────────────────────────────────

def build_record(pdf_path: str, raw: dict) -> dict:
    """
    Combine catalog metadata + raw extraction into a full schema v3.0 record.

    pdf_path : absolute path to the source PDF
    raw      : dict returned by rule_extractor.extract() or vision_extractor.extract()
    """
    filename = os.path.basename(pdf_path)
    part_no  = raw.get("part_no", "UNKNOWN")

    catalog       = lookup(part_no)
    product_line  = catalog.get("product_line", "computing_aiot")
    bu_owner      = catalog.get("bu_owner")
    platform      = catalog.get("platform_brand") or "Intel"
    lifecycle     = catalog.get("lifecycle_status", "Active")

    op_min = _int_or_null(raw.get("op_temp_min_c"))
    op_max = _int_or_null(raw.get("op_temp_max_c"))

    meta = {
        "part_no":        part_no,
        "product_name":   raw.get("product_name", ""),
        "product_line":   product_line,
        "bu_owner":       bu_owner,
        "source_file":    filename,
        "file_hash_md5":  _md5(pdf_path),
        "schema_version": SCHEMA_VERSION,
        "last_updated":   date.today().isoformat(),
        "embedding_id":   part_no,
    }
    common = {
        "temp_grade":      _infer_temp_grade({**raw, "op_temp_min_c": op_min, "op_temp_max_c": op_max}),
        "op_temp_min_c":   op_min,
        "op_temp_max_c":   op_max,
        "mtbf_hours":      None,
        "warranty_years":  None,
        "certifications":  _clean_list(raw.get("certifications", [])),
        "lifecycle_status": lifecycle,
        "eol_date":        None,
        "moq":             1,
        "lead_time_weeks": None,
    }
    apps = _clean_list(raw.get("target_applications", []))

    # ── Camera product path ────────────────────────────────────────────────────
    if product_line == "camera":
        cam_spec = _build_camera_spec(raw)
        tags = ["camera", "industrial"]
        if op_min is not None and op_min <= -40:
            tags.append("wide-temp")
        cam_iface = cam_spec.get("interface_bus") or ""
        if "MIPI" in cam_iface:
            tags.append("MIPI-CSI")
        if "GMSL" in cam_iface:
            tags.append("GMSL2")
        if cam_spec.get("hdr"):
            tags.append("HDR")
        if cam_spec.get("low_light"):
            tags.append("low-light")

        return {
            "meta":           meta,
            "common":         common,
            "camera_spec":    cam_spec,
            "search": {
                "text_summary":       _build_camera_text_summary(raw, part_no, cam_spec),
                "searchable_tags":    tags,
                "target_applications": apps,
            },
            "poc_sw_suggestions": [],
        }

    # ── IPA EP module path (I/O / Networking / Air Sensor) ─────────────────────
    if product_line in _MODULE_SPEC_KEY:
        spec = _MODULE_BUILDER[product_line](raw)
        return {
            "meta":   meta,
            "common": common,
            _MODULE_SPEC_KEY[product_line]: spec,
            "search": {
                "text_summary":       _build_module_text_summary(raw, part_no, product_line, spec),
                "searchable_tags":    _build_module_tags(product_line, spec, op_min),
                "target_applications": apps,
            },
            "poc_sw_suggestions": [],
        }

    # ── Computing product path (AIoT / IPA) ───────────────────────────────────

    # Enrich raw dict with cpu_library data (fills nulls only, never overwrites PDF data)
    raw = _enrich_from_cpu_library(raw)

    # Build v3.0 structured sub-objects
    memory_spec  = _build_memory_spec(raw)
    dimensions   = _build_dimensions(raw)
    pcie_slots   = _build_pcie_slots(raw)
    m2_slots     = _build_m2_slots(raw)
    io_ports     = _build_io_ports(raw)

    # Auto-generate flat connectivity list from structured data
    connectivity = _build_connectivity(raw, io_ports, pcie_slots, m2_slots)

    # ram_gb = backward-compat shorthand
    ram_gb = memory_spec.get("max_capacity_gb") or _float_or_null(raw.get("ram_gb"))

    # Searchable tags
    tags = ["industrial", "AIoT", platform.lower()]
    if lifecycle == "NRND":
        tags.append("preliminary")
    if raw.get("openvino_support"):
        tags.append("OpenVINO")
    if _float_or_null(raw.get("ai_tops")):
        tags.append("AI-inference")
    if op_min is not None and op_min <= -40:
        tags.append("wide-temp")
    if m2_slots:
        tags.append("M.2")
    if pcie_slots:
        tags.append("PCIe-expansion")

    return {
        "meta":   meta,
        "common": common,
        "computing_spec": {
            # ── Identity
            "bu_owner":         bu_owner,
            "platform_brand":   platform,
            "processor_model":  raw.get("processor_model"),
            "processor_series": raw.get("processor_series"),
            # ── CPU
            "cpu_cores":   _int_or_null(raw.get("cpu_cores")),
            "cpu_p_cores": _int_or_null(raw.get("cpu_p_cores")),
            "cpu_e_cores": _int_or_null(raw.get("cpu_e_cores")),
            # ── Performance
            "tdp_watt": _float_or_null(raw.get("tdp_watt")),
            "ai_tops":  _float_or_null(raw.get("ai_tops")),
            # ── Memory (backward-compat scalar + new sub-object)
            "ram_gb":      ram_gb,
            "memory_spec": memory_spec,
            # ── Storage
            "storage_gb":         None,
            "storage_interfaces": _clean_list(raw.get("storage_interfaces", [])),
            # ── System
            "form_factor":      raw.get("form_factor"),
            "os_support":       _clean_list(raw.get("os_support", [])),
            "sdk":              _clean_list(raw.get("sdk", [])),
            "openvino_support": raw.get("openvino_support"),
            # ── Physical
            "dimensions":  dimensions,
            "power_input": raw.get("power_input"),
            # ── Expansion
            "pcie_slots": pcie_slots,
            "m2_slots":   m2_slots,
            # ── I/O (detailed)
            "io_ports":        io_ports,
            "display_outputs": _clean_list(raw.get("display_outputs", [])),
            # ── Backward-compat flat list (auto-generated)
            "connectivity": connectivity,
        },
        "search": {
            "text_summary": _build_text_summary(
                raw, part_no, platform, io_ports, m2_slots, pcie_slots
            ),
            "searchable_tags":    tags,
            "target_applications": apps,
        },
        "poc_sw_suggestions": [],
    }
