import re
import streamlit as st
import pandas as pd
import requests
import io
import unicodedata

# ── Configurações ────────────────────────────────────────────────────────────

LINK_PATIO      = "https://usinaxavantes-my.sharepoint.com/:x:/g/personal/jefferson_ferreira_usinaxavantes_onmicrosoft_com/IQAc3sFoxYzbSqL-j6ZoJWq-AbBgxlJpnRNc8KsTOFWuCqI?e=3JIXRs"
SHEET_PLANEJADO = "Pátio_Máquina_Planejado"

st.set_page_config(
    page_title="Pátio de Máquinas Planejado — Usina Xavantes",
    page_icon="⚙️",
    layout="wide"
)

st.markdown("""
<style>
    html, body {
        background-color: #0f0f1a !important;
        margin: 0 !important;
        padding: 0 !important;
    }
    .stApp { background-color: #0f0f1a !important; min-height: 100vh; }
    [data-testid="stAppViewContainer"] { background-color: #0f0f1a !important; }
    [data-testid="stHeader"] { background-color: #0f0f1a !important; border-bottom: none !important; }
    [data-testid="stToolbar"] { background-color: #0f0f1a !important; }
    .main { background-color: #0f0f1a !important; }
    .block-container {
        background-color: #0f0f1a !important;
        padding-top: 3rem !important;
        min-height: 100vh;
    }
    h1, h2, h3, h4, p, label { color: #e0e0f0 !important; }
    [data-testid="stSidebar"] { background-color: #1e1e2e; }
    [data-testid="stSidebar"] * { color: #e0e0f0 !important; }
    .separador { border: none; border-top: 1px solid #2a2a4a; margin: 16px 0; }

    .stButton > button {
        width: 100% !important;
        font-size: 13px !important;
        padding: 12px 4px !important;
        font-weight: 700 !important;
        border-radius: 10px !important;
        margin: 3px 0 !important;
        background-color: #1e1e32 !important;
        color: #d0d0f0 !important;
        border: 1px solid #3a3a5a !important;
        transition: all 0.2s !important;
        letter-spacing: 0.5px !important;
    }
    .stButton > button:hover {
        background-color: #2a2a4a !important;
        border-color: #7c6af7 !important;
        color: #ffffff !important;
    }

    /* Expanders (listas suspensas no rodapé) */
    [data-testid="stExpander"] {
        background-color: #1a1a2e !important;
        border: 1px solid #3a3a5a !important;
        border-radius: 12px !important;
        margin-bottom: 12px !important;
    }
    [data-testid="stExpander"] summary {
        color: #e0e0f0 !important;
        font-weight: 700 !important;
    }

    /* Resumo geral */
    .resumo-box {
        background:#1a1a2e;
        border:1px solid #3a3a5a;
        border-radius:12px;
        padding:16px 24px;
        margin-bottom:24px;
        display:flex;
        justify-content:space-between;
        align-items:center;
        flex-wrap:wrap;
        gap:16px 28px;
    }
    .resumo-item { text-align:right; }
    .resumo-label { color:#8888aa; font-size:11px; display:block; }
    .resumo-valor { font-size:22px; font-weight:700; display:block; }

    /* Itens das listas suspensas de status */
    .status-list-item {
        color:#e0e0f0;
        font-size:13px;
        padding:6px 0;
        border-bottom:1px solid #2a2a4a;
    }
    .status-list-item:last-child { border-bottom:none; }
    .status-list-item .base-tag {
        font-weight:700;
        margin-right:6px;
    }

    /* Card completo de cada base */
    .base-card {
        background:#1a1a2e;
        border:1px solid #3a3a5a;
        border-radius:14px;
        padding:16px;
        margin-bottom:16px;
        height: 100%;
    }
    .base-card-alert {
        border:1px solid #ef4444aa !important;
    }
    .base-card-alert-manutencao {
        border:1px solid #f59e0baa !important;
    }
    .base-card-header {
        display:flex;
        justify-content:space-between;
        align-items:center;
        margin-bottom:12px;
        padding-bottom:10px;
        border-bottom:1px solid #2a2a4a;
    }
    .base-card-title {
        color:#e0e0f0;
        font-size:17px;
        font-weight:800;
        letter-spacing:0.5px;
    }
    .base-card-power {
        color:#22c55e;
        font-size:15px;
        font-weight:700;
    }
    .base-card-transformer {
        background:#12121f;
        border:1px solid #f59e0b55;
        border-radius:10px;
        padding:10px 12px;
        margin-bottom:12px;
    }
    .base-card-transformer-title {
        color:#f59e0b;
        font-size:12px;
        font-weight:800;
        letter-spacing:0.5px;
        margin-bottom:8px;
    }
    .base-card-transformer-grid {
        display:flex;
        flex-wrap:wrap;
        gap:8px 16px;
    }
    .base-card-transformer-grid .item {
        min-width:110px;
    }
    .base-card-transformer-grid .label {
        display:block;
        color:#8888aa;
        font-size:10px;
        font-weight:700;
        text-transform:uppercase;
    }
    .base-card-transformer-grid .value {
        display:block;
        color:#e0e0f0;
        font-size:13px;
        font-weight:600;
    }
    .base-card-machine {
        padding:8px 0;
        border-top:1px solid #2a2a4a;
    }
    .base-card-machine:first-child {
        border-top:none;
    }
    .base-card-machine-row {
        display:flex;
        gap:14px;
    }
    .base-card-machine .col {
        flex:1;
        min-width:0;
    }
    .base-card-machine .tag {
        display:inline-block;
        font-size:10px;
        font-weight:800;
        letter-spacing:0.5px;
        margin-bottom:3px;
    }
    .base-card-machine .tag.motor { color:#7c6af7; }
    .base-card-machine .tag.alt { color:#06b6d4; }
    .base-card-machine .modelo {
        display:block;
        color:#e0e0f0;
        font-size:13px;
        font-weight:600;
        white-space: normal;
    }
    .base-card-machine .serie {
        display:block;
        color:#8888aa;
        font-size:10px;
    }
    .status-badge {
        display:inline-block;
        font-size:10px;
        font-weight:700;
        padding:2px 8px;
        border-radius:20px;
        margin-bottom:6px;
    }
    .status-disponivel {
        background:#22c55e22;
        color:#22c55e;
        border:1px solid #22c55e55;
    }
    .status-indisponivel {
        background:#ef444422;
        color:#ef4444;
        border:1px solid #ef444455;
    }
    .status-manutencao {
        background:#f59e0b22;
        color:#f59e0b;
        border:1px solid #f59e0b55;
    }
    .status-indefinido {
        background:#8888aa22;
        color:#8888aa;
        border:1px solid #8888aa44;
    }

    /* Card de base vazia (sem máquinas) */
    .base-card-empty {
        background:#14141f;
        border:1px dashed #2a2a4a;
        border-radius:14px;
        padding:16px;
        margin-bottom:16px;
        height: 100%;
        display:flex;
        flex-direction:column;
        justify-content:center;
        align-items:center;
        text-align:center;
        min-height: 90px;
    }
    .base-card-empty .title {
        color:#5a5a7a;
        font-size:15px;
        font-weight:700;
        margin-bottom:4px;
    }
    .base-card-empty .subtitle {
        color:#3a3a5a;
        font-size:11px;
    }

    /* Card da base 17 (container, desabilitada) */
    .base-card-container {
        background:#080810;
        border:2px dashed #2a2a4a;
        border-radius:14px;
        padding:16px;
        margin-bottom:16px;
        height: 100%;
        display:flex;
        flex-direction:column;
        justify-content:center;
        align-items:center;
        text-align:center;
        min-height: 90px;
    }
    .base-card-container .title {
        color:#3a3a6a;
        font-size:13px;
        font-weight:700;
        letter-spacing:1px;
    }
</style>
""", unsafe_allow_html=True)


