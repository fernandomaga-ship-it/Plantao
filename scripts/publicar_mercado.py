#!/usr/bin/env python3
"""
publicar_mercado.py — publica o relatório diário de mercado no dashboard.

Uso:
    python3 scripts/publicar_mercado.py               # processa todos os novos
    python3 scripts/publicar_mercado.py --dry-run     # simula sem gravar
    python3 scripts/publicar_mercado.py --no-push     # commita sem push

Vigia a pasta outputs/ da sessão Cowork e publica HTMLs novos em
rotinas/mercado/YYYY-MM-DD.html no repositório GitHub Pages.
"""

import argparse
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.parse import quote as url_quote

# ── Configuração ──────────────────────────────────────────────────────────────
CODEX = Path(__file__).parent.parent.resolve()
DESTINO = CODEX / "rotinas" / "mercado"

# Raiz de todas as sessões Cowork — busca em TODAS, independente do session ID
COWORK_SESSIONS_ROOT = Path(
    "/Users/fernandomcoutinho/Library/Application Support/Claude"
    "/local-agent-mode-sessions"
)

def encontrar_outputs_dirs() -> list:
    """
    Varre todas as sessões Cowork e devolve a lista de pastas outputs/
    que contenham arquivos mercado_*.html.
    Não depende de ID de sessão fixo.
    """
    if not COWORK_SESSIONS_ROOT.exists():
        return []
    dirs = []
    for outputs in COWORK_SESSIONS_ROOT.glob("*/*/outputs"):
        if any(outputs.glob("mercado_*.html")):
            dirs.append(outputs)
    # Fallback: busca em profundidade variável
    if not dirs:
        for outputs in COWORK_SESSIONS_ROOT.glob("**/outputs"):
            if any(outputs.glob("mercado_*.html")):
                dirs.append(outputs)
    return dirs

# Meses em português → número
MESES = {
    "janeiro": "01", "fevereiro": "02", "março": "03",  "marco": "03",
    "abril": "04",   "maio": "05",      "junho": "06",
    "julho": "07",   "agosto": "08",    "setembro": "09",
    "outubro": "10", "novembro": "11",  "dezembro": "12",
}


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def data_do_nome(nome: str) -> Optional[str]:
    """
    Extrai a data ISO de nomes como:
        mercado_01junho2026.html  → 2026-06-01
        mercado_2026-06-01.html  → 2026-06-01
        relatorio_01_06_2026.html → 2026-06-01
    Devolve None se não encontrar.
    """
    stem = Path(nome).stem.lower()

    # Padrão DDMESAAAA  (ex: 01junho2026)
    m = re.search(r"(\d{1,2})([a-zç]+)(\d{4})", stem)
    if m:
        dd, mes_str, yyyy = m.groups()
        num = MESES.get(mes_str)
        if num:
            return f"{yyyy}-{num}-{dd.zfill(2)}"

    # Padrão YYYY-MM-DD ou DD-MM-YYYY ou DD_MM_YYYY (com separadores)
    m = re.search(r"(\d{4})[-_](\d{2})[-_](\d{2})", stem)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"

    m = re.search(r"(\d{2})[-_](\d{2})[-_](\d{4})", stem)
    if m:
        return f"{m.group(3)}-{m.group(2)}-{m.group(1)}"

    # Padrão DDMMYYYY colado (ex: mercado_29052026)
    m = re.search(r"(\d{2})(\d{2})(\d{4})$", stem)
    if m:
        dd, mm, yyyy = m.groups()
        if 1 <= int(mm) <= 12 and 1 <= int(dd) <= 31:
            return f"{yyyy}-{mm}-{dd}"

    return None


def nome_destino(data_iso: str) -> str:
    """rotinas/mercado/2026-06-01.html"""
    return f"{data_iso}.html"


def ja_publicado(data_iso: str) -> bool:
    return (DESTINO / nome_destino(data_iso)).exists()


