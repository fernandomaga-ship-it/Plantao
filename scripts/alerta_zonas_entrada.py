#!/usr/bin/env python3
"""Alerta automático de zonas de entrada (yfinance + Telegram).

Compara o último preço de cada ativo com a zona [inferior, superior] definida
em config/zonas_entrada.json e envia um único resumo no Telegram quando algum
ativo entra na zona (preço <= superior) ou rompe a zona inferior.

Uso:
  python scripts/alerta_zonas_entrada.py            # roda uma vez (GitHub Actions)
  python scripts/alerta_zonas_entrada.py --dry-run  # imprime sem enviar
  python scripts/alerta_zonas_entrada.py --loop     # agenda 07:00 BRT via APScheduler

Variáveis de ambiente: TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID.
"""
import json, os, sys
from pathlib import Path

import requests
import yfinance as yf

ZONAS = Path(__file__).resolve().parent.parent / "config" / "zonas_entrada.json"


def preco(ticker: str) -> tuple[float, float] | None:
    """Retorna (último preço, fechamento anterior) ou None se sem dados."""
    hist = yf.Ticker(f"{ticker}.SA").history(period="5d")["Close"].dropna()
    return (float(hist.iloc[-1]), float(hist.iloc[-2])) if len(hist) >= 2 else None


def avaliar() -> tuple[list[str], list[str]]:
    zonas = {k: v for k, v in json.loads(ZONAS.read_text()).items() if not k.startswith("_")}
    alertas, erros = [], []
    for ticker, (inf, sup) in zonas.items():
        try:
            dados = preco(ticker)
        except Exception as e:  # noqa: BLE001 — um ativo falhando não derruba os demais
            print(f"{ticker}: {e}", file=sys.stderr)
            dados = None
        if not dados:
            erros.append(f"⚠️ {ticker}: sem cotação")
            continue
        atual, anterior = dados
        if atual < inf:
            cruzou = " (cruzou hoje)" if anterior >= inf else ""
            alertas.append(f"🔴 {ticker} R$ {atual:.2f} — ABAIXO da zona ({inf:.2f}){cruzou}")
        elif atual <= sup:
            alertas.append(f"🟢 {ticker} R$ {atual:.2f} — NA ZONA [{inf:.2f}–{sup:.2f}]")
    return alertas, erros


def enviar_telegram(texto: str) -> None:
    token, chat = os.environ["TELEGRAM_BOT_TOKEN"], os.environ["TELEGRAM_CHAT_ID"]
    r = requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
                      json={"chat_id": chat, "text": texto}, timeout=20)
    r.raise_for_status()


def executar(dry_run: bool = False) -> None:
    alertas, erros = avaliar()
    if not alertas and not erros:
        print("Nenhum ativo na zona de entrada.")
        return
    texto = "📊 Zonas de Entrada\n\n" + "\n".join(alertas + erros) + "\n\nRegra, não emoção."
    print(texto)
    if not dry_run:
        enviar_telegram(texto)


if __name__ == "__main__":
    if "--loop" in sys.argv:
        from apscheduler.schedulers.blocking import BlockingScheduler
        sched = BlockingScheduler(timezone="America/Sao_Paulo")
        sched.add_job(executar, "cron", hour=7, minute=0)
        sched.start()
    else:
        executar(dry_run="--dry-run" in sys.argv)
