#!/usr/bin/env python3
"""
02_parse.py — Convert downloaded .doc files into structured law JSON.

Reads : data/raw/<FILE_ID>.doc  +  data/raw/<FILE_ID>.json  (metadata)
Writes: data/processed/<slug_id>.json

All 319 files are OLE2 legacy Word 97-2003 .doc format.
python-docx cannot read OLE2 .doc (it only handles .docx / ZIP-based files).

Text extraction strategy (in priority order):
  1. pywin32 COM   — opens the file via Microsoft Word automation (Windows).
                     Install: pip install pywin32  (requires Word to be installed)
  2. olefile       — pure-Python OLE2 reader; extracts raw text stream.
                     Install: pip install olefile  (no external tools needed)
  3. LibreOffice   — converts .doc → .txt via headless mode (any platform).
                     Install: https://www.libreoffice.org/download/
  4. antiword      — CLI tool (Linux/macOS only).
                     Install: sudo apt install antiword
  5. Fallback stub — records law metadata but marks text as unavailable.

Each output file contains:
    {
        "id":              "ley-federal-del-trabajo",
        "file_id":         "LFT",
        "name":            "Ley Federal del Trabajo",
        "short_name":      "LFT",
        "year_enacted":    1970,
        "year_last_reform": 2024,
        "category":        "trabajo",
        "source_url":      "https://...",
        "full_text":       "...",
        "articles": [
            {"number": "1", "title": "Artículo 1", "text": "..."},
            ...
        ],
        "num_articles":    1010,
        "extraction_method": "python-docx",
        "processed_at":    "2024-01-15T11:00:00Z",
    }
"""

import json
import logging
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.utils.lookup import CANONICAL_LAWS

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

RAW_DIR       = Path(__file__).parent.parent / "data" / "raw"
PROCESSED_DIR = Path(__file__).parent.parent / "data" / "processed"
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Text extraction from .doc
# ---------------------------------------------------------------------------

def extract_text_pywin32(doc_path: Path) -> tuple[str, str] | None:
    """
    Use Microsoft Word via COM automation (Windows only).
    Requires: pip install pywin32  AND  Microsoft Word installed.
    Most reliable method for OLE2 .doc files on Windows.
    """
    try:
        import win32com.client  # type: ignore
        import pythoncom        # type: ignore
        pythoncom.CoInitialize()
        word = win32com.client.Dispatch("Word.Application")
        word.Visible = False
        try:
            doc = word.Documents.Open(str(doc_path.resolve()))
            text = doc.Content.Text
            doc.Close(False)
        finally:
            word.Quit()
            pythoncom.CoUninitialize()
        if text and len(text.strip()) > 50:
            return text, "pywin32-com"
        return None
    except Exception:
        return None


