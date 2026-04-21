import re
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import requests
import io
import unicodedata

LINK_PATIO      = "https://usinaxavantes-my.sharepoint.com/:x:/g/personal/jefferson_ferreira_usinaxavantes_onmicrosoft_com/IQAc3sFoxYzbSqL-j6ZoJWq-AbBgxlJpnRNc8KsTOFWuCqI?e=3JIXRs"
SHEET_PLANEJADO = "Pátio_Máquina_Planejado"

st.set_page_config(
    page_title="Pátio de Máquinas — Usina Xavantes",
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
    .stApp {
        background-color: #0f0f1a !important;
        min-height: 100vh;
    }
    [data-testid="stAppViewContainer"] {
        background-color: #0f0f1a !important;
    }
    [data-testid="stHeader"] {
        background-color: #0f0f1a !important;
        border-bottom: none !important;
    }
    [data-testid="stToolbar"] {
        background-color: #0f0f1a !important;
    }
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

    /* Estilo geral para TODOS os botões */
    .stButton > button {
        width: 100% !important;
        font-size: 13px !important;
        padding: 12px 4px !important;
        font-weight: 700 !important;
        border-radius: 10px !important;
        margin: 3px 0 !important;
        background-color: #1e1e32 !important; /* Fundo escuro */
        color: #d0d0f0 !important; /* Texto claro */
        border: 1px solid #3a3a5a !important; /* Borda discreta */
        transition: all 0.2s !important;
        letter-spacing: 0.5px !important;
    }
    .stButton > button:hover {
        background-color: #2a2a4a !important; /* Fundo um pouco mais claro no hover */
        border-color: #7c6af7 !important; /* Borda roxa no hover */
        color: #ffffff !important; /* Texto branco no hover */
    }

    /* multiselect dark */
    [data-testid="stMultiSelect"] > div {
        background-color: #1a1a2e !important;
        border-color: #3a3a5a !important;
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
    if kw >= 1000:
        return f"{kw / 1000:,.2f} MW".replace(",", ".")
    return f"{kw:,.0f} kW".replace(",", ".")


def contar_maquinas(df):
    if df is None or "pot_maquina_num" not in df.columns:
        return 0
    return int((df["pot_maquina_num"] > 0).sum())


def opcoes_filtro(df, col):
    if df is None or col not in df.columns:
        return []
    vals = df[col].dropna().unique().tolist()
    vals = sorted([str(v) for v in vals if str(v).strip() not in ("", "—", "nan")])
    return vals


def aplicar_filtros(df, filtro_motor, filtro_alt, filtro_origem):
    if df is None or df.empty:
        return df, set()
    mask = pd.Series([True] * len(df), index=df.index)
    if filtro_motor:
        mask &= df["modelo_motor"].isin(filtro_motor) if "modelo_motor" in df.columns else mask
    if filtro_alt:
        mask &= df["modelo_alternador"].isin(filtro_alt) if "modelo_alternador" in df.columns else mask
    if filtro_origem:
        mask &= df["origem"].isin(filtro_origem) if "origem" in df.columns else mask
    df_filtrado     = df[mask]
    bases_com_match = set(df_filtrado["base"].tolist())
    return df_filtrado, bases_com_match


# ── CACHE APENAS NOS BYTES ────────────────────────────────────────────────────

@st.cache_data(ttl=300)
def baixar_bytes():
    try:
        r = requests.get(converter_link(LINK_PATIO), timeout=20)
        r.raise_for_status()
        return r.content, None
    except Exception as e:
        return None, str(e)


def processar_aba(xl, sheet_name, tem_origem=False):
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
    col_origem    = encontrar_coluna(df.columns, ["ORIGEM"]) if tem_origem else None

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
        "origem":               col_origem,
    }
    cols_validas = {k: v for k, v in cols_usar.items() if v is not None}

    df = df[[v for v in cols_validas.values()]].copy()
    df.columns = list(cols_validas.keys())

    df["base"]    = df["base_raw"].apply(extrair_numero_base)
    df["posicao"] = df["base_raw"].apply(extrair_posicao)
    df["label"]   = df.apply(
        lambda r: f"{int(r['base'])}.{r['posicao']}" if r["posicao"] else str(int(r["base"])),
        axis=1
    )

    df = df.dropna(subset=["base"])
    df["base"] = df["base"].astype(int)
    df = df[df["base"].between(1, 36)]

    if "pot_maquina" in df.columns:
        df["pot_maquina_num"] = pd.to_numeric(
            df["pot_maquina"].astype(str).str.replace(",", "."), errors="coerce"
        ).fillna(0)
    else:
        df["pot_maquina_num"] = 0

    if "origem"            not in df.columns: df["origem"]            = "—"
    if "modelo_motor"      not in df.columns: df["modelo_motor"]      = "—"
    if "modelo_alternador" not in df.columns: df["modelo_alternador"] = "—"

    df = df.sort_values(["base", "posicao"]).reset_index(drop=True)
    return df, None


def carregar_dados():
    conteudo, erro = baixar_bytes()
    if erro:
        return None, None, {"atual": f"Erro ao baixar: {erro}", "planejado": None}, []

    xl          = pd.ExcelFile(io.BytesIO(conteudo))
    sheet_names = xl.sheet_names

    sheet_atual = None
    for nome in sheet_names:
        n = norm(nome)
        if ("PATIO" in n or "MAQUINA" in n) and "PLAN" not in n:
            sheet_atual = nome
            break

    df_atual, err_atual = (
        processar_aba(xl, sheet_atual, tem_origem=False)
        if sheet_atual
        else (None, "Aba atual não encontrada")
    )
    df_plan, err_plan = (
        processar_aba(xl, SHEET_PLANEJADO, tem_origem=True)
        if SHEET_PLANEJADO in sheet_names
        else (None, f"Aba '{SHEET_PLANEJADO}' não encontrada")
    )

    return df_atual, df_plan, {"atual": err_atual, "planejado": err_plan}, sheet_names


# ── componentes visuais ───────────────────────────────────────────────────────

def get_posicoes(df, base_num):
    if df is None or df.empty:
        return pd.DataFrame()
    return df[df["base"] == base_num].copy()


def linha_trafo(label, valor):
    cor_val = "#e0e0f0" if valor != "—" else "#4a4a6a"
    return (
        f'<div style="display:flex; justify-content:space-between; align-items:center; '
        f'padding:6px 0; border-bottom:1px solid #1e1e2e;">'
        f'<span style="color:#8888aa; font-size:11px;">{label}</span>'
        f'<span style="color:{cor_val}; font-size:12px; font-weight:600;">{valor}</span>'
        f'</div>'
    )


def bloco_transformador(row_transf):
    serie   = safe_val(row_transf, "serie_transformador")
    fab     = safe_val(row_transf, "fab_trafo")
    pot     = safe_val(row_transf, "pot_trafo")
    imp     = safe_val(row_transf, "imp_trafo")
    bt      = safe_val(row_transf, "bt_kv")
    mt      = safe_val(row_transf, "mt_kv")
    relacao = safe_val(row_transf, "relacao")

    tensao = (f"{bt} / {mt}" if bt != "—" and mt != "—"
              else bt if bt != "—"
              else mt if mt != "—"
              else "—")

    cor = "#f59e0b" if serie != "—" else "#3a3a5a"
    svg = (
        '<svg width="40" height="48" viewBox="0 0 52 62" fill="none" xmlns="http://www.w3.org/2000/svg">'
        f'<rect x="8" y="14" width="36" height="34" rx="4" fill="#0a0a14" stroke="{cor}" stroke-width="2"/>'
        f'<ellipse cx="19" cy="31" rx="7" ry="10" fill="none" stroke="{cor}" stroke-width="1.8"/>'
        f'<ellipse cx="33" cy="31" rx="7" ry="10" fill="none" stroke="{cor}" stroke-width="1.8"/>'
        f'<line x1="26" y1="2" x2="26" y2="14" stroke="{cor}" stroke-width="2"/>'
        f'<line x1="19" y1="2" x2="19" y2="14" stroke="{cor}" stroke-width="2"/>'
        f'<line x1="33" y1="2" x2="33" y2="14" stroke="{cor}" stroke-width="2"/>'
        f'<line x1="26" y1="48" x2="26" y2="60" stroke="{cor}" stroke-width="2"/>'
        f'<line x1="19" y1="48" x2="19" y2="60" stroke="{cor}" stroke-width="2"/>'
        f'<line x1="33" y1="48" x2="33" y2="60" stroke="{cor}" stroke-width="2"/>'
        '</svg>'
    )
    linhas = (
        linha_trafo("Nº de Série", serie)
        + linha_trafo("Fabricante", fab)
        + linha_trafo("Potência kVA", pot)
        + linha_trafo("Impedância %", imp)
        + linha_trafo("Tensão kV  Baixa / Média", tensao)
        + linha_trafo("Relação", relacao)
    )
    return (
        f'<div style="background:#0a0a14; border:1px solid {cor}55; border-radius:12px; '
        f'padding:16px 20px; margin-top:14px;">'
        f'<div style="display:flex; align-items:center; gap:14px; margin-bottom:12px;">'
        + svg +
        f'<div style="color:{cor}; font-size:12px; font-weight:700; '
        f'text-transform:uppercase; letter-spacing:0.5px;">Transformador — Base (único)</div>'
        f'</div>' + linhas + f'</div>'
    )


def painel_detalhe(base_num, df_posicoes, cor, tem_origem=False):
    n            = len(df_posicoes)
    pot_base_kw  = df_posicoes["pot_maquina_num"].sum() if "pot_maquina_num" in df_posicoes.columns else 0
    pot_base_str = formatar_potencia(pot_base_kw)

    st.markdown(
        f'<div style="background:{cor}18; border:1px solid {cor}55; border-radius:14px; '
        f'padding:14px 20px; margin-bottom:12px; display:flex; justify-content:space-between; align-items:center;">'
        f'<div style="color:{cor}; font-size:15px; font-weight:700; text-transform:uppercase; letter-spacing:1px;">'
        f'⚙️ Base {base_num:02d} — {n} posição(ões)</div>'
        f'<div style="text-align:right;">'
        f'<div style="color:#8888aa; font-size:10px;">Potência total da base</div>'
        f'<div style="color:#22c55e; font-size:16px; font-weight:700;">{pot_base_str}</div>'
        f'</div></div>',
        unsafe_allow_html=True
    )

    posicoes = [row for _, row in df_posicoes.iterrows()]
    n_cols   = min(n, 3)
    grupos   = [posicoes[i:i + n_cols] for i in range(0, n, n_cols)]

    for grupo in grupos:
        cols = st.columns(n_cols)
        for idx, row in enumerate(grupo):
            label        = row.get("label", f"{base_num}.?")
            modelo_motor = safe_val(row, "modelo_motor")
            serie_motor  = safe_val(row, "serie_motor")
            modelo_alt   = safe_val(row, "modelo_alternador")
            serie_alt    = safe_val(row, "serie_alternador")
            origem       = safe_val(row, "origem") if tem_origem else "—"

            pot_num = row["pot_maquina_num"] if "pot_maquina_num" in row.index else 0
            tp  = formatar_potencia(pot_num)
            cp  = "#22c55e" if pot_num > 0 else "#4a4a6a"
            cm  = "#e0e0f0" if modelo_motor != "—" else "#4a4a6a"
            cs  = "#e0e0f0" if serie_motor  != "—" else "#4a4a6a"
            ca  = "#e0e0f0" if modelo_alt   != "—" else "#4a4a6a"
            csa = "#e0e0f0" if serie_alt    != "—" else "#4a4a6a"

            origem_html = ""
            if tem_origem and origem != "—":
                origem_html = (
                    f'<div style="margin-top:10px; padding:6px 10px; background:#1a1a2e; '
                    f'border-left:3px solid {cor}; border-radius:4px;">'
                    f'<span style="color:#8888aa; font-size:10px;">Origem: </span>'
                    f'<span style="color:{cor}; font-size:11px; font-weight:700;">{origem}</span>'
                    f'</div>'
                )

            with cols[idx]:
                st.markdown(
                    f'<div style="background:#0a0a14; border:1px solid {cor}44; '
                    f'border-radius:12px; padding:14px 16px; margin-bottom:10px;">'
                    f'<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">'
                    f'<div style="color:{cor}; font-size:14px; font-weight:800; letter-spacing:1px;">{label}</div>'
                    f'<div style="color:{cp}; font-size:12px; font-weight:700;">{tp}</div>'
                    f'</div>'
                    f'<div style="display:grid; grid-template-columns:1fr 1fr; gap:0 16px;">'
                    f'<div>'
                    f'<div style="color:#7c6af7; font-size:10px; font-weight:700; text-transform:uppercase;">🔧 Motor</div>'
                    f'<div style="color:#8888aa; font-size:10px; margin-top:8px;">Modelo</div>'
                    f'<div style="color:{cm}; font-size:13px; font-weight:600;">{modelo_motor}</div>'
                    f'<div style="color:#8888aa; font-size:10px; margin-top:8px;">Nº de Série</div>'
                    f'<div style="color:{cs}; font-size:13px; font-weight:600;">{serie_motor}</div>'
                    f'</div>'
                    f'<div>'
                    f'<div style="color:#22c55e; font-size:10px; font-weight:700; text-transform:uppercase;">⚡ Alternador</div>'
                    f'<div style="color:#8888aa; font-size:10px; margin-top:8px;">Modelo</div>'
                    f'<div style="color:{ca}; font-size:13px; font-weight:600;">{modelo_alt}</div>'
                    f'<div style="color:#8888aa; font-size:10px; margin-top:8px;">Nº de Série</div>'
                    f'<div style="color:{csa}; font-size:13px; font-weight:600;">{serie_alt}</div>'
                    f'</div>'
                    f'</div>'
                    + origem_html +
                    f'</div>',
                    unsafe_allow_html=True
                )

    row_transf = None
    for _, row in df_posicoes.iterrows():
        if safe_val(row, "serie_transformador") != "—":
            row_transf = row
            break
    if row_transf is None:
        row_transf = df_posicoes.iloc[0]

    st.markdown(bloco_transformador(row_transf), unsafe_allow_html=True)
    st.markdown("<hr class='separador'>", unsafe_allow_html=True)


def resumo_filtro(df_filtrado, cor):
    if df_filtrado is None or df_filtrado.empty:
        st.markdown(
            f'<div style="background:#1a0a0a; border:1px solid #f0383855; border-radius:10px; '
            f'padding:10px 16px; margin-bottom:12px; text-align:center;">'
            f'<div style="color:#f03838; font-size:12px; font-weight:700;">'
            f'Nenhuma máquina encontrada com esses filtros</div></div>',
            unsafe_allow_html=True
        )
        return

    total_maq    = int((df_filtrado["pot_maquina_num"] > 0).sum())
    total_pot    = formatar_potencia(df_filtrado["pot_maquina_num"].sum())
    bases_unicas = df_filtrado["base"].nunique()

    st.markdown(
        f'<div style="background:{cor}12; border:1px solid {cor}44; border-radius:10px; '
        f'padding:10px 16px; margin-bottom:12px;">'
        f'<div style="color:{cor}; font-size:11px; font-weight:700; margin-bottom:6px;">🔍 RESULTADO DO FILTRO</div>'
        f'<div style="display:flex; gap:24px;">'
        f'<div><div style="color:#8888aa; font-size:10px;">MÁQUINAS</div>'
        f'<div style="color:#e0e0f0; font-size:16px; font-weight:700;">{total_maq}</div></div>'
        f'<div><div style="color:#8888aa; font-size:10px;">POTÊNCIA</div>'
        f'<div style="color:#22c55e; font-size:16px; font-weight:700;">{total_pot}</div></div>'
        f'<div><div style="color:#8888aa; font-size:10px;">BASES</div>'
        f'<div style="color:{cor}; font-size:16px; font-weight:700;">{bases_unicas}</div></div>'
        f'</div></div>',
        unsafe_allow_html=True
    )


def renderizar_botao_base(base_num, key_prefix, bases_destaque):
    _sel   = st.session_state.get("base_sel") == base_num
    _match = bases_destaque is not None and base_num in bases_destaque
    _sem   = bases_destaque is not None and base_num not in bases_destaque

    if _sel:
        lbl = f"✓ Base {base_num:02d}"
    elif _match:
        lbl = f"★ Base {base_num:02d}"
    else:
        lbl = f"Base {base_num:02d}"

    if st.button(lbl, key=f"{key_prefix}btn_{base_num}"):
        st.session_state["base_sel"] = None if _sel else base_num
        st.rerun()


def injetar_estilos_botoes(filtro_ativo: bool):
    """
    JS aplicado diretamente no DOM — contorna limitações do CSS do Streamlit.
    Identifica botões pelo texto e aplica cores corretas.
    """
    flag = "true" if filtro_ativo else "false"
    components.html(f"""
    <script>
    function estilizarBotoes() {{
        var filtroAtivo = {flag};
        var botoes = window.parent.document.querySelectorAll('button');

        botoes.forEach(function(btn) {{
            var txt = (btn.innerText || btn.textContent || '').trim();

            if (txt.startsWith('✓')) {{
                // base selecionada — roxo
                btn.style.setProperty('background-color', '#5b21b6', 'important');
                btn.style.setProperty('color',            '#ffffff',  'important');
                btn.style.setProperty('border-color',     '#7c6af7',  'important');
                btn.style.setProperty('font-weight',      '900',      'important');
                btn.style.setProperty('box-shadow', '0 0 10px #7c6af766', 'important');

            }} else if (txt.startsWith('★')) {{
                // match de filtro — verde
                btn.style.setProperty('background-color', '#14532d', 'important');
                btn.style.setProperty('color',            '#22c55e', 'important');
                btn.style.setProperty('border-color',     '#22c55e', 'important');
                btn.style.setProperty('font-weight',      '900',     'important');
                btn.style.setProperty('box-shadow', '0 0 10px #22c55e55', 'important');

            }} else if (txt.startsWith('Base ')) {{
                if (filtroAtivo) {{
                    // sem match — apagado
                    btn.style.setProperty('background-color', '#0f0f18', 'important');
                    btn.style.setProperty('color',            '#2a2a4a', 'important');
                    btn.style.setProperty('border-color',     '#1a1a28', 'important');
                    btn.style.setProperty('box-shadow',       'none',    'important');
                }} else {{
                    // normal
                    btn.style.setProperty('background-color', '#1e1e32', 'important');
                    btn.style.setProperty('color',            '#d0d0f0', 'important');
                    btn.style.setProperty('border-color',     '#3a3a5a', 'important');
                    btn.style.setProperty('font-weight',      '700',     'important');
                    btn.style.setProperty('box-shadow',       'none',    'important');
                }}
            }}
        }});
    }}

    // aplica em múltiplos momentos para garantir que o DOM já renderizou
    setTimeout(estilizarBotoes, 80);
    setTimeout(estilizarBotoes, 300);
    setTimeout(estilizarBotoes, 700);
    setTimeout(estilizarBotoes, 1500);
    </script>
    """, height=0)


# ── telas ─────────────────────────────────────────────────────────────────────

def tela_patio(df, titulo, cor_a, cor_b, tem_origem=False,
               filtro_motor=None, filtro_alt=None, filtro_origem=None):

    if st.button("← Voltar", key="btn_voltar"):
        st.session_state["tela"]     = "home"
        st.session_state["base_sel"] = None
        st.rerun()

    filtro_ativo = bool(filtro_motor or filtro_alt or filtro_origem)
    if filtro_ativo:
        df_view, bases_destaque = aplicar_filtros(df, filtro_motor, filtro_alt, filtro_origem)
    else:
        df_view        = df
        bases_destaque = None

    pot_total_kw  = df_view["pot_maquina_num"].sum() if df_view is not None and "pot_maquina_num" in df_view.columns else 0
    pot_total_str = formatar_potencia(pot_total_kw)

    st.markdown(f"# ⚙️ {titulo}")

    col_sub1, col_sub2 = st.columns([3, 1])
    with col_sub1:
        st.markdown(
            "<p style='color:#8888aa; font-size:13px; margin-top:-10px;'>"
            "Lado A: Bases 01–17 &nbsp;|&nbsp; Lado B: Bases 18–36 &nbsp;|&nbsp; "
            "Clique em uma base para ver as posições e equipamentos.</p>",
            unsafe_allow_html=True
        )
    with col_sub2:
        label_pot = "Potência filtrada" if filtro_ativo else "Potência total disponível"
        st.markdown(
            f'<div style="background:#0a1a0a; border:1px solid #22c55e55; border-radius:10px; '
            f'padding:8px 16px; text-align:center; margin-top:-14px;">'
            f'<div style="color:#8888aa; font-size:10px;">{label_pot}</div>'
            f'<div style="color:#22c55e; font-size:20px; font-weight:700;">{pot_total_str}</div>'
            f'</div>',
            unsafe_allow_html=True
        )

    if filtro_ativo:
        resumo_filtro(df_view, cor_a)

    st.markdown("<hr class='separador'>", unsafe_allow_html=True)

    base_sel   = st.session_state.get("base_sel")
    key_prefix = st.session_state.get("tela", "")

    if base_sel is not None:
        df_pos  = get_posicoes(df_view if filtro_ativo else df, base_sel)
        cor_sel = cor_a if base_sel <= 17 else cor_b
        if not df_pos.empty:
            painel_detalhe(base_sel, df_pos, cor_sel, tem_origem=tem_origem)
        else:
            st.warning(f"Sem dados para Base {base_sel:02d} com os filtros aplicados.")
            st.markdown("<hr class='separador'>", unsafe_allow_html=True)

    N_COLS = 4
    col_lado_a, col_corredor, col_lado_b = st.columns([5, 1, 5])

    with col_lado_a:
        st.markdown(
            f"<div style='background:{cor_a}18; border:1px solid {cor_a}44; border-radius:12px; "
            f"padding:12px 16px; margin-bottom:12px; text-align:center;'>"
            f"<div style='color:{cor_a}; font-size:14px; font-weight:700; "
            f"text-transform:uppercase; letter-spacing:1px;'>LADO A</div>"
            f"<div style='color:#8888aa; font-size:11px;'>Bases 01 – 17</div></div>",
            unsafe_allow_html=True
        )
        bases_a  = list(range(1, 17))
        linhas_a = [bases_a[i:i + N_COLS] for i in range(0, len(bases_a), N_COLS)]
        for linha in linhas_a:
            cols = st.columns(N_COLS)
            for idx, base_num in enumerate(linha):
                with cols[idx]:
                    renderizar_botao_base(base_num, key_prefix, bases_destaque)

        st.markdown(
            "<div style='background:#080810; border:2px dashed #2a2a4a; border-radius:10px; "
            "padding:14px 16px; text-align:center; margin-top:8px;'>"
            "<div style='color:#3a3a6a; font-size:12px; font-weight:700; letter-spacing:1px;'>"
            "⬛ BASE 17 — CONTAINER (DESABILITADA)</div></div>",
            unsafe_allow_html=True
        )

    with col_corredor:
        st.markdown(
            "<div style='background:#0a0a14; border:1px solid #1e1e2e; border-radius:10px; "
            "min-height:500px; display:flex; align-items:center; justify-content:center; "
            "padding:10px 4px; text-align:center;'>"
            "<div style='color:#3a3a6a; font-size:10px; font-weight:600; "
            "writing-mode:vertical-rl; text-orientation:mixed; letter-spacing:3px;'>"
            "C O R R E D O R</div></div>",
            unsafe_allow_html=True
        )

    with col_lado_b:
        st.markdown(
            f"<div style='background:{cor_b}18; border:1px solid {cor_b}44; border-radius:12px; "
            f"padding:12px 16px; margin-bottom:12px; text-align:center;'>"
            f"<div style='color:{cor_b}; font-size:14px; font-weight:700; "
            f"text-transform:uppercase; letter-spacing:1px;'>LADO B</div>"
            f"<div style='color:#8888aa; font-size:11px;'>Bases 18 – 36</div></div>",
            unsafe_allow_html=True
        )
        bases_b  = list(range(18, 37))
        linhas_b = [bases_b[i:i + N_COLS] for i in range(0, len(bases_b), N_COLS)]
        for linha in linhas_b:
            cols = st.columns(N_COLS)
            for idx, base_num in enumerate(linha):
                with cols[idx]:
                    renderizar_botao_base(base_num, key_prefix, bases_destaque)

    # injeta JS para aplicar cores no DOM após render
    injetar_estilos_botoes(filtro_ativo)

    st.markdown("<hr class='separador'>", unsafe_allow_html=True)
    total = len(df) if df is not None else 0
    st.markdown(
        f"<p style='color:#3a3a6a; font-size:11px; text-align:center;'>"
        f"Total de registros: {total} &nbsp;|&nbsp; "
        f"Lado A: bases 01–17 &nbsp;|&nbsp; Lado B: bases 18–36</p>",
        unsafe_allow_html=True
    )

    if df is not None and total > 0:
        with st.expander("🔍 Debug — dados carregados da planilha"):
            st.dataframe(df, use_container_width=True, hide_index=True)


def tela_home(df_atual, df_plan):
    st.markdown(
        "<h1 style='text-align:center; margin-bottom:4px;'>⚙️ Usina Xavantes</h1>"
        "<p style='text-align:center; color:#8888aa; font-size:14px; margin-bottom:40px;'>"
        "Selecione o módulo que deseja acessar</p>",
        unsafe_allow_html=True
    )

    pot_atual = formatar_potencia(
        df_atual["pot_maquina_num"].sum()
        if df_atual is not None and "pot_maquina_num" in df_atual.columns else 0
    )
    pot_plan = formatar_potencia(
        df_plan["pot_maquina_num"].sum()
        if df_plan is not None and "pot_maquina_num" in df_plan.columns else 0
    )
    maq_atual = contar_maquinas(df_atual)
    maq_plan  = contar_maquinas(df_plan)

    col1, col2 = st.columns(2, gap="large")

    with col1:
        st.markdown(
            f'<div style="background:linear-gradient(135deg, #12122a 0%, #1a1a3a 100%); '
            f'border:2px solid #7c6af7; border-radius:20px; padding:36px 32px; text-align:center;">'
            f'<div style="font-size:48px; margin-bottom:16px;">⚙️</div>'
            f'<div style="color:#7c6af7; font-size:22px; font-weight:800; letter-spacing:1px; margin-bottom:8px;">PÁTIO ATUAL</div>'
            f'<div style="color:#8888aa; font-size:13px; margin-bottom:24px;">Configuração atual do pátio de máquinas</div>'
            f'<div style="display:flex; justify-content:center; gap:32px; margin-bottom:24px;">'
            f'<div><div style="color:#8888aa; font-size:10px;">MÁQUINAS COM POTÊNCIA</div>'
            f'<div style="color:#e0e0f0; font-size:24px; font-weight:700;">{maq_atual}</div></div>'
            f'<div><div style="color:#8888aa; font-size:10px;">POTÊNCIA</div>'
            f'<div style="color:#22c55e; font-size:24px; font-weight:700;">{pot_atual}</div></div>'
            f'</div></div>',
            unsafe_allow_html=True
        )
        if st.button("Acessar Pátio Atual →", key="btn_atual", use_container_width=True):
            st.session_state["tela"]     = "atual"
            st.session_state["base_sel"] = None
            st.rerun()

    with col2:
        st.markdown(
            f'<div style="background:linear-gradient(135deg, #1a1200 0%, #2a1e00 100%); '
            f'border:2px solid #f59e0b; border-radius:20px; padding:36px 32px; text-align:center;">'
            f'<div style="font-size:48px; margin-bottom:16px;">📋</div>'
            f'<div style="color:#f59e0b; font-size:22px; font-weight:800; letter-spacing:1px; margin-bottom:8px;">PÁTIO PLANEJADO</div>'
            f'<div style="color:#8888aa; font-size:13px; margin-bottom:24px;">Configuração planejada do pátio de máquinas</div>'
            f'<div style="display:flex; justify-content:center; gap:32px; margin-bottom:24px;">'
            f'<div><div style="color:#8888aa; font-size:10px;">MÁQUINAS COM POTÊNCIA</div>'
            f'<div style="color:#e0e0f0; font-size:24px; font-weight:700;">{maq_plan}</div></div>'
            f'<div><div style="color:#8888aa; font-size:10px;">POTÊNCIA</div>'
            f'<div style="color:#22c55e; font-size:24px; font-weight:700;">{pot_plan}</div></div>'
            f'</div></div>',
            unsafe_allow_html=True
        )
        if st.button("Acessar Pátio Planejado →", key="btn_plan", use_container_width=True):
            st.session_state["tela"]     = "planejado"
            st.session_state["base_sel"] = None
            st.rerun()


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    if "tela"     not in st.session_state:
        st.session_state["tela"]     = "home"
    if "base_sel" not in st.session_state:
        st.session_state["base_sel"] = None

    df_atual, df_plan, erros, sheet_names = carregar_dados()
    tela = st.session_state.get("tela", "home")

    filtro_motor  = []
    filtro_alt    = []
    filtro_origem = []

    with st.sidebar:
        st.markdown("## ⚙️ Pátio de Máquinas")
        st.markdown("---")
        st.markdown("**Usina Xavantes**")
        if tela != "home":
            st.markdown(
                f"<small style='color:#8888bb'>Módulo: "
                f"{'Atual' if tela == 'atual' else 'Planejado'}</small>",
                unsafe_allow_html=True
            )
        st.markdown("---")

        if st.button("🏠 Tela inicial"):
            st.session_state["tela"]     = "home"
            st.session_state["base_sel"] = None
            st.rerun()
        if st.button("🔄 Recarregar dados"):
            st.cache_data.clear()
            st.rerun()

        if tela in ("atual", "planejado"):
            df_ref       = df_atual if tela == "atual" else df_plan
            tem_origem_f = tela == "planejado"

            st.markdown("---")
            st.markdown("### 🔍 Filtros")

            opts_motor = opcoes_filtro(df_ref, "modelo_motor")
            if opts_motor:
                filtro_motor = st.multiselect(
                    "Modelo Motor", options=opts_motor, default=[], key="f_motor"
                )

            opts_alt = opcoes_filtro(df_ref, "modelo_alternador")
            if opts_alt:
                filtro_alt = st.multiselect(
                    "Modelo Alternador", options=opts_alt, default=[], key="f_alt"
                )

            if tem_origem_f:
                opts_orig = opcoes_filtro(df_ref, "origem")
                if opts_orig:
                    filtro_origem = st.multiselect(
                        "Origem", options=opts_orig, default=[], key="f_origem"
                    )

            if filtro_motor or filtro_alt or filtro_origem:
                if st.button("✖ Limpar filtros"):
                    st.session_state["f_motor"] = []
                    st.session_state["f_alt"]   = []
                    if tem_origem_f:
                        st.session_state["f_origem"] = []
                    st.rerun()

    if tela == "home":
        tela_home(df_atual, df_plan)

    elif tela == "atual":
        if erros.get("atual"):
            st.error(f"Erro ao carregar Pátio Atual: {erros['atual']}")
            if sheet_names:
                st.info(f"Abas disponíveis: {sheet_names}")
        else:
            tela_patio(
                df=df_atual,
                titulo="Pátio de Máquinas — Atual",
                cor_a="#7c6af7",
                cor_b="#f97316",
                tem_origem=False,
                filtro_motor=filtro_motor,
                filtro_alt=filtro_alt,
                filtro_origem=filtro_origem,
            )

    elif tela == "planejado":
        if erros.get("planejado"):
            st.error(f"Erro ao carregar Pátio Planejado: {erros['planejado']}")
            if sheet_names:
                st.info(f"Abas disponíveis: {sheet_names}")
        else:
            tela_patio(
                df=df_plan,
                titulo="Pátio de Máquinas — Planejado",
                cor_a="#f59e0b",
                cor_b="#06b6d4",
                tem_origem=True,
                filtro_motor=filtro_motor,
                filtro_alt=filtro_alt,
                filtro_origem=filtro_origem,
            )


main()