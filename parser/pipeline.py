"""
Main pipeline: scan datasheets folder → hash check → Vision extract → build records → write spec_matrix.json
Usage:
    python pipeline.py --datasheets "D:\\管理\\Solution Architect\\AIoT\\1.Datasheet" --output ".\\output"
    python pipeline.py --file "path/to/single.pdf"   # parse one file only
"""

import argparse
import hashlib
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

# Ensure parser package directory is on sys.path when run from any working dir
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
import anthropic

import vision_extractor
import rule_extractor
import schema_builder

CONFIDENCE_THRESHOLD = 0.70   # below this → fall back to Claude Vision

load_dotenv(Path(__file__).parent.parent / ".env")

SUPPORTED_EXT = {".pdf"}
HASH_CACHE_FILE = "parse_hash_cache.json"

# ── Datasheet roots per BU ──────────────────────────────────────────────
# Edit these when the datasheet location changes (e.g. new computer).
# Set to None until the path is confirmed. Use --datasheets to override.
# Note: IPA BU (APEX series) currently lives nested under the AIoT root,
#       so the default AIoT scan already picks it up recursively.
DATASHEET_ROOTS = {
    # AIoT BU — Intel/NXP system boards (product_line: computing_aiot)
    "aiot":          Path(r"D:\Innodisk\Innodisk Product Selector\AIoT\1.Datasheet"),
    # Camera modules (product_line: camera)
    "camera":        Path(r"D:\Innodisk\Innodisk Product Selector\Camera\1.0 Datasheet"),
    # IPA BU \ EP — split into 4 product lines under one parent folder:
    "ipa_computing": Path(r"D:\Innodisk\Innodisk Product Selector\IPA\EP\Computing"),     # computing_ipa (Qualcomm)
    "air_sensor":    Path(r"D:\Innodisk\Innodisk Product Selector\IPA\EP\Air Sensor"),    # air_sensor
    "io":            Path(r"D:\Innodisk\Innodisk Product Selector\IPA\EP\IO Modules"),    # io
    "networking":    Path(r"D:\Innodisk\Innodisk Product Selector\IPA\EP\Networking"),    # networking
}


def _load_cache(output_dir: Path) -> dict:
    cache_path = output_dir / HASH_CACHE_FILE
    if cache_path.exists():
        return json.loads(cache_path.read_text(encoding="utf-8"))
    return {}


def _save_cache(output_dir: Path, cache: dict):
    cache_path = output_dir / HASH_CACHE_FILE
    cache_path.write_text(json.dumps(cache, indent=2, ensure_ascii=False), encoding="utf-8")


def _md5(path: Path) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


# Folder-name keywords that mark NON-datasheet PDFs (sales kits, manuals, roadmaps).
# Matched case-insensitively against each path component.
SKIP_FOLDER_KEYWORDS = ("ODM", "Sales Kit", "User Manual", "Roadmap", "Saleskit")


def _collect_pdfs(root: Path) -> list[Path]:
    """Collect all PDFs, skipping ODM and non-datasheet folders (sales kits, manuals)."""
    pdfs = []
    for p in sorted(root.rglob("*.pdf")):
        skip = next(
            (kw for part in p.parts for kw in SKIP_FOLDER_KEYWORDS
             if kw.lower() in part.lower()),
            None,
        )
        if skip:
            print(f"  [SKIP] {skip}: {p.name}")
            continue
        pdfs.append(p)
    return pdfs


def _load_existing_matrix(output_dir: Path) -> dict[str, dict]:
    """Load existing spec_matrix.json keyed by part_no."""
    matrix_path = output_dir / "spec_matrix.json"
    if not matrix_path.exists():
        return {}
    records = json.loads(matrix_path.read_text(encoding="utf-8-sig"))  # handle BOM from PowerShell writes
    return {r["meta"]["part_no"]: r for r in records}