# ── utilidades ────────────────────────────────────────────────────────────────

def converter_link(link):
    sep = "&" if "?" in link else "?"
    return link + sep + "download=1"


def norm(texto):
    t = str(texto).strip()
    t = unicodedata.normalize("NFKD", t)
    t = "".join(c for c in t if not unicodedata.combining(c))
    return t.upper()


def encontrar_coluna(colunas, alvos):
    if isinstance(alvos, str):
        alvos = [alvos]
    for alvo in alvos:
        for c in colunas:
            if norm(str(c)) == norm(alvo):
                return c
    for alvo in alvos:
        for c in colunas:
            if norm(alvo) in norm(str(c)) or norm(str(c)) in norm(alvo):
                return c
    return None


def extrair_numero_base(valor):
    s = str(valor).strip()
    try:
        f = float(s)
        if f == int(f):
            return int(f)
    except (ValueError, TypeError):
        pass
    nums = re.findall(r'\d+', s)
    return int(nums[0]) if nums else None


def extrair_posicao(valor):
    s = str(valor).strip().upper()
    match = re.search(r'\.([A-Z])$', s)
    if match:
        return match.group(1)
    match = re.search(r'\d([A-Z])$', s)
    if match:
        return match.group(1)
    return ""


def safe_val(row, col, default="—"):
    if col is None:
        return default
    try:
        v = row[col]
    except (KeyError, TypeError):
        return default
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return default
    s = str(v).strip()
    return s if s and s.lower() != "nan" else default


