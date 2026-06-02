"""
ark_fetcher.py — CPU Library Builder for Innodisk Product Selector
==================================================================
從 spec_matrix.json 蒐集所有 processor_model → 查詢 Intel ARK (及 NXP 網站)
→ 解析完整規格 → 寫入 output/cpu_library.json

用法：
  python ark_fetcher.py                    # 增量更新（跳過已有且非 needs_verification 的）
  python ark_fetcher.py --force            # 全部重抓（重新驗證所有條目）
  python ark_fetcher.py --model "i7-13700E"  # 單一型號
  python ark_fetcher.py --verify-only      # 只重抓 needs_verification=true 的條目
  python ark_fetcher.py --list             # 列出 library 目前狀態

依賴：
  pip install requests beautifulsoup4
"""

import argparse
import json
import os
import re
import sys
import time
from datetime import date
from pathlib import Path
from typing import Optional

import requests
from bs4 import BeautifulSoup

# ── 路徑設定 ─────────────────────────────────────────────────────────────────

SCRIPT_DIR   = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
SPEC_MATRIX  = PROJECT_ROOT / "output" / "spec_matrix.json"
CPU_LIBRARY  = PROJECT_ROOT / "output" / "cpu_library.json"

# ── HTTP 設定 ─────────────────────────────────────────────────────────────────

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}
SESSION = requests.Session()
SESSION.headers.update(HEADERS)
RATE_LIMIT_SECONDS = 1.2   # 禮貌性延遲，避免被 Intel ARK 封鎖

# ── 正規化工具 ────────────────────────────────────────────────────────────────

def normalize_model(s: str) -> str:
    """移除 ® ™ 符號、多餘空白，用於 library key 比對。"""
    if not s:
        return ""
    s = re.sub(r"[®™]", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def resolve_alias(model: str, library: dict) -> str:
    """將 PDF 抽取出來的原始 model string 對應到 library 標準 key。"""
    norm = normalize_model(model)
    aliases = library.get("_lookup_aliases", {})
    # 直接命中
    if norm in library:
        return norm
    # alias 表命中
    if norm in aliases:
        return aliases[norm]
    # 部分匹配（去除前導 "Intel " "NXP " 後再試）
    short = re.sub(r"^(Intel\s+(Core\s+|Atom\s+|Celeron\s+)?|NXP\s+)", "", norm, flags=re.I).strip()
    for key in library:
        if key.startswith("_"):
            continue
        if short and short.lower() in key.lower():
            return key
    return norm   # 無法解析 → 回傳正規化後的原文


# ── Intel ARK 查詢 ────────────────────────────────────────────────────────────

ARK_SEARCH_URL  = "https://ark.intel.com/libs/apps/intel/arksearch/autocomplete"
ARK_SEARCH_URL2 = "https://ark.intel.com/content/www/us/en/ark/search.html"   # HTML fallback
ARK_PRODUCT_URL = "https://ark.intel.com/content/www/us/en/ark/products/{ark_id}.html"

# 已知 ARK SKU ID 的直接對應表（繞過 autocomplete）
# 適用對象：工業/嵌入式/OEM 型號，autocomplete 無法可靠找到的 CPU
ARK_KNOWN_IDS: dict = {
    "Intel Atom x7213RE":        236966,   # Rugged-Enhanced Elkhart Lake, 2C
    "Intel Celeron 7305E":       227849,   # Alder Lake-P Celeron, 1P+4E
    "Intel Processor U300E":     233393,   # Alder Lake-N Intel Processor (≠ Celeron)
    "Intel Celeron U300E":       233393,   # alias — spec_matrix 有時抽取出 Celeron 品牌
    "Intel Core Ultra X7 358H":  245527,   # X7 tier, confirmed SKU
    "Intel Core i7-1365URE":     235939,   # Raptor Lake U + RE (robotics-enhanced)
    "Intel Core i7-13800HE":     232150,   # Raptor Lake H embedded, high-perf
}

# ARK data-key → cpu_library 欄位的對應表
ARK_FIELD_MAP = {
    # cores
    "NumCores":           ("cores", "cpu_cores",       "int"),
    "NumThreads":         ("cores", "threads",          "int"),
    "PerformanceCores":   ("cores", "cpu_p_cores",      "int"),
    "EfficientCores":     ("cores", "cpu_e_cores",      "int"),
    "CoreCount":          ("cores", "cpu_cores",        "int"),   # fallback
    "MaxTurboFreq":       ("cores", "max_turbo_ghz",    "float"),
    "ProcessorBaseFreq":  ("cores", "base_freq_p_ghz",  "float"),
    # power
    "MaxTDP":             ("power", "tdp_watt",         "float"),
    "ConfigTDPDown":      ("power", "min_assured_watt", "float"),
    "MaxTurboPower":      ("power", "max_turbo_watt",   "float"),
    # memory
    "MemoryTypes":        ("memory", "type",             "list_str"),
    "MaxMemSize":         ("memory", "max_capacity_gb",  "int_gb"),
    "MemoryMaxBandwidth": ("memory", "_bandwidth_raw",   "str"),
    "ECC":                ("memory", "ecc_support",      "bool"),
    "NumMemoryChannels":  ("memory", "channels",         "int"),
    # pcie
    "PcieSupportedConfigs": ("pcie", "configs",          "str"),
    # graphics
    "GraphicsModel":        ("graphics", "model",        "str"),
    "GraphicsMaxFreq":      ("graphics", "max_freq_mhz", "float"),
    "GraphicsMaxDynamicFreq": ("graphics", "max_freq_mhz", "float"),
    "GraphicsNumDisplaysSupported": ("graphics", "display_support", "int"),
    # cache
    "Cache":              ("cache", "_raw",              "str"),
    # identity
    "ProcessorNumber":    ("identity", "_proc_num",      "str"),
    "CodeNameText":       ("identity", "processor_series", "str"),
    "Lithography":        ("identity", "lithography",    "str"),
    "MarketSegment":      ("identity", "market_segment", "str"),
    "SocketsSupported":   ("identity", "socket",         "str"),
    "LaunchDate":         ("identity", "launch_date",    "str"),
}


def _ark_search(query: str) -> Optional[int]:
    """
    搜尋 ARK autocomplete，回傳第一個命中的 ark_id（整數）或 None。
    嘗試順序：
      1. autocomplete API ?q=  (新格式)
      2. autocomplete API ?_=  (舊格式)
      3. HTML search page fallback（從搜尋結果頁解析第一個產品連結）
    """
    # ── 嘗試 1 & 2：autocomplete JSON API ────────────────────────────────────
    for param_name in ("q", "_"):
        try:
            r = SESSION.get(
                ARK_SEARCH_URL,
                params={param_name: query, "locale": "en_US"},
                timeout=10,
            )
            if r.status_code == 200:
                results = r.json()
                if results:
                    return int(results[0]["id"])
        except Exception as e:
            print(f"    [ARK autocomplete error ({param_name}=)] {e}")

    # ── 嘗試 3：HTML search fallback ──────────────────────────────────────────
    try:
        r = SESSION.get(ARK_SEARCH_URL2, params={"q": query}, timeout=15)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, "html.parser")
            # ARK 搜尋結果頁：第一個產品連結通常是 /ark/products/{id}/...
            link = soup.select_one("a[href*='/ark/products/']")
            if link:
                m = re.search(r"/ark/products/(\d+)/", link["href"])
                if m:
                    print(f"    [ARK HTML fallback] found id={m.group(1)}")
                    return int(m.group(1))
    except Exception as e:
        print(f"    [ARK HTML fallback error] {e}")

    return None


