import re
import json
import os
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import requests
import io
import unicodedata
from datetime import date, datetime, timedelta
import hashlib # Importado para hash de senhas

LINK_PATIO             = "https://usinaxavantes-my.sharepoint.com/:x:/g/personal/jefferson_ferreira_usinaxavantes_onmicrosoft_com/IQAc3sFoxYzbSqL-j6ZoJWq-AbBgxlJpnRNc8KsTOFWuCqI?e=3JIXRs"
SHEET_PLANEJADO        = "Pátio_Máquina_Planejado"
POTENCIA_CONTRATADA_MW = 50.40

# ... (suas importações existentes)
import gspread # Adicione esta linha
# ... (suas constantes existentes)

# --- Configurações do Google Sheets ---
GOOGLE_SHEETS_CREDENTIALS_FILE = "credentials.json" # Nome do arquivo JSON que você baixou
GOOGLE_SHEETS_SPREADSHEET_NAME = "Xavantes_Go" # Nome da sua planilha principal no Google Sheets

# --- Variáveis globais para a conexão com o Google Sheets ---
gc = None # Cliente gspread
spreadsheet = None # Planilha principal

def init_google_sheets():
    """Inicializa a conexão com o Google Sheets."""
    global gc, spreadsheet
    if gc is None:
        try:
            gc = gspread.service_account(filename=GOOGLE_SHEETS_CREDENTIALS_FILE)
            spreadsheet = gc.open(GOOGLE_SHEETS_SPREADSHEET_NAME)
            st.success("Conectado ao Google Sheets com sucesso!")
        except Exception as e:
            st.error(f"Erro ao conectar ao Google Sheets: {e}")
            st.stop() # Interrompe a execução se não conseguir conectar

# Chame a função de inicialização no início do seu script, antes de qualquer operação com Sheets
init_google_sheets()

# --- Funções para carregar/salvar colaboradores ---
# REMOVA OU COMENTE ESTAS LINHAS:
# ARQUIVO_COLABORADORES = "colaboradores.json"
# def load_colaboradores(): ...
# def save_colaboradores(colaboradores): ...
# if not os.path.exists(ARQUIVO_COLABORADORES): ...

# --- Funções para carregar/salvar colaboradores (AGORA DO GOOGLE SHEETS) ---
def load_colaboradores():
    if spreadsheet is None:
        st.error("Conexão com Google Sheets não estabelecida.")
        return {}
    try:
        worksheet = spreadsheet.worksheet("Colaboradores") # Nome da aba
        data = worksheet.get_all_records() # Obtém todos os dados como lista de dicionários
        colaboradores_dict = {}
        for row in data:
            nome = row.get("nome")
            area = row.get("area")
            if nome:
                colaboradores_dict[nome] = {"area": area}
        return colaboradores_dict
    except gspread.exceptions.WorksheetNotFound:
        st.warning("Aba 'Colaboradores' não encontrada. Criando cabeçalhos.")
        worksheet = spreadsheet.add_worksheet(title="Colaboradores", rows="1", cols="2")
        worksheet.append_row(["nome", "area"])
        return {}
    except Exception as e:
        st.error(f"Erro ao carregar colaboradores do Google Sheets: {e}")
        return {}

def save_colaboradores(colaboradores):
    # Para colaboradores, geralmente carregamos tudo, modificamos em memória e salvamos tudo de volta.
    # No entanto, para evitar sobrescrever dados de outros usuários,
    # é melhor ter uma estratégia de atualização mais granular ou recarregar antes de salvar.
    # Por enquanto, esta função não será usada diretamente para salvar, apenas para carregar.
    # A adição/edição de colaboradores será feita manualmente na planilha ou via uma interface específica.
    # Se precisar de uma função de salvar, ela precisaria limpar a aba e reescrever.
    # Por simplicidade, vamos considerar que a aba 'Colaboradores' é gerenciada manualmente.
    pass # Manteremos esta função vazia por enquanto, pois a gestão será manual na planilha.

# --- Inicialização de colaboradores (APENAS PARA O PRIMEIRO USO NO SHEETS) ---
# Se a aba 'Colaboradores' estiver vazia, você pode adicionar os iniciais.
# REMOVA OU COMENTE ESTE BLOCO APÓS A PRIMEIRA EXECUÇÃO E CONFIGURAÇÃO DOS SEUS COLABORADORES REAIS NA PLANILHA
# if not load_colaboradores(): # Verifica se a aba está vazia
#     try:
#         worksheet = spreadsheet.worksheet("Colaboradores")
#     except gspread.exceptions.WorksheetNotFound:
#         worksheet = spreadsheet.add_worksheet(title="Colaboradores", rows="1", cols="2")
#         worksheet.append_row(["nome", "area"])
#
#     initial_colaboradores_list = [
#         {"nome": "Hiago José", "area": "Elétrica"},
#         {"nome": "Marcelo Cirino", "area": "Serralheria"},
#         {"nome": "Paulo Borges", "area": "Mecânica"},
#         {"nome": "Wesnalton Carneiro", "area": "Mecânica"},
#         {"nome": "Ramom Lima", "area": "Operação"}
#     ]
#     # Adiciona os colaboradores iniciais se a aba estiver vazia
#     if not worksheet.get_all_records(): # Verifica novamente se está realmente vazia
#         for colab in initial_colaboradores_list:
#             worksheet.append_row([colab["nome"], colab["area"]])
#         st.success("Colaboradores iniciais adicionados à aba 'Colaboradores'.")
# -----------------------------------------------------------------------------
# --- Funções para carregar/salvar horas extras ---
import json
import os

# REMOVA OU COMENTE ESTAS LINHAS:
# ARQUIVO_HORAS_EXTRAS = "horas_extras.json"
# def load_horas_extras(): ...
# def save_horas_extras(horas_extras_data): ...
# def add_horas_extras_registro(colaborador, data, horas, tipo, observacao): ...

# --- Funções para carregar/salvar horas extras (AGORA DO GOOGLE SHEETS) ---
def load_horas_extras():
    if spreadsheet is None:
        st.error("Conexão com Google Sheets não estabelecida.")
        return {}
    try:
        worksheet = spreadsheet.worksheet("Horas_Extras") # Nome da aba
        data = worksheet.get_all_records()
        horas_extras_dict = {}
        for row in data:
            colaborador = row.get("colaborador")
            if colaborador:
                if colaborador not in horas_extras_dict:
                    horas_extras_dict[colaborador] = []
                horas_extras_dict[colaborador].append({
                    "data": str(row.get("data")),
                    "horas": float(row.get("horas", 0)), # Garante que seja float
                    "tipo": str(row.get("tipo")),
                    "observacao": str(row.get("observacao", ""))
                })
        return horas_extras_dict
    except gspread.exceptions.WorksheetNotFound:
        st.warning("Aba 'Horas_Extras' não encontrada. Criando cabeçalhos.")
        worksheet = spreadsheet.add_worksheet(title="Horas_Extras", rows="1", cols="5")
        worksheet.append_row(["colaborador", "data", "horas", "tipo", "observacao"])
        return {}
    except Exception as e:
        st.error(f"Erro ao carregar horas extras do Google Sheets: {e}")
        return {}

def add_horas_extras_registro(colaborador, data, horas, tipo, observacao):
    if spreadsheet is None:
        st.error("Conexão com Google Sheets não estabelecida.")
        return

    try:
        worksheet = spreadsheet.worksheet("Horas_Extras")
    except gspread.exceptions.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(title="Horas_Extras", rows="1", cols="5")
        worksheet.append_row(["colaborador", "data", "horas", "tipo", "observacao"])

    # Adiciona uma nova linha à aba
    worksheet.append_row([
        colaborador,
        str(data), # Garante que a data seja string no formato YYYY-MM-DD
        horas,
        tipo,
        observacao
    ])

PLANOS_MANUTENCAO = {
    "scania": {
        "intervalo_base": 300,
        "alerta_horas":   30,
        "faixas": {
            300:  {"label": "300h",  "itens": ["Filtros", "Óleo"]},
            600:  {"label": "600h",  "itens": ["Filtros", "Óleo", "Filtro de ar"]},
            900:  {"label": "900h",  "itens": ["Filtros", "Óleo", "Regulagem de válvulas"]},
            3600: {"label": "3600h", "itens": ["Filtros", "Óleo", "Filtro de ar", "Regulagem de válvulas", "Bronzinas de mancal"]},
        }
    },
    "outros": {
        "intervalo_base": 400,
        "alerta_horas":   40,
        "faixas": {
            400:  {"label": "400h",  "itens": ["Filtros", "Óleo"]},
            800:  {"label": "800h",  "itens": ["Filtros", "Óleo", "Filtro de ar"]},
            1200: {"label": "1200h", "itens": ["Filtros", "Óleo", "Regulagem de válvulas"]},
            4000: {"label": "4000h", "itens": ["Filtros", "Óleo", "Filtro de ar", "Regulagem de válvulas"]},
        }
    }
}

st.set_page_config(
    page_title="Pátio de Máquinas — Usina Xavantes",
    page_icon="⚙️",
    layout="wide"
)

st.markdown("""
<style>
    html, body { background-color: #0f0f1a !important; margin: 0 !important; padding: 0 !important; }
    .stApp { background-color: #0f0f1a !important; min-height: 10vh; }
    [data-testid="stAppViewContainer"] { background-color: #0f0f1a !important; }
    [data-testid="stHeader"] { background-color: #0f0f1a !important; border-bottom: none !important; }
    [data-testid="stToolbar"] { background-color: #0f0f1a !important; }
    .main { background-color: #0f0f1a !important; }
    .block-container { background-color: #0f0f1a !important; padding-top: 3rem !important; min-height: 10vh; }
    h1, h2, h3, h4, p, label { color: #e0e0f0 !important; }
    [data-testid="stSidebar"] { background-color: #1e1e2e; }
    [data-testid="stSidebar"] * { color: #e0e0f0 !important; }
    .separador { border: none; border-top: 1px solid #2a2a4a; margin: 16px 0; }
    .stButton > button {
        width: 100% !important; font-size: 13px !important; padding: 12px 4px !important;
        font-weight: 700 !important; border-radius: 10px !important; margin: 3px 0 !important;
        background-color: #1e1e32 !important; color: #d0d0f0 !important;
        border: 1px solid #3a3a5a !important; transition: all 0.2s !important; letter-spacing: 0.5px !important;
    }
    .stButton > button:hover {
        background-color: #2a2a4a !important; border-color: #7c6af7 !important; color: #ffffff !important;
    }
    [data-testid="stMultiSelect"] > div { background-color: #1a1a2e !important; border-color: #3a3a5a !important; }
    .stTabs [data-baseweb="tab-list"] { background-color: #0f0f1a !important; gap: 8px; }
    .stTabs [aria-selected="true"] {
        background-color: #5b21b6 !important; color: #ffffff !important;
        border-color: #7c6af7 !important;
    }
</style>
""", unsafe_allow_html=True)


# ── Funções de Autenticação ───────────────────────────────────────────────────

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# A função load_users foi substituída, mas authenticate precisa dela
# def load_users(): ... (agora vem do Sheets)

def authenticate(username, password):
    users = load_users() # Esta função agora carrega do Google Sheets
    user_info = users.get(username)
    if user_info and user_info["password_hash"] == hash_password(password):
        return user_info["profile"]
    return None


# REMOVA OU COMENTE ESTAS LINHAS:
# USERS_FILE = "users.json"
# def load_users(): ...
# def save_users(users): ...
# if not os.path.exists(USERS_FILE): ...

# --- Funções para carregar/salvar usuários (AGORA DO GOOGLE SHEETS) ---
def load_users():
    if spreadsheet is None:
        st.error("Conexão com Google Sheets não estabelecida.")
        return {}
    try:
        worksheet = spreadsheet.worksheet("Usuarios") # Nome da aba
        data = worksheet.get_all_records()
        users_dict = {}
        for row in data:
            username = row.get("username")
            if username:
                users_dict[username] = {
                    "password_hash": str(row.get("password_hash")),
                    "profile": str(row.get("profile"))
                }
        return users_dict
    except gspread.exceptions.WorksheetNotFound:
        st.warning("Aba 'Usuarios' não encontrada. Criando cabeçalhos.")
        worksheet = spreadsheet.add_worksheet(title="Usuarios", rows="1", cols="3")
        worksheet.append_row(["username", "password_hash", "profile"])
        return {}
    except Exception as e:
        st.error(f"Erro ao carregar usuários do Google Sheets: {e}")
        return {}

def save_users(users):
    # Para usuários, geralmente carregamos tudo, modificamos em memória e salvamos tudo de volta.
    # No entanto, para evitar sobrescrever dados de outros usuários,
    # é melhor ter uma estratégia de atualização mais granular ou recarregar antes de salvar.
    # Por simplicidade, vamos considerar que a aba 'Usuarios' é gerenciada manualmente.
    pass # Manteremos esta função vazia por enquanto, pois a gestão será manual na planilha.

# --- Inicialização de usuários (APENAS PARA O PRIMEIRO USO NO SHEETS) ---
# Se a aba 'Usuarios' estiver vazia, você pode adicionar os iniciais.
# REMOVA OU COMENTE ESTE BLOCO APÓS A PRIMEIRA EXECUÇÃO E CONFIGURAÇÃO DOS SEUS USUÁRIOS REAIS NA PLANILHA
# if not load_users(): # Verifica se a aba está vazia
#     try:
#         worksheet = spreadsheet.worksheet("Usuarios")
#     except gspread.exceptions.WorksheetNotFound:
#         worksheet = spreadsheet.add_worksheet(title="Usuarios", rows="1", cols="3")
#         worksheet.append_row(["username", "password_hash", "profile"])
#
#     initial_users_list = [
#         {"username": "engenharia", "password_hash": hash_password("engxavantes"), "profile": "engenharia"},
#         {"username": "operador",   "password_hash": hash_password("operador123"),   "profile": "operacao"}
#     ]
#     # Adiciona os usuários iniciais se a aba estiver vazia
#     if not worksheet.get_all_records(): # Verifica novamente se está realmente vazia
#         for user in initial_users_list:
#             worksheet.append_row([user["username"], user["password_hash"], user["profile"]])
#         st.success("Usuários iniciais adicionados à aba 'Usuarios'.")
# -----------------------------------------------------------------------------


# ── helpers de persistência ───────────────────────────────────────────────────

# REMOVA OU COMENTE ESTAS LINHAS:
# ARQUIVO_HORIMETROS = "horimetros.json"
# def carregar_horimetros(): ...
# def salvar_horimetro(label, valor, data_registro): ...

# --- Funções para carregar/salvar horimetros (AGORA DO GOOGLE SHEETS) ---
def carregar_horimetros():
    if spreadsheet is None:
        st.error("Conexão com Google Sheets não estabelecida.")
        return {}
    try:
        worksheet = spreadsheet.worksheet("Horimetros") # Nome da aba
        data = worksheet.get_all_records()
        horimetros_dict = {}
        for row in data:
            label = row.get("label")
            if label:
                horimetro = float(row.get("horimetro", 0))
                data_reg = str(row.get("data"))
                if label not in horimetros_dict:
                    horimetros_dict[label] = {"horimetro": 0, "data": "", "historico": []}
                # Sempre mantém o último registro como o "atual"
                if horimetro > horimetros_dict[label]["horimetro"]:
                    horimetros_dict[label]["horimetro"] = horimetro
                    horimetros_dict[label]["data"] = data_reg
                horimetros_dict[label]["historico"].append({"horimetro": horimetro, "data": data_reg})
        return horimetros_dict
    except gspread.exceptions.WorksheetNotFound:
        st.warning("Aba 'Horimetros' não encontrada. Criando cabeçalhos.")
        worksheet = spreadsheet.add_worksheet(title="Horimetros", rows="1", cols="3")
        worksheet.append_row(["label", "horimetro", "data"])
        return {}
    except Exception as e:
        st.error(f"Erro ao carregar horímetros do Google Sheets: {e}")
        return {}

