# Revisor de Encartes — Grupo LLE

App para revisão automática de encartes, folhetos e catálogos de materiais de construção, usando **Claude (Anthropic)** para análise visual dos arquivos comparando-os com a planilha base de produtos.

---

## Como funciona

1. O usuário carrega a **planilha base** (`.xlsx`, `.xls` ou `.csv`) com os dados oficiais dos produtos
2. O usuário carrega um ou mais **encartes** (`.pdf`, `.jpg`, `.png`)
3. O app envia tudo para o **Claude** via API, que analisa visualmente cada item e retorna as divergências estruturadas
4. O resultado aparece em tabela, com opção de exportar para `.csv`

### Critérios de revisão (aplicados automaticamente)
| # | Campo |
|---|-------|
| 1 | Código do produto |
| 2 | Descrição do item |
| 3 | Preço anunciado |
| 4 | Imagem do produto |
| 5 | Tag preço único |

---

## Deploy no Streamlit Community Cloud (grátis)

### Pré-requisitos
- Conta no [GitHub](https://github.com)
- Conta no [Streamlit Community Cloud](https://streamlit.io/cloud)
- Chave de API Anthropic: [console.anthropic.com](https://console.anthropic.com)

### Passo a passo

#### 1. Suba o projeto no GitHub

```bash
# Clone ou crie um repositório novo e adicione os arquivos:
# app.py
# requirements.txt
# README.md

git init
git add .
git commit -m "feat: revisor de encartes LLE"
git remote add origin https://github.com/SEU_USUARIO/SEU_REPO.git
git push -u origin main
```

#### 2. Acesse o Streamlit Cloud

Vá para [share.streamlit.io](https://share.streamlit.io) e clique em **"New app"**.

#### 3. Configure o deploy

| Campo | Valor |
|-------|-------|
| Repository | `SEU_USUARIO/SEU_REPO` |
| Branch | `main` |
| Main file path | `app.py` |

#### 4. Configure a chave da API como Secret

No Streamlit Cloud, antes de fazer deploy:

1. Clique em **"Advanced settings"**
2. Vá em **Secrets**
3. Adicione:

```toml
ANTHROPIC_API_KEY = "sk-ant-..."
```

> **Alternativa**: o app também aceita a chave digitada direto na interface (campo de configuração no topo da página), útil para testes locais.

#### 5. Deploy

Clique em **"Deploy!"** — o app estará online em ~2 minutos.

---

## Rodar localmente

```bash
# 1. Clone o repositório
git clone https://github.com/SEU_USUARIO/SEU_REPO.git
cd SEU_REPO

# 2. Crie um ambiente virtual (recomendado)
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 3. Instale as dependências
pip install -r requirements.txt

# 4. Rode o app
streamlit run app.py
```

O app abrirá automaticamente em `http://localhost:8501`.

---

## Estrutura do projeto

```
revisor-encartes-lle/
├── app.py              # App principal (Streamlit + Claude API)
├── requirements.txt    # Dependências Python
├── README.md           # Este arquivo
└── index.html          # Versão web standalone (opcional)
```

---

## Custos estimados de API

O modelo `claude-opus-4-5` é utilizado para análise de imagens e texto.

| Cenário | Custo estimado |
|---------|---------------|
| 1 encarte (1 página) + planilha pequena | ~$0.02–$0.05 |
| 5 encartes (1–2 páginas cada) | ~$0.10–$0.25 |
| Uso mensal intenso (100 revisões) | ~$5–$20 |

> Valores aproximados. Consulte [anthropic.com/pricing](https://anthropic.com/pricing) para preços atualizados.

---

## Tecnologias

- [Streamlit](https://streamlit.io) — interface web
- [Anthropic Claude](https://anthropic.com) — análise de documentos por IA
- [Pandas](https://pandas.pydata.org) — leitura de planilhas
- [OpenPyXL](https://openpyxl.readthedocs.io) — suporte a `.xlsx`
