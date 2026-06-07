#!/usr/bin/env python3
"""
publicar_downloads.py — detecta e publica arquivos novos em ~/Downloads.

Chamado automaticamente pelo LaunchAgent quando Downloads/ muda.
Distingue:
  - mercado_*.html      →  publicar_mercado.py
  - pasta com HTMLs     →  publicar_plantao.py  (ex: UTI_8B_04-06-2026_*)
  - HTMLs individuais   →  agrupa por hospital+data e publica

Uso manual:
    python3 scripts/publicar_downloads.py
    python3 scripts/publicar_downloads.py --dry-run
"""

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata
from pathlib import Path

CODEX     = Path(__file__).parent.parent.resolve()
DOWNLOADS = Path("/Users/fernandomcoutinho/Downloads")

# Padrões de nome que indicam arquivo de plantão
PLANTAO_KEYWORDS = ["uti", "plantao", "plantão", "bp", "leito", "8b", "6a", "mirante", "dashboard_uti"]


def sanitizar(nome: str) -> str:
    nfd = unicodedata.normalize("NFD", nome)
    sem_acento = "".join(c for c in nfd if unicodedata.category(c) != "Mn")
    return re.sub(r"[^\w.\-]", "_", sem_acento)


def detectar_hospital_de_arquivo(nome: str) -> str:
    n = nome.upper()
    if "_BP_" in n or "UTI_BP" in n:
        return "bp"
    if "_8B_" in n or "UTI_8B" in n or "UTI8B" in n:
        return "8b"
    if "_6A_" in n or "UTI_6A" in n or "UTI6A" in n or "6A" in n:
        return "6a"
    if "MIRANTE" in n:
        return "mirante"
    return ""


def detectar_data_de_arquivo(nome: str) -> str:
    # YYYY-MM-DD
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", nome)
    if m:
        return m.group(0)
    # DD-MM-YYYY
    m = re.search(r"(\d{2})-(\d{2})-(\d{4})", nome)
    if m:
        return f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
    # DD_MM_YYYY
    m = re.search(r"(\d{2})_(\d{2})_(\d{4})", nome)
    if m:
        return f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
    return ""


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
        htmls = list(item.glob("*.html"))
        if not htmls:
            continue
        nome = item.name.lower()
        if not any(k in nome for k in PLANTAO_KEYWORDS):
            continue

        print(f"\n🏥  Pasta de plantão encontrada: {item.name}")
        rodar(["python3", "scripts/publicar_plantao.py", str(item)] +
              (["--dry-run"] if args.dry_run else []))
        rodou_algo = True

    # ── 3. HTMLs individuais de plantão em Downloads/ ─────────────────────────
    # Agrupa por (hospital, data) e cria pasta temporária para publicar
    grupos: dict = {}
    for item in sorted(DOWNLOADS.iterdir()):
        if not item.is_file() or item.suffix.lower() not in {".html", ".htm"}:
            continue
        nome = item.name.lower()
        if not any(k in nome for k in PLANTAO_KEYWORDS):
            continue
        if nome.startswith("mercado_"):
            continue  # já tratado acima

        hospital = detectar_hospital_de_arquivo(item.name)
        data     = detectar_data_de_arquivo(item.name)
        if not hospital or not data:
            continue

        # Verifica se já está publicado (arquivo já existe no repo)
        nome_limpo = sanitizar(item.name)
        dest_path = CODEX / "plantoes" / hospital / data / nome_limpo
        if dest_path.exists():
            continue  # idempotente — não republica o que já está lá

        chave = (hospital, data)
        grupos.setdefault(chave, []).append(item)

    for (hospital, data), arquivos in sorted(grupos.items()):
        print(f"\n🏥  {len(arquivos)} HTML(s) individuais — UTI {hospital.upper()} {data}")

        # Copia para pasta temporária com nome que o publicar_plantao.py entende
        nome_tmp = f"UTI_{hospital.upper()}_{data}"
        tmp_root = Path(tempfile.mkdtemp())
        tmp_pasta = tmp_root / nome_tmp
        tmp_pasta.mkdir()

        for arq in arquivos:
            shutil.copy2(arq, tmp_pasta / arq.name)

        rodar(["python3", "scripts/publicar_plantao.py", str(tmp_pasta)] +
              (["--dry-run"] if args.dry_run else []))
        rodou_algo = True

        # Limpa temp
        shutil.rmtree(tmp_root, ignore_errors=True)

    if not rodou_algo:
        print("  ✓  Nenhum arquivo novo para publicar em Downloads/")


if __name__ == "__main__":
    main()