def _ark_fetch_page(ark_id: int) -> Optional[BeautifulSoup]:
    """抓取 ARK 產品頁，回傳 BeautifulSoup 或 None。"""
    url = ARK_PRODUCT_URL.format(ark_id=ark_id)
    try:
        r = SESSION.get(url, timeout=15)
        r.raise_for_status()
        return BeautifulSoup(r.text, "html.parser"), url
    except Exception as e:
        print(f"    [ARK page error] ark_id={ark_id}: {e}")
    return None, None


def _parse_ark_page(soup: BeautifulSoup) -> dict:
    """
    解析 ARK 產品頁的所有 spec row。
    ARK 使用 <span class="value" data-key="XXX">value</span> 結構。
    """
    raw = {}
    # 主要 spec items（舊格式）
    for li in soup.select("li.blade-item[data-key]"):
        key = li.get("data-key", "")
        val = li.get("data-value") or li.get_text(strip=True)
        if key and val:
            raw[key] = val

    # 備用：直接抓 span[data-key]（新版 ARK 有時用這個）
    for span in soup.select("span.value[data-key]"):
        key = span.get("data-key", "")
        val = span.get_text(strip=True)
        if key and val and key not in raw:
            raw[key] = val

    # 另一個備用：section div with data-key attr
    for div in soup.select("div[data-key]"):
        key = div.get("data-key", "")
        val = div.get_text(strip=True)
        if key and val and key not in raw:
            raw[key] = val

    return raw


def _convert_value(raw_val: str, vtype: str):
    """將 ARK 原始字串轉換為目標型別。"""
    v = raw_val.strip()

    if vtype == "int":
        m = re.search(r"(\d[\d,]*)", v)
        return int(m.group(1).replace(",", "")) if m else None

    if vtype == "float":
        # GHz 值: "3.20 GHz" → 3.2
        # MHz 值: "1550 MHz" → 1550 (保留)
        # W 值: "65 W" → 65.0
        m = re.search(r"([\d.]+)", v)
        return float(m.group(1)) if m else None

    if vtype == "int_gb":
        # "128 GB" → 128; "16 GB" → 16; 若是 MB → 除以 1024
        m = re.search(r"([\d.]+)\s*(GB|MB|TB)", v, re.I)
        if not m:
            return None
        num, unit = float(m.group(1)), m.group(2).upper()
        if unit == "TB":
            return int(num * 1024)
        if unit == "MB":
            return int(num / 1024)
        return int(num)

    if vtype == "list_str":
        # "DDR4, DDR5" → ["DDR4", "DDR5"]
        # "DDR4-3200, LPDDR4-4266" → ["DDR4", "LPDDR4"]
        parts = re.split(r"[,/]", v)
        result = []
        for p in parts:
            p = p.strip()
            # 取類型前綴（DDR5 from DDR5-5600）
            m = re.match(r"(LPDDR\d+X?|DDR\d+)", p, re.I)
            if m:
                t = m.group(1).upper()
                if t not in result:
                    result.append(t)
        return result if result else [v]

    if vtype == "bool":
        return v.strip().lower() in ("yes", "true", "supported", "✓", "1")

    if vtype == "str":
        return v if v else None

    return v


