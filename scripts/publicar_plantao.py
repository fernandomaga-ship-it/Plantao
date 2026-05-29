#!/usr/bin/env python3
"""
publicar_plantao.py — publica uma pasta de HTMLs de plantão no dashboard.

Uso rápido (arraste a pasta para o terminal após o comando):
    python3 scripts/publicar_plantao.py /caminho/para/pasta_de_htmls

Opções:
    --dry-run   Simula sem copiar, commitar ou fazer push
    --no-push   Commita mas não faz push (útil para revisar antes)

O script detecta o hospital (8B, BP, …) e a data a partir do nome da pasta,
copia os HTMLs para plantoes/<hospital>/<YYYY-MM-DD>/, sanitiza nomes de
arquivo (remove acentos), regenera assets/site-data.js e publica no GitHub.

Convenções de nome de pasta reconhecidas automaticamente:
    UTI_8B_28-05-2026_HTML_por_paciente   → hospital=8b  data=2026-05-28
    UTI_BP_25_05_2026                     → hospital=bp  data=2026-05-25
    2026-05-28_plantao_8b                 → hospital=8b  data=2026-05-28
"""

import argparse
import re
import shutil
import subprocess
import sys
import unicodedata
from pathlib import Path
from typing import Optional

# ── Raiz do repositório (dois níveis acima deste script) ─────────────────────
CODEX = Path(__file__).parent.parent.resolve()


# ─────────────────────────────────────────────────────────────────────────────
# Detecção de data e hospital
# ─────────────────────────────────────────────────────────────────────────────

def detectar_hospital(nome: str) -> str:
    """Devolve 'bp' ou '8b' a partir do nome da pasta."""
    n = nome.upper()
    if "UTI_BP" in n or "_BP_" in n or n.startswith("BP_") or n.endswith("_BP"):
        return "bp"
    if "UTI_8B" in n or "_8B_" in n or n.startswith("8B_") or n.endswith("_8B"):
        return "8b"
    # Fallback: pergunta ao usuário
    print("⚠  Não foi possível detectar o hospital no nome da pasta.")
    resp = input("   Digite o hospital (ex: 8b ou bp): ").strip().lower()
    return resp or "8b"


def detectar_data(nome: str) -> Optional[str]:
    """Devolve a data no formato YYYY-MM-DD a partir do nome da pasta."""
    # Padrão DD-MM-YYYY ou DD_MM_YYYY
    m = re.search(r'(\d{2})[-_](\d{2})[-_](\d{4})', nome)
    if m:
        dd, mm, yyyy = m.groups()
        return f"{yyyy}-{mm}-{dd}"
    # Padrão YYYY-MM-DD ou YYYY_MM_DD
    m = re.search(r'(\d{4})[-_](\d{2})[-_](\d{2})', nome)
    if m:
        yyyy, mm, dd = m.groups()
        return f"{yyyy}-{mm}-{dd}"
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Sanitização de nomes de arquivo
# ─────────────────────────────────────────────────────────────────────────────

def sanitizar_nome(nome: str) -> str:
    """
    Remove acentos e caracteres não-ASCII do nome do arquivo.
    ex: leito_2815_gilson_pereira_guimarães.html
     → leito_2815_gilson_pereira_guimaraes.html
    """
    # NFD decompõe os acentos em letra-base + combining char
    nfd = unicodedata.normalize("NFD", nome)
    # Remove os combining characters (categoria Mn = Mark, Nonspacing)
    sem_acento = "".join(c for c in nfd if unicodedata.category(c) != "Mn")
    # Substitui espaços e qualquer char fora de [a-zA-Z0-9._-] por _
    seguro = re.sub(r"[^\w.\-]", "_", sem_acento)
    return seguro


# ─────────────────────────────────────────────────────────────────────────────
# Auxiliares
# ─────────────────────────────────────────────────────────────────────────────

def rodar(cmd: list, dry_run: bool = False, cwd: Optional[Path] = None) -> str:
    """Executa um comando, imprime e aborta em caso de erro."""
    print(f"    $ {' '.join(str(c) for c in cmd)}")
    if dry_run:
        return ""
    resultado = subprocess.run(
        cmd,
        cwd=cwd or CODEX,
        capture_output=True,
        text=True,
    )
    if resultado.returncode != 0:
        print(f"\n  ✗ Erro:\n{resultado.stderr.strip()}", file=sys.stderr)
        sys.exit(resultado.returncode)
    return resultado.stdout.strip()