def salvar_horimetro(label, valor, data_registro):
    if spreadsheet is None:
        st.error("Conexão com Google Sheets não estabelecida.")
        return

    try:
        worksheet = spreadsheet.worksheet("Horimetros")
    except gspread.exceptions.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(title="Horimetros", rows="1", cols="3")
        worksheet.append_row(["label", "horimetro", "data"])

    # Adiciona uma nova linha à aba
    worksheet.append_row([
        label,
        valor,
        str(data_registro) # Garante que a data seja string no formato YYYY-MM-DD
    ])


# REMOVA OU COMENTE ESTAS LINHAS:
# ARQUIVO_MANUTENCOES = "manutencoes.json"
# def carregar_manutencoes(): ...
# def salvar_manutencao(label, faixa, horimetro, data_registro, responsavel, observacao, atualizar_horimetro=True): ...

# --- Funções para carregar/salvar manutenções (AGORA DO GOOGLE SHEETS) ---
def carregar_manutencoes():
    if spreadsheet is None:
        st.error("Conexão com Google Sheets não estabelecida.")
        return {}
    try:
        worksheet = spreadsheet.worksheet("Manutencoes") # Nome da aba
        data = worksheet.get_all_records()
        manutencoes_dict = {}
        for row in data:
            label = row.get("label")
            if label:
                if label not in manutencoes_dict:
                    manutencoes_dict[label] = {"historico": [], "ultimos_horimetros_por_faixa": {}}

                faixa = row.get("faixa")
                horimetro = float(row.get("horimetro", 0))
                data_reg = str(row.get("data"))
                responsavel = str(row.get("responsavel", ""))
                observacao = str(row.get("observacao", ""))

                manutencoes_dict[label]["historico"].append({
                    "faixa": faixa,
                    "horimetro": horimetro,
                    "data": data_reg,
                    "responsavel": responsavel,
                    "observacao": observacao
                })

                # Atualiza o último horímetro para esta faixa específica
                # Para checklist, guardamos a data, para outros, o horímetro
                if faixa == "checklist":
                    # Converte para datetime para comparar e pegar a mais recente
                    current_date = datetime.strptime(data_reg, "%Y-%m-%d").date()
                    last_recorded_date_str = manutencoes_dict[label]["ultimos_horimetros_por_faixa"].get("checklist")
                    if last_recorded_date_str:
                        last_recorded_date = datetime.strptime(last_recorded_date_str, "%Y-%m-%d").date()
                        if current_date > last_recorded_date:
                            manutencoes_dict[label]["ultimos_horimetros_por_faixa"]["checklist"] = data_reg
                    else:
                        manutencoes_dict[label]["ultimos_horimetros_por_faixa"]["checklist"] = data_reg
                else:
                    # Garante que a faixa seja tratada como string para chave do dicionário
                    faixa_key = str(faixa)
                    if horimetro > manutencoes_dict[label]["ultimos_horimetros_por_faixa"].get(faixa_key, 0):
                        manutencoes_dict[label]["ultimos_horimetros_por_faixa"][faixa_key] = horimetro

                # Atualiza os dados da última manutenção geral (a mais recente no histórico)
                # Isso é feito iterativamente, então o último registro no loop será o "último"
                manutencoes_dict[label]["ultima_faixa"] = faixa
                manutencoes_dict[label]["ultimo_horimetro"] = horimetro
                manutencoes_dict[label]["ultima_data"] = data_reg
                manutencoes_dict[label]["ultimo_responsavel"] = responsavel

        return manutencoes_dict
    except gspread.exceptions.WorksheetNotFound:
        st.warning("Aba 'Manutencoes' não encontrada. Criando cabeçalhos.")
        worksheet = spreadsheet.add_worksheet(title="Manutencoes", rows="1", cols="6")
        worksheet.append_row(["label", "faixa", "horimetro", "data", "responsavel", "observacao"])
        return {}
    except Exception as e:
        st.error(f"Erro ao carregar manutenções do Google Sheets: {e}")
        return {}

def salvar_manutencao(label, faixa, horimetro, data_registro, responsavel, observacao, atualizar_horimetro=True):
    if spreadsheet is None:
        st.error("Conexão com Google Sheets não estabelecida.")
        return

    try:
        worksheet = spreadsheet.worksheet("Manutencoes")
    except gspread.exceptions.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(title="Manutencoes", rows="1", cols="6")
        worksheet.append_row(["label", "faixa", "horimetro", "data", "responsavel", "observacao"])

    # Adiciona uma nova linha à aba
    worksheet.append_row([
        label,
        faixa,
        horimetro,
        str(data_registro), # Garante que a data seja string no formato YYYY-MM-DD
        responsavel,
        observacao
    ])

    if atualizar_horimetro and faixa != "checklist":
        salvar_horimetro(label, horimetro, data_registro)

# ── lógica de manutenção ──────────────────────────────────────────────────────

def get_plano(modelo_motor):
    if modelo_motor and "scania" in str(modelo_motor).lower():
        return "scania", PLANOS_MANUTENCAO["scania"]
    return "outros", PLANOS_MANUTENCAO["outros"]


