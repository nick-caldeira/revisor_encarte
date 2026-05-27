import streamlit as st
import anthropic
import base64
import io
import json
import pandas as pd
from pathlib import Path

# ── Load API key from Streamlit secrets (Streamlit Cloud) ──────────────────────
import streamlit as st
_secrets_key = None
try:
    _secrets_key = st.secrets.get("ANTHROPIC_API_KEY")
except Exception:
    pass

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Revisor de Encartes — Grupo LLE",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Custom CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500&display=swap');

html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }

.main .block-container { max-width: 860px; padding-top: 2rem; padding-bottom: 3rem; }

.brand-pill {
    display: inline-flex; align-items: center; gap: 8px;
    background: white; border: 1px solid #e5e5e3;
    border-radius: 100px; padding: 4px 14px 4px 10px;
    margin-bottom: 1rem; font-size: 11px; letter-spacing: 0.07em;
    text-transform: uppercase; color: #888780; font-weight: 500;
}
.brand-dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; background: #E24B4A; }

h1 { font-weight: 500 !important; font-size: 2rem !important; }

.upload-label {
    font-size: 10px; font-weight: 500; letter-spacing: 0.07em;
    text-transform: uppercase; color: #888780; margin-bottom: 4px;
}

.criteria-row {
    display: flex; align-items: center; gap: 10px;
    font-size: 13px; color: #444441; margin-bottom: 6px;
}
.criteria-num {
    width: 22px; height: 22px; border-radius: 50%;
    background: #E24B4A; color: white;
    display: flex; align-items: center; justify-content: center;
    font-size: 10px; font-weight: 500; flex-shrink: 0;
}