def _scan_utf16le_runs(data: bytes, min_run: int = 30) -> str:
    """
    Scan raw bytes for UTF-16-LE encoded text runs.

    Word 97-2003 .doc stores text as UTF-16-LE (2 bytes per char).
    Spanish legal text is mostly ASCII + Latin Extended (á é í ó ú ñ ü etc.).
    In UTF-16-LE those all have a 0x00 high byte, so we look for
    sequences of (printable_byte, 0x00) pairs.

    We try both even and odd byte alignment because the FIB at the
    start of the stream may be an odd number of bytes.
    """
    WORD_NEWLINES = {0x0A, 0x0D, 0x0B, 0x0C, 0x07}  # 0x0B = soft return in Word
    collected: list[str] = []

    for offset in (0, 1):  # try both byte alignments
        run: list[str] = []
        i = offset
        while i < len(data) - 1:
            lo, hi = data[i], data[i + 1]

            if hi == 0x00:
                if 0x20 <= lo <= 0x7E:          # printable ASCII
                    run.append(chr(lo))
                    i += 2
                    continue
                if lo in WORD_NEWLINES:          # newline / page break
                    run.append("\n")
                    i += 2
                    continue
                if 0xC0 <= lo <= 0xFF:           # Latin Extended (áéíóúñü…)
                    run.append(chr(lo))
                    i += 2
                    continue
            elif 0x00 < hi <= 0x05:             # higher BMP plane (rare but valid)
                try:
                    ch = bytes([lo, hi]).decode("utf-16-le")
                    if ch.isprintable() or ch in "\n\r":
                        run.append(ch)
                        i += 2
                        continue
                except Exception:
                    pass

            # Non-text byte — flush run if long enough
            if len(run) >= min_run // 2:
                collected.append("".join(run))
            run = []
            i += 1

        if len(run) >= min_run // 2:
            collected.append("".join(run))

    # Keep runs that look like real words (>40% alpha chars, has spaces)
    good: list[str] = []
    for part in collected:
        if len(part) < 20 or " " not in part:
            continue
        alpha_ratio = sum(1 for c in part if c.isalpha()) / len(part)
        if alpha_ratio > 0.35:
            good.append(part)

    # Deduplicate (both alignments may find the same run)
    seen: set[str] = set()
    unique: list[str] = []
    for part in good:
        key = part[:40]
        if key not in seen:
            seen.add(key)
            unique.append(part)

    return "\n".join(unique)


def extract_text_olefile(doc_path: Path) -> tuple[str, str] | None:
    """
    Pure-Python OLE2 reader — no Word or external tools needed.
    Scans the WordDocument stream for UTF-16-LE text runs.
    Install: pip install olefile
    """
    try:
        import olefile  # type: ignore

        if not olefile.isOleFile(str(doc_path)):
            return None

        ole = olefile.OleFileIO(str(doc_path))
        try:
            if not ole.exists("WordDocument"):
                return None
            raw = ole.openstream("WordDocument").read()
            text = _scan_utf16le_runs(raw)
            if len(text.strip()) > 200:
                return text, "olefile"
            return None
        finally:
            ole.close()
    except ImportError:
        return None
    except Exception:
        return None


def extract_text_antiword(doc_path: Path) -> tuple[str, str] | None:
    """
    Try to extract text using the antiword CLI.
    Works for genuine Word 97-2003 .doc files.
    Returns (full_text, method_name) or None if antiword is not available.
    """
    if not shutil.which("antiword"):
        return None
    try:
        result = subprocess.run(
            ["antiword", "-w", "0", str(doc_path)],
            capture_output=True,
            timeout=60,
        )
        if result.returncode == 0 and result.stdout:
            text = result.stdout.decode("utf-8", errors="replace")
            if len(text.strip()) > 100:
                return text, "antiword"
        return None
    except (subprocess.TimeoutExpired, OSError):
        return None


def _find_libreoffice() -> str | None:
    """Return the soffice/libreoffice executable path, or None if not found."""
    # First try PATH (works on Linux/macOS and Windows if PATH was updated)
    cmd = shutil.which("soffice") or shutil.which("libreoffice")
    if cmd:
        return cmd

    # Windows: LibreOffice is NOT added to PATH by default.
    # Check standard installation directories.
    if sys.platform == "win32":
        import os
        candidates = [
            r"C:\Program Files\LibreOffice\program\soffice.exe",
            r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
        ]
        # Also check PROGRAMFILES / PROGRAMFILES(X86) env vars
        for env_var in ("PROGRAMFILES", "PROGRAMFILES(X86)", "PROGRAMW6432"):
            pf = os.environ.get(env_var)
            if pf:
                candidates.append(os.path.join(pf, "LibreOffice", "program", "soffice.exe"))
        for path in candidates:
            if os.path.isfile(path):
                return path

    return None


