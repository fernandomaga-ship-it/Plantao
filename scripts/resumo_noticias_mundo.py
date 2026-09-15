#!/usr/bin/env python3
"""
Resumo diário de notícias internacionais (InfoMoney /mundo/).

Executado via GitHub Actions às 06:00 BRT (09:00 UTC).
Credenciais de e-mail vêm de variáveis de ambiente / GitHub Secrets.
"""

from __future__ import annotations

import json
import os
import smtplib
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from html import escape
from typing import Any

import requests
from bs4 import BeautifulSoup
from dateutil import parser

URL = "https://www.infomoney.com.br/mundo/"
HEADERS = {"User-Agent": "Mozilla/5.0"}
TIMEOUT = 15
MAX_LINKS = 20
OUTPUT_FILE = "noticias.json"

EMAIL_FROM = (
    os.environ.get("EMAIL_FROM", "").strip() or "drfernandomagalahes@gmail.com"
)
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD", "").strip()
EMAIL_TO = [
    address.strip()
    for address in (
        os.environ.get("EMAIL_TO", "").strip()
        or "drfernandomagalahes@gmail.com,francomotos@terra.com.br"
    ).split(",")
    if address.strip()
]


def get_links() -> list[str]:
    """Busca links de artigos na seção Mundo do InfoMoney."""
    response = requests.get(URL, headers=HEADERS, timeout=TIMEOUT)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    links: set[str] = set()

    for anchor in soup.find_all("a", href=True):
        href = anchor["href"].strip()

        # Converte links relativos para absolutos.
        if href.startswith("/"):
            href = f"https://www.infomoney.com.br{href}"

        # Mantém somente links de artigo da seção /mundo/.
        if href.startswith("https://www.infomoney.com.br/mundo/") and href.count("/") > 4:
            links.add(href.split("?")[0])

    return sorted(links)


def get_article(url: str) -> dict[str, Any] | None:
    """Extrai título, data e conteúdo de um artigo."""
    try:
        response = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        title_tag = soup.find("h1")
        time_tag = soup.find("time")
        if not title_tag or not time_tag:
            return None

        title = title_tag.get_text(strip=True)
        raw_date = time_tag.get("datetime") or time_tag.get_text(strip=True)
        date = parser.parse(raw_date)

        # Garante timezone para comparações consistentes.
        if date.tzinfo is None:
            date = date.replace(tzinfo=timezone.utc)

        paragraphs = soup.find_all("p")
        content = " ".join(p.get_text(" ", strip=True) for p in paragraphs).strip()
        if not content:
            return None

        return {
            "title": title,
            "date": date.isoformat(),
            "content": content,
            "url": url,
        }
    except requests.RequestException as error:
        print(f"Erro de rede ao processar {url}: {error}")
        return None
    except (ValueError, TypeError) as error:
        print(f"Erro de parsing ao processar {url}: {error}")
        return None


def filter_recent(articles: list[dict[str, Any]], hours: int = 48) -> list[dict[str, Any]]:
    """Filtra artigos publicados nas últimas `hours` horas."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    recent_articles: list[dict[str, Any]] = []

    for article in articles:
        try:
            article_date = parser.isoparse(article["date"])
            if article_date > cutoff:
                recent_articles.append(article)
        except (KeyError, ValueError, TypeError):
            continue

    return recent_articles


def save_articles_to_json(articles: list[dict[str, Any]], filename: str = OUTPUT_FILE) -> None:
    """Salva os artigos em JSON com UTF-8 e indentação legível."""
    with open(filename, "w", encoding="utf-8") as file:
        json.dump(articles, file, ensure_ascii=False, indent=2)


def send_email_with_json(filename: str, recent_articles: list[dict[str, Any]]) -> None:
    """Envia o arquivo JSON por e-mail com corpo HTML e resumo das 5 principais notícias."""
    if not EMAIL_PASSWORD:
        raise RuntimeError(
            "EMAIL_PASSWORD não configurada. "
            "Defina o secret EMAIL_PASSWORD no GitHub Actions."
        )

    current_date = datetime.now().strftime("%d/%m/%Y")

    sorted_articles = sorted(recent_articles, key=lambda x: x.get("date", ""), reverse=True)
    top_articles = sorted_articles[:5]
    articles_html = ""
    for index, article in enumerate(top_articles, start=1):
        raw_content = " ".join(article.get("content", "").split())
        summary = raw_content[:220].strip()
        if len(raw_content) > 220:
            summary += "..."

        title = escape(article.get("title", "Sem título"))
        summary = escape(summary)

        articles_html += (
            f"<li style='margin-bottom:12px;'>"
            f"<strong>{index}. {title}</strong><br>"
            f"<span style='color:#444;'>{summary}</span>"
            f"</li>"
        )

    if not articles_html:
        articles_html = "<li>Nenhuma notícia recente encontrada nas últimas 48 horas.</li>"

    message = EmailMessage()
    message["From"] = EMAIL_FROM
    message["To"] = ", ".join(EMAIL_TO)
    message["Subject"] = f"📈 Resumo de Notícias Internacionais - {current_date}"

    plain_content = (
        f"Resumo de Notícias Internacionais - {current_date}\n\n"
        f"Foram encontradas {len(recent_articles)} notícias recentes nas últimas 48 horas.\n"
        "Consulte o anexo noticias.json para os dados completos."
    )
    message.set_content(plain_content)

    html_content = f"""
    <html>
      <body style="font-family: Arial, sans-serif; line-height: 1.5; color: #222;">
        <h2 style="margin-bottom: 8px;">📈 Resumo de Notícias Internacionais - {current_date}</h2>
        <p>Foram encontradas <strong>{len(recent_articles)}</strong> notícias recentes nas últimas 48 horas.</p>
        <p style="margin-bottom: 6px;"><strong>Top 5 notícias:</strong></p>
        <ol>
          {articles_html}
        </ol>
        <p>O arquivo <strong>{filename}</strong> segue em anexo com todos os detalhes.</p>
      </body>
    </html>
    """
    message.add_alternative(html_content, subtype="html")

    with open(filename, "rb") as file:
        message.add_attachment(
            file.read(),
            maintype="application",
            subtype="json",
            filename=filename,
        )

    try:
        with smtplib.SMTP("smtp.gmail.com", 587, timeout=TIMEOUT) as server:
            server.starttls()
            server.login(EMAIL_FROM, EMAIL_PASSWORD)
            server.send_message(message)
        print(f"✅ E-mail enviado para {EMAIL_TO}")
    except smtplib.SMTPException as error:
        print(f"Erro ao enviar e-mail: {error}")
        raise


def main() -> None:
    print("Buscando links...")
    links = get_links()
    print(f"Links encontrados: {len(links)}")

    print("Lendo notícias...")
    articles: list[dict[str, Any]] = []
    for link in links[:MAX_LINKS]:
        article = get_article(link)
        if article:
            articles.append(article)

    print(f"Artigos válidos: {len(articles)}")

    recent_articles = filter_recent(articles, hours=48)
    print(f"Artigos nas últimas 48h: {len(recent_articles)}")

    save_articles_to_json(recent_articles, OUTPUT_FILE)
    print(f"✅ Arquivo salvo: {OUTPUT_FILE}")

    send_email_with_json(OUTPUT_FILE, recent_articles)


if __name__ == "__main__":
    main()
