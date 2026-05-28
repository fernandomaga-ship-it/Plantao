#!/usr/bin/env python3
"""
Publica o card do dia no Instagram via Graph API.

Variáveis de ambiente obrigatórias:
  IG_USER_ID       — ID da conta Instagram Business (ex: 17841401485250823)
  IG_ACCESS_TOKEN  — Token de página de longa duração

Variáveis opcionais:
  IG_HANDLE        — handle para o rodapé do card (ex: @fernandomagalhaescoutinho)
  GITHUB_REPO      — owner/repo para montar a URL da imagem (ex: fernandomaga-ship-it/Plantao)
  TOPIC_ID         — forçar tópico específico; vazio = rotação automática
"""

import os, sys, json, urllib.request, urllib.parse
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
IG_API     = "https://graph.facebook.com/v19.0"

# ── Validar variáveis ────────────────────────────────────────────────────────
USER_ID = os.environ.get("IG_USER_ID", "").strip()
TOKEN   = os.environ.get("IG_ACCESS_TOKEN", "").strip()
if not USER_ID or not TOKEN:
    print("[post_api] ERRO: IG_USER_ID e IG_ACCESS_TOKEN são obrigatórios.", file=sys.stderr)
    sys.exit(1)

# ── Selecionar tópico do dia ─────────────────────────────────────────────────
topics   = json.loads((SCRIPT_DIR / "topics.json").read_text())
topic_id = os.environ.get("TOPIC_ID", "").strip()

if topic_id and topic_id != "auto":
    topic = next((t for t in topics if t["id"] == topic_id), None)
    if not topic:
        print(f"[post_api] Tópico '{topic_id}' não encontrado — usando rotação.", file=sys.stderr)
        topic = None

if not topic_id or topic_id == "auto" or not topic:
    from datetime import date
    day_of_year = date.today().timetuple().tm_yday
    topic = topics[day_of_year % len(topics)]

print(f"[post_api] Tópico: {topic['titulo']}", file=sys.stderr)

# ── Montar URL pública da imagem ─────────────────────────────────────────────
repo  = os.environ.get("GITHUB_REPO", "fernandomaga-ship-it/Plantao")
IMAGE_URL = f"https://raw.githubusercontent.com/{repo}/main/assets/instagram/card-today.png"
print(f"[post_api] URL da imagem: {IMAGE_URL}", file=sys.stderr)

# ── Montar legenda ────────────────────────────────────────────────────────────
handle  = os.environ.get("IG_HANDLE", "@fernandomagalhaescoutinho")
pontos  = "\n".join(f"{i+1}. {p}" for i, p in enumerate(topic["pontos"]))
caption = (
    f"\U0001F4DA {topic['titulo']}\n"
    f"{topic['subtitulo']}\n\n"
    f"{pontos}\n\n"
    f"━━━━━━━━━━━━━━━\n"
    f"Salva esse card para revisar antes do AMIB/TEMI! \U0001F499\n\n"
    f"{topic['hashtags']}"
)

# ── Helpers de request ────────────────────────────────────────────────────────
def api_post(path: str, payload: dict) -> dict:
    url  = f"{IG_API}/{path}"
    data = urllib.parse.urlencode(payload).encode()
    req  = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"[post_api] HTTP {e.code}: {body}", file=sys.stderr)
        sys.exit(1)

# ── 1. Criar container de mídia ───────────────────────────────────────────────
print("[post_api] Criando container de mídia...", file=sys.stderr)
container = api_post(f"{USER_ID}/media", {
    "image_url":    IMAGE_URL,
    "caption":      caption,
    "access_token": TOKEN,
})
creation_id = container.get("id")
if not creation_id:
    print(f"[post_api] Falha ao criar container: {container}", file=sys.stderr)
    sys.exit(1)
print(f"[post_api] Container ID: {creation_id}", file=sys.stderr)

# ── 2. Publicar ────────────────────────────────────────────────────────────────
print("[post_api] Publicando...", file=sys.stderr)
result = api_post(f"{USER_ID}/media_publish", {
    "creation_id":  creation_id,
    "access_token": TOKEN,
})
media_id = result.get("id")
if not media_id:
    print(f"[post_api] Falha ao publicar: {result}", file=sys.stderr)
    sys.exit(1)

print(f"[post_api] ✅ Publicado! Media ID: {media_id}", file=sys.stderr)
print(json.dumps({"success": True, "mediaId": media_id, "topic": topic["titulo"]}))