def get_proxima_manutencao(horimetro_atual_maquina, modelo_motor, label_maquina):
    tipo, plano = get_plano(modelo_motor)
    base        = plano["intervalo_base"]
    faixas      = plano["faixas"]
    faixas_keys = sorted(faixas.keys())
    grande      = faixas_keys[-1]

    dados_manu = carregar_manutencoes()
    info_maquina = dados_manu.get(label_maquina, {})
    ultimos_horimetros_por_faixa = info_maquina.get("ultimos_horimetros_por_faixa", {})

    proxima_manutencao_geral = {
        "horimetro_alvo": float('inf'),
        "faixa_tipo": None,
        "faltam": float('inf'),
        "info_faixa": {}
    }

    for faixa_intervalo, info_faixa in faixas.items():
        ultimo_horimetro_desta_faixa = ultimos_horimetros_por_faixa.get(str(faixa_intervalo), 0)

        # --- CORREÇÃO AQUI ---
        # A próxima manutenção deve ser o último horímetro registrado para esta faixa + o intervalo da faixa
        horimetro_alvo_desta_faixa = ultimo_horimetro_desta_faixa + faixa_intervalo
        # Se o horimetro_alvo_desta_faixa for menor ou igual ao horimetro_atual_maquina,
        # significa que já passou e precisamos calcular o próximo ciclo.
        while horimetro_alvo_desta_faixa <= horimetro_atual_maquina:
            horimetro_alvo_desta_faixa += faixa_intervalo
        # --- FIM DA CORREÇÃO ---

        faltam_desta_faixa = horimetro_alvo_desta_faixa - horimetro_atual_maquina

        if faltam_desta_faixa < proxima_manutencao_geral["faltam"]:
            proxima_manutencao_geral = {
                "horimetro_alvo": horimetro_alvo_desta_faixa,
                "faixa_tipo": faixa_intervalo,
                "faltam": faltam_desta_faixa,
                "info_faixa": info_faixa
            }
        elif faltam_desta_faixa == proxima_manutencao_geral["faltam"]:
            # Se faltam o mesmo número de horas, prioriza a faixa menor (mais frequente)
            if faixa_intervalo < proxima_manutencao_geral["faixa_tipo"]:
                 proxima_manutencao_geral = {
                    "horimetro_alvo": horimetro_alvo_desta_faixa,
                    "faixa_tipo": faixa_intervalo,
                    "faltam": faltam_desta_faixa,
                    "info_faixa": info_faixa
                }

    if proxima_manutencao_geral["faixa_tipo"] is None:
        # Fallback para a lógica original se não houver histórico ou faixas
        if horimetro_atual_maquina <= 0:
            proxima_hora = base
        else:
            proxima_hora = (int(horimetro_atual_maquina // base) + 1) * base

        resto = proxima_hora % grande
        if resto == 0:
            faixa_tipo = grande
        else:
            faixa_tipo = base
            for f in sorted(faixas_keys, reverse=True):
                if resto % f == 0:
                    faixa_tipo = f
                    break
        faltam = proxima_hora - horimetro_atual_maquina
        return proxima_hora, faixa_tipo, faltam, faixas.get(faixa_tipo, {})

    return (
        proxima_manutencao_geral["horimetro_alvo"],
        proxima_manutencao_geral["faixa_tipo"],
        proxima_manutencao_geral["faltam"],
        proxima_manutencao_geral["info_faixa"]
    )


def get_status_manutencao(faltam, alerta_horas):
    if faltam <= 0:
        return "vencida", "#f03838", "#1a0a0a"
    elif faltam <= alerta_horas:
        return "proxima", "#f59e0b", "#1a1200"
    else:
        return "ok",      "#22c55e", "#0a1a0a"


def checklist_status(historico_manu):
    registros_cl = [h for h in historico_manu if h.get("faixa") == "checklist"]
    if not registros_cl:
        return "pendente", "#f59e0b", "#1a1200", None
    ultimo = registros_cl[-1]
    try:
        ultima_data = datetime.strptime(ultimo["data"], "%Y-%m-%d").date()
    except Exception:
        return "pendente", "#f59e0b", "#1a1200", ultimo
    diff = (date.today() - ultima_data).days
    if diff <= 7:
        return "ok",       "#22c55e", "#0a1a0a", ultimo
    else:
        return "pendente", "#f59e0b", "#1a1200", ultimo


def get_opcoes_slicer(modelo_motor):
    tipo, plano = get_plano(modelo_motor)
    opcoes      = [{"key": "checklist", "label": "✅ Check-list"}]
    for faixa in sorted(plano["faixas"].keys()):
        opcoes.append({"key": faixa, "label": plano["faixas"][faixa]["label"]})
    return opcoes


# ── helpers gerais ────────────────────────────────────────────────────────────

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
    unit  = " kW"
    if kw >= 1000:
        value = kw / 1000
        unit  = " MW"
    formatted_value = f"{value:.2f}" if unit == " MW" else f"{value:.0f}"
    parts        = formatted_value.split('.')
    integer_part = parts[0]
    decimal_part = parts[1] if len(parts) > 1 else ""
    n   = len(integer_part)
    fmt = ""
    for i, digit in enumerate(integer_part):
        fmt += digit
        if (n - 1 - i) % 3 == 0 and (n - 1 - i) != 0:
            fmt += "."
    return (fmt + ("," + decimal_part if decimal_part else "")) + unit


def contar_maquinas(df):
    if df is None or "pot_maquina_num" not in df.columns:
        return 0
    return int((df["pot_maquina_num"] > 0).sum())


def opcoes_filtro(df, col):
    if df is None or col not in df.columns:
        return []
    vals = df[col].dropna().unique().tolist()
    return sorted([str(v) for v in vals if str(v).strip() not in ("", "—", "nan")])


def aplicar_filtros(df, filtro_motor, filtro_alt, filtro_origem, filtro_serie_motor=None, filtro_serie_alternador=None):
    if df is None or df.empty:
        return df, set()
    mask = pd.Series([True] * len(df), index=df.index)
    if filtro_motor:
        mask &= df["modelo_motor"].isin(filtro_motor) if "modelo_motor" in df.columns else mask
    if filtro_alt:
        mask &= df["modelo_alternador"].isin(filtro_alt) if "modelo_alternador" in df.columns else mask
    if filtro_origem:
        mask &= df["origem"].isin(filtro_origem) if "origem" in df.columns else mask
    if filtro_serie_motor: # Novo filtro
        mask &= df["serie_motor"].isin(filtro_serie_motor) if "serie_motor" in df.columns else mask
    if filtro_serie_alternador: # Novo filtro
        mask &= df["serie_alternador"].isin(filtro_serie_alternador) if "serie_alternador" in df.columns else mask

    df_filtrado     = df[mask]
    bases_com_match = set(df_filtrado["base"].tolist())
    return df_filtrado, bases_com_match


def pot_lado(df, base_inicio, base_fim):
    # Esta função será usada apenas para o Lado B (18-36)
    # O Lado A terá sua lógica de soma ajustada diretamente na tela_patio
    if df is None or df.empty or "pot_maquina_num" not in df.columns:
        return 0
    return df[df["base"].between(base_inicio, base_fim)]["pot_maquina_num"].sum()


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
    col_transf    = encontrar_coluna(df.columns, ["N° SÉRIE TRANSFORMADOR", "N° SERIE TRANSFORMADOR",
                                                   "SERIE TRANSFORMADOR", "SÉRIE TRANSFORMADOR",
                                                   "N SERIE TRANSFORMADOR", "TRANSFORMADOR"])
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
        return None, f"Coluna BASE não encontrada na aba '{sheet_name}'"

    cols_usar = {
        "base_raw": col_base, "serie_transformador": col_transf,
        "fab_trafo": col_fab_trafo, "pot_trafo": col_pot_trafo,
        "imp_trafo": col_imp_trafo, "bt_kv": col_bt, "mt_kv": col_mt,
        "relacao": col_relacao, "pot_maquina": col_pot_maq,
        "modelo_motor": col_mod_mot, "serie_motor": col_ser_mot,
        "modelo_alternador": col_mod_alt, "serie_alternador": col_ser_alt,
        "origem": col_origem,
    }
    cols_validas = {k: v for k, v in cols_usar.items() if v is not None}

    df = df[[v for v in cols_validas.values()]].copy()
    df.columns = list(cols_validas.keys())

    df["base"]    = df["base_raw"].apply(extrair_numero_base)
    df["posicao"] = df["base_raw"].apply(extrair_posicao)

    # Remover linhas onde 'base' é NaN antes de criar 'label'
    df = df.dropna(subset=["base"])
    df["base"] = df["base"].astype(int) # Agora 'base' é int, sem NaNs

    def montar_label_final(r):
        base_val = r["base"]
        posicao  = r["posicao"]
        if posicao:
            return f"{base_val}.{posicao}"
        return str(base_val)

    df["label"]   = df.apply(montar_label_final, axis=1) # Aplicar após 'base' e 'posicao' estarem limpas


    if "pot_maquina" in df.columns:
        df["pot_maquina_num"] = pd.to_numeric(
            df["pot_maquina"].astype(str).str.replace(",", "."), errors="coerce"
        ).fillna(0)
    else:
        df["pot_maquina_num"] = 0

    if "origem"            not in df.columns: df["origem"]            = "—"
    if "modelo_motor"      not in df.columns: df["modelo_motor"]      = "—"
    if "serie_motor"       not in df.columns: df["serie_motor"]       = "—" # Garante a coluna
    if "modelo_alternador" not in df.columns: df["modelo_alternador"] = "—"
    if "serie_alternador"  not in df.columns: df["serie_alternador"]  = "—" # Garante a coluna

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
        if sheet_atual else (None, "Aba atual não encontrada")
    )
    df_plan, err_plan = (
        processar_aba(xl, SHEET_PLANEJADO, tem_origem=True)
        if SHEET_PLANEJADO in sheet_names
        else (None, f"Aba '{SHEET_PLANEJADO}' não encontrada")
    )

    return df_atual, df_plan, {"atual": err_atual, "planejado": err_plan}, sheet_names


def get_posicoes(df, base_num):
    if df is None or df.empty:
        return pd.DataFrame()
    return df[df["base"] == base_num].copy()


# ── componentes visuais ───────────────────────────────────────────────────────

def linha_trafo(label, valor):
    cor_val = "#e0e0f0" if valor != "—" else "#4a4a6a"
    return (
        '<div style="display:flex; justify-content:space-between; align-items:center; '
        'padding:6px 0; border-bottom:1px solid #1e1e2e;">'
        '<span style="color:#8888aa; font-size:11px;">' + label + '</span>'
        '<span style="color:' + cor_val + '; font-size:12px; font-weight:600;">' + valor + '</span>'
        '</div>'
    )


def bloco_transformador(row_transf):
    serie   = safe_val(row_transf, "serie_transformador")
    fab     = safe_val(row_transf, "fab_trafo")
    pot     = safe_val(row_transf, "pot_trafo")
    imp     = safe_val(row_transf, "imp_trafo")
    bt      = safe_val(row_transf, "bt_kv")
    mt      = safe_val(row_transf, "mt_kv")
    relacao = safe_val(row_transf, "relacao")

    if bt != "—" and mt != "—":
        tensao = bt + " / " + mt
    elif bt != "—":
        tensao = bt
    elif mt != "—":
        tensao = mt
    else:
        tensao = "—"

    cor = "#f59e0b" if serie != "—" else "#3a3a5a"
    svg = (
        '<svg width="40" height="48" viewBox="0 0 52 62" fill="none" xmlns="http://www.w3.org/2000/svg">'
        '<rect x="8" y="14" width="36" height="34" rx="4" fill="#0a0a14" stroke="' + cor + '" stroke-width="2"/>'
        '<ellipse cx="19" cy="31" rx="7" ry="10" fill="none" stroke="' + cor + '" stroke-width="1.8"/>'
        '<ellipse cx="33" cy="31" rx="7" ry="10" fill="none" stroke="' + cor + '" stroke-width="1.8"/>'
        '<line x1="26" y1="2" x2="26" y2="14" stroke="' + cor + '" stroke-width="2"/>'
        '<line x1="19" y1="2" x2="19" y2="14" stroke="' + cor + '" stroke-width="2"/>'
        '<line x1="33" y1="2" x2="33" y2="14" stroke="' + cor + '" stroke-width="2"/>'
        '<line x1="26" y1="48" x2="26" y2="60" stroke="' + cor + '" stroke-width="2"/>'
        '<line x1="19" y1="48" x2="19" y2="60" stroke="' + cor + '" stroke-width="2"/>'
        '<line x1="33" y1="48" x2="33" y2="60" stroke="' + cor + '" stroke-width="2"/>'
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
        '<div style="background:#0a0a14; border:1px solid ' + cor + '55; border-radius:12px; '
        'padding:16px 20px; margin-top:14px;">'
        '<div style="display:flex; align-items:center; gap:14px; margin-bottom:12px;">'
        + svg +
        '<div style="color:' + cor + '; font-size:12px; font-weight:700; '
        'text-transform:uppercase; letter-spacing:0.5px;">Transformador — Base (único)</div>'
        '</div>' + linhas + '</div>'
    )


def painel_detalhe(base_num, df_posicoes, cor, tem_origem=False, modo_horimetro=False):
    n            = len(df_posicoes)
    pot_base_kw  = df_posicoes["pot_maquina_num"].sum() if "pot_maquina_num" in df_posicoes.columns else 0
    pot_base_str = formatar_potencia(pot_base_kw)

    st.markdown(
        '<div style="background:' + cor + '18; border:1px solid ' + cor + '55; border-radius:14px; '
        'padding:14px 20px; margin-bottom:12px; display:flex; justify-content:space-between; align-items:center;">'
        '<div style="color:' + cor + '; font-size:15px; font-weight:700; '
        'text-transform:uppercase; letter-spacing:1px;">⚙️ Base ' + f"{base_num:02d}" + ' — ' + str(n) + ' posição(ões)</div>'
        '<div style="text-align:right;">'
        '<div style="color:#8888aa; font-size:10px;">Potência total da base</div>'
        '<div style="color:#22c55e; font-size:16px; font-weight:700;">' + pot_base_str + '</div>'
        '</div></div>',
        unsafe_allow_html=True
    )

    dados_hor = carregar_horimetros()
    posicoes  = [row for _, row in df_posicoes.iterrows()]
    n_cols    = min(n, 3)
    grupos    = [posicoes[i:i + n_cols] for i in range(0, n, n_cols)]

    for grupo in grupos:
        cols = st.columns(n_cols)
        for idx, row in enumerate(grupo):
            label        = row.get("label", str(base_num))
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
                    '<div style="margin-top:10px; padding:6px 10px; background:#1a1a2e; '
                    'border-left:3px solid ' + cor + '; border-radius:4px;">'
                    '<span style="color:#8888aa; font-size:10px;">Origem: </span>'
                    '<span style="color:' + cor + '; font-size:11px; font-weight:700;">' + origem + '</span>'
                    '</div>'
                )

            hor_html = ""
            reg      = dados_hor.get(label, {})
            hor_val  = reg.get("horimetro", None)
            hor_data = reg.get("data", None)
            if hor_val is not None:
                hor_fmt                       = f"{int(hor_val):,}".replace(",", ".")
                # Passa o label da máquina para get_proxima_manutencao
                prox_hora, faixa_tipo, faltam, info_f = get_proxima_manutencao(hor_val, modelo_motor, label)
                tipo_p, plano_p               = get_plano(modelo_motor)
                alerta_h                      = plano_p["alerta_horas"]
                status_m, cor_m, bg_m         = get_status_manutencao(faltam, alerta_h)
                falta_txt = (
                    "VENCIDA" if faltam <= 0
                    else "Faltam " + f"{int(faltam):,}".replace(",", ".") + " h"
                )
                hor_html = (
                    '<div style="margin-top:10px; padding:8px 10px; background:#0a1a0a; '
                    'border:1px solid #22c55e44; border-radius:8px;">'
                    '<div style="color:#8888aa; font-size:10px; margin-bottom:2px;">🕐 Horímetro atual</div>'
                    '<div style="color:#22c55e; font-size:18px; font-weight:800;">' + hor_fmt + ' h</div>'
                    '<div style="color:#4a8a5a; font-size:10px;">' + str(hor_data) + '</div>'
                    '<div style="margin-top:8px; padding:6px 8px; background:' + bg_m + '; '
                    'border:1px solid ' + cor_m + '44; border-radius:6px;">'
                    '<div style="color:#8888aa; font-size:10px;">🔧 Próxima manutenção</div>'
                    '<div style="color:' + cor_m + '; font-size:12px; font-weight:800;">'
                    + info_f.get("label", "") + ' — ' + f"{int(prox_hora):,}".replace(",", ".") + ' h</div>'
                    '<div style="color:' + cor_m + '; font-size:10px; font-weight:600;">' + falta_txt + '</div>'
                    '</div></div>'
                )
            else:
                hor_html = (
                    '<div style="margin-top:10px; padding:8px 10px; background:#1a0a14; '
                    'border:1px solid #f0383844; border-radius:8px;">'
                    '<div style="color:#8888aa; font-size:10px;">🕐 Horímetro</div>'
                    '<div style="color:#f03838; font-size:11px; font-weight:600;">Não registrado</div>'
                    '</div>'
                )

            with cols[idx]:
                st.markdown(
                    '<div style="background:#0a0a14; border:1px solid ' + cor + '44; '
                    'border-radius:12px; padding:14px 16px; margin-bottom:6px;">'
                    '<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">'
                    '<div style="color:' + cor + '; font-size:14px; font-weight:800; letter-spacing:1px;">' + label + '</div>'
                    '<div style="color:' + cp + '; font-size:12px; font-weight:700;">' + tp + '</div>'
                    '</div>'
                    '<div style="display:grid; grid-template-columns:1fr 1fr; gap:0 16px;">'
                    '<div>'
                    '<div style="color:#7c6af7; font-size:10px; font-weight:700; text-transform:uppercase;">🔧 Motor</div>'
                    '<div style="color:#8888aa; font-size:10px; margin-top:8px;">Modelo</div>'
                    '<div style="color:' + cm + '; font-size:13px; font-weight:600;">' + modelo_motor + '</div>'
                    '<div style="color:#8888aa; font-size:10px; margin-top:8px;">Nº de Série</div>'
                    '<div style="color:' + cs + '; font-size:13px; font-weight:600;">' + serie_motor + '</div>'
                    '</div>'
                    '<div>'
                    '<div style="color:#22c55e; font-size:10px; font-weight:700; text-transform:uppercase;">⚡ Alternador</div>'
                    '<div style="color:#8888aa; font-size:10px; margin-top:8px;">Modelo</div>'
                    '<div style="color:' + ca + '; font-size:13px; font-weight:600;">' + modelo_alt + '</div>'
                    '<div style="color:#8888aa; font-size:10px; margin-top:8px;">Nº de Série</div>'
                    '<div style="color:' + csa + '; font-size:13px; font-weight:600;">' + serie_alt + '</div>'
                    '</div>'
                    '</div>'
                    + origem_html + hor_html + '</div>',
                    unsafe_allow_html=True
                )

                # Botão de atualização de horímetro visível apenas se modo_horimetro for True
                if modo_horimetro:
                    chave_ativa = st.session_state.get("editar_horimetro")
                    btn_label   = "✏️ Editando..." if chave_ativa == label else "📝 Atualizar Horímetro"
                    if st.button(btn_label, key="btn_hor_" + label):
                        st.session_state["editar_horimetro"] = None if chave_ativa == label else label
                        st.rerun()

    # Formulário de registro de horímetro visível apenas se modo_horimetro for True
    if modo_horimetro:
        label_ativo = st.session_state.get("editar_horimetro")
        labels_base = [r.get("label", "") for r in posicoes]

        if label_ativo and label_ativo in labels_base:
            reg         = dados_hor.get(label_ativo, {})
            valor_atual = reg.get("horimetro", 0)
            hor_fmt     = f"{int(valor_atual):,}".replace(",", ".") if valor_atual else "0"

            st.markdown(
                '<div style="background:linear-gradient(135deg, #0a1a2a 0%, #0f2030 100%); '
                'border:2px solid #06b6d4; border-radius:16px; padding:20px 24px; margin-top:8px;">'
                '<div style="color:#06b6d4; font-size:13px; font-weight:700; '
                'text-transform:uppercase; letter-spacing:1px;">'
                '🕐 Registrar Horímetro — Máquina ' + label_ativo + '</div>'
                '<div style="color:#8888aa; font-size:11px;">'
                'Último valor registrado: <strong style="color:#e0e0f0;">' + hor_fmt + ' h</strong>'
                '</div></div>',
                unsafe_allow_html=True
            )

            col_hor, col_data, col_salvar = st.columns([2, 2, 1], gap="small")

            with col_hor:
                novo_valor = st.number_input(
                    "Horímetro (horas)", min_value=0,
                    value=int(valor_atual) if valor_atual else 0,
                    step=1, key="input_hor_" + label_ativo
                )
            with col_data:
                nova_data = st.date_input(
                    "Data da leitura", value=date.today(),
                    key="input_data_" + label_ativo
                )
            with col_salvar:
                st.markdown("<div style='margin-top:28px;'>", unsafe_allow_html=True)
                if st.button("💾 Salvar", key="salvar_hor_" + label_ativo):
                    salvar_horimetro(label_ativo, novo_valor, nova_data)
                    st.session_state["editar_horimetro"] = None
                    st.success("✅ Horímetro registrado: " + str(novo_valor) + " h")
                    st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)

    if not modo_horimetro: # Esta condição é para a tela de Pátio de Máquinas, não a de Horímetro
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
            '<div style="background:#1a0a1a; border:1px solid #f0383855; border-radius:10px; '
            'padding:10px 16px; margin-bottom:12px; text-align:center;">'
            '<div style="color:#f03838; font-size:12px; font-weight:700;">'
            'Nenhuma máquina encontrada com esses filtros</div></div>',
            unsafe_allow_html=True
        )
        return

    total_maq    = int((df_filtrado["pot_maquina_num"] > 0).sum())
    total_pot    = formatar_potencia(df_filtrado["pot_maquina_num"].sum())
    bases_unicas = df_filtrado["base"].nunique()

    st.markdown(
        '<div style="background:' + cor + '12; border:1px solid ' + cor + '44; border-radius:10px; '
        'padding:10px 16px; margin-bottom:12px;">'
        '<div style="color:' + cor + '; font-size:11px; font-weight:700; margin-bottom:6px;">🔍 RESULTADO DO FILTRO</div>'
        '<div style="display:flex; gap:24px;">'
        '<div><div><div style="color:#8888aa; font-size:10px;">MÁQUINAS</div>'
        '<div style="color:#e0e0f0; font-size:16px; font-weight:700;">' + str(total_maq) + '</div></div></div>'
        '<div><div><div style="color:#8888aa; font-size:10px;">POTÊNCIA</div>'
        '<div style="color:#22c55e; font-size:16px; font-weight:700;">' + total_pot + '</div></div></div>'
        '<div><div><div style="color:#8888aa; font-size:10px;">BASES</div>'
        '<div style="color:' + cor + '; font-size:16px; font-weight:700;">' + str(bases_unicas) + '</div></div></div>'
        '</div></div>',
        unsafe_allow_html=True
    )


def renderizar_botao_base(base_num, key_prefix, bases_destaque):
    _sel   = st.session_state.get("base_sel") == base_num
    _match = bases_destaque is not None and base_num in bases_destaque
    if _sel:
        lbl = "✓ Base " + f"{base_num:02d}"
    elif _match:
        lbl = "★ Base " + f"{base_num:02d}"
    else:
        lbl = "Base " + f"{base_num:02d}"
    if st.button(lbl, key=key_prefix + "btn_" + str(base_num)):
        st.session_state["base_sel"] = None if _sel else base_num
        st.rerun()


def injetar_estilos_botoes(filtro_ativo):
    flag = "true" if filtro_ativo else "false"
    components.html("""
    <script>
    function estilizarBotoes() {
        var filtroAtivo = """ + flag + """;
        var botoes = window.parent.document.querySelectorAll('button');
        botoes.forEach(function(btn) {
            var txt = (btn.innerText || btn.textContent || '').trim();
            if (txt.startsWith('✓')) {
                btn.style.setProperty('background-color', '#5b21b6', 'important');
                btn.style.setProperty('color',            '#ffffff',  'important');
                btn.style.setProperty('border-color',     '#7c6af7',  'important');
                btn.style.setProperty('font-weight',      '900',      'important');
                btn.style.setProperty('box-shadow', '0 0 10px #7c6af766', 'important');
            } else if (txt.startsWith('★')) {
                btn.style.setProperty('background-color', '#14532d', 'important');
                btn.style.setProperty('color',            '#22c55e', 'important');
                btn.style.setProperty('border-color',     '#22c55e', 'important');
                btn.style.setProperty('font-weight',      '900',     'important');
                btn.style.setProperty('box-shadow', '0 0 10px #22c55e55', 'important');
            } else if (txt.startsWith('Base ')) {
                if (filtroAtivo) {
                    btn.style.setProperty('background-color', '#0f0f18', 'important');
                    btn.style.setProperty('color',            '#2a2a4a', 'important');
                    btn.style.setProperty('border-color',     '#1a1a28', 'important');
                    btn.style.setProperty('box-shadow',       'none',    'important');
                } else {
                    btn.style.setProperty('background-color', '#1e1e32', 'important');
                    btn.style.setProperty('color',            '#d0d0f0', 'important');
                    btn.style.setProperty('border-color',     '#3a3a5a', 'important');
                    btn.style.setProperty('font-weight',      '700',     'important');
                    btn.style.setProperty('box-shadow',       'none',    'important');
                }
            }
        });
    }
    setTimeout(estilizarBotoes, 80);
    setTimeout(estilizarBotoes, 300);
    setTimeout(estilizarBotoes, 700);
    setTimeout(estilizarBotoes, 1500);
    </script>
    """, height=0)


