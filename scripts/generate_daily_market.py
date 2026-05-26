#!/usr/bin/env python3
"""
Gerador de Relatório Diário de Mercado
Dashboard Plantão — Dr. Fernando Coutinho

Executado via GitHub Actions às 09:00 BRT (12:00 UTC) em dias úteis.
Usa Claude API com web_search para dados reais de mercado.
"""

import anthropic
import datetime
import json
import os
import pathlib
import re
import sys

# ── Configuração ──────────────────────────────────────────────────────────────
DATE_OVERRIDE = os.environ.get("DATE_OVERRIDE", "").strip()
if DATE_OVERRIDE:
    TODAY = datetime.date.fromisoformat(DATE_OVERRIDE)
else:
    TODAY = datetime.date.today()

DATE_STR   = TODAY.strftime("%Y-%m-%d")
DATE_BR    = TODAY.strftime("%d/%m/%Y")
WEEKDAYS   = ["segunda-feira","terça-feira","quarta-feira","quinta-feira",
              "sexta-feira","sábado","domingo"]
WEEKDAY_BR = WEEKDAYS[TODAY.weekday()]

REPORT_PATH   = pathlib.Path(f"mercado/relatorios/{DATE_STR}.html")
MANIFEST_PATH = pathlib.Path("mercado/data/manifest.json")

# ── Prompt ────────────────────────────────────────────────────────────────────
PROMPT = f"""Você é um analista financeiro sênior especializado no mercado brasileiro e global.
Data de hoje: {DATE_BR} ({WEEKDAY_BR}).

TAREFA: Produza um relatório diário completo de mercado usando web_search para obter dados reais.
NÃO invente cotações ou números — busque tudo na web.

FONTES PRIORITÁRIAS (use web_search com esses domínios):
- infomoney.com.br  → mercado BR, Ibovespa, ações, FIIs
- valor.globo.com   → macroeconomia Brasil
- bloomberg.com     → economia global, commodities
- cnbc.com          → EUA, geopolítica, petróleo
- statusinvest.com.br → dados técnicos de ações e FIIs
- fundamentus.com.br  → indicadores fundamentalistas

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ESTRUTURA DO RELATÓRIO (siga esta ordem exata):

1. CONTEXTO GLOBAL
   - Principais eventos econômicos e geopolíticos
   - Mercados americanos: S&P 500, Nasdaq, Dow Jones
   - Câmbio: USD/BRL
   - Commodities: petróleo (WTI/Brent), minério de ferro, ouro

2. MERCADO BRASILEIRO
   - Ibovespa: pontuação, variação %, tendência
   - Juros futuros DI (curva)
   - Maiores altas e baixas do dia
   - Fatores macro relevantes (IPCA, Selic, fiscal, político)

3. AÇÕES PRINCIPAIS — análise individual completa de CADA UMA:
   Para AXIA3, VALE3, BBDC4, MRFG3, MSFT34, B3SA3:
   • Cotação e variação do dia
   • Análise técnica: MM21/MM50/MM200, RSI(14), MACD, suportes, resistências
   • Notícias recentes relevantes
   • Recomendações: BTG Pactual, XP, Goldman Sachs, JPMorgan, Morgan Stanley
   • Orientação personalizada: COMPRAR / MANTER / VENDER — com justificativa
     (considere os preços médios do investidor abaixo)

4. FUNDOS IMOBILIÁRIOS — análise de PCIP11 e KNCR11:
   • Cotação e variação
   • Último dividendo pago e DY mensal/anual
   • Orientação

5. ALERTAS DE CARTEIRA — APENAS se houver notícia importante e significativa:
   BEEF3, COGN3, WEGE3, EQTL3, SUZB3, VULC3, MBRF3, BHIA3, OIBR3
   (mencione SOMENTE se houver evento relevante — downgrade, resultado, M&A, regulatório)

6. RESUMO EXECUTIVO
   Tabela: Ativo | Sinal do Dia | Orientação | Justificativa resumida

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PREÇOS MÉDIOS DA CARTEIRA (use para contextualizar orientações):

Conta XP:
  MSFT34 → PM R$ 87,59 (497 ações)
  KNCR11 → PM R$ 105,54 (376 cotas)
  VALE3  → PM R$ 81,36 (300 ações)
  WEGE3  → PM R$ 46,75 (500 ações)
  AXIA3  → PM R$ 55,50 (300 ações)
  PCIP11 → PM R$ 85,72 (120 cotas)
  BBDC4  → PM R$ 19,20 (500 ações)
  SUZB3  → PM R$ 56,71 (100 ações)
  BEEF3  → PM R$ 5,84 (1.000 ações)

Conta Itaú (F&K):
  MRFG3  → PM R$ 19,92 (494 ações)
  EQTL3  → PM R$ 38,30 (259 ações)
  MSFT34 → PM R$ 109,69 (91 ações)
  PCIP11 → PM R$ 82,35 (115 cotas)
  BEEF3  → PM R$ 5,27 (3.800 ações)

Conta Grande:
  AXIA3  → PM R$ 35,53 (2.800 ações)
  VALE3  → PM R$ 66,79 (1.829 ações)
  BBDC4  → PM R$ 17,94 (4.055 ações)
  B3SA3  → PM R$ 16,32 (2.400 ações)
  BEEF3  → PM R$ 7,80 (1.375 ações)
  COGN3  → PM R$ 4,49 (9.350 ações)
  WEGE3  → PM R$ 41,83 (200 ações)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FORMATO DE SAÍDA:
- Escreva em português brasileiro, narrativa fluida e profissional
- Use os elementos HTML abaixo — retorne SOMENTE o conteúdo interno (sem <html>/<head>/<body>)
- NÃO inclua ```html ou marcadores de código

ELEMENTOS HTML DISPONÍVEIS:
<div class="report-section">...</div>  — para cada seção
<h2>Título da Seção</h2>
<h3>Subtítulo do Ativo</h3>
<p>Parágrafo de análise</p>
<span class="badge badge-up">COMPRA</span>
<span class="badge badge-down">VENDA</span>
<span class="badge badge-neutral">MANTER</span>
<span class="badge badge-alert">ALERTA</span>
<div class="tech-block">análise técnica</div>
<div class="alert-box"><div class="alert-icon">⚠️</div><div><div class="alert-title">Título</div><div class="alert-text">Detalhe</div></div></div>
<table class="market-table"><thead><tr><th>Col</th></tr></thead><tbody><tr><td>Val</td></tr></tbody></table>
<table class="summary-table">...</table>  — para o resumo executivo

No início do relatório, inclua este bloco com dados extraídos da busca:
<!-- META
ibov: [VALOR ex: 176.011]
ibov_chg: [ex: -1,01%]
ibov_up: [true/false]
dolar: [ex: R$ 5,03]
oil: [ex: US$ 94]
-->
"""