def extract_text_libreoffice(doc_path: Path) -> tuple[str, str] | None:
    """
    Convert .doc -> .txt using LibreOffice headless mode.
    Works as a universal fallback for any Word format.
    Returns (full_text, method_name) or None if libreoffice is not available.
    """
    lo_cmd = _find_libreoffice()
    if not lo_cmd:
        return None
    try:
        with tempfile.TemporaryDirectory() as tmp_dir:
            result = subprocess.run(
                [
                    lo_cmd, "--headless", "--convert-to", "txt:Text",
                    "--outdir", tmp_dir, str(doc_path),
                ],
                capture_output=True,
                timeout=120,
            )
            if result.returncode != 0:
                return None
            txt_path = Path(tmp_dir) / (doc_path.stem + ".txt")
            if not txt_path.exists():
                return None
            # LibreOffice on Windows outputs CP1252 by default, not UTF-8.
            # Try encodings in order: UTF-8 with BOM, UTF-8, CP1252, Latin-1.
            raw_bytes = txt_path.read_bytes()
            text = None
            for enc in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
                try:
                    text = raw_bytes.decode(enc)
                    break
                except UnicodeDecodeError:
                    continue
            if text is None:
                text = raw_bytes.decode("latin-1")  # never fails
            if len(text.strip()) > 100:
                return text, "libreoffice"
            return None
    except (subprocess.TimeoutExpired, OSError):
        return None


def extract_text_from_doc(doc_path: Path) -> tuple[str, str]:
    """
    Try all extraction methods in priority order.
    Always returns (text, method_name) — text may be empty string if all methods fail.
    """
    for extractor in [
        extract_text_pywin32,      # Windows COM (best quality, needs Word)
        extract_text_libreoffice,  # Any platform (if LibreOffice installed) — best without Word
        extract_text_antiword,     # Linux/macOS CLI
        extract_text_olefile,      # Pure Python OLE2 fallback (no external tools)
    ]:
        result = extractor(doc_path)
        if result is not None:
            text, method = result
            if text and len(text.strip()) > 50:
                return text, method

    log.warning(f"  All extraction methods failed for {doc_path.name}")
    log.warning(
        "  To fix, install ONE of:\n"
        "    pip install pywin32   (Windows + Microsoft Word)\n"
        "    pip install olefile   (pure Python, any platform)\n"
        "    LibreOffice           (https://www.libreoffice.org/download/)"
    )
    return "", "none"


# ---------------------------------------------------------------------------
# Text cleaning
# ---------------------------------------------------------------------------

def clean_doc_text(raw_text: str) -> str:
    """Clean extracted text: normalize whitespace, remove control chars, etc."""
    text = raw_text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\f", "\n\n")
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"\n{4,}", "\n\n\n", text)
    return text.strip()


# ---------------------------------------------------------------------------
# Article extraction
# ---------------------------------------------------------------------------

ARTICLE_PATTERNS = [
    re.compile(r"^Art[ií]culo\s+(\d+[\w\-]*)[.\s\-\u2013]*(.*)$", re.IGNORECASE),
    re.compile(r"^ART[IÍ]CULO\s+(\d+[\w\-]*)[.\s\-\u2013]*(.*)$"),
    re.compile(r"^Art\.\s+(\d+[\w\-]*)[.\s\-\u2013]*(.*)$", re.IGNORECASE),
]

YEAR_PATTERN      = re.compile(r"\b(19[4-9]\d|20[0-2]\d)\b")
REFORM_PATTERN    = re.compile(
    r"[ÚU]ltima\s+reforma\s+publicada[^0-9]*(\d{1,2}\s+de\s+\w+\s+de\s+\d{4})",
    re.IGNORECASE,
)
PUBLISHED_PATTERN = re.compile(
    r"publicad[ao]\s+en\s+el\s+D\.?O\.?F\.?[^0-9]*(\d{1,2}\s+de\s+\w+\s+de\s+\d{4})",
    re.IGNORECASE,
)