# ── telas ─────────────────────────────────────────────────────────────────────

def show_login_page():
    st.markdown(
        "<div style='text-align:center; padding:20px 0 10px 0;'>"
        "<div style='font-size:64px; margin-bottom:12px;'>🔒</div>"
        "<h1 style='font-size:36px; font-weight:900; letter-spacing:2px; color:#e0e0f0; margin-bottom:4px;'>LOGIN</h1>"
        "<p style='color:#8888aa; font-size:14px; margin:0;'>Acesse o Sistema de Gestão do Pátio de Máquinas</p></div>",
        unsafe_allow_html=True
    )
    st.markdown("<hr class='separador'>", unsafe_allow_html=True)

    with st.form("login_form"):
        username = st.text_input("Usuário")
        password = st.text_input("Senha", type="password")
        login_button = st.form_submit_button("Entrar")

        if login_button:
            profile = authenticate(username, password)
            if profile:
                st.session_state["logged_in"] = True
                st.session_state["user_profile"] = profile
                st.success(f"Bem-vindo, {username}! Perfil: {profile.capitalize()}")
                st.rerun()
            else:
                st.error("Usuário ou senha inválidos.")

    st.markdown("<hr class='separador'>", unsafe_allow_html=True)
    st.markdown(
        "<small style='color:#4a4a6a; text-align:center; display:block;'>Usina Xavantes · Goiânia/GO</small>",
        unsafe_allow_html=True
    )


def tela_home(df_plan=None):
    pot_contratada_str = f"{POTENCIA_CONTRATADA_MW:.2f}".replace(".", ",") + " MW"
    pot_planejada_kw   = (
        df_plan["pot_maquina_num"].sum()
        if df_plan is not None and "pot_maquina_num" in df_plan.columns else 0
    )
    pot_planejada_str = formatar_potencia(pot_planejada_kw)

    st.markdown(
        "<div style='text-align:center; padding:20px 0 10px 0;'>"
        "<div style='font-size:64px; margin-bottom:12px;'>⚙️</div>"
        "<h1 style='font-size:36px; font-weight:900; letter-spacing:2px; color:#e0e0f0; margin-bottom:4px;'>USINA XAVANTES</h1>"
        "<p style='color:#8888aa; font-size:14px; margin:0;'>Sistema de Gestão do Pátio de Máquinas</p></div>",
        unsafe_allow_html=True
    )
    st.markdown("<hr class='separador'>", unsafe_allow_html=True)

    col_contratada, col_planejada = st.columns(2, gap="large")
    with col_contratada:
        st.markdown(
            '<div style="background:linear-gradient(135deg, #0a1a0a 0%, #0f2a0f 100%); '
            'border:2px solid #22c55e; border-radius:20px; padding:32px; text-align:center;">'
            '<div style="color:#8888aa; font-size:11px; font-weight:700; letter-spacing:2px; '
            'text-transform:uppercase; margin-bottom:8px;">⚡ Potência Contratada</div>'
            '<div style="color:#22c55e; font-size:48px; font-weight:900; letter-spacing:1px; line-height:1;">' + pot_contratada_str + '</div>'
            '<div style="color:#4a8a5a; font-size:11px; margin-top:10px;">Potência total contratada pela usina</div></div>',
            unsafe_allow_html=True
        )
    with col_planejada:
        st.markdown(
            '<div style="background:linear-gradient(135deg, #0a0a1a 0%, #12122a 100%); '
            'border:2px solid #7c6af7; border-radius:20px; padding:32px; text-align:center;">'
            '<div style="color:#8888aa; font-size:11px; font-weight:700; letter-spacing:2px; '
            'text-transform:uppercase; margin-bottom:8px;">📋 Potência Planejada</div>'
            '<div style="color:#7c6af7; font-size:48px; font-weight:900; letter-spacing:1px; line-height:1;">' + pot_planejada_str + '</div>'
            '<div style="color:#4a4a8a; font-size:11px; margin-top:10px;">Somatória das máquinas no pátio planejado</div></div>',
            unsafe_allow_html=True
        )

    st.markdown("<hr class='separador'>", unsafe_allow_html=True)
    col_end, col_tel = st.columns(2, gap="large")
    with col_end:
        st.markdown(
            '<div style="background:#0f0f1e; border:1px solid #2a2a4a; border-radius:16px; padding:24px 28px;">'
            '<div style="color:#7c6af7; font-size:11px; font-weight:700; text-transform:uppercase; letter-spacing:2px; margin-bottom:14px;">📍 Endereço</div>'
            '<div style="color:#e0e0f0; font-size:14px; font-weight:600; line-height:1.8;">Rodovia GO 080, Km 06</div>'
            '<div style="color:#a0a0c0; font-size:13px; line-height:1.8;">Chácaras — Bom Retiro — Zona Rural<br>Goiânia / GO — CEP 74690-170</div></div>',
            unsafe_allow_html=True
        )
    with col_tel:
        st.markdown(
            '<div style="background:#0f0f1e; border:1px solid #2a2a4a; border-radius:16px; padding:24px 28px;">'
            '<div style="color:#f59e0b; font-size:11px; font-weight:700; text-transform:uppercase; letter-spacing:2px; margin-bottom:14px;">📞 Contato</div>'
            '<div style="color:#8888aa; font-size:12px; margin-bottom:6px;">Telefone</div>'
            '<div style="color:#e0e0f0; font-size:22px; font-weight:700; letter-spacing:1px;">(62) 3221-0700</div>'
            '<div style="color:#4a4a6a; font-size:11px; margin-top:16px;">Atendimento em horário comercial</div></div>',
            unsafe_allow_html=True
        )


def tela_selecao_patio(df_atual, df_plan):
    if st.button("← Voltar", key="btn_voltar_selecao"):
        st.session_state["tela"]     = "home"
        st.session_state["base_sel"] = None
        st.session_state["editar_horimetro"] = None
        st.rerun()

    st.markdown(
        "<h2 style='text-align:center; margin-bottom:4px;'>⚙️ Pátio de Máquinas</h2>"
        "<p style='text-align:center; color:#8888aa; font-size:13px; margin-bottom:36px;'>Selecione a visualização desejada</p>",
        unsafe_allow_html=True
    )

    pot_atual = formatar_potencia(df_atual["pot_maquina_num"].sum() if df_atual is not None and "pot_maquina_num" in df_atual.columns else 0)
    pot_plan  = formatar_potencia(df_plan["pot_maquina_num"].sum()  if df_plan  is not None and "pot_maquina_num" in df_plan.columns  else 0)
    maq_atual = contar_maquinas(df_atual)
    maq_plan  = contar_maquinas(df_plan)

    col1, col2 = st.columns(2, gap="large")
    with col1:
        st.markdown(
            '<div style="background:linear-gradient(135deg, #12122a 0%, #1a1a3a 100%); '
            'border:2px solid #7c6af7; border-radius:20px; padding:36px 32px; text-align:center;">'
            '<div style="font-size:48px; margin-bottom:16px;">⚙️</div>'
            '<div style="color:#7c6af7; font-size:22px; font-weight:800; margin-bottom:8px;">PÁTIO ATUAL</div>'
            '<div style="color:#8888aa; font-size:13px; margin-bottom:24px;">Configuração atual do pátio de máquinas</div>'
            '<div style="display:flex; justify-content:center; gap:32px;">'
            '<div><div><div style="color:#8888aa; font-size:10px;">MÁQUINAS</div>'
            '<div style="color:#e0e0f0; font-size:24px; font-weight:700;">' + str(maq_atual) + '</div></div></div>'
            '<div><div><div style="color:#8888aa; font-size:10px;">POTÊNCIA</div>'
            '<div style="color:#22c55e; font-size:24px; font-weight:700;">' + pot_atual + '</div></div></div>'
            '</div></div>',
            unsafe_allow_html=True
        )
        if st.button("Acessar Pátio Atual →", key="btn_atual"):
            st.session_state["tela"] = "atual"; st.session_state["base_sel"] = None; st.rerun()
    with col2:
        st.markdown(
            '<div style="background:linear-gradient(135deg, #1a1200 0%, #2a1e00 100%); '
            'border:2px solid #f59e0b; border-radius:20px; padding:36px 32px; text-align:center;">'
            '<div style="font-size:48px; margin-bottom:16px;">📋</div>'
            '<div style="color:#f59e0b; font-size:22px; font-weight:800; margin-bottom:8px;">PÁTIO PLANEJADO</div>'
            '<div style="color:#8888aa; font-size:13px; margin-bottom:24px;">Configuração planejada do pátio</div>'
            '<div style="display:flex; justify-content:center; gap:32px;">'
            '<div><div><div style="color:#8888aa; font-size:10px;">MÁQUINAS</div>'
            '<div style="color:#e0e0f0; font-size:24px; font-weight:700;">' + str(maq_plan) + '</div></div></div>'
            '<div><div><div style="color:#8888aa; font-size:10px;">POTÊNCIA</div>'
            '<div style="color:#22c55e; font-size:24px; font-weight:700;">' + pot_plan + '</div></div></div>'
            '</div></div>',
            unsafe_allow_html=True
        )
        if st.button("Acessar Pátio Planejado →", key="btn_plan"):
            st.session_state["tela"] = "planejado"; st.session_state["base_sel"] = None; st.rerun()


def tela_patio(df, titulo, cor_a, cor_b, tela_origem="selecao_patio",
               tem_origem=False, filtro_motor=None, filtro_alt=None,
               filtro_origem=None, modo_horimetro=False,
               filtro_serie_motor=None, filtro_serie_alternador=None): # Novos parâmetros de filtro

    if st.button("← Voltar", key="btn_voltar"):
        st.session_state["tela"]             = tela_origem
        st.session_state["base_sel"] = None
        st.session_state["editar_horimetro"] = None
        st.rerun()

    filtro_ativo = bool(filtro_motor or filtro_alt or filtro_origem or filtro_serie_motor or filtro_serie_alternador)
    if filtro_ativo:
        df_view, bases_destaque = aplicar_filtros(df, filtro_motor, filtro_alt, filtro_origem, filtro_serie_motor, filtro_serie_alternador)
    else:
        df_view        = df
        bases_destaque = None

    pot_total_kw  = df_view["pot_maquina_num"].sum() if df_view is not None and "pot_maquina_num" in df_view.columns else 0

    # --- AJUSTE AQUI: Lógica de soma para o Lado A ---
    pot_a_kw_parte1 = df_view[df_view["base"].between(1, 17)]["pot_maquina_num"].sum() if df_view is not None and "pot_maquina_num" in df_view.columns else 0
    pot_a_kw_parte2 = df_view[df_view["base"] == 37]["pot_maquina_num"].sum() if df_view is not None and "pot_maquina_num" in df_view.columns else 0
    pot_a_kw        = pot_a_kw_parte1 + pot_a_kw_parte2
    # --- FIM DO AJUSTE ---

    pot_b_kw      = pot_lado(df_view, 18, 36) # Lado B continua de 18 a 36
    pot_total_str = formatar_potencia(pot_total_kw)
    pot_a_str     = formatar_potencia(pot_a_kw)
    pot_b_str     = formatar_potencia(pot_b_kw)

    st.markdown("# ⚙️ " + titulo)

    _, col_total, _ = st.columns([2, 2, 2], gap="small")
    with col_total:
        label_t = "Potência Total (filtrada)" if filtro_ativo else "Potência Total"
        st.markdown(
            '<div style="background:#0a1a0a; border:1px solid #22c55e55; '
            'border-radius:10px; padding:10px 16px; text-align:center;">'
            '<div style="color:#8888aa; font-size:10px;">' + label_t + '</div>'
            '<div style="color:#22c55e; font-size:20px; font-weight:700;">' + pot_total_str + '</div>'
            '<div style="color:#4a4a6a; font-size:10px;">Bases 01 – 37</div>', # Texto atualizado para 37
            unsafe_allow_html=True
        )

    if filtro_ativo:
        resumo_filtro(df_view, cor_a)

    st.markdown(
        "<p style='color:#8888aa; font-size:13px; margin-top:10px;'>"
        "Clique em uma base para ver as posições e equipamentos.</p>",
        unsafe_allow_html=True
    )

    st.markdown("<hr class='separador'>", unsafe_allow_html=True)

    base_sel   = st.session_state.get("base_sel")
    key_prefix = st.session_state.get("tela", "")

    if base_sel is not None:
        df_pos  = get_posicoes(df_view if filtro_ativo else df, base_sel)
        # Corrigido para considerar a base 37 como parte do Lado A
        cor_sel = cor_a if base_sel <= 17 or base_sel == 37 else cor_b
        if not df_pos.empty:
            painel_detalhe(base_sel, df_pos, cor_sel, tem_origem=tem_origem, modo_horimetro=modo_horimetro)
        else:
            st.warning("Sem dados para Base " + f"{base_sel:02d}" + " com os filtros aplicados.")
            st.markdown("<hr class='separador'>", unsafe_allow_html=True)

    N_COLS = 4
    col_lado_a, col_corredor, col_lado_b = st.columns([5, 1, 5])

    with col_lado_a:
        st.markdown(
            '<div style="background:' + cor_a + '18; border:1px solid ' + cor_a + '44; '
            'border-radius:12px; padding:12px 16px; margin-bottom:12px; text-align:center;">'
            '<div style="color:' + cor_a + '; font-size:14px; font-weight:700; text-transform:uppercase;">LADO A</div>'
            '<div style="color:#8888aa; font-size:11px;">Bases 01 – 17 e Base 37</div>' # Texto atualizado
            '<div style="color:' + cor_a + '; font-size:16px; font-weight:800; margin-top:6px;">' + pot_a_str + '</div>'
            '</div>',
            unsafe_allow_html=True
        )
        # --- AJUSTE AQUI: Bases do Lado A ---
        bases_a  = list(range(1, 18)) + [37] # Inclui 1 a 17 e a 37
        # --- FIM DO AJUSTE ---
        linhas_a = [bases_a[i:i + N_COLS] for i in range(0, len(bases_a), N_COLS)]
        for linha in linhas_a:
            cols = st.columns(N_COLS)
            for idx, base_num in enumerate(linha):
                with cols[idx]:
                    renderizar_botao_base(base_num, key_prefix, bases_destaque)

        # O bloco que desabilitava a Base 17 foi removido, reabilitando-a.

    with col_corredor:
        st.markdown(
            '<div style="background:#0a0a14; border:1px solid #1e1e2e; border-radius:10px; '
            'min-height:500px; display:flex; align-items:center; justify-content:center; '
            'padding:10px 4px; text-align:center;">'
            '<div style="color:#3a3a6a; font-size:10px; font-weight:600; '
            'writing-mode:vertical-rl; text-orientation:mixed; letter-spacing:3px;">C O R R E D O R</div></div>',
            unsafe_allow_html=True
        )

    with col_lado_b:
        st.markdown(
            '<div style="background:' + cor_b + '18; border:1px solid ' + cor_b + '44; '
            'border-radius:12px; padding:12px 16px; margin-bottom:12px; text-align:center;">'
            '<div style="color:' + cor_b + '; font-size:14px; font-weight:700; text-transform:uppercase;">LADO B</div>'
            '<div style="color:#8888aa; font-size:11px;">Bases 18 – 36</div>'
            '<div style="color:' + cor_b + '; font-size:16px; font-weight:800; margin-top:6px;">' + pot_b_str + '</div>'
            '</div>',
            unsafe_allow_html=True
        )
        bases_b  = list(range(18, 37))
        linhas_b = [bases_b[i:i + N_COLS] for i in range(0, len(bases_b), N_COLS)]
        for linha in linhas_b:
            cols = st.columns(N_COLS)
            for idx, base_num in enumerate(linha):
                with cols[idx]:
                    renderizar_botao_base(base_num, key_prefix, bases_destaque)

    injetar_estilos_botoes(filtro_ativo)

    st.markdown("<hr class='separador'>", unsafe_allow_html=True)
    total = len(df) if df is not None else 0
    st.markdown(
        "<p style='color:#3a3a6a; font-size:11px; text-align:center;'>"
        "Total de registros: " + str(total) + " &nbsp;|&nbsp; Lado A: bases 01–17 e 37 &nbsp;|&nbsp; Lado B: bases 18–36</p>", # Texto atualizado
        unsafe_allow_html=True
    )

    if df is not None and total > 0:
        with st.expander("🔍 Debug — dados carregados da planilha"):
            st.dataframe(df, use_container_width=True, hide_index=True)