.result-card {
    background: white; border: 1px solid #e5e5e3;
    border-radius: 12px; padding: 1.5rem; margin-top: 1.5rem;
}
.result-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 1rem; }
.badge-error { background: #FCEBEB; color: #791F1F; padding: 3px 12px; border-radius: 100px; font-size: 12px; font-weight: 500; }
.badge-ok    { background: #E1F5EE; color: #085041; padding: 3px 12px; border-radius: 100px; font-size: 12px; font-weight: 500; }

div[data-testid="stButton"] > button {
    background: #E24B4A; color: white; border: none;
    font-weight: 500; font-size: 14px; padding: 0.6rem 2rem;
    border-radius: 8px; width: 100%;
    transition: opacity 0.15s;
}
div[data-testid="stButton"] > button:hover { background: #c73d3c; border: none; }
div[data-testid="stButton"] > button:disabled { opacity: 0.4; }
</style>
""", unsafe_allow_html=True)


# ── Helpers ─────────────────────────────────────────────────────────────────────

def file_to_base64(file_bytes: bytes) -> str:
    return base64.standard_b64encode(file_bytes).decode("utf-8")


def read_spreadsheet(uploaded_file) -> str:
    """Parse spreadsheet and return as markdown-style text for the prompt."""
    name = uploaded_file.name.lower()
    try:
        if name.endswith(".csv"):
            df = pd.read_csv(uploaded_file)
        elif name.endswith(".xls"):
            df = pd.read_excel(uploaded_file, engine="xlrd")
        else:
            df = pd.read_excel(uploaded_file, engine="openpyxl")
        return df.to_markdown(index=False)
    except Exception as e:
        return f"[Erro ao ler planilha: {e}]"


SYSTEM_PROMPT = """Você é um revisor especializado de encartes e folhetos de materiais de construção do Grupo LLE.

Você receberá:
1. O conteúdo da planilha base com os dados oficiais dos produtos (código, descrição, preço, e outros campos relevantes).
2. Um ou mais encartes/folhetos em formato de imagem ou PDF.

Sua tarefa é analisar cada item visível nos encartes e compará-lo com a planilha base, verificando obrigatoriamente nesta ordem:
1. Código — o código do produto no encarte corresponde ao da planilha?
2. Descrição — a descrição está correta e alinhada com o cadastro?
3. Preço — o preço anunciado bate com o valor da planilha?
4. Imagem — a imagem representa o produto correto (quando possível inferir)?
5. Tag Preço Único — a tag de preço único está presente e correta quando aplicável?

Responda APENAS com um objeto JSON válido no seguinte formato (sem markdown, sem texto antes ou depois):
{
  "resumo": {
    "total_itens": <número de itens analisados>,
    "total_divergencias": <número de divergências encontradas>,
    "status": "ok" | "divergencias"
  },
  "divergencias": [
    {
      "item": "<nome/descrição do produto no encarte>",
      "campo": "<Código | Descrição | Preço | Imagem | Tag Preço Único>",
      "valor_encarte": "<o que está no encarte>",
      "valor_correto": "<o que deveria estar conforme a planilha>",
      "observacao": "<observação adicional opcional>"
    }
  ],
  "itens_ok": [
    "<lista de produtos sem divergências>"
  ]
}

Se não houver divergências, retorne "divergencias": [] e "status": "ok".
Seja preciso e objetivo. Não invente dados — se não conseguir identificar um campo claramente, indique "Não identificado" no valor."""


def build_messages(planilha_text: str, encartes: list) -> list:
    """Build the messages array for the Claude API call."""
    content = []

    # Spreadsheet as text
    content.append({
        "type": "text",
        "text": f"## PLANILHA BASE — DADOS OFICIAIS DOS PRODUTOS\n\n{planilha_text}"
    })

    # Each encarte as image
    for i, (name, mime, b64) in enumerate(encartes, 1):
        content.append({
            "type": "text",
            "text": f"\n## ENCARTE {i}: {name}"
        })
        content.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": mime,
                "data": b64,
            }
        })

    content.append({
        "type": "text",
        "text": "\nAgora analise todos os encartes acima contra a planilha base e retorne o JSON de divergências conforme instruído."
    })

    return [{"role": "user", "content": content}]


def mime_type(filename: str) -> str:
    ext = Path(filename).suffix.lower()
    return {
        ".pdf":  "application/pdf",
        ".jpg":  "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png":  "image/png",
    }.get(ext, "image/jpeg")


def run_analysis(api_key: str, planilha_text: str, encartes: list) -> dict:
    client = anthropic.Anthropic(api_key=api_key)
    messages = build_messages(planilha_text, encartes)

    response = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=messages,
    )

    raw = response.content[0].text.strip()
    # Strip markdown fences if model wraps in ```json
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())


# ── UI ──────────────────────────────────────────────────────────────────────────

st.markdown('<div class="brand-pill"><span class="brand-dot"></span> Grupo LLE · Materiais de Construção</div>', unsafe_allow_html=True)
st.title("Revisor de Encartes")
st.markdown("<p style='color:#888780; font-size:14px; margin-top:-0.5rem; margin-bottom:1.5rem;'>Carregue a planilha base e os encartes para identificar divergências automaticamente.</p>", unsafe_allow_html=True)

# ── API Key ────────────────────────────────────────────────────────────────────
with st.expander("🔑 Configuração da API", expanded=not bool(st.session_state.get("api_key"))):
    # Pre-fill from Streamlit secrets if available
    default_key = st.session_state.get("api_key") or _secrets_key or ""
    if _secrets_key and not st.session_state.get("api_key"):
        st.session_state["api_key"] = _secrets_key

    api_key_input = st.text_input(
        "Chave da API Anthropic",
        type="password",
        value=default_key,
        placeholder="sk-ant-...",
        help="Obtenha sua chave em https://console.anthropic.com"
    )
    if api_key_input:
        st.session_state["api_key"] = api_key_input
        if _secrets_key and api_key_input == _secrets_key:
            st.success("✓ Chave carregada automaticamente via Secrets.")
        else:
            st.success("Chave salva para esta sessão.")

st.divider()

# ── Upload columns ─────────────────────────────────────────────────────────────
col1, col2 = st.columns(2)

with col1:
    st.markdown('<p class="upload-label">📊 Campo 1 — Planilha base</p>', unsafe_allow_html=True)
    planilha_file = st.file_uploader(
        "Dados oficiais dos produtos",
        type=["xlsx", "xls", "csv"],
        key="planilha",
        label_visibility="collapsed",
    )
    if planilha_file:
        st.success(f"✓ {planilha_file.name}")

with col2:
    st.markdown('<p class="upload-label">🗂 Campo 2 — Encartes / Folhetos</p>', unsafe_allow_html=True)
    encarte_files = st.file_uploader(
        "Materiais a serem revisados",
        type=["pdf", "jpg", "jpeg", "png"],
        accept_multiple_files=True,
        key="encartes",
        label_visibility="collapsed",
    )
    if encarte_files:
        st.success(f"✓ {len(encarte_files)} arquivo(s) carregado(s)")

st.divider()

# ── Criteria checklist ─────────────────────────────────────────────────────────
st.markdown("<p style='font-size:11px; font-weight:500; letter-spacing:0.07em; text-transform:uppercase; color:#888780;'>Critérios de revisão aplicados</p>", unsafe_allow_html=True)
criterios = ["Código do produto", "Descrição do item", "Preço anunciado", "Imagem do produto", "Tag preço único"]
cols = st.columns(5)
for i, (col, c) in enumerate(zip(cols, criterios), 1):
    col.markdown(f"""
    <div style="text-align:center; background:white; border:1px solid #e5e5e3; border-radius:10px; padding:10px 6px;">
        <div style="width:22px; height:22px; border-radius:50%; background:#E24B4A; color:white; font-size:10px; font-weight:500; display:flex; align-items:center; justify-content:center; margin:0 auto 6px;">{i}</div>
        <p style="font-size:11px; color:#444441; margin:0; line-height:1.3;">{c}</p>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br/>", unsafe_allow_html=True)

# ── Run button ─────────────────────────────────────────────────────────────────
ready = planilha_file and encarte_files and st.session_state.get("api_key")

if st.button("🔍 Iniciar revisão", disabled=not ready):
    with st.spinner("Analisando arquivos com Claude..."):
        try:
            # Parse spreadsheet
            planilha_text = read_spreadsheet(planilha_file)

            # Prepare encartes
            encartes = []
            for f in encarte_files:
                raw = f.read()
                b64 = file_to_base64(raw)
                mt = mime_type(f.name)
                encartes.append((f.name, mt, b64))

            # Call Claude
            result = run_analysis(st.session_state["api_key"], planilha_text, encartes)
            st.session_state["result"] = result

        except json.JSONDecodeError as e:
            st.error(f"Erro ao interpretar resposta da API: {e}")
        except anthropic.AuthenticationError:
            st.error("Chave da API inválida. Verifique em console.anthropic.com")
        except anthropic.BadRequestError as e:
            st.error(f"Erro na requisição: {e}")
        except Exception as e:
            st.error(f"Erro inesperado: {e}")

# ── Results ────────────────────────────────────────────────────────────────────
if "result" in st.session_state:
    result = st.session_state["result"]
    resumo = result.get("resumo", {})
    divergencias = result.get("divergencias", [])
    itens_ok = result.get("itens_ok", [])

    st.divider()
    st.markdown("### Resultado da análise")

    # Summary metrics
    m1, m2, m3 = st.columns(3)
    m1.metric("Itens analisados", resumo.get("total_itens", "—"))
    m2.metric("Divergências", resumo.get("total_divergencias", len(divergencias)))
    m3.metric("Itens corretos", len(itens_ok))

    # Divergencias table
    if divergencias:
        st.markdown(f"<br/><span style='background:#FCEBEB; color:#791F1F; padding:4px 12px; border-radius:100px; font-size:12px; font-weight:500;'>⚠ {len(divergencias)} divergência(s) encontrada(s)</span>", unsafe_allow_html=True)
        st.markdown("<br/>", unsafe_allow_html=True)

        df_div = pd.DataFrame(divergencias)
        df_div.columns = ["Item", "Campo", "No encarte", "Correto", "Observação"] if len(df_div.columns) == 5 else df_div.columns
        st.dataframe(df_div, use_container_width=True, hide_index=True)

        # Download button
        csv = df_div.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="⬇ Exportar divergências (.csv)",
            data=csv,
            file_name="divergencias_encarte.csv",
            mime="text/csv",
        )
    else:
        st.success("✅ Nenhuma divergência encontrada. Todos os itens estão corretos!")

    # Items OK
    if itens_ok:
        with st.expander(f"Ver {len(itens_ok)} item(ns) sem divergência"):
            for item in itens_ok:
                st.markdown(f"- {item}")

# ── Footer ──────────────────────────────────────────────────────────────────────
st.markdown("<br/><br/>")
st.markdown("<p style='text-align:center; font-size:11px; color:#D3D1C7;'>Grupo LLE · Revisor de Encartes · Powered by Claude</p>", unsafe_allow_html=True)