def br(iso: str) -> str:
    """YYYY-MM-DD → DD/MM/YYYY"""
    return f"{iso[8:10]}/{iso[5:7]}/{iso[:4]}"


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Publica pasta de HTMLs de plantão no dashboard do GitHub Pages.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "pasta",
        help="Caminho para a pasta com os HTMLs do plantão",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simula tudo sem gravar, commitar ou fazer push",
    )
    parser.add_argument(
        "--no-push",
        action="store_true",
        help="Commita localmente mas não faz push",
    )
    args = parser.parse_args()

    src = Path(args.pasta).expanduser().resolve()
    if not src.is_dir():
        print(f"\n✗ Pasta não encontrada: {src}", file=sys.stderr)
        sys.exit(1)

    # ── Detecção ──────────────────────────────────────────────────────────────
    data_iso = detectar_data(src.name)
    if not data_iso:
        print(f"\n⚠  Não foi possível detectar a data no nome da pasta: {src.name}")
        raw = input("   Digite a data do plantão (DD/MM/AAAA): ").strip()
        m = re.match(r"(\d{2})/(\d{2})/(\d{4})", raw)
        if not m:
            print("✗ Data inválida.", file=sys.stderr)
            sys.exit(1)
        dd, mm, yyyy = m.groups()
        data_iso = f"{yyyy}-{mm}-{dd}"

    hospital = detectar_hospital(src.name)
    dest = CODEX / "plantoes" / hospital / data_iso

    # ── Resumo ────────────────────────────────────────────────────────────────
    print()
    print("━" * 56)
    print(f"  📁  Origem    : {src}")
    print(f"  📂  Destino   : plantoes/{hospital}/{data_iso}/")
    print(f"  📅  Data      : {br(data_iso)}")
    print(f"  🏥  Hospital  : {hospital.upper()}")
    print("━" * 56)

    # ── Cópia e sanitização ───────────────────────────────────────────────────
    htmls = sorted(src.glob("*.html"))
    if not htmls:
        print("\n✗ Nenhum arquivo .html encontrado na pasta.", file=sys.stderr)
        sys.exit(1)

    if not args.dry_run:
        dest.mkdir(parents=True, exist_ok=True)

    print(f"\n  Copiando {len(htmls)} arquivo(s)…\n")
    renomeados = 0
    for arquivo in htmls:
        nome_limpo = sanitizar_nome(arquivo.name)
        destino = dest / nome_limpo

        if nome_limpo != arquivo.name:
            print(f"  ⚠  {arquivo.name}")
            print(f"     → {nome_limpo}")
            renomeados += 1
        else:
            print(f"  ✓  {nome_limpo}")

        if not args.dry_run:
            shutil.copy2(arquivo, destino)

    if renomeados:
        print(f"\n  ℹ  {renomeados} nome(s) sanitizado(s) (acentos removidos).")

    # ── Regenera site-data.js ─────────────────────────────────────────────────
    print("\n  🔄  Regenerando site-data.js…")
    rodar(["python3", "scripts/gerar_site_data.py"], dry_run=args.dry_run)

    if args.dry_run:
        print("\n  [dry-run] Nenhuma alteração foi gravada.\n")
        return

    # ── Git: add + commit ─────────────────────────────────────────────────────
    rel_dest = f"plantoes/{hospital}/{data_iso}"
    msg = (
        f"feat: plantão UTI {hospital.upper()} {br(data_iso)}\n\n"
        f"Adiciona {len(htmls)} HTML(s) via publicar_plantao.py\n\n"
        f"Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
    )

    print("\n  📝  Commitando…")
    rodar(["git", "add", rel_dest, "assets/site-data.js"])
    rodar(["git", "commit", "-m", msg])

    # ── Push (com pull --rebase automático se o remote tiver commits novos) ───
    if not args.no_push:
        print("  🚀  Fazendo push…")
        # Tenta push direto; se rejeitado, faz pull --rebase e tenta de novo
        resultado = subprocess.run(
            ["git", "push", "origin", "main"],
            cwd=CODEX, capture_output=True, text=True,
        )
        if resultado.returncode != 0:
            if "fetch first" in resultado.stderr or "rejected" in resultado.stderr:
                print("  ↕  Remote tem commits novos — fazendo pull --rebase…")
                rodar(["git", "pull", "--rebase", "origin", "main"])
                rodar(["git", "push", "origin", "main"])
            else:
                print(f"\n  ✗ Erro no push:\n{resultado.stderr.strip()}", file=sys.stderr)
                sys.exit(1)
        print()
        print("━" * 56)
        print("  ✅  Dashboard atualizado no GitHub Pages!")
        print(f"      https://fernandomaga-ship-it.github.io/Plantao/")
        print("━" * 56)
    else:
        print()
        print("━" * 56)
        print("  ✅  Commit feito. Push pendente (--no-push ativo).")
        print("━" * 56)
    print()


if __name__ == "__main__":
    main()