def _parse_cache(raw_cache: str) -> dict:
    """解析 cache 字串，回傳 {l2_mb, l3_mb}。"""
    result = {"l2_mb": None, "l3_mb": None}
    if not raw_cache:
        return result
    # "L2: 24 MB; L3: 36 MB" or "36 MB Intel Smart Cache"
    l3m = re.search(r"L3[:\s]+([0-9.]+)\s*MB", raw_cache, re.I)
    l2m = re.search(r"L2[:\s]+([0-9.]+)\s*MB", raw_cache, re.I)
    if not l3m:
        # "32 MB Intel Smart Cache" — 若只有一個數字 → 假設 L3
        sm = re.search(r"([0-9.]+)\s*MB", raw_cache, re.I)
        if sm:
            result["l3_mb"] = float(sm.group(1))
    else:
        result["l3_mb"] = float(l3m.group(1))
    if l2m:
        result["l2_mb"] = float(l2m.group(1))
    return result


def _parse_memory_speed(raw_specs: dict) -> Optional[int]:
    """從 MemoryTypes 或 MemoryMaxBandwidth 推斷最大記憶體速度 MHz。"""
    # 嘗試從 MemoryTypes 抓速度（如 "DDR5-5600"）
    mem_types = raw_specs.get("MemoryTypes", "")
    speeds = re.findall(r"(?:DDR\d+|LPDDR\d+)[-\s](\d{4,5})", mem_types)
    if speeds:
        return max(int(s) for s in speeds)
    # 嘗試從其他欄位
    for key in ("MemoryMaxBandwidth", "MaxMemBW"):
        val = raw_specs.get(key, "")
        m = re.search(r"(\d{3,5})\s*(?:MT/s|MHz)", val, re.I)
        if m:
            return int(m.group(1))
    return None


def _build_record_from_ark(model_str: str, ark_id: int, ark_url: str, raw_specs: dict) -> dict:
    """將 ARK raw specs dict 對應到 cpu_library schema。"""
    record = {
        "meta": {
            "ark_id": ark_id,
            "ark_url": ark_url,
            "source": "intel_ark",
            "needs_verification": False,
            "last_fetched": date.today().isoformat(),
        },
        "identity": {
            "processor_model": model_str,
            "processor_series": None,
            "platform_brand": "Intel",
            "launch_date": None,
            "lithography": None,
            "socket": None,
            "market_segment": None,
        },
        "cores": {
            "cpu_cores": None, "cpu_p_cores": None, "cpu_e_cores": None,
            "threads": None,
            "base_freq_p_ghz": None, "base_freq_e_ghz": None,
            "max_turbo_ghz": None,
        },
        "power": {
            "tdp_watt": None, "max_turbo_watt": None, "min_assured_watt": None,
        },
        "memory": {
            "type": [], "max_speed_mhz": None, "max_capacity_gb": None,
            "channels": None, "ecc_support": None,
        },
        "pcie": {
            "revision": None, "max_lanes": None, "configs": None,
        },
        "graphics": {
            "model": None, "eu_count": None, "max_freq_mhz": None, "display_support": None,
        },
        "ai": {
            "ai_tops": None, "npu_model": None,
        },
        "cache": {
            "l2_mb": None, "l3_mb": None,
        },
        "features": [],
    }

    # 套用 ARK_FIELD_MAP
    for ark_key, (section, field, vtype) in ARK_FIELD_MAP.items():
        if ark_key not in raw_specs:
            continue
        val = _convert_value(raw_specs[ark_key], vtype)
        if val is None:
            continue
        # 跳過內部暫存欄位
        if field.startswith("_"):
            record[section][field] = val
        else:
            record[section][field] = val

    # 後處理：cache
    cache_raw = record.get("cache", {}).pop("_raw", None)
    if cache_raw:
        parsed = _parse_cache(cache_raw)
        record["cache"].update(parsed)

    # 後處理：memory speed（從 MemoryTypes 字串推斷）
    if not record["memory"]["max_speed_mhz"]:
        speed = _parse_memory_speed(raw_specs)
        if speed:
            record["memory"]["max_speed_mhz"] = speed

    # 後處理：PCIe revision（從 PcieSupportedConfigs 字串推斷）
    pcie_conf_raw = raw_specs.get("PcieSupportedConfigs", "")
    pcie_rev_m = re.search(r"PCIe\s*([\d.]+)", pcie_conf_raw, re.I)
    if pcie_rev_m and not record["pcie"]["revision"]:
        record["pcie"]["revision"] = pcie_rev_m.group(1)

    # 後處理：processor_series 從 CodeNameText 清理
    code = raw_specs.get("CodeNameText", "")
    if code:
        # 去掉 "Products formerly " 前綴
        code = re.sub(r"^Products\s+formerly\s+", "", code, flags=re.I).strip()
        record["identity"]["processor_series"] = code

    # 後處理：AI/NPU（部分新 ARK 頁面有 NPU TOPS 欄位）
    for npu_key in ("NPUTOPS", "NPUTops", "AIBoost", "IntelAIBoost"):
        if npu_key in raw_specs:
            m = re.search(r"([\d.]+)", raw_specs[npu_key])
            if m:
                record["ai"]["ai_tops"] = float(m.group(1))
                record["ai"]["npu_model"] = "Intel AI Boost NPU"
                break

    # 後處理：移除暫存欄位
    for section in record.values():
        if isinstance(section, dict):
            for k in list(section.keys()):
                if k.startswith("_"):
                    del section[k]

    return record