def _save_matrix(output_dir: Path, records: dict[str, dict]):
    matrix_path = output_dir / "spec_matrix.json"
    matrix_path.write_text(
        json.dumps(list(records.values()), indent=2, ensure_ascii=False),
        encoding="utf-8"
    )


def _save_log(output_dir: Path, log: list[dict]):
    log_path = output_dir / "parse_log.json"
    log_path.write_text(json.dumps(log, indent=2, ensure_ascii=False), encoding="utf-8")


UNPARSED_FILE = "unparsed.json"


def _load_unparsed(output_dir: Path) -> dict[str, dict]:
    """Load the set-aside list of files whose part_no could not be resolved.
    Keyed by full file path so each unparseable PDF is preserved individually
    (avoids the UNKNOWN-key collision that collapses many files into one)."""
    path = output_dir / UNPARSED_FILE
    if not path.exists():
        return {}
    try:
        items = json.loads(path.read_text(encoding="utf-8-sig"))
        return {it["path"]: it for it in items}
    except Exception:
        return {}


def _save_unparsed(output_dir: Path, unparsed: dict[str, dict]):
    path = output_dir / UNPARSED_FILE
    path.write_text(
        json.dumps(list(unparsed.values()), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def parse_one(pdf_path: Path, client: anthropic.Anthropic) -> tuple[dict | None, dict]:
    """
    Parse a single PDF. Returns (record, log_entry).
    Strategy:
      1. Rule-based (pdfplumber) — fast, free, works for ~85% of cases
      2. Claude Vision fallback — only when rule-based confidence < threshold
    """
    log_entry = {
        "file": pdf_path.name,
        "path": str(pdf_path),
        "timestamp": datetime.now().isoformat(),
        "status": "ok",
        "method": "rule_based",
        "confidence_score": None,
        "warnings": [],
    }
    try:
        # ── Step 1: Rule-based ──────────────────────────────────────────────
        raw = rule_extractor.extract(str(pdf_path))
        confidence = raw.get("_confidence", 0.0)
        log_entry["confidence_score"] = round(confidence, 2)

        # ── Step 2: Vision fallback if needed ───────────────────────────────
        if confidence < CONFIDENCE_THRESHOLD:
            log_entry["method"] = "vision_fallback"
            if client is not None:
                log_entry["warnings"].append(
                    f"Rule-based confidence {confidence:.0%} < {CONFIDENCE_THRESHOLD:.0%}, using Vision API"
                )
                vision_raw = vision_extractor.extract(str(pdf_path), client)
                if "_parse_error" in vision_raw:
                    log_entry["status"] = "parse_error"
                    log_entry["warnings"].append(vision_raw["_parse_error"])
                    return None, log_entry
                # Merge: Vision takes priority; rule-based fills gaps
                for key, val in raw.items():
                    if key.startswith("_"):
                        continue
                    if not vision_raw.get(key) and val:
                        vision_raw[key] = val
                raw = vision_raw
            else:
                log_entry["warnings"].append(
                    f"Rule-based confidence {confidence:.0%} — Vision skipped (no API key set)"
                )

        if not raw.get("part_no") or raw["part_no"] == "UNKNOWN":
            log_entry["warnings"].append("part_no not detected — verify datasheet")

        record = schema_builder.build_record(str(pdf_path), raw)
        log_entry["part_no"] = record["meta"]["part_no"]
        return record, log_entry

    except Exception as e:
        log_entry["status"] = "error"
        log_entry["warnings"].append(str(e))
        return None, log_entry


def run(datasheets_dir: Path, output_dir: Path, force: bool = False, single_file: Path | None = None):
    output_dir.mkdir(parents=True, exist_ok=True)

    api_key = os.getenv("ANTHROPIC_API_KEY")
    has_api_key = api_key and api_key != "your_api_key_here"
    client = anthropic.Anthropic(api_key=api_key) if has_api_key else None

    if not has_api_key:
        print("NOTE: ANTHROPIC_API_KEY not set — Vision fallback disabled.")
        print(f"      PDFs below {CONFIDENCE_THRESHOLD:.0%} rule-based confidence will be SKIPPED.\n")
    cache = _load_cache(output_dir)
    existing = _load_existing_matrix(output_dir)
    unparsed = _load_unparsed(output_dir)
    log: list[dict] = []

    if single_file:
        pdfs = [single_file]
    else:
        pdfs = _collect_pdfs(datasheets_dir)

    print(f"\n{'='*60}")
    print(f"PDFs found: {len(pdfs)}")
    print(f"Output dir: {output_dir}")
    print(f"{'='*60}\n")

    processed = skipped = errors = set_aside = 0

    for pdf in pdfs:
        file_hash = _md5(pdf)
        cached_hash = cache.get(str(pdf))

        if not force and cached_hash == file_hash:
            print(f"  [SKIP] unchanged: {pdf.name}")
            skipped += 1
            continue

        print(f"  [PARSE] {pdf.name} ...", end=" ", flush=True)
        t0 = time.time()
        record, log_entry = parse_one(pdf, client)
        elapsed = time.time() - t0

        if record and record["meta"]["part_no"] != "UNKNOWN":
            part_no = record["meta"]["part_no"]
            existing[part_no] = record
            cache[str(pdf)] = file_hash
            processed += 1
            # If this file was previously set aside, it's now resolved → drop it.
            unparsed.pop(str(pdf), None)
            method  = log_entry.get("method", "rule_based")
            conf    = log_entry.get("confidence_score", "?")
            method_tag = "rule" if method == "rule_based" else "vision"
            print(f"OK  [{method_tag}:{conf}] {part_no} ({elapsed:.1f}s)")
        elif record:
            # part_no == UNKNOWN → set aside for later manual handling instead of
            # collapsing every UNKNOWN file into one polluting matrix record.
            cache[str(pdf)] = file_hash
            unparsed[str(pdf)] = {
                "path": str(pdf),
                "file": pdf.name,
                "reason": "part_no not detected (UNKNOWN)",
                "product_line_guess": record.get("meta", {}).get("product_line"),
                "confidence_score": log_entry.get("confidence_score"),
                "timestamp": datetime.now().isoformat(),
            }
            set_aside += 1
            print(f"SET-ASIDE [unparsed] {pdf.name} ({elapsed:.1f}s)")
        else:
            errors += 1
            print(f"FAIL ({elapsed:.1f}s) — {log_entry['warnings']}")

        log.append(log_entry)

        # Save incrementally after each file
        _save_matrix(output_dir, existing)
        _save_cache(output_dir, cache)
        _save_log(output_dir, log)
        _save_unparsed(output_dir, unparsed)

        # Brief pause to avoid API rate limits
        time.sleep(0.5)

    print(f"\n{'='*60}")
    print(f"Done. Processed: {processed}  Skipped: {skipped}  "
          f"Set-aside: {set_aside}  Errors: {errors}")
    print(f"Output: {output_dir / 'spec_matrix.json'}")
    if set_aside:
        print(f"Unparsed (set aside): {output_dir / UNPARSED_FILE}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Innodisk AIoT Datasheet Parser")
    parser.add_argument("--datasheets", type=Path,
                        default=DATASHEET_ROOTS["aiot"],
                        help="Root folder of datasheets (default: AIoT BU root)")
    parser.add_argument("--output", type=Path,
                        default=Path(__file__).parent.parent / "output",
                        help="Output directory for spec_matrix.json")
    parser.add_argument("--force", action="store_true",
                        help="Re-parse all files even if hash unchanged")
    parser.add_argument("--file", type=Path, default=None,
                        help="Parse a single PDF file only")
    args = parser.parse_args()

    run(
        datasheets_dir=args.datasheets,
        output_dir=args.output,
        force=args.force,
        single_file=args.file,
    )
