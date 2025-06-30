import streamlit as st
import pandas as pd
import firebase_admin
from firebase_admin import credentials, db
from datetime import datetime, date, timedelta
import plotly.express as px
from geopy.geocoders import Nominatim
import time
import io
from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from dateutil.relativedelta import relativedelta
import locale
from collections import Counter, defaultdict
import geopandas as gpd
from streamlit_calendar import calendar

# --- INTERFACE PRINCIPAL ---
st.set_page_config(layout="wide")

# --- USUÁRIOS PARA LOGIN (Exemplo) ---
USERS = {
    "admin": "admin123",
    "taylan": "taylan123",
    "fernanda": "fernanda123"
}

# --- CONFIGURAÇÃO DO FIREBASE ---
try:
    if not firebase_admin._apps:
        if 'firebase_credentials' in st.secrets:
            cred_dict = dict(st.secrets["firebase_credentials"])
            cred = credentials.Certificate(cred_dict)
        else:
            cred = credentials.Certificate("denuncias-48660-firebase-adminsdk-fbsvc-9f27fef1c8.json")

        firebase_admin.initialize_app(cred, {
            'databaseURL': 'https://denuncias-48660-default-rtdb.firebaseio.com/'
        })
except Exception as e:
    st.error(f"Erro ao inicializar o Firebase: {e}. Verifique as suas credenciais.")

# --- FUNÇÕES GLOBAIS DE DADOS E UTILITÁRIAS ---

def formatar_nome(nome_completo):
    """Retorna o primeiro e o segundo nome de um nome completo."""
    if not isinstance(nome_completo, str):
        return ""
    partes = nome_completo.split()
    if len(partes) > 1:
        return f"{partes[0]} {partes[1]}"
    return partes[0] if partes else ""

@st.cache_data
def carregar_dados_firebase(node):
    try:
        ref = db.reference(f'/{node}')
        data = ref.get()
        if data:
            if isinstance(data, dict):
                df = pd.DataFrame.from_dict(data, orient='index')
                if 'id' not in df.columns:
                    df['id'] = df.index
                return df
            elif isinstance(data, list) and all(isinstance(item, dict) for item in data if item):
                return pd.DataFrame([item for item in data if item])
            return pd.DataFrame()
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Erro ao carregar dados do nó '{node}': {e}")
        return pd.DataFrame()

@st.cache_data
def carregar_quarteiroes_csv():
    url_csv = 'https://raw.githubusercontent.com/fernandafrisson/sistema-gestao/main/Quarteirao.csv'
    try:
        df_quarteiroes = pd.read_csv(url_csv, header=None, encoding='latin-1')
        quarteiroes_lista = sorted(df_quarteiroes[0].astype(str).unique().tolist())
        return quarteiroes_lista
    except Exception as e:
        st.error(f"Não foi possível carregar a lista de quarteirões. Verifique o link no código. Erro: {e}")
        return []

@st.cache_data
def carregar_geo_kml():
    url_kml = 'https://raw.githubusercontent.com/fernandafrisson/sistema-gestao/main/Quadras%20de%20Guar%C3%A1.kml'
    try:
        gdf = gpd.read_file(url_kml, driver='KML')
        pontos = []
        for index, row in gdf.iterrows():
            quadra_nome = row['Name']
            if row['geometry'] is not None and hasattr(row['geometry'], 'geom_type'):
                if row['geometry'].geom_type == 'Point':
                    lon, lat = row['geometry'].x, row['geometry'].y
                else:
                    centroid = row['geometry'].centroid
                    lon, lat = centroid.x, centroid.y
                pontos.append({'quadra': str(quadra_nome), 'lat': lat, 'lon': lon})
        df_geo = pd.DataFrame(pontos)
        df_geo.dropna(subset=['lat', 'lon'], inplace=True)
        return df_geo
    except Exception as e:
        st.error(f"Não foi possível carregar os dados de geolocalização do KML. Verifique o link ou o formato do arquivo. Erro: {e}")
        return pd.DataFrame()


def create_abonada_word_report(data):
    # ... (Conteúdo desta função omitido)
    pass

def calcular_status_ferias_saldo(employee_row, all_folgas_df):
    # ... (Conteúdo desta função omitido)
    pass

def get_abonadas_ano(employee_id, all_folgas_df):
    # ... (Conteúdo desta função omitido)
    pass