def rodar(cmd: list, dry_run: bool = False) -> str:
    print(f"    $ {' '.join(str(c) for c in cmd)}")
    if dry_run:
        return ""
    res = subprocess.run(cmd, cwd=CODEX, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"  ✗ Erro:\n{res.stderr.strip()}", file=sys.stderr)
        sys.exit(res.returncode)
    return res.stdout.strip()


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Publica relatórios de mercado do Cowork no dashboard GitHub Pages."
    )
    parser.add_argument(
        "--source",
        default=None,
        help="Pasta de origem dos HTMLs (padrão: busca automática em todas as sessões Cowork)",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-push", action="store_true")
    args = parser.parse_args()

    # ── Resolve pasta(s) de origem ────────────────────────────────────────────
    if args.source:
        src_dirs = [Path(args.source).expanduser().resolve()]
        if not src_dirs[0].is_dir():
            print(f"✗ Pasta não encontrada: {src_dirs[0]}", file=sys.stderr)
            sys.exit(1)
    else:
        src_dirs = encontrar_outputs_dirs()
        if not src_dirs:
            print("✗ Nenhuma pasta outputs/ com mercado_*.html encontrada.", file=sys.stderr)
            sys.exit(1)
        print(f"  🔍  {len(src_dirs)} pasta(s) Cowork encontrada(s).")

    # ── Encontra HTMLs novos ──────────────────────────────────────────────────
    todos = []
    for src_dir in src_dirs:
        todos.extend(src_dir.glob("mercado_*.html"))
    candidatos = sorted(todos, key=lambda p: p.stat().st_mtime)
    novos = []
    ignorados = []

    for arquivo in candidatos:
        data = data_do_nome(arquivo.name)
        if not data:
            ignorados.append(arquivo.name)
            continue
        if ja_publicado(data):
            ignorados.append(f"{arquivo.name} (já publicado como {data}.html)")
            continue
        novos.append((arquivo, data))

    if ignorados:
        print(f"  ℹ  Ignorados: {', '.join(ignorados)}")

    if not novos:
        print("  ✓  Nenhum relatório novo para publicar.")
        return

    # ── Copia e publica ───────────────────────────────────────────────────────
    if not args.dry_run:
        DESTINO.mkdir(parents=True, exist_ok=True)

    publicados = []
    for arquivo, data_iso in novos:
        dest_nome = nome_destino(data_iso)
        dest_path = DESTINO / dest_nome
        br = f"{data_iso[8:10]}/{data_iso[5:7]}/{data_iso[:4]}"

        print(f"\n  📊  {arquivo.name}  →  rotinas/mercado/{dest_nome}")
        if not args.dry_run:
            shutil.copy2(arquivo, dest_path)
        publicados.append((dest_nome, data_iso, br))

    # ── Regenera site-data.js ─────────────────────────────────────────────────
    print("\n  🔄  Regenerando site-data.js…")
    rodar(["python3", "scripts/gerar_site_data.py"], dry_run=args.dry_run)

    if args.dry_run:
        print("\n  [dry-run] Nenhuma alteração gravada.")
        return

    # ── Git ───────────────────────────────────────────────────────────────────
    datas_br = ", ".join(br for _, _, br in publicados)
    msg = (
        f"feat: relatório de mercado {datas_br}\n\n"
        f"Publicado automaticamente via publicar_mercado.py\n\n"
        f"Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
    )

    print("\n  📝  Commitando…")
    rodar(["git", "add", "rotinas/mercado/", "assets/site-data.js"])
    rodar(["git", "commit", "-m", msg])

    if not args.no_push:
        print("  🚀  Fazendo push…")
        res = subprocess.run(
            ["git", "push", "origin", "main"],
            cwd=CODEX, capture_output=True, text=True,
        )
        if res.returncode != 0 and ("fetch first" in res.stderr or "rejected" in res.stderr):
            print("  ↕  Remote tem commits novos — fazendo pull --rebase…")
            rodar(["git", "pull", "--rebase", "origin", "main"])
            rodar(["git", "push", "origin", "main"])
        elif res.returncode != 0:
            print(f"  ✗ {res.stderr.strip()}", file=sys.stderr)
            sys.exit(1)

        print()
        print("━" * 56)
        print(f"  ✅  {len(publicados)} relatório(s) publicado(s)!")
        print("      https://fernandomaga-ship-it.github.io/Plantao/")
        print("━" * 56)
    else:
        print("\n  ✅  Commit feito. Push pendente (--no-push).")
    print()


if __name__ == "__main__":
    main()