def fetch_intel(model_str: str) -> Optional[dict]:
    """
    查詢 Intel ARK，回傳 cpu_library record 或 None。
    搜尋策略（三層降級）：
      1. ARK_KNOWN_IDS 直接命中（繞過 autocomplete，適用工業/嵌入式型號）
      2. Autocomplete：移除品牌前綴（含 Core Ultra / Processor / Xeon 等）後搜尋
      3. Fallback A：從 query 抽取核心 model identifier（如 i7-13700E → i7-13700E）
      4. Fallback B：剝除工業後綴（URE→U, HE→H, RE→''）再試
    """
    print(f"  [ARK] Searching: {model_str}")
    norm = normalize_model(model_str)

    # ── 策略 1：已知 ID 直接命中 ────────────────────────────────────────────────
    ark_id = ARK_KNOWN_IDS.get(norm) or ARK_KNOWN_IDS.get(model_str)
    if ark_id:
        print(f"    [ARK] Known ID hit: {ark_id}")
    else:
        # ── 策略 2：Autocomplete（改良版 strip regex）────────────────────────────
        # 移除 "Intel " + 可選品牌前綴（含 Core Ultra, Processor, Xeon, Celeron, Atom）
        query = re.sub(
            r"^Intel\s+(Core\s+Ultra\s+|Core\s+|Atom\s+|Celeron\s+|Processor\s+|Xeon\s+)?",
            "", model_str, flags=re.I
        ).strip()
        ark_id = _ark_search(query)

        if not ark_id:
            # ── Fallback A：抽取核心 model identifier ───────────────────────────
            # 匹配模式：i7-13700E / U300E / X7-358H / 6731P 等
            m = re.search(r"([iCUX]\d[\w-]+|\d{3,5}[A-Z]+[\w-]*)", query)
            if m:
                ark_id = _ark_search(m.group())

        if not ark_id:
            # ── Fallback B：剝除工業/特殊後綴 ───────────────────────────────────
            # URE → U（Raptor Lake URE），HE → H，RE → ''，HL/UL → H/U，TE → E
            last_token = query.split()[-1] if query else ""
            stripped = re.sub(r"(URE|HE|RE|HL|UL|TE)$", "", last_token)
            if stripped and stripped != last_token:
                print(f"    [ARK] Fallback B: trying stripped suffix '{stripped}'")
                ark_id = _ark_search(stripped)

    if not ark_id:
        print(f"    [FAIL] Not found on ARK: {model_str}")
        return None

    time.sleep(RATE_LIMIT_SECONDS)

    result = _ark_fetch_page(ark_id)
    if result[0] is None:
        return None
    soup, ark_url = result

    raw_specs = _parse_ark_page(soup)
    if not raw_specs:
        print(f"    [FAIL] Empty spec page for ark_id={ark_id}")
        return None

    print(f"    [OK] ark_id={ark_id}, {len(raw_specs)} spec fields")
    record = _build_record_from_ark(model_str, ark_id, ark_url, raw_specs)
    return record


# ── NXP 查詢 ──────────────────────────────────────────────────────────────────

NXP_PRODUCT_URLS = {
    "NXP i.MX 8M Plus": (
        "https://www.nxp.com/products/processors-and-microcontrollers/"
        "arm-processors/i-mx-applications-processors/i-mx-8-processors/"
        "i-mx-8m-plus-arm-cortex-a53-machine-learning-vision-multimedia-and-industrial-iot:IMX8MPLUS"
    ),
    "NXP i.MX 8M Nano": (
        "https://www.nxp.com/products/processors-and-microcontrollers/"
        "arm-processors/i-mx-applications-processors/i-mx-8-processors/"
        "i-mx-8m-nano-arm-cortex-a53-cortex-m7-based-processor:IMX8MNANO"
    ),
    "NXP i.MX 8M Mini": (
        "https://www.nxp.com/products/processors-and-microcontrollers/"
        "arm-processors/i-mx-applications-processors/i-mx-8-processors/"
        "i-mx-8m-mini-arm-cortex-a53-cortex-m4-based-processor:IMX8MMINI"
    ),
}


def _parse_nxp_page(soup: BeautifulSoup) -> dict:
    """
    NXP 產品頁 spec 解析。
    NXP 使用多種 HTML 結構：
      1. <div class="product-specs"> 裡的 <ul> list items
      2. <table> 含有 <th>/<td> 的規格表格
      3. <div class="feature-list"> 含有 feature 項目
    回傳 raw dict {field_name: value_str}
    """
    raw = {}

    # ── 方法 1: 規格 list (最常見)
    for ul in soup.select("ul.specs-list, ul.product-specs, div.specs ul"):
        for li in ul.find_all("li"):
            text = li.get_text(" ", strip=True)
            # "Key: Value" 格式
            if ":" in text:
                parts = text.split(":", 1)
                raw[parts[0].strip()] = parts[1].strip()

    # ── 方法 2: 規格表格
    for table in soup.select("table"):
        rows = table.find_all("tr")
        for row in rows:
            th = row.find("th")
            td = row.find("td")
            if th and td:
                raw[th.get_text(strip=True)] = td.get_text(" ", strip=True)

    # ── 方法 3: 從 JSON-LD structured data 抓（NXP 有時嵌入 schema.org）
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            jd = json.loads(script.string)
            if isinstance(jd, dict) and jd.get("@type") in ("Product", "SoftwareApplication"):
                if "description" in jd:
                    raw["_description"] = jd["description"]
        except Exception:
            pass

    # ── 方法 4: feature bullets（一行一個 feature，沒有 key: value 分隔）
    features = []
    for div in soup.select("div.feature-list, section.features, ul.feature-list"):
        for li in div.find_all("li"):
            t = li.get_text(strip=True)
            if t:
                features.append(t)
    if features:
        raw["_features"] = features

    return raw


