#!/usr/bin/env python3
"""
02_00_diagnose.py — Diagnose why 02_parse.py fails to extract text from .doc files.

Run this, paste the output, and we'll fix 02_parse.py accordingly.
Then delete this file.
"""

import shutil
import subprocess
import sys
import traceback
from pathlib import Path

RAW_DIR = Path(__file__).parent.parent / "data" / "raw"

# ── Magic-byte signatures ────────────────────────────────────────────────────
MAGIC = {
    b"\x50\x4b\x03\x04": "ZIP / DOCX (Office Open XML)",
    b"\xd0\xcf\x11\xe0": "OLE2 / legacy Word 97-2003 .doc",
    b"\x3c\x3f\x78\x6d": "XML (<?xm...)",
    b"\x3c\x68\x74\x6d": "HTML (<htm...)",
    b"\x3c\x48\x54\x4d": "HTML (<HTM...)",
    b"\x25\x50\x44\x46": "PDF (%PDF)",
    b"\x52\x74\x66\x31": "RTF (Rtf1)",
    b"\x7b\x5c\x72\x74": "RTF ({\\rt...)",
}


def identify_file(path: Path) -> str:
    try:
        header = path.read_bytes()[:8]
        for sig, label in MAGIC.items():
            if header[:len(sig)] == sig:
                return label
        printable = header.decode("latin-1", errors="replace")
        return f"Unknown — first 8 bytes: {header.hex()}  ({printable!r})"
    except Exception as exc:
        return f"Cannot read: {exc}"


# ── Tool availability ────────────────────────────────────────────────────────

def check_tools():
    print("\n=== TOOL AVAILABILITY ===")

    # python-docx
    try:
        import docx
        print(f"[OK] python-docx      version {docx.__version__}")
    except ImportError as e:
        print(f"[MISSING] python-docx  — {e}")
        print("        Fix: pip install python-docx")

    # antiword
    aw = shutil.which("antiword")
    if aw:
        print(f"[OK] antiword         {aw}")
    else:
        print("[MISSING] antiword     — not on PATH")
        print("        Fix (Debian/Ubuntu): sudo apt install antiword")

    # libreoffice
    lo = shutil.which("libreoffice") or shutil.which("soffice")
    if lo:
        print(f"[OK] libreoffice      {lo}")
    else:
        print("[MISSING] libreoffice  — not on PATH")
        print("        Fix (Debian/Ubuntu): sudo apt install libreoffice")


# ── Per-file diagnostics ─────────────────────────────────────────────────────

def diagnose_file(path: Path):
    print(f"\n--- {path.name} ({path.stat().st_size:,} bytes) ---")

    fmt = identify_file(path)
    print(f"  Format   : {fmt}")

    # 1. python-docx
    print("  [python-docx] ", end="", flush=True)
    try:
        from docx import Document
        doc = Document(str(path))
        paras = [p.text for p in doc.paragraphs if p.text.strip()]
        if paras:
            print(f"OK — {len(paras)} non-empty paragraphs  |  first: {paras[0][:80]!r}")
        else:
            print("Opened but ZERO non-empty paragraphs")
    except Exception:
        print("FAILED")
        traceback.print_exc(limit=3)

    # 2. antiword
    aw = shutil.which("antiword")
    print(f"  [antiword]    ", end="", flush=True)
    if not aw:
        print("skipped (not installed)")
    else:
        try:
            r = subprocess.run(["antiword", "-w", "0", str(path)],
                               capture_output=True, timeout=30)
            if r.returncode == 0 and r.stdout:
                snippet = r.stdout[:120].decode("utf-8", errors="replace").strip()
                print(f"OK — {len(r.stdout):,} bytes  |  first: {snippet!r}")
            else:
                err = r.stderr.decode("utf-8", errors="replace").strip()[:200]
                print(f"FAILED (rc={r.returncode})  stderr: {err!r}")
        except Exception:
            print("FAILED")
            traceback.print_exc(limit=2)

    # 3. libreoffice
    lo = shutil.which("libreoffice") or shutil.which("soffice")
    print(f"  [libreoffice] ", end="", flush=True)
    if not lo:
        print("skipped (not installed)")
    else:
        import tempfile
        try:
            with tempfile.TemporaryDirectory() as tmp:
                r = subprocess.run(
                    [lo, "--headless", "--convert-to", "txt:Text",
                     "--outdir", tmp, str(path)],
                    capture_output=True, timeout=60,
                )
                out_txt = Path(tmp) / (path.stem + ".txt")
                if r.returncode == 0 and out_txt.exists():
                    text = out_txt.read_text(encoding="utf-8", errors="replace").strip()
                    snippet = text[:120].replace("\n", " ")
                    print(f"OK — {len(text):,} chars  |  first: {snippet!r}")
                else:
                    err = r.stderr.decode("utf-8", errors="replace").strip()[:200]
                    print(f"FAILED (rc={r.returncode})  stderr: {err!r}")
        except Exception:
            print("FAILED")
            traceback.print_exc(limit=2)


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("02_00_diagnose.py — Genoma Regulatorio de México")
    print(f"Python  : {sys.version}")
    print(f"RAW_DIR : {RAW_DIR}")
    print("=" * 60)

    check_tools()

    # Collect up to 5 sample .doc files
    docs = sorted(RAW_DIR.glob("*.doc"))
    if not docs:
        print(f"\n[ERROR] No .doc files found in {RAW_DIR}")
        print("Run 01_scrape.py first.")
        sys.exit(1)

    print(f"\n=== FILE FORMAT SURVEY (first 10 of {len(docs)}) ===")
    format_counts: dict[str, int] = {}
    for doc in docs[:10]:
        fmt = identify_file(doc)
        format_counts[fmt] = format_counts.get(fmt, 0) + 1
        print(f"  {doc.name:20s}  {fmt}")

    # Full format survey (all files, just count)
    if len(docs) > 10:
        for doc in docs[10:]:
            fmt = identify_file(doc)
            format_counts[fmt] = format_counts.get(fmt, 0) + 1
        print(f"\n  Summary across all {len(docs)} files:")
        for fmt, count in sorted(format_counts.items(), key=lambda x: -x[1]):
            print(f"    {count:4d} × {fmt}")

    # Deep-diagnose 3 sample files (spread across the list)
    sample_indices = [0, len(docs) // 2, len(docs) - 1]
    samples = [docs[i] for i in sample_indices]

    print(f"\n=== DEEP DIAGNOSIS (3 sample files) ===")
    for path in samples:
        diagnose_file(path)

    print("\n" + "=" * 60)
    print("Diagnosis complete. Paste this output to decide the fix.")
    print("=" * 60)


if __name__ == "__main__":
    main()