def extract_articles(text: str) -> list[dict]:
    articles: list[dict] = []
    current: dict | None = None
    current_lines: list[str] = []

    for line in text.split("\n"):
        line = line.strip()
        if not line:
            if current_lines:
                current_lines.append("")
            continue

        match = None
        for pat in ARTICLE_PATTERNS:
            m = pat.match(line)
            if m:
                match = m
                break

        if match:
            if current is not None:
                articles.append({
                    "number": current["number"],
                    "title":  current["title"],
                    "text":   "\n".join(current_lines).strip(),
                })
            num   = match.group(1)
            title = (match.group(2).strip() if match.lastindex >= 2 else "")
            current = {
                "number": num,
                "title":  f"Artículo {num}" + (f" — {title}" if title else ""),
            }
            current_lines = [line]
        elif current is not None:
            current_lines.append(line)

    if current is not None and current_lines:
        articles.append({
            "number": current["number"],
            "title":  current["title"],
            "text":   "\n".join(current_lines).strip(),
        })

    return articles


def extract_dates(text: str, meta: dict) -> dict:
    """Extract year_enacted and year_last_reform from text + index metadata."""
    result: dict = {}

    m = REFORM_PATTERN.search(text[:3000])
    if m:
        year_m = re.search(r"\b(\d{4})\b", m.group(1))
        if year_m:
            result["year_last_reform"] = int(year_m.group(1))

    m = PUBLISHED_PATTERN.search(text[:3000])
    if m:
        year_m = re.search(r"\b(\d{4})\b", m.group(1))
        if year_m:
            result["year_enacted"] = int(year_m.group(1))

    # Supplement from index metadata (DOF dates on the index page)
    if "year_enacted" not in result:
        dof_pub = meta.get("dof_published", "")
        year_m = re.search(r"\b(\d{4})\b", dof_pub)
        if year_m and 1917 <= int(year_m.group(1)) <= 2030:
            result["year_enacted"] = int(year_m.group(1))

    if "year_last_reform" not in result:
        dof_ref = meta.get("dof_last_reform", "")
        year_m = re.search(r"\b(\d{4})\b", dof_ref)
        if year_m and 1917 <= int(year_m.group(1)) <= 2030:
            result["year_last_reform"] = int(year_m.group(1))

    if "year_enacted" not in result:
        years = [int(y) for y in YEAR_PATTERN.findall(text[:2000]) if 1917 <= int(y) <= 2030]
        if years:
            result["year_enacted"] = min(years)

    return result


# ---------------------------------------------------------------------------
# Main processing per law
# ---------------------------------------------------------------------------