def tela_horimetro(df_plan, erros):
    st.markdown(
        '<div style="display:flex; align-items:center; gap:16px; margin-bottom:4px;">'
        '<div style="font-size:32px;">🕐</div>'
        '<div>'
        '<h1 style="margin:0; font-size:28px; font-weight:900; color:#e0e0f0;">Atualização de Horímetro</h1>'
        '<p style="margin:0; color:#8888aa; font-size:13px;">Visualização baseada no Pátio Planejado</p>'
        '</div></div>',
        unsafe_allow_html=True
    )
    st.markdown("<hr class='separador'>", unsafe_allow_html=True)

    if erros.get("planejado"):
        st.error("Erro ao carregar Pátio Planejado: " + erros["planejado"])
        return

    # Operador e Engenharia podem editar horímetros
    modo_horimetro_habilitado = (st.session_state.get("user_profile") in ["engenharia", "operacao"])

    tela_patio(
        df=df_plan,
        titulo="Horímetro — Pátio Planejado",
        cor_a="#06b6d4",
        cor_b="#f59e0b",
        tela_origem="home",
        tem_origem=False,
        modo_horimetro=modo_horimetro_habilitado,
        filtro_motor=st.session_state.get("hf_motor", []),
        filtro_alt=st.session_state.get("hf_alt", []),
        filtro_origem=[],
    )


# ── slicer e formulário de manutenção ─────────────────────────────────────────

def slicer_manutencao(modelo_motor, key_prefix):
    opcoes  = get_opcoes_slicer(modelo_motor)
    sel     = st.session_state.get("manut_slicer_" + key_prefix)
    cols_sl = st.columns(len(opcoes))
    for idx, op in enumerate(opcoes):
        with cols_sl[idx]:
            ativo   = sel == op["key"]
            btn_lbl = "✓ " + op["label"] if ativo else op["label"]
            if st.button(btn_lbl, key="sl_" + key_prefix + "_" + str(op["key"])):
                st.session_state["manut_slicer_" + key_prefix] = None if ativo else op["key"]
                st.rerun()


def formulario_registro(maq_sel, faixa_sel, hor_atual, faixas, key_suffix, user_profile):
    eh_checklist = faixa_sel == "checklist"
    if eh_checklist:
        titulo_form = "✅ Registrar Check-list"
        cor_form    = "#06b6d4"
        itens_txt   = "Verificação geral da máquina"
    else:
        info_f      = faixas.get(faixa_sel, {})
        titulo_form = "📋 Registrar Manutenção " + info_f.get("label", str(faixa_sel) + "h")
        cor_form    = "#22c55e"
        itens_txt   = ", ".join(info_f.get("itens", []))

    st.markdown(
        '<div style="background:linear-gradient(135deg, #0a1a0a 0%, #0f2010 100%); '
        'border:2px solid ' + cor_form + '; border-radius:16px; padding:18px 22px; margin-top:12px;">'
        '<div style="color:' + cor_form + '; font-size:13px; font-weight:700; '
        'text-transform:uppercase; letter-spacing:1px;">'
        + titulo_form + ' — ' + maq_sel + '</div>'
        '<div style="color:#8888aa; font-size:11px;">' + itens_txt + '</div>'
        '</div>',
        unsafe_allow_html=True
    )

    # Operador e Engenharia podem registrar
    if user_profile in ["engenharia", "operacao"]:
        col1, col2, col3, col4 = st.columns([2, 2, 2, 2], gap="small")

        with col1:
            hor_registro = st.number_input(
                "Horímetro Manutenção (h)", min_value=0,
                value=int(hor_atual) if hor_atual else 0,
                step=1, key="mf_hor_" + key_suffix
            )
        with col2:
            data_registro = st.date_input(
                "Data da execução", value=date.today(),
                key="mf_data_" + key_suffix
            )
        with col3:
            responsavel = st.text_input("Responsável", key="mf_resp_" + key_suffix)
        with col4:
            st.markdown("<div style='margin-top:10px; color:#8888aa; font-size:10px;'>Atualiza horímetro?</div>",
                        unsafe_allow_html=True)
            atualizar_hor = st.checkbox(
                "Sim, atualizar", value=not eh_checklist,
                key="mf_atkhor_" + key_suffix
            )

        observacao = st.text_area("Observações (opcional)", key="mf_obs_" + key_suffix, height=70)

        col_salvar, col_cancel, _ = st.columns([1, 1, 3])
        with col_salvar:
            if st.button("💾 Salvar", key="mf_salvar_" + key_suffix):
                if not responsavel.strip():
                    st.warning("Informe o nome do responsável.")
                else:
                    salvar_manutencao(
                        maq_sel, faixa_sel, hor_registro,
                        data_registro, responsavel, observacao,
                        atualizar_horimetro=atualizar_hor
                    )
                    st.session_state["manut_slicer_" + maq_sel] = None
                    label_ok = "Check-list" if eh_checklist else faixas.get(faixa_sel, {}).get("label", str(faixa_sel) + "h")
                    st.success("✅ " + label_ok + " registrado para " + maq_sel)
                    st.rerun()
        with col_cancel:
            if st.button("✖ Cancelar", key="mf_cancel_" + key_suffix):
                st.session_state["manut_slicer_" + maq_sel] = None
                st.rerun()
    else:
        st.info("Você não tem permissão para registrar manutenções.")


# ── gráficos de análise ───────────────────────────────────────────────────────

def plot_config():
    return {
        "paper_bgcolor": "#0f0f1a",
        "plot_bgcolor":  "#0a0a14",
        "font":          {"color": "#e0e0f0", "family": "sans-serif"},
        "xaxis":         {"gridcolor": "#1e1e2e", "linecolor": "#2a2a4a", "tickfont": {"color": "#8888aa"}},
        "yaxis":         {"gridcolor": "#1e1e2e", "linecolor": "#2a2a4a", "tickfont": {"color": "#8888aa"}},
        "margin":        {"l": 40, "r": 20, "t": 50, "b": 40},
    }


def grafico_horimetro_tendencia(dados_hor, labels_maquinas):
    fig = go.Figure()
    cores = px.colors.qualitative.Plotly

    for i, label in enumerate(labels_maquinas):
        hist = dados_hor.get(label, {}).get("historico", [])
        if len(hist) < 2:
            continue
        datas    = [h["data"]      for h in hist]
        valores  = [h["horimetro"] for h in hist]
        cor      = cores[i % len(cores)]

        fig.add_trace(go.Scatter(
            x=datas, y=valores,
            mode="lines+markers",
            name=label,
            line={"color": cor, "width": 2},
            marker={"size": 6, "color": cor},
            hovertemplate="<b>" + label + "</b><br>Data: %{x}<br>Horímetro: %{y:,} h<extra></extra>"
        ))

    cfg = plot_config()
    fig.update_layout(
        title={"text": "📈 Evolução do Horímetro por Máquina", "font": {"size": 16, "color": "#e0e0f0"}},
        paper_bgcolor=cfg["paper_bgcolor"],
        plot_bgcolor=cfg["plot_bgcolor"],
        font=cfg["font"],
        xaxis={**cfg["xaxis"], "title": "Data"},
        yaxis={**cfg["yaxis"], "title": "Horímetro (h)"},
        margin=cfg["margin"],
        legend={"bgcolor": "#0a0a14", "bordercolor": "#2a2a4a", "borderwidth": 1},
        hovermode="x unified",
    )
    return fig


def grafico_manutencoes_por_tipo(dados_manu, labels_maquinas, periodo_dias):
    data_corte = date.today() - timedelta(days=periodo_dias)
    contagem   = {}

    for label in labels_maquinas:
        hist = dados_manu.get(label, {}).get("historico", [])
        for h in hist:
            try:
                d = datetime.strptime(h["data"], "%Y-%m-%d").date()
            except Exception:
                continue
            if d < data_corte:
                continue
            faixa = h.get("faixa", "—")
            if faixa == "checklist":
                chave = "Check-list"
            else:
                chave = str(faixa) + "h"
            contagem[chave] = contagem.get(chave, 0) + 1

    if not contagem:
        return None

    ordem = ["Check-list"] + [k for k in sorted(contagem.keys()) if k != "Check-list"]
    tipos = [t for t in ordem if t in contagem]
    qtds  = [contagem[t] for t in tipos]
    cores_mapa = {
        "Check-list": "#06b6d4",
        "300h": "#7c6af7", "600h": "#a78bfa", "900h": "#c4b5fd", "3600h": "#5b21b6",
        "400h": "#f59e0b", "800h": "#fbbf24", "1200h": "#fcd34d", "4000h": "#d97706",
    }
    cores = [cores_mapa.get(t, "#8888aa") for t in tipos]

    fig = go.Figure(go.Bar(
        x=tipos, y=qtds,
        marker_color=cores,
        text=qtds,
        textposition="outside",
        textfont={"color": "#e0e0f0"},
        hovertemplate="<b>%{x}</b><br>Quantidade: %{y}<extra></extra>"
    ))

    cfg = plot_config()
    fig.update_layout(
        title={"text": "🔧 Manutenções Realizadas por Tipo", "font": {"size": 16, "color": "#e0e0f0"}},
        paper_bgcolor=cfg["paper_bgcolor"],
        plot_bgcolor=cfg["plot_bgcolor"],
        font=cfg["font"],
        xaxis={**cfg["xaxis"], "title": "Tipo"},
        yaxis={**cfg["yaxis"], "title": "Quantidade"},
        margin=cfg["margin"],
    )
    return fig


def grafico_intervalo_real_vs_esperado(dados_manu, dados_hor, labels_maquinas, df_plan):
    registros = []
    for label in labels_maquinas:
        row_df = df_plan[df_plan["label"] == label]
        if row_df.empty:
            continue
        modelo_motor = safe_val(row_df.iloc[0], "modelo_motor")
        tipo, plano  = get_plano(modelo_motor)
        hist         = dados_manu.get(label, {}).get("historico", [])
        manut_hora   = [h for h in hist if h.get("faixa") != "checklist" and isinstance(h.get("faixa"), int)]

        if len(manut_hora) < 2:
            continue

        for i in range(1, len(manut_hora)):
            prev = manut_hora[i - 1]
            curr = manut_hora[i]
            intervalo_real    = curr.get("horimetro", 0) - prev.get("horimetro", 0)
            faixa             = curr.get("faixa", 0)
            intervalo_esperado = faixa if faixa in plano["faixas"] else plano["intervalo_base"]
            desvio            = intervalo_real - intervalo_esperado
            registros.append({
                "Máquina":   label,
                "Faixa":     str(faixa) + "h",
                "Data":      curr.get("data", ""),
                "Real (h)":  intervalo_real,
                "Esperado (h)": intervalo_esperado,
                "Desvio (h)":   desvio,
            })

    if not registros:
        return None

    df_r  = pd.DataFrame(registros)
    cores = df_r["Desvio (h)"].apply(lambda d: "#f03838" if d < -20 else ("#f59e0b" if d < 0 else "#22c55e"))

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df_r["Máquina"] + " — " + df_r["Faixa"],
        y=df_r["Desvio (h)"],
        marker_color=cores,
        text=df_r["Desvio (h)"].apply(lambda v: ("+" if v >= 0 else "") + str(int(v)) + " h"),
        textposition="outside",
        textfont={"color": "#e0e0f0"},
        hovertemplate=(
            "<b>%{x}</b><br>"
            "Intervalo real: %{customdata[0]} h<br>"
            "Intervalo esperado: %{customdata[1]} h<br>"
            "Desvio: %{y} h<extra></extra>"
        ),
        customdata=df_r[["Real (h)", "Esperado (h)"]].values
    ))

    fig.add_hline(y=0, line_color="#4a4a6a", line_width=1, line_dash="dash")

    cfg = plot_config()
    fig.update_layout(
        title={"text": "📊 Desvio de Intervalo: Real vs Esperado", "font": {"size": 16, "color": "#e0e0f0"}},
        paper_bgcolor=cfg["paper_bgcolor"],
        plot_bgcolor=cfg["plot_bgcolor"],
        font=cfg["font"],
        xaxis={**cfg["xaxis"], "title": "", "tickangle": -30},
        yaxis={**cfg["yaxis"], "title": "Desvio (h)"},
        margin={"l": 40, "r": 20, "t": 50, "b": 80},
    )
    return fig


def grafico_checklist_frequencia(dados_manu, labels_maquinas, periodo_dias):
    data_corte = date.today() - timedelta(days=periodo_dias)
    registros  = []

    for label in labels_maquinas:
        hist = dados_manu.get(label, {}).get("historico", [])
        cls  = [h for h in hist if h.get("faixa") == "checklist"]
        for h in cls:
            try:
                d = datetime.strptime(h["data"], "%Y-%m-%d").date()
            except Exception:
                continue
            if d >= data_corte:
                registros.append({"Máquina": label, "Data": str(d)})

    if not registros:
        return None

    df_cl  = pd.DataFrame(registros)
    contag = df_cl.groupby(["Data", "Máquina"]).size().reset_index(name="Qtd")

    fig = px.bar(
        contag, x="Data", y="Qtd", color="Máquina",
        barmode="stack",
        color_discrete_sequence=px.colors.qualitative.Plotly,
    )

    cfg = plot_config()
    fig.update_layout(
        title={"text": "✅ Frequência de Check-lists por Data", "font": {"size": 16, "color": "#e0e0f0"}},
        paper_bgcolor=cfg["paper_bgcolor"],
        plot_bgcolor=cfg["plot_bgcolor"],
        font=cfg["font"],
        xaxis={**cfg["xaxis"], "title": "Data"},
        yaxis={**cfg["yaxis"], "title": "Quantidade"},
        margin=cfg["margin"],
        legend={"bgcolor": "#0a0a14", "bordercolor": "#2a2a4a", "borderwidth": 1},
    )
    fig.update_traces(
        hovertemplate="<b>%{fullData.name}</b><br>Data: %{x}<br>Qtd: %{y}<extra></extra>"
    )
    return fig