def _build_record_from_nxp(model_str: str, url: str, raw: dict) -> dict:
    """將 NXP raw dict 對應到 cpu_library schema。"""
    record = {
        "meta": {
            "ark_id": None,
            "ark_url": url,
            "source": "nxp_web",
            "needs_verification": False,
            "last_fetched": date.today().isoformat(),
        },
        "identity": {
            "processor_model": model_str,
            "processor_series": None,
            "platform_brand": "NXP",
            "launch_date": None,
            "lithography": None,
            "socket": "BGA",
            "market_segment": "Embedded/IoT",
        },
        "cores": {
            "cpu_cores": None, "cpu_p_cores": None, "cpu_e_cores": None,
            "threads": None, "base_freq_p_ghz": None, "max_turbo_ghz": None,
        },
        "power": {"tdp_watt": None, "max_turbo_watt": None, "min_assured_watt": None},
        "memory": {"type": [], "max_speed_mhz": None, "max_capacity_gb": None,
                   "channels": None, "ecc_support": False},
        "pcie":    {"revision": None, "max_lanes": None, "configs": None},
        "graphics": {"model": None, "eu_count": None, "max_freq_mhz": None},
        "ai":      {"ai_tops": None, "npu_model": None},
        "cache":   {"l2_mb": None, "l3_mb": None},
        "features": [],
    }

    # 嘗試從 raw 解析關鍵欄位
    for key, val in raw.items():
        kl = key.lower()

        # CPU cores
        if any(x in kl for x in ("core", "processor", "cpu")):
            m = re.search(r"(\d+)[- ]?core", val, re.I)
            if m and not record["cores"]["cpu_cores"]:
                record["cores"]["cpu_cores"] = int(m.group(1))
            m2 = re.search(r"up to\s*([\d.]+)\s*GHz", val, re.I)
            if m2 and not record["cores"]["max_turbo_ghz"]:
                record["cores"]["max_turbo_ghz"] = float(m2.group(1))

        # Memory type & capacity
        if any(x in kl for x in ("memory", "dram", "ram")):
            for mt in ("LPDDR5X", "LPDDR5", "LPDDR4X", "LPDDR4", "DDR4", "DDR5"):
                if mt in val.upper() and mt not in record["memory"]["type"]:
                    record["memory"]["type"].append(mt)
            m = re.search(r"([\d.]+)\s*(?:MT/s|MHz|Mbps)", val)
            if m and not record["memory"]["max_speed_mhz"]:
                record["memory"]["max_speed_mhz"] = int(float(m.group(1)))
            m2 = re.search(r"(\d+)\s*GB", val, re.I)
            if m2 and not record["memory"]["max_capacity_gb"]:
                record["memory"]["max_capacity_gb"] = int(m2.group(1))

        # PCIe
        if "pcie" in kl or "pci express" in kl:
            m = re.search(r"Gen\s*(\d)", val, re.I)
            if m and not record["pcie"]["revision"]:
                record["pcie"]["revision"] = m.group(1) + ".0"
            m2 = re.search(r"x(\d+)", val)
            if m2 and not record["pcie"]["max_lanes"]:
                record["pcie"]["max_lanes"] = int(m2.group(1))

        # AI / NPU
        if any(x in kl for x in ("npu", "ai", "tops", "inference")):
            m = re.search(r"([\d.]+)\s*TOPS", val, re.I)
            if m and not record["ai"]["ai_tops"]:
                record["ai"]["ai_tops"] = float(m.group(1))
                record["ai"]["npu_model"] = key.strip()

        # TDP
        if any(x in kl for x in ("power", "tdp", "thermal")):
            m = re.search(r"([\d.]+)\s*W", val)
            if m and not record["power"]["tdp_watt"]:
                record["power"]["tdp_watt"] = float(m.group(1))

        # GPU
        if any(x in kl for x in ("gpu", "graphics", "vivante", "mali")):
            if not record["graphics"]["model"]:
                record["graphics"]["model"] = val[:60]

    # Features list
    if "_features" in raw:
        record["features"] = raw["_features"][:10]

    return record


def fetch_nxp(model_str: str) -> Optional[dict]:
    """爬取 NXP 產品頁，解析規格表，回傳 cpu_library record。"""
    norm = normalize_model(model_str)
    url = NXP_PRODUCT_URLS.get(norm) or NXP_PRODUCT_URLS.get(model_str)

    if not url:
        print(f"  [NXP] No URL configured for: {model_str}")
        print(f"    ! Add URL to NXP_PRODUCT_URLS in ark_fetcher.py")
        return None

    print(f"  [NXP] Fetching: {url}")
    try:
        r = SESSION.get(url, timeout=20)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
    except Exception as e:
        print(f"    ✗ HTTP error: {e}")
        return None

    raw = _parse_nxp_page(soup)
    if not raw:
        print(f"    ! No structured data found on NXP page. Using manual library entry.")
        return None

    print(f"    ok {len(raw)} fields parsed from NXP page")
    record = _build_record_from_nxp(norm, url, raw)
    return record


# ── Spec Matrix Fallback（vendor-agnostic datasheet 回退策略） ───────────────────