def formatar_potencia(kw):
    if kw <= 0:
        return "—"

    value = kw
    unit = " kW"
    if kw >= 1000:
        value = kw / 1000
        unit = " MW"

    if unit == " MW":
        formatted_value = f"{value:.2f}"
    else:
        formatted_value = f"{value:.0f}"

    parts = formatted_value.split('.')
    integer_part = parts[0]
    decimal_part = parts[1] if len(parts) > 1 else ""

    n = len(integer_part)
    formatted_integer_part = ""
    for i, digit in enumerate(integer_part):
        formatted_integer_part += digit
        if (n - 1 - i) % 3 == 0 and (n - 1 - i) != 0:
            formatted_integer_part += "."

    final_string = formatted_integer_part
    if decimal_part:
        final_string += "," + decimal_part

    return final_string + unit


def contar_maquinas(df):
    if df is None or "pot_maquina_num" not in df.columns:
        return 0
    return int((df["pot_maquina_num"] > 0).sum())


def classificar_status(status_raw):
    """
    Classifica o texto bruto da coluna Status em:
    'disponivel', 'indisponivel', 'manutencao' ou 'indefinido'.
    Ajuste esta função caso a planilha use termos diferentes dos previstos aqui.
    """
    s = norm(status_raw)
    if not s or s in ("—", "NAN", ""):
        return "indefinido"
    if "MANUTEN" in s:
        return "manutencao"
    if "INDISPON" in s:
        return "indisponivel"
    if "DISPON" in s:
        return "disponivel"
    if any(k in s for k in ["PARADA", "INATIV", "QUEBRAD", "DEFEITO"]):
        return "indisponivel"
    if any(k in s for k in ["OPERANDO", "ATIVA", "FUNCIONANDO", "OK"]):
        return "disponivel"
    return "indefinido"


def status_badge_html(status_raw):
    classe = classificar_status(status_raw)
    if classe == "disponivel":
        emoji, label = "🟢", safe_val_str(status_raw, "Disponível")
    elif classe == "indisponivel":
        emoji, label = "🔴", safe_val_str(status_raw, "Indisponível")
    elif classe == "manutencao":
        emoji, label = "🟡", safe_val_str(status_raw, "Manutenção")
    else:
        emoji, label = "⚪", safe_val_str(status_raw, "Não informado")
    return f'<span class="status-badge status-{classe}">{emoji} {label}</span>'


def safe_val_str(status_raw, fallback):
    s = str(status_raw).strip()
    if not s or s.lower() == "nan" or s == "—":
        return fallback
    return s


# ── carregamento dos dados ───────────────────────────────────────────────────

