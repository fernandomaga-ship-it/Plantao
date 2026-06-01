#!/usr/bin/env python3
"""
Gera assets/site-data.js a partir dos HTMLs em plantoes/ e rotinas/.
Equivalente Python do generate-site-data.mjs (sem precisar de Node.js).

Uso:
    python3 scripts/gerar_site_data.py
    python3 scripts/gerar_site_data.py --dry-run   # só imprime, não grava
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import quote as url_quote

# ── Configuração ──────────────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parent.parent
CONTENT_ROOTS = [
    REPO_ROOT / "plantoes",
    REPO_ROOT / "rotinas",
]
OUTPUT = REPO_ROOT / "assets" / "site-data.js"
IGNORED_DIRS = {"legacy", ".git", "__pycache__", "node_modules"}

# ── Categorias ────────────────────────────────────────────────────────────────
def category_for(path_str: str, text_snippet: str) -> str:
    v = (path_str + " " + text_snippet).lower()
    if "rotinas/" in v:
        return "rotinas"
    if "plantoes/bp" in v or "plantoes/8b" in v:
        return "uti"
    if re.search(r"(uti|intensiv|cti|icu)", v):
        return "uti"
    if re.search(r"(enfermaria|ward|ala|posto|quarto)", v):
        return "enfermaria"
    if re.search(r"(centro.cir|cirurg|cc|sala\s+cir)", v):
        return "centro-cirurgico"
    return "outros"

CATEGORY_LABELS = {
    "uti": "UTI",
    "enfermaria": "Enfermaria",
    "centro-cirurgico": "Centro cirúrgico",
    "rotinas": "Rotinas",
    "outros": "Outros",
}

# ── Extração de texto ─────────────────────────────────────────────────────────
def clean_text(html: str) -> str:
    text = re.sub(r"<script[\s\S]*?</script>", " ", html, flags=re.IGNORECASE)
    text = re.sub(r"<style[\s\S]*?</style>", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def extract_title(html: str, fallback: str) -> str:
    m = re.search(r"<title[^>]*>([\s\S]*?)</title>", html, re.IGNORECASE)
    if m:
        t = clean_text(m.group(1)).strip()
        if t:
            return t
    m = re.search(r"<h1[^>]*>([\s\S]*?)</h1>", html, re.IGNORECASE)
    if m:
        t = clean_text(m.group(1)).strip()
        if t:
            return t
    return fallback

def title_from_path(rel: str) -> str:
    parts = Path(rel).stem
    return re.sub(r"[-_]+", " ", parts).title()

# ── Datas ─────────────────────────────────────────────────────────────────────
def shift_date_from_path(rel: str) -> str:
    """Extrai data ISO (YYYY-MM-DD) do caminho, ex: plantoes/bp/2026-05-15/leito.html"""
    m = re.search(r"(?:^|/)(\d{4}-\d{2}-\d{2})(?:/|\.|$)", rel)
    return m.group(1) if m else ""

def shift_date_from_html(html: str) -> str:
    """Extrai data do conteúdo HTML (padrões DD/MM/YYYY)."""
    patterns = [
        r"plant[aã]o[^\d]{0,20}(\d{2})\s*/\s*(\d{2})\s*/\s*(\d{4})",
        r"passagem de plant[aã]o[^\d]{0,20}(\d{2})\s*/\s*(\d{2})\s*/\s*(\d{4})",
        r"(\d{2})\s*/\s*(\d{2})\s*/\s*(\d{4})\s*</",
    ]
    for pat in patterns:
        m = re.search(pat, html, re.IGNORECASE)
        if m:
            dd, mm, yyyy = m.group(1), m.group(2), m.group(3)
            return f"{yyyy}-{mm}-{dd}"
    return ""

def format_date_label(iso: str) -> str:
    if not iso or len(iso) < 10:
        return ""
    yyyy, mm, dd = iso[:4], iso[5:7], iso[8:10]
    return f"{dd}/{mm}/{yyyy}"

# ── Metadados por arquivo ─────────────────────────────────────────────────────
def page_data(file: Path) -> dict:
    rel = str(file.relative_to(REPO_ROOT)).replace(os.sep, "/")
    html = file.read_text(encoding="utf-8", errors="replace")
    text = clean_text(html)

    title = extract_title(html, title_from_path(rel))
    folder = str(file.parent.relative_to(REPO_ROOT)).replace(os.sep, "/")
    if folder == ".":
        folder = ""

    shift_date = shift_date_from_path(rel) or shift_date_from_html(html)
    category = category_for(rel, text[:1600])
    mtime = datetime.fromtimestamp(file.stat().st_mtime).strftime("%Y-%m-%d")
    summary = text[:168] if text else "Arquivo HTML publicado no GitHub Pages."

    # Percent-encode o href para funcionar em URLs (ex: ã → %C3%A3)
    # Preserva / e . como separadores de caminho
    href = "/".join(url_quote(part, safe="") for part in rel.split("/"))

    return {
        "title": title,
        "path": rel,
        "href": href,
        "folder": folder,
        "category": category,
        "categoryLabel": CATEGORY_LABELS.get(category, "Outros"),
        "summary": summary,
        "updated": mtime,
        "shiftDate": shift_date,
        "shiftDateLabel": format_date_label(shift_date),
    }

# ── Walk ──────────────────────────────────────────────────────────────────────
def walk(directory: Path) -> list[Path]:
    if not directory.exists():
        return []
    result = []
    for entry in sorted(directory.iterdir()):
        if entry.name in IGNORED_DIRS or entry.name.startswith("."):
            continue
        if entry.is_dir():
            result.extend(walk(entry))
        elif entry.is_file() and entry.suffix.lower() in {".html", ".htm"}:
            result.append(entry)
    return result

# ── Ordenação ─────────────────────────────────────────────────────────────────
def sort_key(page: dict):
    # Mais recente primeiro; dentro da mesma data, ordem alfabética do título
    date = page["shiftDate"] or "0000-00-00"
    return (-int(date.replace("-", "")), page["title"])

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Gera assets/site-data.js")
    parser.add_argument("--dry-run", action="store_true", help="Imprime sem gravar")
    args = parser.parse_args()

    all_files: list[Path] = []
    for root in CONTENT_ROOTS:
        all_files.extend(walk(root))

    pages = [page_data(f) for f in all_files]
    pages.sort(key=sort_key)

    generated_at = datetime.now().strftime("%Y-%m-%d")
    payload = {"generatedAt": generated_at, "pages": pages}
    js_source = f"window.PLANTAO_DATA = {json.dumps(payload, ensure_ascii=False, indent=2)};\n"

    if args.dry_run:
        print(js_source[:1000], "...")
        print(f"\n[dry-run] {len(pages)} páginas encontradas. Nada gravado.")
        return

    OUTPUT.write_text(js_source, encoding="utf-8")
    print(f"site-data.js atualizado: {len(pages)} páginas em {OUTPUT}")

if __name__ == "__main__":
    main()