def _fallback_from_spec_matrix(cpu_model: str) -> Optional[dict]:
    """
    Vendor 網頁無法取得規格時的回退策略：從 spec_matrix.json 讀取已解析的 CPU 規格。

    設計原則：「針對不同 vendor 可以用不同的資料結構讀取，最終回歸到 datasheet」
    適用場景：
      - Qualcomm 等 JS-heavy 網頁（無法靠 requests 爬取）
      - 小廠商 / OEM CPU，無公開網頁
      - 任何 vendor 的 web_fetch 失敗情況

    回傳欄位（與 computing_spec 的 CPU 相關部分對齊）：
      cpu_cores, cpu_p_cores, cpu_e_cores, tdp_watt, ai_tops,
      os_support, sdk, _source_part（來源 part_no）
    """
    if not SPEC_MATRIX.exists():
        return None
    try:
        with open(SPEC_MATRIX, encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"    [spec_matrix fallback] Load error: {e}")
        return None

    norm_target = normalize_model(cpu_model)
    for product in data:
        cs = product.get("computing_spec") or {}
        raw_model = cs.get("processor_model", "")
        if not raw_model:
            continue
        if normalize_model(raw_model) == norm_target:
            part_no = product.get("meta", {}).get("part_no") or "unknown"
            print(f"    [spec_matrix fallback] Sourced from datasheet: {part_no}")
            return {
                "cpu_cores":    cs.get("cpu_cores"),
                "cpu_p_cores":  cs.get("cpu_p_cores"),
                "cpu_e_cores":  cs.get("cpu_e_cores"),
                "tdp_watt":     cs.get("tdp_watt"),
                "ai_tops":      cs.get("ai_tops"),
                "os_support":   cs.get("os_support"),
                "sdk":          cs.get("sdk"),
                "_source_part": part_no,
            }
    return None


# ── Qualcomm 查詢 ─────────────────────────────────────────────────────────────

QUALCOMM_PRODUCT_URLS = {
    "Qualcomm Cloud AI 100":       "https://www.qualcomm.com/products/technology/artificial-intelligence/cloud-ai-100",
    "Qualcomm Cloud AI 100 Ultra": "https://www.qualcomm.com/products/technology/artificial-intelligence/cloud-ai-100",
    "Qualcomm IQ-9075":            "https://www.qualcomm.com/internet-of-things/products/iq9-series/iq-9075",
    "Snapdragon X Elite":          "https://www.qualcomm.com/products/mobile/snapdragon/pcs-and-tablets/snapdragon-x-series",
}

# Qualcomm 重點規格（手動維護，因 Qualcomm 網頁無法可靠自動解析）
# product_type: "pcie_card" = PCIe AI accelerator (no CPU), "soc" = full SoC (has CPU)
QUALCOMM_MANUAL_SPECS = {
    "Qualcomm Cloud AI 100": {
        "product_type": "pcie_card",
        "ai_tops": 200,
        "cpu_cores": None,
        "tdp_watt": 75.0,
        "memory_type": "HBM2e",
        "notes": "PCIe AI accelerator card. No general-purpose CPU. 200 TOPS INT8."
    },
    "Qualcomm Cloud AI 100 Ultra": {
        "product_type": "pcie_card",
        "ai_tops": 870,
        "cpu_cores": None,
        "tdp_watt": 75.0,
        "memory_type": "HBM2e",
        "notes": "PCIe AI accelerator card. Ultra variant. 870 TOPS INT8."
    },
    "Qualcomm IQ-9075": {
        "product_type": "soc",
        "ai_tops": 200.0,           # 200 TOPS INT8 sparse / 100 TOPS dense (Hexagon HTP)
        "cpu_cores": 8,             # Octa-core Kryo Gen 6 (Cortex-A78C-based)
        "base_freq_p_ghz": 3.36,    # Prime core max
        "tdp_watt": None,           # Not publicly specified
        "memory_type": "LPDDR5X",
        "memory_capacity_gb": 36,   # 36GB ECC LPDDR5X (Lantronix EVK confirmed)
        "memory_channels": 6,       # 6×16-bit channels
        "pcie_gen": "4.0",
        "pcie_max_lanes": 4,
        "pcie_configs": "x4",
        "gpu_model": "Adreno 663 GPU",
        "npu_model": "Qualcomm Hexagon Tensor Processor (HTP)",
        "lithography": "5nm LPE",
        "processor_series": "Qualcomm IQ-9",
        "socket": "BGA/SoC",
        "market_segment": "Industrial IoT/Edge AI",
        "notes": "Industrial IoT SoC (Dragonwing IQ-9075 / QCS9075). 200 TOPS INT8 sparse (100 TOPS dense). Octa-core Kryo Gen 6. Used in APEX-A100. Source: Lantronix EVK page + CNX Software 2026-01.",
    },
}