@st.cache_data(ttl=300)
def baixar_bytes():
    try:
        r = requests.get(converter_link(LINK_PATIO), timeout=20)
        r.raise_for_status()
        return r.content, None
    except Exception as e:
        return None, str(e)


def processar_aba(xl, sheet_name):
    try:
        df_raw = pd.read_excel(xl, sheet_name=sheet_name, header=None, nrows=20)
    except Exception as e:
        return None, f"Erro ao ler aba '{sheet_name}': {e}"

    header_row = None
    for i, row in df_raw.iterrows():
        valores = [norm(str(v)) for v in row.values]
        if norm("BASE") in valores:
            header_row = i
            break

    if header_row is None:
        return None, f"Coluna BASE não encontrada na aba '{sheet_name}'"

    df = pd.read_excel(xl, sheet_name=sheet_name, header=header_row)

    col_base      = encontrar_coluna(df.columns, ["BASE"])
    col_transf    = encontrar_coluna(df.columns, [
        "N° SÉRIE TRANSFORMADOR", "N° SERIE TRANSFORMADOR",
        "SERIE TRANSFORMADOR",    "SÉRIE TRANSFORMADOR",
        "N SERIE TRANSFORMADOR",  "TRANSFORMADOR"
    ])
    col_fab_trafo = encontrar_coluna(df.columns, ["FABRICANTE TRAFO", "FABRICANTE TRANSFORMADOR", "FABRICANTE"])
    col_pot_trafo = encontrar_coluna(df.columns, ["POTENCIA TRAFO", "POTÊNCIA TRAFO", "POTENCIA KVA", "POTÊNCIA KVA"])
    col_imp_trafo = encontrar_coluna(df.columns, ["IMPEDANCIA %", "IMPEDÂNCIA %", "IMPEDANCIA", "IMPEDÂNCIA"])
    col_bt        = encontrar_coluna(df.columns, ["BAIXA TENSAO KV", "BAIXA TENSÃO KV", "BAIXA TENSAO", "BAIXA TENSÃO", "BT KV"])
    col_mt        = encontrar_coluna(df.columns, ["MEDIA TENSAO KV", "MÉDIA TENSÃO KV", "MEDIA TENSAO", "MÉDIA TENSÃO", "MT KV"])
    col_relacao   = encontrar_coluna(df.columns, ["RELACAO", "RELAÇÃO"])
    col_pot_maq   = encontrar_coluna(df.columns, ["POTENCIA MAQUINA", "POTÊNCIA MAQUINA", "POTENCIA MÁQUINA", "POTÊNCIA MÁQUINA"])
    col_mod_mot   = encontrar_coluna(df.columns, ["MODELO MOTOR", "MOTOR MODELO"])
    col_ser_mot   = encontrar_coluna(df.columns, ["SÉRIE MOTOR", "SERIE MOTOR"])
    col_mod_alt   = encontrar_coluna(df.columns, ["MODELO ALTERNADOR", "ALTERNADOR MODELO"])
    col_ser_alt   = encontrar_coluna(df.columns, ["SÉRIE ALTERNADOR", "SERIE ALTERNADOR"])
    col_status    = encontrar_coluna(df.columns, ["STATUS", "SITUACAO", "SITUAÇÃO"])

    if col_base is None:
        return None, f"Coluna BASE não encontrada. Colunas: {list(df.columns)}"

    cols_usar = {
        "base_raw":             col_base,
        "serie_transformador":  col_transf,
        "fab_trafo":            col_fab_trafo,
        "pot_trafo":            col_pot_trafo,
        "imp_trafo":            col_imp_trafo,
        "bt_kv":                col_bt,
        "mt_kv":                col_mt,
        "relacao":              col_relacao,
        "pot_maquina":          col_pot_maq,
        "modelo_motor":         col_mod_mot,
        "serie_motor":          col_ser_mot,
        "modelo_alternador":    col_mod_alt,
        "serie_alternador":     col_ser_alt,
        "status":               col_status,
    }
    cols_validas = {k: v for k, v in cols_usar.items() if v is not None}

    df = df[[v for v in cols_validas.values()]].copy()
    df.columns = list(cols_validas.keys())

    # --- Extração de base e posição a partir do valor bruto ---
    df["base"]    = df["base_raw"].apply(extrair_numero_base)
    df["posicao"] = df["base_raw"].apply(extrair_posicao)

    # --- Descartar linhas sem base válida ANTES de converter para int
    #     e ANTES de montar o "label"
    df = df.dropna(subset=["base"])
    df["base"] = df["base"].astype(int)
    df = df[df["base"].between(1, 36)]

    # Só agora, com "base" já validada e sem NaN, é seguro montar o label
    df["label"] = df.apply(
        lambda r: f"{int(r['base'])}.{r['posicao']}" if r["posicao"] else str(int(r["base"])),
        axis=1
    )

    if "pot_maquina" in df.columns:
        df["pot_maquina_num"] = pd.to_numeric(
            df["pot_maquina"].astype(str).str.replace(",", "."), errors="coerce"
        ).fillna(0)
    else:
        df["pot_maquina_num"] = 0

    if "modelo_motor"      not in df.columns: df["modelo_motor"]      = "—"
    if "modelo_alternador" not in df.columns: df["modelo_alternador"] = "—"
    if "serie_transformador" not in df.columns: df["serie_transformador"] = "—"
    if "fab_trafo"           not in df.columns: df["fab_trafo"]           = "—"
    if "pot_trafo"           not in df.columns: df["pot_trafo"]           = "—"
    if "imp_trafo"           not in df.columns: df["imp_trafo"]           = "—"
    if "bt_kv"               not in df.columns: df["bt_kv"]               = "—"
    if "mt_kv"               not in df.columns: df["mt_kv"]               = "—"
    if "relacao"             not in df.columns: df["relacao"]             = "—"
    if "status"              not in df.columns: df["status"]              = "—"

    df["status_classe"] = df["status"].apply(classificar_status)

    df = df.sort_values(["base", "posicao"]).reset_index(drop=True)
    return df, None