def aba_analise(dados_manu, dados_hor, df_plan):
    st.markdown(
        '<div style="color:#8888aa; font-size:12px; margin-bottom:16px;">'
        'Análise de tendência baseada nos registros salvos de todas as máquinas.</div>',
        unsafe_allow_html=True
    )

    labels_todas = []
    if df_plan is not None and not df_plan.empty:
        labels_todas = df_plan["label"].tolist()

    col_filtro, col_periodo = st.columns([3, 1], gap="small")
    with col_filtro:
        opcoes_maq = [l for l in labels_todas if l in dados_manu or l in dados_hor]
        if not opcoes_maq:
            opcoes_maq = labels_todas
        maquinas_sel = st.multiselect(
            "Filtrar máquinas", options=labels_todas,
            default=opcoes_maq[:10] if len(opcoes_maq) > 10 else opcoes_maq,
            key="analise_maq_sel"
        )
    with col_periodo:
        periodo = st.selectbox(
            "Período", options=[30, 60, 90, 180, 365],
            format_func=lambda x: str(x) + " dias",
            index=2, key="analise_periodo"
        )

    if not maquinas_sel:
        st.info("Selecione ao menos uma máquina para visualizar os gráficos.")
        return

    st.markdown("<hr class='separador'>", unsafe_allow_html=True)

    # Gráfico 1 — Evolução do horímetro
    fig1 = grafico_horimetro_tendencia(dados_hor, maquinas_sel)
    if fig1:
        st.plotly_chart(fig1, use_container_width=True)
    else:
        st.markdown(
            '<div style="background:#0a0a14; border:1px solid #2a2a4a; border-radius:10px; '
            'padding:20px; text-align:center; color:#4a4a6a; margin-bottom:16px;">'
            '📈 Sem dados de horímetro suficientes para o gráfico de evolução.</div>',
            unsafe_allow_html=True
        )

    col_g2, col_g3 = st.columns(2, gap="medium")

    # Gráfico 2 — Manutenções por tipo
    with col_g2:
        fig2 = grafico_manutencoes_por_tipo(dados_manu, maquinas_sel, periodo)
        if fig2:
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.markdown(
                '<div style="background:#0a0a14; border:1px solid #2a2a4a; border-radius:10px; '
                'padding:20px; text-align:center; color:#4a4a6a;">'
                '🔧 Sem manutenções registradas no período.</div>',
                unsafe_allow_html=True
            )

    # Gráfico 3 — Check-list frequência
    with col_g3:
        fig3 = grafico_checklist_frequencia(dados_manu, maquinas_sel, periodo)
        if fig3:
            st.plotly_chart(fig3, use_container_width=True)
        else:
            st.markdown(
                '<div style="background:#0a0a14; border:1px solid #2a2a4a; border-radius:10px; '
                'padding:20px; text-align:center; color:#4a4a6a;">'
                '✅ Sem check-lists registrados no período.</div>',
                unsafe_allow_html=True
            )

    # Gráfico 4 — Desvio intervalo real vs esperado
    fig4 = grafico_intervalo_real_vs_esperado(dados_manu, dados_hor, maquinas_sel, df_plan)
    if fig4:
        st.plotly_chart(fig4, use_container_width=True)
    else:
        st.markdown(
            '<div style="background:#0a0a14; border:1px solid #2a2a4a; border-radius:10px; '
            'padding:20px; text-align:center; color:#4a4a6a;">'
            '📊 Dados insuficientes para análise de desvio de intervalo.</div>',
            unsafe_allow_html=True
        )


# ── tela principal de manutenção ──────────────────────────────────────────────

def tela_manutencao(df_plan, erros):
    if "manut_base_sel" not in st.session_state: st.session_state["manut_base_sel"] = None
    if "manut_maq_sel"  not in st.session_state: st.session_state["manut_maq_sel"]  = None

    st.markdown(
        '<div style="display:flex; align-items:center; gap:16px; margin-bottom:4px;">'
        '<div style="font-size:32px;">🔧</div>'
        '<div>'
        '<h1 style="margin:0; font-size:28px; font-weight:900; color:#e0e0f0;">Histórico de Manutenção</h1>'
        '<p style="margin:0; color:#8888aa; font-size:13px;">Registro e acompanhamento das manutenções preventivas</p>'
        '</div></div>',
        unsafe_allow_html=True
    )
    st.markdown("<hr class='separador'>", unsafe_allow_html=True)

    if erros.get("planejado"):
        st.error("Erro ao carregar dados: " + erros["planejado"])
        return

    dados_hor  = carregar_horimetros()
    dados_manu = carregar_manutencoes()
    user_profile = st.session_state.get("user_profile")

    tab_registro, tab_analise = st.tabs(["📋 Registro", "📊 Análise de Tendência"])

    # ── aba registro ──────────────────────────────────────────────────────────
    with tab_registro:
        base_sel = st.session_state.get("manut_base_sel")

        st.markdown(
            '<div style="color:#8888aa; font-size:13px; margin-bottom:12px; margin-top:12px;">'
            'Selecione uma base para ver as máquinas.</div>',
            unsafe_allow_html=True
        )

        N_COLS   = 6
        bases_df = sorted(df_plan["base"].unique().tolist())
        linhas   = [bases_df[i:i + N_COLS] for i in range(0, len(bases_df), N_COLS)]

        for linha in linhas:
            cols = st.columns(N_COLS)
            for idx, base_num in enumerate(linha):
                with cols[idx]:
                    _sel = base_sel == base_num
                    lbl  = "✓ Base " + f"{base_num:02d}" if _sel else "Base " + f"{base_num:02d}"
                    if st.button(lbl, key="mb_" + str(base_num)):
                        st.session_state["manut_base_sel"] = None if _sel else base_num
                        st.session_state["manut_maq_sel"]  = None
                        for k in list(st.session_state.keys()):
                            if k.startswith("manut_slicer_"):
                                del st.session_state[k]
                        st.rerun()

        if base_sel is None:
            st.markdown("<hr class='separador'>", unsafe_allow_html=True)
            st.markdown(
                '<div style="text-align:center; padding:32px; color:#4a4a6a;">'
                '⬆️ Selecione uma base acima para continuar</div>',
                unsafe_allow_html=True
            )
        else:
            st.markdown("<hr class='separador'>", unsafe_allow_html=True)

            df_pos = get_posicoes(df_plan, base_sel)
            if df_pos.empty:
                st.warning("Nenhuma máquina encontrada nessa base.")
            else:
                st.markdown(
                    '<div style="color:#06b6d4; font-size:13px; font-weight:700; margin-bottom:10px;">'
                    '⚙️ Base ' + f"{base_sel:02d}" + ' — selecione a máquina</div>',
                    unsafe_allow_html=True
                )

                maq_sel  = st.session_state.get("manut_maq_sel")
                posicoes = [row for _, row in df_pos.iterrows()]
                n_cols   = min(len(posicoes), 4)
                grupos   = [posicoes[i:i + n_cols] for i in range(0, len(posicoes), n_cols)]

                for grupo in grupos:
                    cols = st.columns(n_cols)
                    for idx, row in enumerate(grupo):
                        label        = row.get("label", str(base_sel))
                        modelo_motor = safe_val(row, "modelo_motor")
                        serie_motor  = safe_val(row, "serie_motor") # Adicionado: Obter série do motor
                        reg_hor      = dados_hor.get(label, {})
                        hor_atual    = reg_hor.get("horimetro", None)
                        hist_manu    = dados_manu.get(label, {}).get("historico", [])

                        if hor_atual is not None:
                            # Passa o label da máquina para get_proxima_manutencao
                            prox_hora, faixa_tipo, faltam, info_faixa = get_proxima_manutencao(hor_atual, modelo_motor, label)
                            tipo_p, plano_p = get_plano(modelo_motor)
                            alerta_h        = plano_p["alerta_horas"]
                            status, cor_status, bg_status = get_status_manutencao(faltam, alerta_h)
                        else:
                            faltam     = None
                            info_faixa = {}
                            cor_status = "#4a4a6a"
                            bg_status  = "#0a0a14"

                        cl_status, cl_cor, cl_bg, cl_ultimo = checklist_status(hist_manu)

                        _sel = maq_sel == label
                        cor  = "#06b6d4" if _sel else cor_status

                        hor_txt  = f"{int(hor_atual):,}".replace(",", ".") + " h" if hor_atual else "Sem horímetro"
                        prox_txt = (
                            info_faixa.get("label", "") + " — faltam " + f"{int(faltam):,}".replace(",", ".") + " h"
                            if faltam is not None else "—"
                        )
                        cl_txt = "Último: " + cl_ultimo["data"] if cl_ultimo else "Nunca realizado"

                        with cols[idx]:
                            st.markdown(
                                '<div style="background:' + bg_status + '; border:2px solid ' + cor + '; '
                                'border-radius:12px; padding:12px 14px; margin-bottom:6px;">'
                                '<div style="color:' + cor + '; font-size:14px; font-weight:800;">' + label + '</div>'
                                '<div style="color:#8888aa; font-size:10px; margin-top:4px;">Motor</div>'
                                '<div style="color:#e0e0f0; font-size:11px;">' + modelo_motor + '</div>'
                                # Adicionado: Exibir número de série do motor
                                '<div style="color:#8888aa; font-size:10px; margin-top:4px;">Nº de Série Motor</div>'
                                '<div style="color:#e0e0f0; font-size:11px;">' + serie_motor + '</div>'
                                '<div style="color:#8888aa; font-size:10px; margin-top:6px;">Horímetro</div>'
                                '<div style="color:#e0e0f0; font-size:12px; font-weight:700;">' + hor_txt + '</div>'
                                '<div style="color:#8888aa; font-size:10px; margin-top:6px;">Próx. manutenção</div>'
                                '<div style="color:' + cor_status + '; font-size:11px; font-weight:700;">' + prox_txt + '</div>'
                                '<div style="margin-top:8px; padding:5px 8px; background:' + cl_bg + '; '
                                'border:1px solid ' + cl_cor + '66; border-radius:6px;">'
                                '<div style="color:' + cl_cor + '; font-size:10px; font-weight:700;">✅ Check-list — ' + cl_status.upper() + '</div>'
                                '<div style="color:#8888aa; font-size:10px;">' + cl_txt + '</div>'
                                '</div></div>',
                                unsafe_allow_html=True
                            )
                            btn_lbl = "✓ Selecionada" if _sel else "🔧 Registrar"
                            # Botão de registro visível para engenharia e operador
                            if user_profile in ["engenharia", "operacao"]:
                                if st.button(btn_lbl, key="maq_sel_" + label):
                                    st.session_state["manut_maq_sel"] = None if _sel else label
                                    if not _sel:
                                        st.session_state["manut_slicer_" + label] = None
                                    st.rerun()
                            else:
                                # Se não for engenharia ou operador, apenas mostra o status sem o botão de ação
                                st.markdown(
                                    '<div style="color:#8888aa; font-size:11px; text-align:center; padding:8px 0;">'
                                    'Visualizar apenas</div>', unsafe_allow_html=True
                                )


                if maq_sel is not None:
                    st.markdown("<hr class='separador'>", unsafe_allow_html=True)

                    row_maq      = df_pos[df_pos["label"] == maq_sel].iloc[0]
                    modelo_motor = safe_val(row_maq, "modelo_motor")
                    serie_motor  = safe_val(row_maq, "serie_motor") # Adicionado: Obter série do motor
                    tipo, plano  = get_plano(modelo_motor)
                    faixas       = plano["faixas"]
                    reg_hor      = dados_hor.get(maq_sel, {})
                    hor_atual    = reg_hor.get("horimetro", 0) or 0
                    historico    = dados_manu.get(maq_sel, {}).get("historico", [])
                    hor_fmt      = f"{int(hor_atual):,}".replace(",", ".") if hor_atual else "0"

                    cl_status, cl_cor, cl_bg, cl_ultimo = checklist_status(historico)
                    cl_data_txt = cl_ultimo["data"] if cl_ultimo else "Nunca realizado"

                    st.markdown(
                        '<div style="background:#0a1a2a; border:2px solid #06b6d4; border-radius:16px; '
                        'padding:16px 22px; margin-bottom:16px; display:flex; justify-content:space-between; align-items:center;">'
                        '<div>'
                        '<div style="color:#06b6d4; font-size:16px; font-weight:800;">🔧 Máquina ' + maq_sel + '</div>'
                        '<div style="color:#8888aa; font-size:12px;">' + modelo_motor + ' — Série: ' + serie_motor + ' — Plano ' + tipo.upper() + '</div>' # Atualizado
                        '</div>'
                        '<div style="display:flex; gap:24px; align-items:center;">'
                        '<div style="text-align:right;">'
                        '<div style="color:#8888aa; font-size:10px;">Horímetro atual</div>'
                        '<div style="color:#22c55e; font-size:22px; font-weight:800;">' + hor_fmt + ' h</div>'
                        '</div>'
                        '<div style="padding:8px 14px; background:' + cl_bg + '; border:1px solid ' + cl_cor + '88; border-radius:10px; text-align:center;">'
                        '<div style="color:' + cl_cor + '; font-size:11px; font-weight:700;">✅ Check-list</div>'
                        '<div style="color:' + cl_cor + '; font-size:12px; font-weight:800;">' + cl_status.upper() + '</div>'
                        '<div style="color:#8888aa; font-size:10px;">' + cl_data_txt + '</div>'
                        '</div>'
                        '</div></div>',
                        unsafe_allow_html=True
                    )

                    st.markdown(
                        '<div style="color:#8888aa; font-size:11px; margin-bottom:8px;">'
                        '🔘 Selecione o tipo de manutenção realizada:</div>',
                        unsafe_allow_html=True
                    )
                    slicer_manutencao(modelo_motor, maq_sel)

                    faixa_sel = st.session_state.get("manut_slicer_" + maq_sel)

                    if faixa_sel is not None:
                        key_suffix = maq_sel + "_" + str(faixa_sel)

                        if faixa_sel != "checklist":
                            faixa_int   = int(faixa_sel)
                            faixas_keys = sorted(faixas.keys())
                            grande      = faixas_keys[-1]

                            # Obter o último horímetro para esta faixa específica
                            dados_manu_form = carregar_manutencoes()
                            info_maq_form = dados_manu_form.get(maq_sel, {})
                            ultimos_horimetros_por_faixa_form = info_maq_form.get("ultimos_horimetros_por_faixa", {})
                            ultimo_horimetro_desta_faixa_form = ultimos_horimetros_por_faixa_form.get(str(faixa_int), 0)

                            # Buscar no histórico apenas as manutenções desta faixa para exibição da última data
                            feitas      = [h for h in historico if h.get("faixa") == faixa_int]
                            ultima      = feitas[-1] if feitas else None

                            if ultimo_horimetro_desta_faixa_form > 0:
                                proxima_exec = ultimo_horimetro_desta_faixa_form + faixa_int
                            else:
                                proxima_exec = faixa_int # Se nunca foi feita, a primeira é no próprio intervalo

                            faltam_f     = proxima_exec - hor_atual

                            alerta_h          = plano["alerta_horas"]
                            status_f, cor_f, bg_f = get_status_manutencao(faltam_f, alerta_h)
                            info_f            = faixas.get(faixa_int, {})
                            ultima_txt        = (
                                f"{int(ultima['horimetro']):,}".replace(",", ".") + " h — " + ultima.get("data", "")
                                if ultima else "Nunca realizada"
                            )
                            prox_txt  = f"{int(proxima_exec):,}".replace(",", ".") + " h"
                            falta_txt = (
                                "VENCIDA há " + f"{abs(int(faltam_f)):,}".replace(",", ".") + " h"
                                if faltam_f <= 0 else "Faltam " + f"{int(faltam_f):,}".replace(",", ".") + " h"
                            )
                            itens_html = "".join([
                                '<span style="background:#1e1e32; color:#c0c0e0; font-size:11px; '
                                'padding:3px 10px; border-radius:6px; margin:2px;">• ' + it + '</span>'
                                for it in info_f.get("itens", [])
                            ])

                            st.markdown(
                                '<div style="background:' + bg_f + '; border:1px solid ' + cor_f + '55; '
                                'border-radius:12px; padding:12px 16px; margin-bottom:10px; '
                                'display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px;">'
                                '<div>'
                                '<div style="color:' + cor_f + '; font-size:14px; font-weight:800;">'
                                + info_f.get("label", "") + ' — ' + falta_txt + '</div>'
                                '<div style="display:flex; flex-wrap:wrap; gap:4px; margin-top:6px;">' + itens_html + '</div>'
                                '</div>'
                                '<div style="text-align:right;">'
                                '<div style="color:#8888aa; font-size:10px;">Última execução</div>'
                                '<div style="color:#e0e0f0; font-size:12px; font-weight:600;">' + ultima_txt + '</div>'
                                '<div style="color:#8888aa; font-size:10px; margin-top:4px;">Próxima prevista</div>'
                                '<div style="color:' + cor_f + '; font-size:13px; font-weight:700;">' + prox_txt + '</div>'
                                '</div></div>',
                                unsafe_allow_html=True
                            )
                            formulario_registro(maq_sel, faixa_int, hor_atual, faixas, key_suffix, user_profile)
                        else:
                            formulario_registro(maq_sel, "checklist", hor_atual, faixas, key_suffix, user_profile)

                    if historico:
                        st.markdown("<hr class='separador'>", unsafe_allow_html=True)
                        st.markdown(
                            '<div style="color:#e0e0f0; font-size:13px; font-weight:700; margin-bottom:10px;">'
                            '📜 Histórico completo — ' + maq_sel + '</div>',
                            unsafe_allow_html=True
                        )
                        df_hist = pd.DataFrame(historico[::-1])
                        df_hist.columns = ["Tipo", "Horímetro (h)", "Data", "Responsável", "Observações"]
                        st.dataframe(df_hist, use_container_width=True, hide_index=True)

    # ── aba análise ───────────────────────────────────────────────────────────
    with tab_analise:
        st.markdown("<div style='margin-top:12px;'></div>", unsafe_allow_html=True)
        aba_analise(dados_manu, dados_hor, df_plan)