def fetch_qualcomm(model_str: str) -> Optional[dict]:
    """
    Qualcomm 產品規格。
    支援兩種類型：
      - product_type="pcie_card": PCIe AI 加速卡（Cloud AI 100 系列），無一般用途 CPU
      - product_type="soc": 完整 SoC（IQ 系列），含 CPU + NPU + GPU

    資料來源優先順序（vendor-agnostic 原則）：
      1. QUALCOMM_MANUAL_SPECS（手動維護，最高優先）
      2. _fallback_from_spec_matrix()（從已解析的 Innodisk datasheet 補充）
    Qualcomm 官網為 JS-heavy → 不嘗試 live scraping。
    """
    norm   = normalize_model(model_str)
    manual = QUALCOMM_MANUAL_SPECS.get(norm) or QUALCOMM_MANUAL_SPECS.get(model_str)
    url    = QUALCOMM_PRODUCT_URLS.get(norm) or QUALCOMM_PRODUCT_URLS.get(model_str)

    if not manual:
        print(f"  [Qualcomm] No manual spec configured for: {model_str}")
        print(f"    ! Add entry to QUALCOMM_MANUAL_SPECS in ark_fetcher.py")
        return None

    product_type = manual.get("product_type", "pcie_card")
    print(f"  [Qualcomm] Building record for: {model_str} (type={product_type})")

    # ── 共用 meta ──────────────────────────────────────────────────────────────
    record = {
        "meta": {
            "ark_id": None,
            "ark_url": url,
            "source": "qualcomm_manual",
            "needs_verification": False,   # 手動維護 + datasheet 補充，不再強制標記
            "last_fetched": date.today().isoformat(),
            "notes": manual.get("notes", ""),
        },
        "identity": {
            "processor_model": norm,
            "processor_series": manual.get("processor_series", "Qualcomm Cloud AI"),
            "platform_brand": "Qualcomm",
            "launch_date": None,
            "lithography": manual.get("lithography"),
            "socket": manual.get("socket", "PCIe Card"),
            "market_segment": manual.get("market_segment", "AI Accelerator"),
        },
        "cores": {
            "cpu_cores":      manual.get("cpu_cores"),
            "cpu_p_cores":    None,
            "cpu_e_cores":    None,
            "threads":        None,
            "base_freq_p_ghz": manual.get("base_freq_p_ghz"),
            "max_turbo_ghz":  None,
        },
        "power": {
            "tdp_watt":         manual.get("tdp_watt"),
            "max_turbo_watt":   None,
            "min_assured_watt": None,
        },
        "pcie": {
            "revision":  manual.get("pcie_gen", "4.0"),
            "max_lanes": manual.get("pcie_max_lanes", 16 if product_type == "pcie_card" else 4),
            "configs":   manual.get("pcie_configs", "x16" if product_type == "pcie_card" else "x4"),
        },
        "graphics": {
            "model":           manual.get("gpu_model"),
            "eu_count":        None,
            "max_freq_mhz":    None,
            "display_support": None,
        },
        "ai": {
            "ai_tops":   manual.get("ai_tops"),
            "npu_model": manual.get("npu_model"),
        },
        "cache":   {"l2_mb": None, "l3_mb": None},
        "features": [],
    }

    # ── 依類型填入 memory 欄位 ─────────────────────────────────────────────────
    mem_type = manual.get("memory_type", "HBM2e" if product_type == "pcie_card" else "LPDDR5")
    if product_type == "pcie_card":
        record["memory"] = {
            "type":           [mem_type],
            "max_speed_mhz":  None,
            "max_capacity_gb": manual.get("memory_capacity_gb"),
            "channels":       manual.get("memory_channels"),
            "ecc_support":    None,
        }
        record["ai"]["npu_model"] = record["ai"]["npu_model"] or "Qualcomm Cloud AI Engine"
        record["features"] = ["PCIe AI Accelerator", "INT8", "INT4", "FP16", "BF16",
                              f"{int(manual['ai_tops'])} TOPS"]
    else:
        # SoC (e.g. IQ-9075)
        record["memory"] = {
            "type":           [mem_type],
            "max_speed_mhz":  None,
            "max_capacity_gb": manual.get("memory_capacity_gb"),
            "channels":       manual.get("memory_channels"),
            "ecc_support":    True,
        }
        record["ai"]["npu_model"] = record["ai"]["npu_model"] or "Qualcomm Hexagon NPU"
        record["graphics"]["model"] = record["graphics"]["model"] or "Adreno GPU"
        tops_str = f"{int(manual['ai_tops'])} TOPS INT8" if manual.get("ai_tops") else ""
        record["features"] = ["SNPE", "QNN", "Industrial Grade", "Wide Temperature", "ECC"]
        if tops_str:
            record["features"].append(tops_str)

    # ── Datasheet fallback：從 spec_matrix.json 補充 os_support / sdk 等欄位 ──
    ds = _fallback_from_spec_matrix(norm)
    if ds:
        record["meta"]["notes"] += f" [datasheet_supplement: {ds.get('_source_part', '?')}]"
        # 補充 spec_matrix 有但 manual 沒有的欄位
        if ds.get("os_support"):
            record["identity"]["os_support"] = ds["os_support"]
        if ds.get("sdk"):
            record["identity"]["sdk"] = ds["sdk"]
        # 如果 manual 的 tdp 是 None，嘗試從 datasheet 取
        if record["power"]["tdp_watt"] is None and ds.get("tdp_watt"):
            record["power"]["tdp_watt"] = ds["tdp_watt"]

    print(f"    ok TOPS={manual.get('ai_tops')}, TDP={manual.get('tdp_watt')}W, type={product_type}")
    return record


# ── 主流程 ────────────────────────────────────────────────────────────────────

def load_library() -> dict:
    if CPU_LIBRARY.exists():
        with open(CPU_LIBRARY, encoding="utf-8") as f:
            return json.load(f)
    return {"_meta": {}, "_lookup_aliases": {}}


def save_library(library: dict) -> None:
    # 更新 meta
    lib = dict(library)
    count = sum(1 for k in lib if not k.startswith("_"))
    lib["_meta"] = lib.get("_meta", {})
    lib["_meta"]["last_updated"] = date.today().isoformat()
    lib["_meta"]["total_entries"] = count
    lib["_meta"]["schema_version"] = "1.0"

    with open(CPU_LIBRARY, "w", encoding="utf-8") as f:
        json.dump(lib, f, ensure_ascii=False, indent=2)
    print(f"\n✓ Saved cpu_library.json ({count} CPU entries)")


def collect_models_from_spec_matrix() -> list[str]:
    """從 spec_matrix.json 收集所有非 null 的 processor_model。"""
    if not SPEC_MATRIX.exists():
        print(f"[WARN] spec_matrix.json not found at {SPEC_MATRIX}")
        return []
    with open(SPEC_MATRIX, encoding="utf-8") as f:
        data = json.load(f)
    models = set()
    for product in data:
        cs = product.get("computing_spec") or {}
        m = cs.get("processor_model")
        if m and m.strip():
            models.add(m.strip())
    return sorted(models)


