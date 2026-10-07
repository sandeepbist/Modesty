#!/usr/bin/env python3
"""Page-aware PDF text with OCR only for pages without an embedded text layer."""
from pathlib import Path
import re
import shutil
import subprocess
import tempfile


def render_page(path, page, scale=1600):
    image = subprocess.run(["pdftoppm", "-f", str(page), "-l", str(page), "-singlefile", "-scale-to", str(scale), "-png", str(path)], capture_output=True, check=True, timeout=15).stdout
    if not image.startswith(b"\x89PNG") or len(image)>6_000_000:
        raise ValueError("Document page could not be rendered")
    return image


def read_pdf(path, max_pages=20, limit=50000, progress=None):
    info = subprocess.run(["pdfinfo", str(path)], capture_output=True, text=True, check=True, timeout=5).stdout
    total = int(re.search(r"^Pages:\s+(\d+)", info, re.M).group(1))
    count = min(total, max_pages)
    raw = subprocess.run(["pdftotext", "-layout", "-f", "1", "-l", str(count), str(path), "-"], capture_output=True, text=True, check=True, timeout=10).stdout.split("\f")
    pages, size = [], 0
    with tempfile.TemporaryDirectory(prefix="modesty-document-") as folder:
        for number in range(1, count+1):
            text = raw[number-1].strip() if number <= len(raw) else ""
            method = "text"
            if len(re.sub(r"\W", "", text)) < 24 and shutil.which("tesseract"):
                if progress:
                    progress(number, count)
                prefix = Path(folder)/"page"
                try:
                    Path(str(prefix)+".png").write_bytes(render_page(path, number, 2200))
                    text = subprocess.run(["tesseract", str(prefix)+".png", "stdout", "-l", "eng"], capture_output=True, text=True, check=True, timeout=20).stdout.strip()
                    method = "ocr"
                except (OSError, ValueError, subprocess.SubprocessError):
                    method = "unreadable"
            remaining = limit-size
            if remaining <= 0:
                break
            text = text[:remaining]
            pages.append({"page": number, "text": text, "method": method})
            size += len(text)
    return {"pages": pages, "totalPages": total, "truncated": len(pages)<total or size>=limit, "unreadablePages": [p["page"] for p in pages if not p["text"]],
            "text": "\n\n".join(f"[Page {p['page']} · {p['method']}]\n{p['text']}" for p in pages)}