# ── HTML template ─────────────────────────────────────────────────────────────
def clean_content(raw: str) -> str:
    """Remove thinking text, orphaned citation periods and HTML comments."""
    lines = raw.splitlines()
    cleaned = []
    # Prefixes that indicate Claude thinking/status lines (not report content)
    skip_prefixes = (
        "Vou ", "Tenho ", "Aguarde", "Preciso ", "Deixa eu ",
        "Buscando", "Encontrei", "Já tenho", "Com base",
    )
    for line in lines:
        stripped = line.strip()
        # Drop thinking lines
        if any(stripped.startswith(p) for p in skip_prefixes):
            continue
        # Drop lines that are just a lone period (citation artifact)
        if stripped in (".", ". ", ""):
            if cleaned and cleaned[-1].strip() == "":
                continue  # avoid double blank lines
        cleaned.append(line)

    result = "\n".join(cleaned)
    # Remove HTML comments (<!-- ... -->)
    result = re.sub(r"<!--.*?-->", "", result, flags=re.DOTALL)
    # Collapse 3+ consecutive blank lines into 2
    result = re.sub(r"\n{3,}", "\n\n", result)
    return result.strip()


def wrap_in_html(content: str, date_br: str, weekday: str) -> str:
    clean = clean_content(content)
    return f"""<!-- REPORT:{DATE_STR} -->
<!-- GENERATED:{datetime.datetime.utcnow().isoformat()}Z -->

{clean}

<div class="sources-footer">
  <h4>Fontes consultadas</h4>
  <div class="source-links">
    <a href="https://www.infomoney.com.br" target="_blank">InfoMoney</a>
    <a href="https://valor.globo.com" target="_blank">Valor Econômico</a>
    <a href="https://www.bloomberg.com" target="_blank">Bloomberg</a>
    <a href="https://www.cnbc.com" target="_blank">CNBC</a>
    <a href="https://statusinvest.com.br" target="_blank">Status Invest</a>
    <a href="https://www.fundamentus.com.br" target="_blank">Fundamentus</a>
    <a href="https://www.b3.com.br" target="_blank">B3</a>
  </div>
  <p style="margin-top:12px;font-size:0.75rem;color:var(--sub)">
    Relatório gerado automaticamente em {datetime.datetime.now().strftime("%d/%m/%Y às %H:%M")} (BRT).
    Caráter educacional e informativo. Não constitui recomendação formal de investimento.
  </p>
</div>
"""