def process_law(meta_path: Path) -> dict | None:
    """Parse a single raw law (.doc + metadata JSON) into structured output."""
    try:
        with open(meta_path, encoding="utf-8") as f:
            meta = json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        log.error(f"Cannot read {meta_path}: {exc}")
        return None

    if meta.get("download_failed"):
        log.warning(f"  Skipping {meta_path.stem}: download previously failed")
        return None

    file_id  = meta.get("file_id", meta_path.stem)
    slug_id  = meta.get("id", file_id.lower())
    law_name = meta.get("name", "")

    doc_path = RAW_DIR / f"{file_id}.doc"
    if not doc_path.exists():
        log.warning(f"  .doc file not found: {doc_path}")
        return None

    log.info(f"  Extracting text from {doc_path.name}")
    raw_text, method = extract_text_from_doc(doc_path)

    canonical  = CANONICAL_LAWS.get(slug_id, {})
    short_name = canonical.get("short", "") or file_id
    category   = canonical.get("sector", "")

    if not raw_text:
        log.warning(f"  No text extracted — saving stub for {file_id}")
        return {
            "id":              slug_id,
            "file_id":         file_id,
            "name":            law_name,
            "short_name":      short_name,
            "year_enacted":    None,
            "year_last_reform": None,
            "category":        category,
            "source_url":      meta.get("doc_url", ""),
            "pdf_url":         meta.get("pdf_url", ""),
            "full_text":       "",
            "articles":        [],
            "num_articles":    0,
            "char_count":      0,
            "is_abrogated":    meta.get("is_abrogated", False),
            "abrogation_note": meta.get("abrogation_note"),
            "extraction_method": "none",
            "doc_checksum":    meta.get("doc_checksum"),
            "processed_at":    datetime.now(timezone.utc).isoformat(),
        }

    full_text = clean_doc_text(raw_text)
    articles  = extract_articles(full_text)
    dates     = extract_dates(full_text, meta)
    log.info(f"  -> {len(articles)} articles  ({len(full_text):,} chars, method={method})")

    return {
        "id":              slug_id,
        "file_id":         file_id,
        "name":            law_name,
        "short_name":      short_name,
        "year_enacted":    dates.get("year_enacted"),
        "year_last_reform": dates.get("year_last_reform"),
        "category":        category,
        "source_url":      meta.get("doc_url", ""),
        "pdf_url":         meta.get("pdf_url", ""),
        "full_text":       full_text,
        "articles":        articles,
        "num_articles":    len(articles),
        "char_count":      len(full_text),
        "is_abrogated":    meta.get("is_abrogated", False),
        "abrogation_note": meta.get("abrogation_note"),
        "extraction_method": method,
        "doc_checksum":    meta.get("doc_checksum"),
        "processed_at":    datetime.now(timezone.utc).isoformat(),
    }


def already_processed(slug_id: str, doc_checksum: str | None) -> bool:
    out = PROCESSED_DIR / f"{slug_id}.json"
    if not out.exists():
        return False
    if doc_checksum is None:
        return True
    try:
        with open(out, encoding="utf-8") as f:
            return json.load(f).get("doc_checksum") == doc_checksum
    except Exception:
        return False


def save_processed(data: dict) -> None:
    path = PROCESSED_DIR / f"{data['id']}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    log.info(f"  -> Saved: {path.name}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    log.info("=" * 60)
    log.info("02_parse.py — Genoma Regulatorio de México")
    log.info("=" * 60)

    # Process laws in the order they appear in the index
    index_path = RAW_DIR / "_index.json"
    if index_path.exists():
        with open(index_path, encoding="utf-8") as f:
            index = json.load(f)
        file_ids = [law["file_id"] for law in index.get("laws", [])]
    else:
        file_ids = [p.stem for p in sorted(RAW_DIR.glob("*.json")) if p.stem != "_index"]

    if not file_ids:
        log.error(f"No laws found in {RAW_DIR}. Run 01_scrape.py first.")
        sys.exit(1)

    log.info(f"Processing {len(file_ids)} laws")

    success = skip = fail = 0

    for i, file_id in enumerate(file_ids, 1):
        meta_path = RAW_DIR / f"{file_id}.json"
        if not meta_path.exists():
            log.warning(f"[{i}/{len(file_ids)}] No metadata for {file_id}, skipping")
            fail += 1
            continue

        try:
            with open(meta_path, encoding="utf-8") as f:
                meta = json.load(f)
        except Exception:
            fail += 1
            continue

        slug_id   = meta.get("id", file_id.lower())
        checksum  = meta.get("doc_checksum")
        law_name  = meta.get("name", file_id)[:55]

        log.info(f"[{i:03d}/{len(file_ids)}] {file_id:12s}  {law_name}")

        if already_processed(slug_id, checksum):
            log.info("  -> Already processed, skipping")
            skip += 1
            continue

        result = process_law(meta_path)
        if result:
            save_processed(result)
            success += 1
        else:
            fail += 1

    log.info("")
    log.info("=" * 60)
    log.info("Parsing complete")
    log.info(f"  Processed : {success}")
    log.info(f"  Skipped   : {skip}  (cached)")
    log.info(f"  Failed    : {fail}")
    log.info("=" * 60)


if __name__ == "__main__":
    main()
