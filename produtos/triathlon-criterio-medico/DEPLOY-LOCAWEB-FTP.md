# Deploy FTP → Locaweb (drfernandomc.com.br)

Para o Cloud Agent publicar arquivos direto na hospedagem, configure **Secrets** no ambiente Cursor. **Nunca cole a senha no chat.**

## 1. Pegar dados no painel Locaweb

1. Abra [Central do Cliente Locaweb](https://www.locaweb.com.br/) → Hospedagem → **Administrar**
2. Vá em **Arquivos e FTP**
3. Anote:
   - **Host** (principal ou alternativo)
   - **Usuário FTP**
   - **Senha FTP** (ou redefina)
4. Pasta do site em geral: `public_html`

## 2. Cadastrar secrets no Cursor

Ambiente: [0f9b41b8-a87b-11f1-b532-320a589b8025](https://cursor.com/dashboard/cloud-agents/environments/e/0f9b41b8-a87b-11f1-b532-320a589b8025)

Crie estes secrets:

| Nome | Exemplo |
|---|---|
| `LOCAWEB_FTP_HOST` | `ftp.drfernandomc.com.br` ou o host do painel |
| `LOCAWEB_FTP_USER` | usuário FTP do painel |
| `LOCAWEB_FTP_PASSWORD` | senha FTP |
| `LOCAWEB_FTP_REMOTE_DIR` | `public_html` (opcional) |

Depois de salvar, **inicie um novo Cloud Agent** (secrets costumam valer em runs novos).

## 3. Publicar o curso

```bash
python3 scripts/deploy-locaweb-ftp.py --dry-run
python3 scripts/deploy-locaweb-ftp.py --target triathlon
```

Isso sobe:
`produtos/triathlon-criterio-medico/pagina-vendas.html` → `public_html/triathlon/index.html`

URL esperada: `https://www.drfernandomc.com.br/triathlon/`

## 4. Link no menu do site

No `index.html` do site (Locaweb), adicione no `<nav>`:

```html
<a href="./triathlon/">Curso Triathlon</a>
```

Se quiser, no próximo passo o agent também pode baixar o `index.html` atual, editar o menu e republicar via FTP.