def carregar_dados_planejado():
    conteudo, erro = baixar_bytes()
    if erro:
        return None, f"Erro ao baixar: {erro}", []

    xl          = pd.ExcelFile(io.BytesIO(conteudo))
    sheet_names = xl.sheet_names

    if SHEET_PLANEJADO not in sheet_names:
        return None, f"Aba '{SHEET_PLANEJADO}' não encontrada", sheet_names

    df, err = processar_aba(xl, SHEET_PLANEJADO)
    return df, err, sheet_names


# ── card completo de uma base ─────────────────────────────────────────────────

def render_card_base(base_num, machines_in_base):
    """Renderiza o card completo de uma base: transformador + máquina(s), sempre visível."""
    if machines_in_base.empty:
        st.markdown(
            f"""
            <div class="base-card-empty">
                <div class="title">BASE {base_num:02d}</div>
                <div class="subtitle">Sem máquina planejada</div>
            </div>
            """,
            unsafe_allow_html=True
        )
        return

    # --- Agora soma apenas a potência das máquinas com status "Disponível" ---
    total_pot = machines_in_base.loc[
        machines_in_base["status_classe"] == "disponivel", "pot_maquina_num"
    ].sum()

    transformador_data = machines_in_base.iloc[0]
    tem_indisponivel = (machines_in_base["status_classe"] == "indisponivel").any()
    tem_manutencao   = (machines_in_base["status_classe"] == "manutencao").any()

    machines_html = ""
    for _, row in machines_in_base.iterrows():
        machines_html += f"""
        <div class="base-card-machine">
            {status_badge_html(row.get('status', '—'))}
            <div class="base-card-machine-row">
                <div class="col">
                    <span class="tag motor">MOTOR</span>
                    <span class="modelo">{safe_val(row, 'modelo_motor')}</span>
                    <span class="serie">Nº Série: {safe_val(row, 'serie_motor')}</span>
                </div>
                <div class="col">
                    <span class="tag alt">ALTERNADOR</span>
                    <span class="modelo">{safe_val(row, 'modelo_alternador')}</span>
                    <span class="serie">Nº Série: {safe_val(row, 'serie_alternador')}</span>
                </div>
            </div>
        </div>
        """

    if tem_indisponivel:
        card_class = "base-card base-card-alert"
    elif tem_manutencao:
        card_class = "base-card base-card-alert-manutencao"
    else:
        card_class = "base-card"

    st.markdown(
        f"""
        <div class="{card_class}">
            <div class="base-card-header">
                <span class="base-card-title">BASE {base_num:02d}</span>
                <span class="base-card-power">{formatar_potencia(total_pot)}</span>
            </div>
            <div class="base-card-transformer">
                <div class="base-card-transformer-title">⟷ TRANSFORMADOR</div>
                <div class="base-card-transformer-grid">
                    <div class="item">
                        <span class="label">Nº Série</span>
                        <span class="value">{safe_val(transformador_data, 'serie_transformador')}</span>
                    </div>
                    <div class="item">
                        <span class="label">Fabricante</span>
                        <span class="value">{safe_val(transformador_data, 'fab_trafo')}</span>
                    </div>
                    <div class="item">
                        <span class="label">Potência kVA</span>
                        <span class="value">{safe_val(transformador_data, 'pot_trafo')}</span>
                    </div>
                    <div class="item">
                        <span class="label">Impedância %</span>
                        <span class="value">{safe_val(transformador_data, 'imp_trafo')}</span>
                    </div>
                    <div class="item">
                        <span class="label">BT / MT kV</span>
                        <span class="value">{safe_val(transformador_data, 'bt_kv')} / {safe_val(transformador_data, 'mt_kv')}</span>
                    </div>
                    <div class="item">
                        <span class="label">Relação</span>
                        <span class="value">{safe_val(transformador_data, 'relacao')}</span>
                    </div>
                </div>
            </div>
            {machines_html}
        </div>
        """,
        unsafe_allow_html=True
    )