# ── tela de exportação de dados ───────────────────────────────────────────────

def tela_exportar_dados(df_plan):
    st.markdown(
        '<div style="display:flex; align-items:center; gap:16px; margin-bottom:4px;">'
        '<div style="font-size:32px;">📊</div>'
        '<div>'
        '<h1 style="margin:0; font-size:28px; font-weight:900; color:#e0e0f0;">Exportar Dados</h1>'
        '<p style="margin:0; color:#8888aa; font-size:13px;">Baixe os históricos de horímetros e manutenções</p>'
        '</div></div>',
        unsafe_allow_html=True
    )
    st.markdown("<hr class='separador'>", unsafe_allow_html=True)

    dados_hor  = carregar_horimetros()
    dados_manu = carregar_manutencoes()

    # Obter todas as máquinas disponíveis para filtro
    todas_maquinas = []
    todas_series_motor = []
    todas_series_alternador = []

    if df_plan is not None and not df_plan.empty:
        todas_maquinas = sorted(df_plan["label"].unique().tolist())
        # Correção: Converter para string antes de ordenar para evitar TypeError
        todas_series_motor = sorted([str(s) for s in df_plan["serie_motor"].dropna().unique().tolist()])
        todas_series_alternador = sorted([str(s) for s in df_plan["serie_alternador"].dropna().unique().tolist()])

    st.markdown("### ⚙️ Filtros de Exportação")
    col_maq, col_data_inicio, col_data_fim = st.columns([2, 1, 1])

    with col_maq:
        maquinas_selecionadas = st.multiselect(
            "Máquinas",
            options=todas_maquinas,
            default=todas_maquinas,
            key="export_maquinas_sel"
        )
    with col_data_inicio:
        data_inicio = st.date_input(
            "Data Início",
            value=date(2023, 1, 1), # Valor padrão razoável
            key="export_data_inicio"
        )
    with col_data_fim:
        data_fim = st.date_input(
            "Data Fim",
            value=date.today(),
            key="export_data_fim"
        )

    col_serie_motor, col_serie_alternador = st.columns(2)
    with col_serie_motor:
        series_motor_selecionadas = st.multiselect(
            "Série do Motor",
            options=todas_series_motor,
            default=todas_series_motor,
            key="export_serie_motor_sel"
        )
    with col_serie_alternador:
        series_alternador_selecionadas = st.multiselect(
            "Série do Alternador",
            options=todas_series_alternador,
            default=todas_series_alternador,
            key="export_serie_alternador_sel"
        )

    st.markdown("<hr class='separador'>", unsafe_allow_html=True)

    # --- Exportação de Horímetros ---
    st.markdown("### 🕐 Histórico de Horímetros")
    if dados_hor:
        registros_flat = []
        for maquina, info in dados_hor.items():
            if not maquinas_selecionadas or maquina in maquinas_selecionadas:
                # Obter informações da máquina do df_plan
                maq_info_row = df_plan[df_plan["label"] == maquina]
                serie_motor_maq = safe_val(maq_info_row.iloc[0], "serie_motor") if not maq_info_row.empty else "—"
                serie_alternador_maq = safe_val(maq_info_row.iloc[0], "serie_alternador") if not maq_info_row.empty else "—"

                # Aplicar filtros de série
                if (not series_motor_selecionadas or serie_motor_maq in series_motor_selecionadas) and \
                   (not series_alternador_selecionadas or serie_alternador_maq in series_alternador_selecionadas):

                    for registro in info.get("historico", []):
                        try:
                            data_reg = datetime.strptime(registro.get("data"), "%Y-%m-%d").date()
                        except (ValueError, TypeError):
                            data_reg = None

                        if data_reg and data_inicio <= data_reg <= data_fim:
                            registros_flat.append({
                                "Maquina": maquina,
                                "Serie_Motor": serie_motor_maq, # Adicionado
                                "Serie_Alternador": serie_alternador_maq, # Adicionado
                                "Horimetro": registro.get("horimetro"),
                                "Data": registro.get("data")
                            })
        if registros_flat:
            df_hor = pd.DataFrame(registros_flat)
            csv_hor = df_hor.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="Baixar Histórico de Horímetros (CSV)",
                data=csv_hor,
                file_name="historico_horimetros_filtrado.csv",
                mime="text/csv",
                key="download_horimetros"
            )
        else:
            st.info("Nenhum registro de horímetro encontrado com os filtros aplicados.")
    else:
        st.info("Nenhum registro de horímetro encontrado para exportação.")

    st.markdown("<hr class='separador'>", unsafe_allow_html=True)

    # --- Exportação de Manutenções ---
    st.markdown("### 🔧 Histórico de Manutenções")
    if dados_manu:
        registros_flat = []
        for maquina, info in dados_manu.items():
            if not maquinas_selecionadas or maquina in maquinas_selecionadas:
                # Obter informações da máquina do df_plan
                maq_info_row = df_plan[df_plan["label"] == maquina]
                serie_motor_maq = safe_val(maq_info_row.iloc[0], "serie_motor") if not maq_info_row.empty else "—"
                serie_alternador_maq = safe_val(maq_info_row.iloc[0], "serie_alternador") if not maq_info_row.empty else "—"

                # Aplicar filtros de série
                if (not series_motor_selecionadas or serie_motor_maq in series_motor_selecionadas) and \
                   (not series_alternador_selecionadas or serie_alternador_maq in series_alternador_selecionadas):

                    for registro in info.get("historico", []):
                        try:
                            data_reg = datetime.strptime(registro.get("data"), "%Y-%m-%d").date()
                        except (ValueError, TypeError):
                            data_reg = None

                        if data_reg and data_inicio <= data_reg <= data_fim:
                            registros_flat.append({
                                "Maquina": maquina,
                                "Serie_Motor": serie_motor_maq, # Adicionado
                                "Serie_Alternador": serie_alternador_maq, # Adicionado
                                "Tipo_Manutencao": registro.get("faixa"),
                                "Horimetro_Execucao": registro.get("horimetro"),
                                "Data_Execucao": registro.get("data"),
                                "Responsavel": registro.get("responsavel"),
                                "Observacoes": registro.get("observacao")
                            })
        if registros_flat:
            df_manu = pd.DataFrame(registros_flat)
            csv_manu = df_manu.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="Baixar Histórico de Manutenções (CSV)",
                data=csv_manu,
                file_name="historico_manutencoes_filtrado.csv",
                mime="text/csv",
                key="download_manutencoes"
            )
        else:
            st.info("Nenhum registro de manutenção encontrado com os filtros aplicados.")
    else:
        st.info("Nenhum registro de manutenção encontrado para exportação.")


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    if "tela"             not in st.session_state: st.session_state["tela"]             = "home"
    if "base_sel"         not in st.session_state: st.session_state["base_sel"]         = None
    if "editar_horimetro" not in st.session_state: st.session_state["editar_horimetro"] = None
    if "logged_in"        not in st.session_state: st.session_state["logged_in"]        = False
    if "user_profile"     not in st.session_state: st.session_state["user_profile"]     = None

    if not st.session_state["logged_in"]:
        st.sidebar.empty() # Limpa a sidebar para a tela de login
        show_login_page()
        return # Interrompe a execução do resto da main() até o login

    # Se logado, continua com o resto da aplicação
    df_atual, df_plan, erros, sheet_names = carregar_dados()
    tela = st.session_state.get("tela", "home")
    user_profile = st.session_state["user_profile"]

    filtro_motor  = []
    filtro_alt    = []
    filtro_origem = []
    filtro_serie_motor = [] # Inicializa o filtro de série do motor
    filtro_serie_alternador = [] # Inicializa o filtro de série do alternador


    with st.sidebar:
        st.markdown("## ⚙️ Usina Xavantes")
        st.markdown("---")

        if st.button("🏠 Página Inicial"):
            st.session_state["tela"]             = "home"
            st.session_state["base_sel"]         = None
            st.session_state["editar_horimetro"] = None
            st.rerun()

        # Botão "Pátio de Máquinas" apenas para Engenharia
        if user_profile == "engenharia":
            if st.button("⚙️ Pátio de Máquinas"):
                st.session_state["tela"]             = "selecao_patio"
                st.session_state["base_sel"]         = None
                st.session_state["editar_horimetro"] = None
                st.rerun()

        # Botões de Horímetro e Manutenção para Engenharia e Operador
        if user_profile in ["engenharia", "operacao"]:
            if st.button("🕐 Atualização de Horímetro"):
                st.session_state["tela"]             = "horimetro"
                st.session_state["base_sel"]         = None
                st.session_state["editar_horimetro"] = None
                st.rerun()

            if st.button("🔧 Histórico de Manutenção"):
                st.session_state["tela"]             = "manutencao"
                st.session_state["base_sel"]         = None
                st.session_state["editar_horimetro"] = None
                st.rerun()

        # Exportar Dados é apenas para Engenharia
        if user_profile == "engenharia":
            if st.button("📊 Exportar Dados"):
                st.session_state["tela"]             = "exportar_dados"
                st.session_state["base_sel"]         = None
                st.session_state["editar_horimetro"] = None
                st.rerun()
                
                        # Botão "Controle de Horas Extras" apenas para Engenharia
        if user_profile == "engenharia":
            if st.button("⏰ Controle de Horas Extras"):
                st.session_state["tela"]             = "horas_extras"
                st.session_state["base_sel"]         = None
                st.session_state["editar_horimetro"] = None
                st.rerun()

        if st.button("🔄 Recarregar dados"):
            st.cache_data.clear()
            st.rerun()

        st.markdown("---")
        if st.button("🚪 Sair"):
            st.session_state["logged_in"] = False
            st.session_state["user_profile"] = None
            st.session_state["tela"] = "home" # Redireciona para home/login
            st.rerun()

        # Garante que user_profile não seja None antes de tentar capitalizar
        display_profile = user_profile.capitalize() if user_profile else "Não Logado"
        st.markdown(
            f"<small style='color:#4a4a6a;'>Logado como: {display_profile}</small>",
            unsafe_allow_html=True
        )
        st.markdown(
            "<small style='color:#4a4a6a;'>Usina Xavantes · Goiânia/GO</small>",
            unsafe_allow_html=True
        )

    if tela == "home":
        tela_home(df_plan)

    elif tela == "selecao_patio":
        # Verifica se o usuário tem permissão para acessar esta tela
        if user_profile == "engenharia":
            tela_selecao_patio(df_atual, df_plan)
        else:
            st.error("Acesso negado. Você não tem permissão para visualizar esta página.")
            st.session_state["tela"] = "home" # Redireciona para a home
            st.rerun()

    elif tela == "atual":
        # Verifica se o usuário tem permissão para acessar esta tela
        if user_profile == "engenharia":
            if erros.get("atual"):
                st.error("Erro ao carregar Pátio Atual: " + erros["atual"])
                if sheet_names:
                    st.info("Abas disponíveis: " + str(sheet_names))
            else:
                tela_patio(
                    df=df_atual, titulo="Pátio de Máquinas — Atual",
                    cor_a="#7c6af7", cor_b="#f97316",
                    tela_origem="selecao_patio", tem_origem=False,
                    filtro_motor=filtro_motor, filtro_alt=filtro_alt, filtro_origem=filtro_origem,
                    filtro_serie_motor=filtro_serie_motor, filtro_serie_alternador=filtro_serie_alternador # Passa os novos filtros
                )
        else:
            st.error("Acesso negado. Você não tem permissão para visualizar esta página.")
            st.session_state["tela"] = "home" # Redireciona para a home
            st.rerun()

    elif tela == "planejado":
        # Verifica se o usuário tem permissão para acessar esta tela
        if user_profile == "engenharia":
            if erros.get("planejado"):
                st.error("Erro ao carregar Pátio Planejado: " + erros["planejado"])
                if sheet_names:
                    st.info("Abas disponíveis: " + str(sheet_names))
            else:
                tela_patio(
                    df=df_plan, titulo="Pátio de Máquinas — Planejado",
                    cor_a="#f59e0b", cor_b="#06b6d4",
                    tela_origem="selecao_patio", tem_origem=True,
                    filtro_motor=filtro_motor, filtro_alt=filtro_alt, filtro_origem=filtro_origem,
                    filtro_serie_motor=filtro_serie_motor, filtro_serie_alternador=filtro_serie_alternador # Passa os novos filtros
                )
        else:
            st.error("Acesso negado. Você não tem permissão para visualizar esta página.")
            st.session_state["tela"] = "home" # Redireciona para a home
            st.rerun()

    elif tela == "horimetro":
        # Verifica se o usuário tem permissão para acessar esta tela
        if user_profile in ["engenharia", "operacao"]:
            tela_horimetro(df_plan, erros)
        else:
            st.error("Acesso negado. Você não tem permissão para visualizar esta página.")
            st.session_state["tela"] = "home" # Redireciona para a home
            st.rerun()

    elif tela == "manutencao":
        # Verifica se o usuário tem permissão para acessar esta tela
        if user_profile in ["engenharia", "operacao"]:
            tela_manutencao(df_plan, erros)
        else:
            st.error("Acesso negado. Você não tem permissão para visualizar esta página.")
            st.session_state["tela"] = "home" # Redireciona para a home
            st.rerun()

    elif tela == "exportar_dados":
        # Verifica se o usuário tem permissão para acessar esta tela
        if user_profile == "engenharia":
            tela_exportar_dados(df_plan)
        else:
            st.error("Acesso negado. Você não tem permissão para visualizar esta página.")
            st.session_state["tela"] = "home" # Redireciona para a home
            st.rerun()
            
    elif tela == "horas_extras":
        # Verifica se o usuário tem permissão para acessar esta tela
        if user_profile == "engenharia":
            tela_horas_extras()
        else:
            st.error("Acesso negado. Você não tem permissão para visualizar esta página.")
            st.session_state["tela"] = "home" # Redireciona para a home
            st.rerun() 
