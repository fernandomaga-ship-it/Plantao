#!/usr/bin/env python3
"""Deploy arquivos para a Locaweb via FTP usando secrets do ambiente.

Secrets necessários (não commitar senha):
  LOCAWEB_FTP_HOST        ex.: ftp.drfernandomc.com.br ou host do painel
  LOCAWEB_FTP_USER        usuário FTP do painel Locaweb
  LOCAWEB_FTP_PASSWORD    senha FTP
  LOCAWEB_FTP_REMOTE_DIR  opcional (padrão: public_html)

Uso:
  python3 scripts/deploy-locaweb-ftp.py --dry-run
  python3 scripts/deploy-locaweb-ftp.py --target triathlon
  python3 scripts/deploy-locaweb-ftp.py --local produtos/triathlon-criterio-medico/pagina-vendas.html --remote triathlon/index.html
"""

from __future__ import annotations

import argparse
import os
import sys
from ftplib import FTP, error_perm
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

TARGETS = {
    "triathlon": {
        "local": ROOT / "produtos" / "triathlon-criterio-medico" / "pagina-vendas.html",
        "remote": "triathlon/index.html",
    }
}


def require_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise SystemExit(
            f"Secret ausente: {name}\n"
            "Adicione em Cursor → Cloud Agents → Environment → Secrets.\n"
            "Painel Locaweb: Central do Cliente → Hospedagem → Arquivos e FTP."
        )
    return value


def ftp_makedirs(ftp: FTP, remote_dir: str) -> None:
    parts = [p for p in remote_dir.strip("/").split("/") if p]
    path = ""
    for part in parts:
        path = f"{path}/{part}" if path else part
        try:
            ftp.mkd(path)
            print(f"  criada pasta remota: {path}")
        except error_perm as exc:
            # 550 normalmente = já existe
            if not str(exc).startswith("550"):
                raise


def upload_file(ftp: FTP, local_path: Path, remote_path: str) -> None:
    remote_path = remote_path.lstrip("/")
    parent = "/".join(remote_path.split("/")[:-1])
    if parent:
        ftp_makedirs(ftp, parent)

    with local_path.open("rb") as handle:
        ftp.storbinary(f"STOR {remote_path}", handle)
    print(f"  enviado: {local_path} → {remote_path}")


def connect() -> tuple[FTP, str]:
    host = require_env("LOCAWEB_FTP_HOST")
    user = require_env("LOCAWEB_FTP_USER")
    password = require_env("LOCAWEB_FTP_PASSWORD")
    remote_root = os.environ.get("LOCAWEB_FTP_REMOTE_DIR", "public_html").strip() or "public_html"

    ftp = FTP()
    ftp.connect(host, 21, timeout=30)
    ftp.login(user, password)
    ftp.set_pasv(True)

    try:
        ftp.cwd(remote_root)
    except error_perm:
        # algumas contas já abrem dentro de public_html
        print(f"  aviso: não entrou em '{remote_root}', usando diretório atual: {ftp.pwd()}")

    return ftp, remote_root


def main() -> int:
    parser = argparse.ArgumentParser(description="Deploy Locaweb via FTP")
    parser.add_argument("--target", choices=sorted(TARGETS), help="Pacote pré-definido")
    parser.add_argument("--local", type=Path, help="Arquivo local")
    parser.add_argument("--remote", help="Caminho remoto relativo a public_html")
    parser.add_argument("--dry-run", action="store_true", help="Só valida secrets e lista o que enviaria")
    args = parser.parse_args()

    jobs: list[tuple[Path, str]] = []
    if args.target:
        cfg = TARGETS[args.target]
        jobs.append((cfg["local"], cfg["remote"]))
    if args.local or args.remote:
        if not args.local or not args.remote:
            raise SystemExit("Use --local e --remote juntos.")
        jobs.append((args.local.resolve(), args.remote))
    if not jobs:
        raise SystemExit("Informe --target triathlon  ou  --local + --remote")

    for local_path, _ in jobs:
        if not local_path.is_file():
            raise SystemExit(f"Arquivo local não encontrado: {local_path}")

    print("Jobs de deploy:")
    for local_path, remote_path in jobs:
        print(f"  - {local_path.relative_to(ROOT)} → {remote_path}")

    if args.dry_run:
        # valida presença dos secrets sem conectar
        for key in ("LOCAWEB_FTP_HOST", "LOCAWEB_FTP_USER", "LOCAWEB_FTP_PASSWORD"):
            require_env(key)
        print("Dry-run OK: secrets presentes. Nada foi enviado.")
        return 0

    ftp, remote_root = connect()
    print(f"Conectado. Raiz remota efetiva: {ftp.pwd()} (config: {remote_root})")
    try:
        for local_path, remote_path in jobs:
            upload_file(ftp, local_path, remote_path)
    finally:
        ftp.quit()

    print("Deploy concluído.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