def render_card_base_17():
    st.markdown(
        """
        <div class="base-card-container">
            <div class="title">⬛ BASE 17 — CONTAINER (DESABILITADA)</div>
        </div>
        """,
        unsafe_allow_html=True
    )


def render_lista_status(df_lista, cor_hex):
    """Monta o HTML de uma lista de máquinas (indisponíveis ou em manutenção) para uso dentro de um expander."""
    itens_html = ""
    for _, row in df_lista.iterrows():
        itens_html += f"""
        <div class="status-list-item">
            <span class="base-tag" style="color:{cor_hex};">Base {row['label']}</span>
            {safe_val(row, 'modelo_motor')} / {safe_val(row, 'modelo_alternador')}
            — <em>{safe_val(row, 'status')}</em>
        </div>
        """
    st.markdown(itens_html, unsafe_allow_html=True)


# ── tela principal ───────────────────────────────────────────────────────────

def tela_patio_planejado(df):
    st.markdown("# 📋 Usina Xavantes S/A - Pátio de Máquinas")
    st.markdown("<hr class='separador'>", unsafe_allow_html=True)

    if df is None or df.empty:
        st.error("Não foi possível carregar os dados do pátio planejado.")
        return

    df_com_maquina = df[df["pot_maquina_num"] > 0]

    total_maquinas        = contar_maquinas(df)
    potencia_disponivel   = df_com_maquina.loc[df_com_maquina["status_classe"] == "disponivel",   "pot_maquina_num"].sum()
    potencia_indisponivel = df_com_maquina.loc[df_com_maquina["status_classe"] == "indisponivel", "pot_maquina_num"].sum()
    potencia_manutencao   = df_com_maquina.loc[df_com_maquina["status_classe"] == "manutencao",   "pot_maquina_num"].sum()

    qtd_indisponiveis  = int((df_com_maquina["status_classe"] == "indisponivel").sum())
    qtd_manutencao     = int((df_com_maquina["status_classe"] == "manutencao").sum())
    qtd_nao_informado  = int((df_com_maquina["status_classe"] == "indefinido").sum())

    resumo_extra = ""
    if qtd_nao_informado > 0:
        resumo_extra = f"""
        <div class="resumo-item">
            <span class="resumo-label">Status não informado</span>
            <span class="resumo-valor" style="color:#8888aa;">{qtd_nao_informado}</span>
        </div>
        """

    st.markdown(
        f"""
        <div class="resumo-box">
            <h3 style="color:#e0e0f0; margin:0; padding:0;">Total de Máquinas: {total_maquinas}</h3>
            <div class="resumo-item">
                <span class="resumo-label">Potência Disponível</span>
                <span class="resumo-valor" style="color:#22c55e;">{formatar_potencia(potencia_disponivel)}</span>
            </div>
            <div class="resumo-item">
                <span class="resumo-label">Potência Indisponível</span>
                <span class="resumo-valor" style="color:#ef4444;">{formatar_potencia(potencia_indisponivel)}</span>
            </div>
            <div class="resumo-item">
                <span class="resumo-label">Potência em Manutenção</span>
                <span class="resumo-valor" style="color:#f59e0b;">{formatar_potencia(potencia_manutencao)}</span>
            </div>
            <div class="resumo-item">
                <span class="resumo-label">Máquinas Indisponíveis</span>
                <span class="resumo-valor" style="color:#ef4444;">{qtd_indisponiveis}</span>
            </div>
            <div class="resumo-item">
                <span class="resumo-label">Máquinas em Manutenção</span>
                <span class="resumo-valor" style="color:#f59e0b;">{qtd_manutencao}</span>
            </div>
            {resumo_extra}
        </div>
        """,
        unsafe_allow_html=True
    )

    N_COLS = 3
    todas_bases = list(range(1, 37))

    for i in range(0, len(todas_bases), N_COLS):
        linha = todas_bases[i:i + N_COLS]
        cols = st.columns(N_COLS)
        for idx, base_num in enumerate(linha):
            with cols[idx]:
                if base_num == 17:
                    render_card_base_17()
                else:
                    machines_in_base = df[df["base"] == base_num].sort_values("posicao")
                    render_card_base(base_num, machines_in_base)

    # --- Listas suspensas no rodapé da página ---
    st.markdown("<hr class='separador'>", unsafe_allow_html=True)
    st.markdown("### 📑 Detalhamento por Status")

    df_indisponiveis = df_com_maquina[df_com_maquina["status_classe"] == "indisponivel"].sort_values(["base", "posicao"])
    with st.expander(f"🔴 Máquinas Indisponíveis ({len(df_indisponiveis)})"):
        if df_indisponiveis.empty:
            st.info("Nenhuma máquina indisponível.")
        else:
            render_lista_status(df_indisponiveis, "#ef4444")

    df_manutencao = df_com_maquina[df_com_maquina["status_classe"] == "manutencao"].sort_values(["base", "posicao"])
    with st.expander(f"🟡 Máquinas em Manutenção ({len(df_manutencao)})"):
        if df_manutencao.empty:
            st.info("Nenhuma máquina em manutenção.")
        else:
            render_lista_status(df_manutencao, "#f59e0b")


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    df_plan, erro, sheet_names = carregar_dados_planejado()

    with st.sidebar:
        st.markdown("## ⚙️ Pátio de Máquinas")
        st.markdown("---")
        st.markdown("**Usina Xavantes**")
        st.markdown("<small style='color:#8888bb'>Módulo: Planejado</small>", unsafe_allow_html=True)
        st.markdown("---")

        if st.button("🔄 Recarregar dados", key="sidebar_btn_recarregar"):
            st.cache_data.clear()
            st.rerun()

    if erro:
        st.error(f"Erro ao carregar Pátio Planejado: {erro}")
        if sheet_names:
            st.info(f"Abas disponíveis: {sheet_names}")
    else:
        tela_patio_planejado(df_plan)


main()
