#!/usr/bin/env bash
# ════════════════════════════════════════════════════════════════════════════════
#  importar_plantao.sh
#  Copia uma pasta de HTMLs de plantão para o repositório, regenera o
#  site-data.js e publica no GitHub Pages em um único comando.
#
#  Uso:
#    ./scripts/importar_plantao.sh /path/para/pasta_de_htmls
#    ./scripts/importar_plantao.sh ~/Downloads/UTI_8B_28-05-2026_HTML_por_paciente
#    ./scripts/importar_plantao.sh ~/Downloads/UTI_BP_15_05_2026_Plantao
#
#  O script detecta automaticamente:
#    • Hospital: UTI 8B  → plantoes/8b/YYYY-MM-DD/
#               UTI BP  → plantoes/bp/YYYY-MM-DD/
#               Rotinas → rotinas/mercado/
#    • Data:    DD-MM-YYYY, DD_MM_YYYY ou YYYY-MM-DD no nome da pasta
# ════════════════════════════════════════════════════════════════════════════════
set -euo pipefail

CODEX_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BLUE='\033[1;34m'; GREEN='\033[1;32m'; YELLOW='\033[1;33m'
RED='\033[1;31m'; NC='\033[0m'

info()    { echo -e "${BLUE}▶ $*${NC}"; }
success() { echo -e "${GREEN}✓ $*${NC}"; }
warn()    { echo -e "${YELLOW}⚠ $*${NC}"; }
error()   { echo -e "${RED}✗ $*${NC}" >&2; exit 1; }

# ── Valida argumento ──────────────────────────────────────────────────────────
[[ $# -eq 0 ]] && error "Uso: $0 /caminho/para/pasta_htmls"
SOURCE_DIR="${1%/}"  # remove trailing slash
[[ -d "$SOURCE_DIR" ]] || error "Pasta não encontrada: $SOURCE_DIR"

FOLDER_NAME="$(basename "$SOURCE_DIR")"
info "Importando: $FOLDER_NAME"

# ── Detecta data (suporta DD-MM-YYYY, DD_MM_YYYY e YYYY-MM-DD) ───────────────
ISO_DATE=""

# Tenta YYYY-MM-DD (ex: 2026-05-28)
if [[ "$FOLDER_NAME" =~ ([0-9]{4})-([0-9]{2})-([0-9]{2}) ]]; then
    ISO_DATE="${BASH_REMATCH[1]}-${BASH_REMATCH[2]}-${BASH_REMATCH[3]}"

# Tenta DD-MM-YYYY (ex: 28-05-2026 ou 28_05_2026)
elif [[ "$FOLDER_NAME" =~ ([0-9]{2})[-_]([0-9]{2})[-_]([0-9]{4}) ]]; then
    ISO_DATE="${BASH_REMATCH[3]}-${BASH_REMATCH[2]}-${BASH_REMATCH[1]}"
fi

# Fallback: data de hoje
if [[ -z "$ISO_DATE" ]]; then
    ISO_DATE="$(date +%Y-%m-%d)"
    warn "Data não encontrada no nome da pasta. Usando hoje: $ISO_DATE"
fi

info "Data do plantão: $ISO_DATE"

# ── Detecta hospital ──────────────────────────────────────────────────────────
FOLDER_UPPER="$(echo "$FOLDER_NAME" | tr '[:lower:]' '[:upper:]')"

if [[ "$FOLDER_UPPER" =~ UTI[_-]?8B || "$FOLDER_UPPER" =~ 8B[_-]?UTI ]]; then
    HOSPITAL="8b"
    DEST_REL="plantoes/8b/$ISO_DATE"
elif [[ "$FOLDER_UPPER" =~ UTI[_-]?BP || "$FOLDER_UPPER" =~ BP[_-]?UTI || "$FOLDER_UPPER" =~ PLANTAO.*BP || "$FOLDER_UPPER" =~ BP.*PLANTAO ]]; then
    HOSPITAL="bp"
    DEST_REL="plantoes/bp/$ISO_DATE"
elif [[ "$FOLDER_UPPER" =~ MERCADO || "$FOLDER_UPPER" =~ DIARIO || "$FOLDER_UPPER" =~ MARKET ]]; then
    HOSPITAL="mercado"
    DEST_REL="rotinas/mercado"
else
    warn "Hospital não detectado no nome da pasta."
    echo -e "  Opções: ${BLUE}1${NC} UTI BP  |  ${BLUE}2${NC} UTI 8B  |  ${BLUE}3${NC} Rotinas/Mercado  |  ${BLUE}4${NC} Cancelar"
    read -rp "  Escolha [1/2/3/4]: " CHOICE
    case "$CHOICE" in
        1) HOSPITAL="bp";      DEST_REL="plantoes/bp/$ISO_DATE" ;;
        2) HOSPITAL="8b";      DEST_REL="plantoes/8b/$ISO_DATE" ;;
        3) HOSPITAL="mercado"; DEST_REL="rotinas/mercado" ;;
        *) error "Importação cancelada." ;;
    esac
fi

info "Hospital detectado: UTI $HOSPITAL  →  $DEST_REL"

# ── Copia arquivos ────────────────────────────────────────────────────────────
DEST_ABS="$CODEX_DIR/$DEST_REL"
mkdir -p "$DEST_ABS"

HTML_COUNT=$(find "$SOURCE_DIR" -maxdepth 1 -name "*.html" | wc -l | tr -d ' ')
[[ "$HTML_COUNT" -eq 0 ]] && error "Nenhum arquivo .html encontrado em: $SOURCE_DIR"

cp "$SOURCE_DIR"/*.html "$DEST_ABS/"
success "Copiados $HTML_COUNT arquivos HTML → $DEST_REL/"

# ── Regenera site-data.js ─────────────────────────────────────────────────────
info "Atualizando site-data.js..."
cd "$CODEX_DIR"
python3 scripts/gerar_site_data.py
success "site-data.js regenerado"

# ── Commit e push ─────────────────────────────────────────────────────────────
DATE_BR="${ISO_DATE:8:2}/${ISO_DATE:5:2}/${ISO_DATE:0:4}"
COMMIT_MSG="feat: plantão UTI $HOSPITAL — $DATE_BR ($HTML_COUNT HTMLs)"

git add "$DEST_REL/" assets/site-data.js

# Verifica se há algo staged antes de commitar
if git diff --cached --quiet; then
    warn "Nenhuma mudança detectada (arquivos já existem idênticos?). Nada commitado."
    exit 0
fi

git commit -m "$COMMIT_MSG

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"

info "Publicando no GitHub..."
git push origin main

echo ""
success "Dashboard atualizado! Acesse em ~2 min:"
echo -e "  ${BLUE}https://fernandomaga-ship-it.github.io/Plantao/${NC}"