# Adicione esta função em qualquer lugar fora da função main(),
# preferencialmente junto com as outras funções de tela (tela_home, tela_patio, etc.)
def tela_horas_extras():
    st.markdown(
        '<div style="display:flex; align-items:center; gap:16px; margin-bottom:4px;">'
        '<div style="font-size:32px;">⏰</div>'
        '<div>'
        '<h1 style="margin:0; font-size:28px; font-weight:900; color:#e0e0f0;">Controle de Horas Extras</h1>'
        '<p style="margin:0; color:#8888aa; font-size:13px;">Gestão de banco de horas por colaborador</p>'
        '</div></div>',
        unsafe_allow_html=True
    )
    st.markdown("<hr class='separador'>", unsafe_allow_html=True)

    colaboradores_data = load_colaboradores()
    colaboradores_nomes = sorted(list(colaboradores_data.keys()))

    if not colaboradores_nomes:
        st.warning("Nenhum colaborador cadastrado. Por favor, adicione colaboradores no arquivo 'colaboradores.json'.")
        return

    # --- Filtros ---
    st.markdown("### 🔎 Filtros")
    col_colab, col_data_inicio_ponto, col_data_fim_ponto = st.columns([2, 1, 1])

    with col_colab:
        # Mantemos o seletor de colaborador, mas ele agora afeta apenas o formulário de lançamento
        # e a tabela de histórico detalhado, não o gráfico de acúmulo principal.
        colaborador_selecionado = st.selectbox(
            "Selecione o Colaborador para Lançamento/Detalhes",
            options=["Todos"] + colaboradores_nomes,
            key="he_colaborador_sel"
        )

    # Lógica para o período de fechamento de ponto (16 ao 15)
    today = date.today()
    if today.day >= 16:
        data_inicio_default = date(today.year, today.month, 16)
        # Calcula o dia 15 do próximo mês
        proximo_mes = today.replace(day=1) + timedelta(days=32)
        data_fim_default    = proximo_mes.replace(day=15)
    else:
        data_fim_default    = date(today.year, today.month, 15)
        # Calcula o dia 16 do mês anterior
        mes_anterior = today.replace(day=1) - timedelta(days=1)
        data_inicio_default = mes_anterior.replace(day=16)

    with col_data_inicio_ponto:
        data_inicio_ponto = st.date_input(
            "Início do Período",
            value=data_inicio_default,
            key="he_data_inicio_ponto"
        )
    with col_data_fim_ponto:
        data_fim_ponto = st.date_input(
            "Fim do Período",
            value=data_fim_default,
            key="he_data_fim_ponto"
        )

    st.markdown("<hr class='separador'>", unsafe_allow_html=True)

    # --- Lançamento de Horas ---
    st.markdown("### ➕ Lançar Horas de Ponto")
    if colaborador_selecionado == "Todos":
        st.info("Selecione um colaborador específico para lançar horas.")
    else:
        # Inicializa o estado da sessão para o tipo de lançamento, se ainda não existir
        if "tipo_lancamento_state" not in st.session_state:
            st.session_state.tipo_lancamento_state = "Cálculo Automático (Entrada/Saída)"

        # Mover o st.radio para FORA do st.form
        col_data, col_tipo_lancamento = st.columns([1, 1])
        with col_data:
            data_lancamento = st.date_input("Data do Ponto", value=date.today(), key="he_data_lancamento_fora_form")
        with col_tipo_lancamento:
            # O st.radio agora está fora do formulário, então on_change é permitido
            tipo_lancamento_selecionado = st.radio(
                "Tipo de Lançamento",
                ("Cálculo Automático (Entrada/Saída)", "Feriado (Horas Trabalhadas)", "Utilizar Banco de Horas (Dia Completo)"),
                key="he_tipo_lancamento_fora_form",
                on_change=lambda: st.session_state.update(tipo_lancamento_state=st.session_state.he_tipo_lancamento_fora_form)
            )
        # Atualiza o tipo_lancamento para a lógica abaixo
        tipo_lancamento = st.session_state.tipo_lancamento_state

        with st.form("form_lancar_horas_extras"):
            # A data do ponto é passada para o formulário
            # st.write(f"Data do Ponto: {data_lancamento.strftime('%Y-%m-%d')}") # Opcional: exibir a data selecionada

            horas_para_registrar = 0.0
            tipo_registro = "extra" # Default, pode ser alterado

            # --- Componentes de entrada de horas (visibilidade controlada pelo tipo_lancamento) ---
            default_hora_entrada = datetime.strptime("08:00", "%H:%M").time()
            default_hora_saida = datetime.strptime("17:00", "%H:%M").time()

            if tipo_lancamento in ["Cálculo Automático (Entrada/Saída)", "Feriado (Horas Trabalhadas)"]:
                col_entrada, col_saida = st.columns([1, 1])
                with col_entrada:
                    hora_entrada_val = st.time_input("Hora de Entrada", value=default_hora_entrada, key="he_hora_entrada")
                with col_saida:
                    hora_saida_val = st.time_input("Hora de Saída", value=default_hora_saida, key="he_hora_saida")

                # Converter horas para objetos datetime para cálculo
                dt_entrada = datetime.combine(data_lancamento, hora_entrada_val)
                dt_saida   = datetime.combine(data_lancamento, hora_saida_val)

                # Se a hora de saída for menor que a de entrada, assume que virou o dia
                if dt_saida < dt_entrada:
                    dt_saida += timedelta(days=1)

                duracao_total_trabalhada = dt_saida - dt_entrada
                duracao_total_horas      = duracao_total_trabalhada.total_seconds() / 3600

                # --- Descontar o intervalo de almoço (1h12m = 1.2 horas) ---
                intervalo_almoco_horas = 1.2 # 1 hora e 12 minutos
                duracao_liquida_trabalhada = duracao_total_horas - intervalo_almoco_horas

                # Jornada padrão de 8h48m = 8.8 horas
                jornada_padrao_horas = 8.8

                if tipo_lancamento == "Cálculo Automático (Entrada/Saída)":
                    horas_para_registrar = duracao_liquida_trabalhada - jornada_padrao_horas
                    tipo_registro = "extra" if horas_para_registrar >= 0 else "negativa"

                elif tipo_lancamento == "Feriado (Horas Trabalhadas)":
                    # Em feriado, todas as horas líquidas trabalhadas são extras
                    horas_para_registrar = duracao_liquida_trabalhada
                    tipo_registro = "extra"
                    if horas_para_registrar < 0: # Garante que não registre horas negativas em feriado
                        horas_para_registrar = 0.0
                    st.info(f"Serão registradas {horas_para_registrar:.2f} horas extras de feriado.")

            elif tipo_lancamento == "Utilizar Banco de Horas (Dia Completo)":
                # Jornada padrão de 8h48m = 8.8 horas
                jornada_padrao_horas = 8.8
                horas_para_registrar = -jornada_padrao_horas # Abate um dia completo
                tipo_registro = "negativa"
                st.info(f"Serão abatidas {jornada_padrao_horas:.2f} horas do banco de horas do colaborador.")


            observacao_lancamento = st.text_area("Observação (opcional)", key="he_observacao_lancamento")

            # O st.form_submit_button DEVE estar dentro do st.form
            submitted = st.form_submit_button("Registrar Ponto")
            if submitted:
                add_horas_extras_registro(
                    colaborador_selecionado,
                    data_lancamento, # Usa a data selecionada fora do form
                    horas_para_registrar,
                    tipo_registro,
                    observacao_lancamento
                )
                st.success(f"Ponto registrado para {colaborador_selecionado}: {horas_para_registrar:.2f}h ({tipo_registro.capitalize()})!")
                st.rerun() # Recarrega para atualizar os dados exibidos

    st.markdown("<hr class='separador'>", unsafe_allow_html=True)

    # --- Exibição de Dados e Gráficos ---
    st.markdown("### 📊 Resumo e Histórico")

    horas_extras_registros = load_horas_extras()
    df_he = pd.DataFrame()

    # Sempre carregamos todos os registros para os gráficos e saldos gerais
    all_records = []
    for colab, records in horas_extras_registros.items():
        for rec in records:
            rec_copy = rec.copy()
            rec_copy["colaborador"] = colab
            rec_copy["area"] = colaboradores_data.get(colab, {}).get("area", "Desconhecida")
            all_records.append(rec_copy)
    if all_records:
        df_he = pd.DataFrame(all_records)
        df_he["data"] = pd.to_datetime(df_he["data"])
        df_he = df_he.sort_values("data")

    if not df_he.empty:
        # Filtrar por período de ponto (afeta todos os gráficos e saldos)
        df_he_periodo = df_he[(df_he["data"].dt.date >= data_inicio_ponto) & (df_he["data"].dt.date <= data_fim_ponto)]

        # Calcular saldo
        saldo_periodo = df_he_periodo["horas"].sum()

        st.markdown("#### Resumo do Período Selecionado")
        col1, col2, col3 = st.columns(3)

        total_extras = df_he_periodo[df_he_periodo["horas"] > 0]["horas"].sum()
        total_negativas = df_he_periodo[df_he_periodo["horas"] < 0]["horas"].sum()

        with col1:
            st.markdown(
                f'<div style="background:#1e1e32; border:1px solid #3a3a5a; border-radius:12px; padding:10px; text-align:center;">'
                f'<div style="color:#8888aa; font-size:12px;">Horas Extras</div>'
                f'<div style="color:#28a745; font-size:20px; font-weight:700;">{total_extras:.2f} h</div>'
                f'</div>'.replace('.', ','), unsafe_allow_html=True
            )
        with col2:
            st.markdown(
                f'<div style="background:#1e1e32; border:1px solid #3a3a5a; border-radius:12px; padding:10px; text-align:center;">'
                f'<div style="color:#8888aa; font-size:12px;">Horas Negativas</div>'
                f'<div style="color:#dc3545; font-size:20px; font-weight:700;">{total_negativas:.2f} h</div>'
                f'</div>'.replace('.', ','), unsafe_allow_html=True
            )
        with col3:
            st.markdown(
                f'<div style="background:#1e1e32; border:1px solid #3a3a5a; border-radius:12px; padding:10px; text-align:center;">'
                f'<div style="color:#8888aa; font-size:12px;">Saldo Final</div>'
                f'<div style="color:#e0e0f0; font-size:20px; font-weight:700;">{saldo_periodo:.2f} h</div>'
                f'</div>'.replace('.', ','), unsafe_allow_html=True
            )
        st.markdown("<br>", unsafe_allow_html=True) # Espaçamento

        # --- GRÁFICO: Saldo de Horas por Colaborador (Eixo X: Colaborador, Eixo Y: Saldo) - Gráfico de LINHAS com rótulos ---
        st.markdown("#### Saldo de Horas por Colaborador (Período Atual)")
        if not df_he_periodo.empty:
            saldo_por_colaborador = df_he_periodo.groupby("colaborador")["horas"].sum().reset_index()

            # Ordenar por colaborador para consistência
            saldo_por_colaborador = saldo_por_colaborador.sort_values("colaborador")

            fig_saldo_colab = px.line( # Alterado para px.line
                saldo_por_colaborador,
                x="colaborador", # Eixo X agora é o nome do colaborador
                y="horas",
                title="Saldo Total de Horas por Colaborador",
                labels={"colaborador": "Colaborador", "horas": "Saldo de Horas (h)"},
                color_discrete_sequence=["#FFFFFF"], # Cor branca para a linha
                hover_data={"horas": ":.2f"} # Formata o hover para 2 casas decimais
            )
            fig_saldo_colab.update_layout(
                paper_bgcolor="#0f0f1a",
                plot_bgcolor="#0f0f1a",
                font={"color": "#e0e0f0"},
                xaxis={"gridcolor": "#2a2a4a", "linecolor": "#2a2a4a"},
                yaxis={"gridcolor": "#2a2a4a", "linecolor": "#2a2a4a"},
                title_font_color="#e0e0f0"
            )
            # Adicionar marcadores para cada ponto (colaborador)
            fig_saldo_colab.update_traces(mode='lines+markers')

            # --- Adicionar rótulos de texto com o valor das horas ---
            for index, row in saldo_por_colaborador.iterrows():
                fig_saldo_colab.add_annotation(
                    x=row["colaborador"],
                    y=row["horas"],
                    text=f"{row['horas']:.2f}h".replace('.', ','), # Formata o texto com vírgula
                    showarrow=False,
                    yshift=10, # Desloca o texto um pouco para cima do ponto
                    font=dict(color="#FFFFFF", size=10) # Cor e tamanho do texto
                )

            st.plotly_chart(fig_saldo_colab, use_container_width=True, key="fig_saldo_colaborador")
        else:
            st.info("Nenhum registro no período para exibir o saldo por colaborador.")


        # --- Gráfico de Horas por Área (mantido) ---
        st.markdown("#### Horas por Área (Período Atual)")
        if not df_he_periodo.empty:
            horas_por_area = df_he_periodo.groupby("area")["horas"].sum().reset_index()
            fig_area = px.bar(
                horas_por_area,
                x="area",
                y="horas",
                title="Total de Horas Extras/Negativas por Área no Período",
                labels={"area": "Área", "horas": "Total de Horas (h)"},
                color="area",
                color_discrete_sequence=px.colors.qualitative.Plotly
            )
            fig_area.update_layout(
                paper_bgcolor="#0f0f1a",
                plot_bgcolor="#0f0f1a",
                font={"color": "#e0e0f0"},
                xaxis={"gridcolor": "#2a2a4a", "linecolor": "#2a2a4a"},
                yaxis={"gridcolor": "#2a2a4a", "linecolor": "#2a2a4a"},
                title_font_color="#e0e0f0"
            )
            st.plotly_chart(fig_area, use_container_width=True, key="fig_horas_por_area")
        else:
            st.info("Nenhum registro no período para exibir o gráfico por área.")


        st.markdown("#### Histórico Detalhado")
        # Exibir histórico detalhado, filtrado pelo período de ponto
        # Se "Todos" estiver selecionado, mostra todos os colaboradores no período
        # Se um colaborador específico estiver selecionado, mostra apenas ele no período
        if colaborador_selecionado != "Todos":
            df_he_detalhado = df_he_periodo[df_he_periodo["colaborador"] == colaborador_selecionado].copy()
        else:
            df_he_detalhado = df_he_periodo.copy()

        if not df_he_detalhado.empty:
            df_he_detalhado["data"] = df_he_detalhado["data"].dt.strftime("%Y-%m-%d")
            # --- Formatação para vírgula na tabela ---
            df_he_detalhado["horas"] = df_he_detalhado["horas"].apply(lambda x: f"{x:.2f}".replace('.', ',') + " h")
            df_he_detalhado = df_he_detalhado.rename(columns={
                "colaborador": "Colaborador",
                "area": "Área",
                "data": "Data",
                "horas": "Horas",
                "tipo": "Tipo",
                "observacao": "Observação"
            })
            st.dataframe(df_he_detalhado[["Colaborador", "Área", "Data", "Horas", "Tipo", "Observação"]], use_container_width=True, hide_index=True)
        else:
            st.info("Nenhum registro de horas extras/negativas encontrado para os filtros aplicados.")

    else:
        st.info("Nenhum registro de horas extras/negativas encontrado para os filtros aplicados.")
                                                         
main()