def print_library_status(library: dict) -> None:
    """列出 library 目前所有條目及驗證狀態。"""
    print(f"\n{'='*65}")
    print(f"  CPU Library Status — {CPU_LIBRARY}")
    print(f"{'='*65}")
    entries = [(k, v) for k, v in library.items() if not k.startswith("_")]
    verified   = [e for e in entries if not e[1].get("meta", {}).get("needs_verification")]
    unverified = [e for e in entries if     e[1].get("meta", {}).get("needs_verification")]
    print(f"  Total: {len(entries)}  |  Verified: {len(verified)}  |  Needs verification: {len(unverified)}")
    print()

    for key, entry in sorted(entries):
        meta   = entry.get("meta", {})
        cores  = entry.get("cores", {})
        power  = entry.get("power", {})
        status = "! VERIFY" if meta.get("needs_verification") else "OK"
        src    = meta.get("source", "?")
        c_str  = f"{cores.get('cpu_cores','?')}C"
        if cores.get("cpu_p_cores"):
            c_str += f" ({cores['cpu_p_cores']}P+{cores['cpu_e_cores']}E)"
        tdp    = power.get("tdp_watt")
        tdp_str = f"{tdp}W" if tdp else "?W"
        print(f"  {status:8s} {key:<40s}  {c_str:<14s}  {tdp_str:<6s}  [{src}]")
    print()


def main():
    # Windows cp950 safe output — 防止 ® ™ 等符號 crash
    import sys as _sys
    if hasattr(_sys.stdout, "reconfigure"):
        _sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="Fetch CPU specs from Intel ARK into cpu_library.json")
    parser.add_argument("--force",       action="store_true", help="Re-fetch all entries")
    parser.add_argument("--verify-only", action="store_true", help="Only re-fetch needs_verification=true entries")
    parser.add_argument("--model",       type=str,            help="Fetch a single specific model string")
    parser.add_argument("--list",        action="store_true", help="Print library status and exit")
    args = parser.parse_args()

    library = load_library()

    if args.list:
        print_library_status(library)
        return

    # 決定要處理哪些 model strings
    if args.model:
        targets = [args.model]
    else:
        targets = collect_models_from_spec_matrix()
        if not targets:
            print("[INFO] No models found in spec_matrix.json")
            return

    print(f"\n{'='*65}")
    print(f"  ARK Fetcher — {len(targets)} model(s) to process")
    print(f"  Mode: {'--force' if args.force else '--verify-only' if args.verify_only else 'incremental'}")
    print(f"{'='*65}\n")

    fetched = 0
    skipped = 0
    failed  = 0

    for raw_model in targets:
        norm   = normalize_model(raw_model)
        lib_key = resolve_alias(raw_model, library)

        existing = library.get(lib_key)
        needs_v  = existing and existing.get("meta", {}).get("needs_verification", False)

        # 決定是否跳過
        if existing and not args.force:
            if args.verify_only and not needs_v:
                skipped += 1
                continue
            if not args.verify_only and not needs_v:
                skipped += 1
                continue

        print(f"\n[{fetched+failed+1}/{len(targets)}] {raw_model}")

        # NXP → 爬取 NXP 產品頁
        if "NXP" in raw_model or "i.MX" in raw_model:
            result = fetch_nxp(norm)
        # Qualcomm → 手動規格庫（TOPS/TDP）
        elif "Qualcomm" in raw_model or "Snapdragon" in raw_model or "Cloud AI" in raw_model:
            result = fetch_qualcomm(norm)
        else:
            result = fetch_intel(norm)
            time.sleep(RATE_LIMIT_SECONDS)

        if result:
            # 確保 processor_model 與 library key 一致（防止 alias 解析後 identity 欄位殘留舊名）
            if "identity" in result:
                result["identity"]["processor_model"] = lib_key
            library[lib_key] = result
            fetched += 1
        else:
            if existing:
                # 保留現有條目，標記 needs_verification
                library[lib_key]["meta"]["needs_verification"] = True
                print(f"    [KEEP] Keeping existing entry, marked needs_verification=true")
            else:
                # 新建空佔位條目
                library[lib_key] = {
                    "meta": {
                        "ark_id": None,
                        "ark_url": None,
                        "source": "manual_estimate",
                        "needs_verification": True,
                        "last_fetched": date.today().isoformat(),
                        "notes": f"Auto-fetch failed. Populate manually from Intel ARK."
                    },
                    "identity": {
                        "processor_model": norm,
                        "processor_series": None,
                        "platform_brand": "Intel",
                    },
                    "cores":   {"cpu_cores": None, "cpu_p_cores": None, "cpu_e_cores": None},
                    "power":   {"tdp_watt": None},
                    "memory":  {"type": [], "max_capacity_gb": None, "ecc_support": None},
                    "pcie":    {"revision": None},
                    "graphics": {"model": None},
                    "ai":      {"ai_tops": None, "npu_model": None},
                    "cache":   {"l2_mb": None, "l3_mb": None},
                    "features": [],
                }
                failed += 1

    # ── 同步 _lookup_aliases ──────────────────────────────────────────────────
    # 確保 spec_matrix 裡有 ® 符號的 model string 都有 alias 指向 library key
    aliases = library.setdefault("_lookup_aliases", {})
    for raw_model in targets:
        norm = normalize_model(raw_model)
        if norm != raw_model and norm in library:
            aliases[raw_model] = norm

    save_library(library)
    print(f"\n  Fetched: {fetched}  Skipped: {skipped}  Failed/Placeholder: {failed}")
    print_library_status(library)


if __name__ == "__main__":
    main()
