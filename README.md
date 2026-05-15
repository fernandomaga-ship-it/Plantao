# Plantão

Website estático para GitHub Pages com dashboard médico, busca, dark mode e navegação entre arquivos HTML de plantão.

## Como abrir localmente

1. Rode `./serve-local.sh`.
2. Abra `http://127.0.0.1:8000`.
3. Se quiser outra porta, rode `./serve-local.sh 8080`.

Também funciona abrindo `index.html` diretamente no navegador.

## Estrutura

- `index.html`: dashboard principal.
- `styles.css`: layout responsivo para desktop, iPad e iPhone.
- `assets/app.js`: busca, filtros, dark mode e visualizador com anterior/próximo.
- `assets/site-data.js`: manifesto estático dos HTMLs publicados.
- `scripts/generate-site-data.mjs`: gera automaticamente o manifesto.
- `plantoes/bp/`: arquivos de plantão por leito/paciente.
- `.github/workflows/pages.yml`: deploy automático do GitHub Pages no branch `main`.
- `CNAME.example`: base para futuro domínio personalizado.

## Atualizar lista de plantões

Após adicionar novos arquivos `.html`, rode:

```bash
node scripts/generate-site-data.mjs
```

Depois faça commit e push para `main`. O GitHub Pages publica automaticamente.
