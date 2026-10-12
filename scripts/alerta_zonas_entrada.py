#!/usr/bin/env python3
"""Alerta automático de zonas de entrada + monitor do resultado eleitoral.

1. Zonas: compara o último preço de cada ativo com a zona [inferior, superior]
   de config/zonas_entrada.json e envia resumo no Telegram quando algum ativo
   entra na zona (preço <= superior) ou rompe a zona inferior.
2. Eleição: no 1º pregão após `eleicao.data_resultado`, mede o gap de EWZ
   (pré-mercado em NY, proxy do Ibovespa futuro), ^BVSP e BRL=X contra o
   fechamento anterior e alerta 🚨 quando |variação| >= `limite_pct`.

Uso:
  python scripts/alerta_zonas_entrada.py             # zonas (+ eleição se for o dia)
  python scripts/alerta_zonas_entrada.py --eleicao   # só o check eleitoral (qualquer dia)
  python scripts/alerta_zonas_entrada.py --dry-run   # imprime sem enviar
  python scripts/alerta_zonas_entrada.py --loop      # agenda local via APScheduler

Variáveis de ambiente: TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID.
"""
import json, os, sys
from datetime import date, timedelta, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
import yfinance as yf

TZ = ZoneInfo("America/Sao_Paulo")
CONFIG = json.loads((Path(__file__).resolve().parent.parent / "config" / "zonas_entrada.json").read_text())


def simbolo(ticker: str) -> str:
    return ticker if ticker.startswith("^") or "=" in ticker or not ticker[-1].isdigit() else f"{ticker}.SA"


def hoje() -> date:
    return datetime.now(TZ).date()


def dia_pos_eleicao() -> date:
    d = date.fromisoformat(CONFIG["eleicao"]["data_resultado"]) + timedelta(days=1)
    while d.weekday() >= 5:
        d += timedelta(days=1)
    return d


# ---------- 1. Zonas de entrada ----------

def checar_zonas() -> list[str]:
    linhas = []
    for ticker, (inf, sup) in CONFIG["zonas"].items():
        try:
            hist = yf.Ticker(simbolo(ticker)).history(period="5d")["Close"].dropna()
        except Exception as e:  # noqa: BLE001 — um ativo falhando não derruba os demais
            print(f"{ticker}: {e}", file=sys.stderr)
            hist = []
        if len(hist) < 2:
            linhas.append(f"⚠️ {ticker}: sem cotação")
            continue
        atual, anterior = float(hist.iloc[-1]), float(hist.iloc[-2])
        if atual < inf:
            cruzou = " (cruzou hoje)" if anterior >= inf else ""
            linhas.append(f"🔴 {ticker} {atual:,.2f} — ABAIXO da zona ({inf:,.2f}){cruzou}")
        elif atual <= sup:
            linhas.append(f"🟢 {ticker} {atual:,.2f} — NA ZONA [{inf:,.2f}–{sup:,.2f}]")
    return linhas


# ---------- 2. Resultado eleitoral ----------

def gap_hoje(sym: str) -> tuple[float, float] | None:
    """(preço mais recente de hoje incl. pré-mercado, variação % vs. fechamento anterior)."""
    t = yf.Ticker(sym)
    diario = t.history(period="10d")["Close"].dropna()
    ref = diario[[d.date() < hoje() for d in diario.index]]
    intraday = t.history(period="1d", interval="1m", prepost=True)["Close"].dropna()
    intraday = intraday[[d.date() == hoje() for d in intraday.index]]
    if ref.empty or intraday.empty:
        return None
    atual, base = float(intraday.iloc[-1]), float(ref.iloc[-1])
    return atual, (atual / base - 1) * 100


def checar_eleicao() -> list[str]:
    limite = CONFIG["eleicao"]["limite_pct"]
    linhas, disparou, com_dados = [], False, False
    for sym in CONFIG["eleicao"]["ativos"]:
        try:
            r = gap_hoje(sym)
        except Exception as e:  # noqa: BLE001
            print(f"{sym}: {e}", file=sys.stderr)
            r = None
        if r is None:
            linhas.append(f"⏳ {sym}: ainda sem negociação hoje")
            continue
        atual, var = r
        com_dados = True
        forte = abs(var) >= limite
        disparou |= forte
        linhas.append(f"{'🚨' if forte else '▫️'} {sym} {atual:,.2f} ({var:+.2f}%)")
    if disparou:
        titulo = f"🚨 MOVE > ±{limite:g}% PÓS-ELEIÇÃO"
    elif com_dados:
        titulo = f"🗳️ Pós-eleição: moves dentro de ±{limite:g}%"
    else:
        titulo = "🗳️ Pós-eleição: mercados ainda sem negociação"
    return [titulo, *linhas]


# ---------- Envio ----------

def enviar(texto: str, dry_run: bool) -> None:
    print(texto)
    if dry_run:
        return
    token, chat = os.environ["TELEGRAM_BOT_TOKEN"], os.environ["TELEGRAM_CHAT_ID"]
    r = requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
                      json={"chat_id": chat, "text": texto}, timeout=20)
    r.raise_for_status()


def executar(zonas: bool = True, eleicao: bool | None = None, dry_run: bool = False) -> None:
    if eleicao is None:
        eleicao = hoje() == dia_pos_eleicao()
    blocos, z = [], []
    if eleicao:
        blocos.append("\n".join(checar_eleicao()))
    if zonas:
        z = checar_zonas()
        blocos.append("📊 Zonas de Entrada\n" + ("\n".join(z) if z else "Nenhum ativo na zona."))
    if eleicao or z:
        enviar("\n\n".join(blocos) + "\n\nRegra, não emoção.", dry_run)
    else:
        print("Nenhum ativo na zona de entrada.")


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    if "--loop" in sys.argv:
        from apscheduler.schedulers.blocking import BlockingScheduler
        sched = BlockingScheduler(timezone=TZ)
        sched.add_job(executar, "cron", day_of_week="mon-fri", hour=7, kwargs={"dry_run": dry})
        d = dia_pos_eleicao()
        for h, m in ((10, 30), (17, 30)):  # abertura e fechamento da B3 no dia seguinte ao 2º turno
            sched.add_job(executar, "date", run_date=datetime(d.year, d.month, d.day, h, m, tzinfo=TZ),
                          kwargs={"zonas": False, "eleicao": True, "dry_run": dry})
        sched.start()
    elif "--eleicao" in sys.argv:
        executar(zonas=False, eleicao=True, dry_run=dry)
    else:
        executar(dry_run=dry)