# ── Atualiza manifest.json ────────────────────────────────────────────────────
def update_manifest(ibov: str, ibov_chg: str, ibov_up: bool, dolar: str, oil: str):
    manifest = {"reports": []}
    if MANIFEST_PATH.exists():
        try:
            manifest = json.loads(MANIFEST_PATH.read_text())
        except Exception:
            pass

    # Remove entrada duplicada do mesmo dia se existir
    manifest["reports"] = [r for r in manifest["reports"] if r.get("date") != DATE_STR]

    manifest["reports"].append({
        "date":    DATE_STR,
        "title":   f"Relatório {DATE_BR}",
        "ibov":    ibov,
        "ibovChg": ibov_chg,
        "ibovUp":  ibov_up,
        "dolar":   dolar,
        "oil":     oil,
    })

    # Ordena por data crescente
    manifest["reports"].sort(key=lambda r: r["date"])

    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
    print(f"  manifest.json atualizado ({len(manifest['reports'])} relatórios)")

# ── Extrai metadados do comentário <!-- META --> ───────────────────────────────
def extract_meta(html: str) -> dict:
    meta = {"ibov": "—", "ibov_chg": "—", "ibov_up": False, "dolar": "—", "oil": "—"}
    block = re.search(r"<!--\s*META(.*?)-->", html, re.DOTALL)
    if not block:
        return meta
    for line in block.group(1).strip().splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            k = k.strip().lower().replace(" ", "_")
            v = v.strip()
            if k in meta:
                meta[k] = v.lower() == "true" if k == "ibov_up" else v
    return meta

# ── Geração via Claude API ────────────────────────────────────────────────────
def generate_report() -> str:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERRO: ANTHROPIC_API_KEY não definida.", file=sys.stderr)
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)
    print(f"Gerando relatório para {DATE_BR}...")

    messages = [{"role": "user", "content": PROMPT}]
    collected_text = []

    # Loop agentico para suportar tool_use do web_search
    while True:
        response = client.messages.create(
            model="claude-opus-4-7",
            max_tokens=8000,
            tools=[{
                "type": "web_search_20250305",
                "name": "web_search",
                "max_uses": 25,
            }],
            messages=messages,
        )

        for block in response.content:
            if block.type == "text":
                collected_text.append(block.text)

        if response.stop_reason == "end_turn":
            break

        if response.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": response.content})
            tool_results = [
                {"type": "tool_result", "tool_use_id": b.id, "content": ""}
                for b in response.content if b.type == "tool_use"
            ]
            if tool_results:
                messages.append({"role": "user", "content": tool_results})
        else:
            break

    return "\n".join(collected_text)


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    # Verifica se já existe (evita duplicar em re-runs)
    if REPORT_PATH.exists():
        print(f"Relatório {DATE_STR} já existe. Sobrescrevendo...")

    # Garante que os diretórios existem
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Gera o conteúdo via Claude
    raw_content = generate_report()
    print(f"  Conteúdo gerado: {len(raw_content)} caracteres")

    # Extrai metadados e monta HTML final
    meta = extract_meta(raw_content)
    final_html = wrap_in_html(raw_content, DATE_BR, WEEKDAY_BR)

    # Salva o relatório
    REPORT_PATH.write_text(final_html, encoding="utf-8")
    print(f"  Relatório salvo em: {REPORT_PATH}")

    # Atualiza manifest
    update_manifest(
        ibov=meta["ibov"],
        ibov_chg=meta["ibov_chg"],
        ibov_up=meta["ibov_up"],
        dolar=meta["dolar"],
        oil=meta["oil"],
    )

    print("Concluído.")


if __name__ == "__main__":
    main()
