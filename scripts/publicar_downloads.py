#!/usr/bin/env python3
"""
publicar_downloads.py — detecta e publica arquivos novos em ~/Downloads.

Chamado automaticamente pelo LaunchAgent quando Downloads/ muda.
Distingue:
  - mercado_*.html  →  publicar_mercado.py
  - pasta com HTML  →  publicar_plantao.py  (ex: UTI_8B_04-06-2026_*)

Uso manual:
    python3 scripts/publicar_downloads.py
    python3 scripts/publicar_downloads.py --dry-run
"""

import argparse
import subprocess
import sys
from pathlib import Path

CODEX    = Path(__file__).parent.parent.resolve()
DOWNLOADS = Path("/Users/fernandomcoutinho/Downloads")


def rodar(cmd, dry_run=False):
    print(f"  $ {' '.join(str(c) for c in cmd)}")
    if not dry_run:
        result = subprocess.run(cmd, cwd=CODEX)
        if result.returncode != 0:
            sys.exit(result.returncode)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    rodou_algo = False

    # ── 1. Relatórios de mercado (mercado_*.html em Downloads/) ──────────────
    mercados = list(DOWNLOADS.glob("mercado_*.html"))
    if mercados:
        print(f"\n📊  {len(mercados)} relatório(s) de mercado em Downloads/")
        rodar(["python3", "scripts/publicar_mercado.py"] +
              (["--dry-run"] if args.dry_run else []))
        rodou_algo = True

    # ── 2. Pastas de plantão (UTI_*/plantao_* com HTMLs dentro) ─────────────
    for item in sorted(DOWNLOADS.iterdir()):
        if not item.is_dir():
            continue
        # Ignora pastas sem HTML ou claramente não-plantão
        htmls = list(item.glob("*.html"))
        if not htmls:
            continue
        nome = item.name.lower()
        if not any(k in nome for k in ["uti", "plantao", "plantão", "bp", "leito", "8b"]):
            continue

        print(f"\n🏥  Pasta de plantão encontrada: {item.name}")
        rodar(["python3", "scripts/publicar_plantao.py", str(item)] +
              (["--dry-run"] if args.dry_run else []))
        rodou_algo = True

    if not rodou_algo:
        print("  ✓  Nenhum arquivo novo para publicar em Downloads/")


if __name__ == "__main__":
    main()