def get_datas_abonadas_ano(employee_id, all_folgas_df):
    # ... (Conteúdo desta função omitido)
    pass

def get_ultimas_ferias(employee_id, all_folgas_df):
    # ... (Conteúdo desta função omitido)
    pass

def modulo_rh():
    # ... (Conteúdo desta função omitido)
    pass

def modulo_denuncias():
    # ... (Conteúdo desta função omitido)
    pass 

def create_boletim_word_report(data):
    # ... (Conteúdo desta função omitido)
    pass

# --- MÓDULO BOLETIM (COM LAYOUT ALTERADO) ---
def modulo_boletim():
    st.title("Boletim de Programação Diária")

    df_funcionarios = carregar_dados_firebase('funcionarios')
    df_boletins = carregar_dados_firebase('boletins')
    lista_quarteiroes = carregar_quarteiroes_csv()
    df_geo_quarteiroes = carregar_geo_kml()

    if 'num_equipes_manha' not in st.session_state:
        st.session_state.num_equipes_manha = 1
    if 'num_equipes_tarde' not in st.session_state:
        st.session_state.num_equipes_tarde = 1

    tab1, tab2, tab3, tab4 = st.tabs(["🗓️ Criar Boletim", "🔍 Visualizar/Editar Boletim", "🗺️ Mapa de Atividades", "📊 Dashboard"])

    with tab1:
        st.subheader("Novo Boletim de Programação")
        data_boletim = st.date_input("Data do Trabalho", date.today())
        
        df_folgas = carregar_dados_firebase('folgas_ferias') 
        
        if isinstance(df_funcionarios, pd.DataFrame) and not df_funcionarios.empty:
            funcionarios_do_dia = df_funcionarios.copy()
            if not df_folgas.empty and 'data_inicio' in df_folgas.columns and 'data_fim' in df_folgas.columns:
                try:
                    datas_validas_folgas = df_folgas.dropna(subset=['data_inicio', 'data_fim'])
                    ausentes_ids = datas_validas_folgas[
                        (pd.to_datetime(datas_validas_folgas['data_inicio']).dt.date <= data_boletim) & 
                        (pd.to_datetime(datas_validas_folgas['data_fim']).dt.date >= data_boletim)
                    ]['id_funcionario'].tolist()
                    if ausentes_ids:
                        funcionarios_do_dia = df_funcionarios[~df_funcionarios['id'].isin(ausentes_ids)]
                except Exception as e:
                    st.warning(f"Não foi possível filtrar funcionários ausentes do RH: {e}")
            
            nome_map = {formatar_nome(nome): nome for nome in funcionarios_do_dia['nome']}
            lista_nomes_curtos_full = sorted(list(nome_map.keys()))
        else:
            nome_map = {}
            lista_nomes_curtos_full = []
            st.warning("Não há funcionários cadastrados para criar um boletim.")

        atividades_gerais_options = ["Controle de criadouros", "Visita a Imóveis", "ADL", "Nebulização"]
        bairros = st.text_area("Bairros a serem trabalhados")
        atividades_gerais = st.multiselect("Atividades Gerais do Dia", atividades_gerais_options)
        
        motoristas_curtos = st.multiselect("Motorista(s)", options=lista_nomes_curtos_full)
        st.divider()
        
        st.markdown("**Faltas do Dia**")
        col_falta_m, col_falta_t = st.columns(2)
        with col_falta_m:
            faltas_manha_curtos = st.multiselect("Ausentes (Manhã)", options=lista_nomes_curtos_full, key="falta_manha_nomes")
            motivo_falta_manha = st.text_input("Motivo (Manhã)", key="falta_manha_motivo")
        with col_falta_t:
            faltas_tarde_curtos = st.multiselect("Ausentes (Tarde)", options=lista_nomes_curtos_full, key="falta_tarde_nomes")
            motivo_falta_tarde = st.text_input("Motivo (Tarde)", key="falta_tarde_motivo")
        st.divider()
        
        nomes_disponiveis_manha = [nome for nome in lista_nomes_curtos_full if nome not in faltas_manha_curtos and nome not in motoristas_curtos]
        nomes_disponiveis_tarde = [nome for nome in lista_nomes_curtos_full if nome not in faltas_tarde_curtos and nome not in motoristas_curtos]
        
        # --- MUDANÇA DE LAYOUT: COLUNAS PARA OS TURNOS ---
        col_manha, col_tarde = st.columns(2)
        
        # --- COLUNA DA MANHÃ ---
        with col_manha:
            st.markdown("### Turno da Manhã")
            equipes_manha = []
            membros_selecionados_manha = []
            for i in range(st.session_state.num_equipes_manha):
                st.markdown(f"--- *Equipe {i+1}* ---")
                opcoes_equipe_manha = [nome for nome in nomes_disponiveis_manha if nome not in membros_selecionados_manha]
                
                membros_curtos = st.multiselect(f"Membros da Equipe {i+1}", options=opcoes_equipe_manha, key=f"manha_membros_{i}")
                atividades = st.multiselect("Atividades", options=atividades_gerais_options, key=f"manha_atividades_{i}")
                quarteiroes = st.multiselect("Quarteirões", options=lista_quarteiroes, key=f"manha_quarteiroes_{i}")
                
                if membros_curtos:
                    membros_completos = [nome_map[nome] for nome in membros_curtos]
                    equipes_manha.append({"membros": membros_completos, "atividades": atividades, "quarteiroes": quarteiroes})
                    membros_selecionados_manha.extend(membros_curtos)

            if st.button("➕ Adicionar Equipe (Manhã)"):
                st.session_state.num_equipes_manha += 1
                st.rerun()

        # --- COLUNA DA TARDE ---
        with col_tarde:
            st.markdown("### Turno da Tarde")
            equipes_tarde = []
            membros_selecionados_tarde = []
            for i in range(st.session_state.num_equipes_tarde):
                st.markdown(f"--- *Equipe {i+1}* ---")
                opcoes_equipe_tarde = [nome for nome in nomes_disponiveis_tarde if nome not in membros_selecionados_tarde]

                membros_curtos = st.multiselect(f"Membros da Equipe {i+1}", options=opcoes_equipe_tarde, key=f"tarde_membros_{i}")
                atividades = st.multiselect("Atividades ", options=atividades_gerais_options, key=f"tarde_atividades_{i}")
                quarteiroes = st.multiselect("Quarteirões ", options=lista_quarteiroes, key=f"tarde_quarteiroes_{i}")
                
                if membros_curtos:
                    membros_completos = [nome_map[nome] for nome in membros_curtos]
                    equipes_tarde.append({"membros": membros_completos, "atividades": atividades, "quarteiroes": quarteiroes})
                    membros_selecionados_tarde.extend(membros_curtos)

            if st.button("➕ Adicionar Equipe (Tarde)"):
                st.session_state.num_equipes_tarde += 1
                st.rerun()

        st.divider()
        if st.button("Salvar Boletim", use_container_width=True, type="primary"):
            motoristas_completos = [nome_map[nome] for nome in motoristas_curtos]
            faltas_manha_completos = [nome_map[nome] for nome in faltas_manha_curtos]
            faltas_tarde_completos = [nome_map[nome] for nome in faltas_tarde_curtos]
            
            boletim_id = data_boletim.strftime("%Y-%m-%d")
            boletim_data = {"data": boletim_id, "bairros": bairros, "atividades_gerais": atividades_gerais, "motoristas": motoristas_completos, "equipes_manha": equipes_manha, "equipes_tarde": equipes_tarde, "faltas_manha": {"nomes": faltas_manha_completos, "motivo": motivo_falta_manha}, "faltas_tarde": {"nomes": faltas_tarde_completos, "motivo": motivo_falta_tarde}}
            try:
                ref = db.reference(f'boletins/{boletim_id}'); ref.set(boletim_data)
                st.success(f"Boletim para o dia {data_boletim.strftime('%d/%m/%Y')} salvo com sucesso!")
                st.cache_data.clear()
            except Exception as e:
                st.error(f"Erro ao salvar o boletim: {e}")

    with tab2:
        # ... (Conteúdo desta aba omitido)
        pass

    with tab3:
        # ... (Conteúdo desta aba omitido)
        pass

    with tab4:
        # ... (Conteúdo desta aba omitido)
        pass


def login_screen():
    # ... (Conteúdo desta função omitido)
    pass

def main_app():
    # ... (Conteúdo desta função omitido)
    pass

if __name__ == "__main__":
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False
    if st.session_state['logged_in']:
        main_app()
    else:
        login_screen()
