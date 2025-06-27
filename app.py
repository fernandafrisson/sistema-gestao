import streamlit as st
import pandas as pd
import firebase_admin
from firebase_admin import credentials, db
from datetime import datetime, date
import plotly.express as px
from geopy.geocoders import Nominatim
import time
import io
from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from dateutil.relativedelta import relativedelta
import locale
from collections import Counter
import geopandas as gpd

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

# --- FUNÇÕES GLOBAIS DE DADOS ---
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
        gdf = gpd.read_file(url_kml)
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
    def format_date_pt(dt):
        months = ("Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro")
        return f"{dt.day} de {months[dt.month - 1]} de {dt.year}"
    document = Document()
    black_color = RGBColor(0, 0, 0)
    def add_black_run(p, text, bold=False, size=11):
        run = p.add_run(text)
        run.bold = bold
        font = run.font
        font.name = 'Calibri'
        font.size = Pt(size)
        font.color.rgb = black_color
        p.paragraph_format.space_after = Pt(0)
    for text in ["Fundo Municipal de Saúde", "Prefeitura Municipal da Estância Turística de Guaratinguetá", "São Paulo", "Secretaria Municipal da Saúde"]:
        p = document.add_paragraph()
        add_black_run(p, text)
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    titulo = document.add_heading('FALTA ABONADA', level=1)
    titulo.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for run in titulo.runs:
        run.font.color.rgb = black_color
    titulo.paragraph_format.space_before = Pt(18)
    titulo.paragraph_format.space_after = Pt(18)
    p_nome = document.add_paragraph(); add_black_run(p_nome, 'Nome: '); add_black_run(p_nome, data.get('nome', ''), bold=True)
    p_funcao = document.add_paragraph(); add_black_run(p_funcao, 'Função: '); add_black_run(p_funcao, data.get('funcao', ''), bold=True)
    p_unidade = document.add_paragraph(); add_black_run(p_unidade, 'Unidade de Trabalho: '); add_black_run(p_unidade, data.get('unidade', ''), bold=True)
    solicitacao_text = f"Solicito que a minha falta ao serviço seja abonada no dia: {data.get('data_abonada', '')}"
    p_solicitacao = document.add_paragraph(); add_black_run(p_solicitacao, solicitacao_text)
    p_solicitacao.paragraph_format.space_before = Pt(18)
    p_solicitacao.paragraph_format.space_after = Pt(18)
    data_atual_formatada = format_date_pt(date.today())
    p_data = document.add_paragraph(f"Guaratinguetá, {data_atual_formatada}"); p_data.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    for run in p_data.runs: run.font.color.rgb = black_color
    p_data.paragraph_format.space_after = Pt(36)
    p_ass1 = document.add_paragraph('____________________________'); p_ass1.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_lab1 = document.add_paragraph('Assinatura do Servidor'); p_lab1.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_ass2 = document.add_paragraph('_____________________________'); p_ass2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_lab2 = document.add_paragraph('Assinatura da Chefia Imediata'); p_lab2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_lab2.paragraph_format.space_after = Pt(18)
    p_info = document.add_paragraph(); add_black_run(p_info, 'Informação da Seção de Pessoal:', bold=True)
    add_black_run(document.add_paragraph(), "Refere-se à:      1ª (  )      2ª (  )    3ª (  ) do Primeiro Semestre de: ____________")
    add_black_run(document.add_paragraph(), "                 1ª (  )      2ª (  )    3ª (  ) do Segundo Semestre de: ____________")
    p_visto = document.add_paragraph("     ___________________________________________");
    p_visto_label = document.add_paragraph("                              (visto do funcionário da seção de pessoal)")
    p_abone = document.add_paragraph("                          Abone-se: _____/_____/______")
    p_abone.paragraph_format.space_after = Pt(18)
    p_secretario_sig = document.add_paragraph("_________________________________"); p_secretario_sig.alignment = 1
    p_secretario_label = document.add_paragraph("Secretário Municipal da Saúde"); p_secretario_label.alignment = 1
    for p in document.paragraphs:
        if not p.runs:
            p.paragraph_format.space_after = Pt(0)
        for run in p.runs:
            if run.font.color.rgb is None:
                run.font.color.rgb = black_color
    buffer = io.BytesIO()
    document.save(buffer)
    buffer.seek(0)
    return buffer.getvalue()

def calcular_status_ferias_saldo(employee_row, all_folgas_df):
    try:
        today = date.today()
        if 'data_admissao' not in employee_row or pd.isna(employee_row['data_admissao']):
            return "Admissão Inválida", "Erro", "ERROR"

        data_admissao = pd.to_datetime(employee_row['data_admissao']).date()
        ferias_do_funcionario = pd.DataFrame()
        if not all_folgas_df.empty and 'id_funcionario' in all_folgas_df.columns:
            ferias_do_funcionario = all_folgas_df[(all_folgas_df['id_funcionario'] == str(employee_row['id'])) & (all_folgas_df['tipo'] == 'Férias')].copy()
            if not ferias_do_funcionario.empty:
                ferias_do_funcionario['data_inicio'] = pd.to_datetime(ferias_do_funcionario['data_inicio']).dt.date
                ferias_do_funcionario['data_fim'] = pd.to_datetime(ferias_do_funcionario['data_fim']).dt.date
                
                for _, ferias in ferias_do_funcionario.iterrows():
                    if ferias['data_inicio'] <= today <= ferias['data_fim']:
                        return f"Em gozo desde {ferias['data_inicio'].strftime('%d/%m/%Y')}", "EM FÉRIAS", "ON_VACATION"

        periodo_aquisitivo_inicio = data_admissao
        periodos_vencendo = 0
        
        while periodo_aquisitivo_inicio < today:
            periodo_aquisitivo_fim = periodo_aquisitivo_inicio + relativedelta(years=1) - relativedelta(days=1)
            periodo_concessivo_fim = periodo_aquisitivo_fim + relativedelta(years=1)

            if today <= periodo_aquisitivo_fim:
                break
                
            dias_gozados = 0
            if not ferias_do_funcionario.empty:
                ferias_neste_periodo = ferias_do_funcionario[(ferias_do_funcionario['data_inicio'] > periodo_aquisitivo_fim) & (ferias_do_funcionario['data_inicio'] <= periodo_concessivo_fim)]
                if not ferias_neste_periodo.empty:
                    dias_gozados = sum((fim - inicio).days + 1 for inicio, fim in zip(ferias_neste_periodo['data_inicio'], ferias_neste_periodo['data_fim']))
            
            if dias_gozados < 30:
                if today <= periodo_concessivo_fim and (periodo_concessivo_fim - today).days <= 90:
                    periodos_vencendo += 1
            
            periodo_aquisitivo_inicio += relativedelta(years=1)
            if periodo_aquisitivo_inicio.year > today.year + 10: break

        if periodos_vencendo >= 2:
            return "Múltiplos Períodos", f"RISCO: {periodos_vencendo} FÉRIAS VENCENDO!", "RISK_EXPIRING"

        periodo_aquisitivo_inicio = data_admissao
        while True:
            periodo_aquisitivo_fim = periodo_aquisitivo_inicio + relativedelta(years=1) - relativedelta(days=1)
            periodo_concessivo_fim = periodo_aquisitivo_fim + relativedelta(years=1)

            if today <= periodo_aquisitivo_fim:
                return f"{periodo_aquisitivo_inicio.strftime('%d/%m/%Y')} a {periodo_aquisitivo_fim.strftime('%d/%m/%Y')}", "Em Aquisição", "ACQUIRING"

            dias_gozados = 0
            if not ferias_do_funcionario.empty:
                ferias_neste_periodo = ferias_do_funcionario[(ferias_do_funcionario['data_inicio'] > periodo_aquisitivo_fim) & (ferias_do_funcionario['data_inicio'] <= periodo_concessivo_fim)]
                if not ferias_neste_periodo.empty:
                    dias_gozados = sum((fim - inicio).days + 1 for inicio, fim in zip(ferias_neste_periodo['data_inicio'], ferias_neste_periodo['data_fim']))

            if dias_gozados < 30:
                if dias_gozados > 0:
                    return f"{periodo_aquisitivo_inicio.strftime('%d/%m/%Y')} a {periodo_aquisitivo_fim.strftime('%d/%m/%Y')}", f"Parcialmente Agendada ({dias_gozados}/30)", "SCHEDULED"
                else:
                    return f"{periodo_aquisitivo_inicio.strftime('%d/%m/%Y')} a {periodo_aquisitivo_fim.strftime('%d/%m/%Y')}", "PENDENTE DE AGENDAMENTO", "PENDING"

            periodo_aquisitivo_inicio += relativedelta(years=1)
            if periodo_aquisitivo_inicio.year > today.year + 10: break
            
    except Exception as e:
        return "Erro de Cálculo", f"Erro: {e}", "ERROR"
    return "N/A", "Concluído", "OK"


def get_abonadas_ano(employee_id, all_folgas_df):
    try:
        current_year = date.today().year
        if all_folgas_df.empty or 'id_funcionario' not in all_folgas_df.columns:
            return 0
        abonadas_funcionario = all_folgas_df[(all_folgas_df['id_funcionario'] == str(employee_id)) & (all_folgas_df['tipo'] == 'Abonada') & (pd.to_datetime(all_folgas_df['data_inicio']).dt.year == current_year)]
        return len(abonadas_funcionario)
    except Exception:
        return 0

def get_datas_abonadas_ano(employee_id, all_folgas_df):
    try:
        current_year = date.today().year
        if all_folgas_df.empty or 'id_funcionario' not in all_folgas_df.columns:
            return []
        
        abonadas_df = all_folgas_df[
            (all_folgas_df['id_funcionario'] == str(employee_id)) & 
            (all_folgas_df['tipo'] == 'Abonada') & 
            (pd.to_datetime(all_folgas_df['data_inicio']).dt.year == current_year)
        ]
        
        if abonadas_df.empty:
            return []
            
        return [pd.to_datetime(d).strftime('%d/%m/%Y') for d in abonadas_df['data_inicio']]
    except Exception:
        return []


def get_ultimas_ferias(employee_id, all_folgas_df):
    try:
        if all_folgas_df.empty or 'id_funcionario' not in all_folgas_df.columns:
            return "Nenhum registro"
        ferias_do_funcionario = all_folgas_df[(all_folgas_df['id_funcionario'] == str(employee_id)) & (all_folgas_df['tipo'] == 'Férias')].copy()
        if ferias_do_funcionario.empty:
            return "Nenhuma férias registrada"
        ferias_do_funcionario['data_inicio'] = pd.to_datetime(ferias_do_funcionario['data_inicio'])
        ultima_ferias = ferias_do_funcionario.sort_values(by='data_inicio', ascending=False).iloc[0]
        return ultima_ferias['data_inicio'].strftime('%d/%m/%Y')
    except Exception:
        return "Erro"

def modulo_rh():
    st.title("Recursos Humanos")
    df_funcionarios = carregar_dados_firebase('funcionarios')
    df_folgas = carregar_dados_firebase('folgas_ferias')
    
    tab_rh1, tab_rh2, tab_rh3 = st.tabs(["✈️ Férias e Abonadas", "👥 Visualizar Equipe", "👨‍💼 Gerenciar Funcionários"])
    
    with tab_rh1:
        st.subheader("Registro de Férias e Abonadas")
        if not df_funcionarios.empty and 'nome' in df_funcionarios.columns:
            lista_funcionarios = sorted(df_funcionarios['nome'].tolist())
            funcionario_selecionado = st.selectbox("Selecione o Funcionário", lista_funcionarios)
            tipo_evento = st.selectbox("Tipo de Evento", ["Férias", "Abonada"], key="tipo_evento_selector")
            
            if 'doc_data' not in st.session_state:
                st.session_state.doc_data = None

            with st.form("folgas_ferias_form", clear_on_submit=True):
                if tipo_evento == "Férias":
                    st.write("Período de Férias:")
                    col1, col2 = st.columns(2)
                    with col1:
                        data_inicio = st.date_input("Data de Início")
                    with col2:
                        data_fim = st.date_input("Data de Fim")
                else:
                    st.write("Data da Abonada:")
                    data_inicio = st.date_input("Data")
                    data_fim = data_inicio
                
                submit_evento = st.form_submit_button("Registrar Evento")
                
                if submit_evento:
                    if tipo_evento == "Férias" and data_inicio > data_fim:
                        st.error("A data de início não pode ser posterior à data de fim.")
                    else:
                        try:
                            id_funcionario = df_funcionarios[df_funcionarios['nome'] == funcionario_selecionado]['id'].iloc[0]
                            evento_id = str(int(time.time() * 1000))
                            ref = db.reference(f'folgas_ferias/{evento_id}')
                            ref.set({'id_funcionario': id_funcionario,'nome_funcionario': funcionario_selecionado,'tipo': tipo_evento,'data_inicio': data_inicio.strftime("%Y-%m-%d"),'data_fim': data_fim.strftime("%Y-%m-%d")})
                            st.success(f"{tipo_evento} para {funcionario_selecionado} registrado com sucesso!")
                            
                            if tipo_evento == "Abonada":
                                dados_func = df_funcionarios[df_funcionarios['id'] == id_funcionario].iloc[0]
                                doc_data = {'nome': dados_func.get('nome', ''),'funcao': dados_func.get('funcao', ''),'unidade': dados_func.get('unidade_trabalho', ''),'data_abonada': data_inicio.strftime('%d-%m-%Y'),}
                                st.session_state.doc_data = doc_data
                            else:
                                st.session_state.doc_data = None
                            
                            st.cache_data.clear()
                            st.rerun() 
                        except Exception as e:
                            st.error(f"Erro ao registrar evento: {e}")

            if st.session_state.doc_data:
                word_bytes = create_abonada_word_report(st.session_state.doc_data)
                st.download_button(label="📥 Baixar Requerimento de Abonada (.docx)",data=word_bytes,file_name=f"Abonada_{st.session_state.doc_data['nome']}_{st.session_state.doc_data['data_abonada']}.docx",mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        else:
            st.info("Nenhum funcionário cadastrado.")
        st.divider()

        st.subheader("Editar Registro de Férias ou Abonada")
        if not df_folgas.empty:
            df_folgas['label'] = df_folgas.apply(lambda row: f"{row['tipo']} - {row['nome_funcionario']} ({pd.to_datetime(row['data_inicio']).strftime('%d/%m/%Y')})", axis=1)
            lista_eventos = ["Selecione um registro para editar..."] + df_folgas.sort_values(by='data_inicio', ascending=False)['label'].tolist()
            evento_label_selecionado = st.selectbox("Selecione o Registro", options=lista_eventos)

            if evento_label_selecionado != "Selecione um registro para editar...":
                evento_selecionado_df = df_folgas[df_folgas['label'] == evento_label_selecionado]
                if not evento_selecionado_df.empty:
                    dados_evento = evento_selecionado_df.iloc[0]
                    evento_id = dados_evento.name

                    with st.form(f"edit_folga_{evento_id}"):
                        st.write(f"Editando: **{dados_evento['label']}**")
                        tipo_evento_edit = dados_evento['tipo']
                        
                        if tipo_evento_edit == "Férias":
                            st.write("Período de Férias:")
                            col1_edit, col2_edit = st.columns(2)
                            with col1_edit:
                                data_inicio_edit = st.date_input("Nova Data de Início", value=pd.to_datetime(dados_evento['data_inicio']))
                            with col2_edit:
                                data_fim_edit = st.date_input("Nova Data de Fim", value=pd.to_datetime(dados_evento['data_fim']))
                        else: # Abonada
                            st.write("Data da Abonada:")
                            data_inicio_edit = st.date_input("Nova Data", value=pd.to_datetime(dados_evento['data_inicio']))
                            data_fim_edit = data_inicio_edit

                        submit_edit = st.form_submit_button("Salvar Alterações")

                        if submit_edit:
                            if tipo_evento_edit == "Férias" and data_inicio_edit > data_fim_edit:
                                st.error("A data de início não pode ser posterior à data de fim.")
                            else:
                                try:
                                    ref = db.reference(f'folgas_ferias/{evento_id}')
                                    ref.update({'data_inicio': data_inicio_edit.strftime("%Y-%m-%d"),'data_fim': data_fim_edit.strftime("%Y-%m-%d")})
                                    st.success("Registro atualizado com sucesso!")
                                    st.cache_data.clear()
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Erro ao atualizar o registro: {e}")
                else:
                    st.warning("Registro não encontrado. Por favor, atualize a página.")
        else:
            st.info("Nenhum registro de férias ou abonada para editar.")
        st.divider()

        st.subheader("Histórico de Férias e Abonadas")
        df_folgas_filtrado = df_folgas.copy()
        if not df_folgas_filtrado.empty:
            st.markdown("##### Filtrar Histórico")
            col1, col2, col3 = st.columns(3)
            with col1:
                funcionarios_disponiveis = sorted(df_folgas_filtrado['nome_funcionario'].unique().tolist())
                filtro_funcionarios = st.multiselect("Filtrar por Funcionário(s)", options=funcionarios_disponiveis)
            with col2:
                filtro_tipo = st.selectbox("Filtrar por Tipo", ["Todos", "Férias", "Abonada"])
            with col3:
                if 'data_inicio' in df_folgas_filtrado.columns:
                    df_folgas_filtrado['ano'] = pd.to_datetime(df_folgas_filtrado['data_inicio']).dt.year
                    anos_disponiveis = sorted(df_folgas_filtrado['ano'].unique(), reverse=True)
                    filtro_ano = st.selectbox("Filtrar por Ano", ["Todos"] + anos_disponiveis)
                    if filtro_funcionarios:
                        df_folgas_filtrado = df_folgas_filtrado[df_folgas_filtrado['nome_funcionario'].isin(filtro_funcionarios)]
                    if filtro_tipo != "Todos":
                        df_folgas_filtrado = df_folgas_filtrado[df_folgas_filtrado['tipo'] == filtro_tipo]
                    if filtro_ano != "Todos":
                        df_folgas_filtrado = df_folgas_filtrado[df_folgas_filtrado['ano'] == filtro_ano]
            
            cols_to_display = [col for col in ['nome_funcionario', 'tipo', 'data_inicio', 'data_fim'] if col in df_folgas_filtrado.columns]
            st.dataframe(df_folgas_filtrado[cols_to_display].rename(columns={'nome_funcionario': 'Funcionário', 'tipo': 'Tipo', 'data_inicio': 'Início', 'data_fim': 'Fim'}), use_container_width=True,hide_index=True)
        else:
            st.write("Nenhum registro de ausência encontrado.")
            
    with tab_rh2:
        col_ficha, col_tabela = st.columns([0.7, 2.3])
        with col_tabela:
            st.subheader("Equipe e Status de Férias")
            if not df_funcionarios.empty and 'id' in df_funcionarios.columns:
                
                ferias_info_completa = [calcular_status_ferias_saldo(func, df_folgas) for _, func in df_funcionarios.iterrows()]
                
                df_display = df_funcionarios.copy()
                df_display['Período Aquisitivo de Referência'] = [info[0] for info in ferias_info_completa]
                df_display['Status Agendamento'] = [info[1] for info in ferias_info_completa]
                df_display['status_code'] = [info[2] for info in ferias_info_completa] 
                df_display['Abonadas no Ano'] = [get_abonadas_ano(func_id, df_folgas) for func_id in df_funcionarios['id']]

                def style_status_code(code):
                    color = ''
                    if code == "PENDING": color = '#fff2cc'
                    elif code == "SCHEDULED": color = '#d4e6f1'
                    elif code == "ON_VACATION": color = '#d5f5e3'
                    elif code == "RISK_EXPIRING": color = '#f5b7b1'
                    return f'background-color: {color}'

                df_para_exibir = df_display[['nome', 'funcao', 'Período Aquisitivo de Referência', 'Status Agendamento', 'Abonadas no Ano']]
                df_renomeado = df_para_exibir.rename(columns={'nome': 'Nome', 'funcao': 'Função'})
                
                styler = df_renomeado.style.apply(
                    lambda row: [style_status_code(df_display.loc[row.name, 'status_code'])] * len(row),
                    axis=1
                )
                
                st.dataframe(
                    styler,
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info("Nenhum funcionário cadastrado.")

        with col_ficha:
            st.subheader("Consultar Ficha")
            if not df_funcionarios.empty:
                funcionario_ficha = st.selectbox("Selecione um funcionário", sorted(df_funcionarios['nome'].tolist()), index=None, placeholder="Selecione...")
                if funcionario_ficha:
                    dados_func = df_funcionarios[df_funcionarios['nome'] == funcionario_ficha].iloc[0]
                    st.image("https://placehold.co/150x150/FFFFFF/333333?text=FOTO", use_column_width='auto')
                    st.markdown(f"**Nome:** {dados_func.get('nome', 'N/A')}")
                    st.markdown(f"**Matrícula:** {dados_func.get('matricula', 'N/A')}")
                    st.markdown(f"**Telefone:** {dados_func.get('telefone', 'N/A')}")
                    
                    data_adm_str = dados_func.get('data_admissao', 'N/A')
                    if data_adm_str != 'N/A':
                        data_adm_str = pd.to_datetime(data_adm_str).strftime('%d/%m/%Y')
                    st.markdown(f"**Data de Admissão:** {data_adm_str}")

                    st.divider()
                    st.markdown("**Histórico Recente:**")

                    datas_abonadas = get_datas_abonadas_ano(dados_func.get('id'), df_folgas)
                    st.markdown(f"- **Abonadas no ano ({len(datas_abonadas)}):** {', '.join(datas_abonadas) if datas_abonadas else 'Nenhuma'}")
                    
                    ultimas_ferias = get_ultimas_ferias(dados_func.get('id'), df_folgas)
                    st.markdown(f"- **Últimas Férias:** {ultimas_ferias}")
            else:
                st.info("Nenhum funcionário.")

    with tab_rh3:
        st.subheader("Cadastrar Novo Funcionário")
        with st.form("novo_funcionario_form_2", clear_on_submit=True):
            nome = st.text_input("Nome Completo")
            matricula = st.text_input("Número da Matrícula")
            telefone = st.text_input("Telefone")
            funcao = st.text_input("Função")
            unidade_trabalho = st.text_input("Unidade de Trabalho")
            data_admissao = st.date_input("Data de Admissão", datetime.now())
            submit_funcionario = st.form_submit_button("Cadastrar Funcionário")
            if submit_funcionario and nome and funcao and unidade_trabalho:
                try:
                    novo_id = str(int(time.time() * 1000))
                    ref = db.reference(f'funcionarios/{novo_id}')
                    ref.set({'id': novo_id, 'nome': nome, 'matricula': matricula, 'telefone': telefone, 'funcao': funcao, 'unidade_trabalho': unidade_trabalho, 'data_admissao': data_admissao.strftime("%Y-%m-%d")})
                    st.success(f"Funcionário {nome} cadastrado com sucesso!")
                    st.cache_data.clear(); st.rerun()
                except Exception as e:
                    st.error(f"Erro ao cadastrar funcionário: {e}")
        st.divider()
        st.subheader("Editar Funcionário")
        if not df_funcionarios.empty:
            func_para_editar = st.selectbox("Selecione para editar", sorted(df_funcionarios['nome'].tolist()), index=None, placeholder="Selecione um funcionário...")
            if func_para_editar:
                dados_func_originais = df_funcionarios[df_funcionarios['nome'] == func_para_editar].iloc[0]
                with st.form("edit_funcionario_form"):
                    st.write(f"Editando dados de **{func_para_editar}**")
                    nome_edit = st.text_input("Nome Completo", value=dados_func_originais.get('nome'))
                    matricula_edit = st.text_input("Número da Matrícula", value=dados_func_originais.get('matricula'))
                    telefone_edit = st.text_input("Telefone", value=dados_func_originais.get('telefone'))
                    funcao_edit = st.text_input("Função", value=dados_func_originais.get('funcao'))
                    unidade_edit = st.text_input("Unidade de Trabalho", value=dados_func_originais.get('unidade_trabalho'))
                    data_admissao_edit = st.date_input("Data de Admissão", value=pd.to_datetime(dados_func_originais.get('data_admissao')))
                    if st.form_submit_button("Salvar Alterações"):
                        dados_atualizados = {'nome': nome_edit, 'matricula': matricula_edit, 'telefone': telefone_edit, 'funcao': funcao_edit, 'unidade_trabalho': unidade_edit, 'data_admissao': data_admissao_edit.strftime('%Y-%m-%d')}
                        ref = db.reference(f"funcionarios/{dados_func_originais['id']}")
                        ref.update(dados_atualizados)
                        st.success("Dados do funcionário atualizados com sucesso!")
                        st.cache_data.clear(); st.rerun()
        st.divider()
        st.subheader("🚨 Deletar Funcionário")
        if not df_funcionarios.empty:
            func_para_deletar = st.selectbox("Selecione para deletar", sorted(df_funcionarios['nome'].tolist()), index=None, placeholder="Selecione um funcionário...")
            if func_para_deletar:
                st.warning(f"**Atenção:** Você está prestes a deletar **{func_para_deletar}** e todos os seus registos de férias e abonadas. Esta ação é irreversível.")
                if st.button("Confirmar Deleção", type="primary"):
                    try:
                        id_func_deletar = df_funcionarios[df_funcionarios['nome'] == func_para_deletar]['id'].iloc[0]
                        db.reference(f'funcionarios/{id_func_deletar}').delete()
                        folgas_ref = db.reference('folgas_ferias')
                        folgas_para_deletar = folgas_ref.order_by_child('id_funcionario').equal_to(id_func_deletar).get()
                        for key in folgas_para_deletar:
                            folgas_ref.child(key).delete()
                        st.success(f"Funcionário {func_para_deletar} deletado com sucesso.")
                        st.cache_data.clear(); st.rerun()
                    except Exception as e:
                        st.error(f"Ocorreu um erro ao deletar: {e}")

def modulo_denuncias():
    st.title("Denúncias")
    @st.cache_data
    def geocode_addresses(df):
        geolocator = Nominatim(user_agent=f"streamlit_app_{time.time()}")
        latitudes, longitudes = [], []
        df_copy = df.copy()
        for col in ['logradouro', 'numero', 'bairro', 'cep']:
            if col not in df_copy.columns: df_copy[col] = ''
        for index, row in df_copy.iterrows():
            address = f"{row.get('logradouro', '')}, {row.get('numero', '')}, {row.get('bairro', '')}, Guaratinguetá, SP, Brasil"
            try:
                location = geolocator.geocode(address, timeout=10)
                if location: latitudes.append(location.latitude); longitudes.append(location.longitude)
                else: latitudes.append(None); longitudes.append(None)
            except Exception as e:
                latitudes.append(None); longitudes.append(None)
            time.sleep(1)
        df_copy['lat'], df_copy['lon'] = latitudes, longitudes
        return df_copy.dropna(subset=['lat', 'lon'])
    def create_word_report(data):
        document = Document()
        style = document.styles['Normal']; font = style.font; font.name = 'Calibri'; font.size = Pt(11)
        titulo = document.add_heading('RELATÓRIO DE INSPEÇÃO ZOOSSANITÁRIA', level=1); titulo.alignment = 1
        try: data_obj = datetime.strptime(data.get('data_denuncia', ''), '%Y-%m-%d'); data_formatada = data_obj.strftime('%d/%m/%Y')
        except (ValueError, TypeError): data_formatada = "Data não informada"
        p_data = document.add_paragraph(data_formatada); p_data.alignment = 2
        document.add_paragraph('Vigilância Epidemiológica')
        p = document.add_paragraph(); p.add_run('Responsável: ').bold = True; p.add_run(str(data.get('responsavel_atendimento', '')))
        endereco_completo = f"{data.get('logradouro', '')}, {data.get('numero', '')} - {data.get('bairro', '')}"
        p = document.add_paragraph(); p.add_run('Endereço: ').bold = True; p.add_run(endereco_completo)
        document.add_paragraph(); p = document.add_paragraph(); p.add_run('Relato da Situação: ').bold = True
        document.add_paragraph(str(data.get('detalhes_denuncia', '')))
        document.add_paragraph(); p = document.add_paragraph(); p.add_run('Situação Encontrada: ').bold = True
        document.add_paragraph(str(data.get('relatorio_atendimento', '')))
        document.add_paragraph(); p = document.add_paragraph(); p.add_run('Conclusão: ').bold = True
        document.add_paragraph(str(data.get('conclusao_atendimento', '')))
        footer = document.sections[0].footer; footer_para = footer.paragraphs[0]
        footer_para.text = ("PREFEITURA MUNICIPAL DA ESTÂNCIA TURÍSTICA DE GUARATINGUETÁ/SP\n"
                            "Secretaria Municipal de Saúde - Fundo Municipal de Saúde\n"
                            "Rua Jacques Felix, 02 – São Gonçalo - Guaratinguetá/SP - CEP 12.502-180\n"
                            "Telefone / Fax: (12) 3123-2900 - e-mail: ccz@guaratingueta.sp.gov.br")
        footer_para.alignment = 1
        font_footer = footer_para.style.font
        font_footer.name = 'Arial'; font_footer.size = Pt(8)
        buffer = io.BytesIO(); document.save(buffer); buffer.seek(0)
        return buffer.getvalue()
    def carregar_e_cachear_denuncias():
        ref = db.reference('denuncias')
        denuncias_data = ref.get()
        if denuncias_data:
            denuncias_padronizadas = []
            for protocolo, dados in denuncias_data.items():
                if isinstance(dados, dict):
                    dados['protocolo'] = protocolo
                    dados.setdefault('logradouro', dados.get('rua', ''))
                    dados.setdefault('conclusao_atendimento', ''); dados.setdefault('cep', ''); dados.setdefault('status', 'Não atendida'); dados.setdefault('auto_infracao', 'Não');
                    dados.setdefault('protocolo_auto_infracao', ''); dados.setdefault('auto_imposicao_penalidade', 'Não');
                    dados.setdefault('protocolo_auto_imposicao_penalidade', ''); dados.setdefault('responsavel_atendimento', '');
                    dados.setdefault('relatorio_atendimento', '')
                    denuncias_padronizadas.append(dados)
            df = pd.DataFrame(denuncias_padronizadas)
            if 'protocolo' in df.columns:
                df['protocolo_int'] = df['protocolo'].apply(lambda x: int(x) if str(x).isdigit() else 0)
                df = df.sort_values(by='protocolo_int', ascending=False)
                del df['protocolo_int']
            st.session_state.denuncias_df = df
        else: st.session_state.denuncias_df = pd.DataFrame()
    if 'denuncias_df' not in st.session_state: carregar_e_cachear_denuncias()
    tab1, tab2, tab3 = st.tabs(["📋 Registrar Denúncia", "🛠️ Gerenciamento", "📊 Dashboard"])
    with tab1:
        st.subheader("Registrar Nova Denúncia")
        with st.form("nova_denuncia_form", clear_on_submit=True):
            data_denuncia = st.date_input("Data da Denúncia", datetime.now()); motivo_denuncia = st.text_input("Motivo da Denúncia")
            bairro = st.text_input("Bairro"); logradouro = st.text_input("Logradouro"); numero = st.text_input("Nº"); cep = st.text_input("CEP (Opcional)")
            detalhes_denuncia = st.text_area("Detalhes da Denúncia"); submit_button = st.form_submit_button("Registrar Denúncia")
        if submit_button:
            if motivo_denuncia and logradouro and bairro:
                ano_atual = datetime.now().year; ref_contador = db.reference(f'contadores/{ano_atual}')
                def incrementar(valor_atual):
                    if valor_atual is None: return 1
                    return valor_atual + 1
                protocolo_gerado = f"{ref_contador.transaction(incrementar):04d}{ano_atual}"
                if protocolo_gerado:
                    nova_denuncia = { "data_denuncia": data_denuncia.strftime("%Y-%m-%d"), "motivo_denuncia": motivo_denuncia, "bairro": bairro, "logradouro": logradouro, "numero": numero, "cep": cep, "detalhes_denuncia": detalhes_denuncia, "status": "Não atendida", "auto_infracao": "Não", "protocolo_auto_infracao": "", "auto_imposicao_penalidade": "Não", "protocolo_auto_imposicao_penalidade": "", "responsavel_atendimento": "", "relatorio_atendimento": "", "conclusao_atendimento": ""}
                    ref = db.reference(f'denuncias/{protocolo_gerado}'); ref.set(nova_denuncia)
                    st.success(f"Denúncia registrada com sucesso! Protocolo: {protocolo_gerado}")
                    carregar_e_cachear_denuncias(); st.cache_data.clear(); st.rerun()
            else: st.warning("Por favor, preencha os campos obrigatórios.")
        st.divider()
        st.subheader("Editar Denúncia Registrada")
        if 'denuncias_df' in st.session_state and not st.session_state.denuncias_df.empty:
            protocolo_para_editar = st.selectbox("Selecione uma denúncia para editar", st.session_state.denuncias_df['protocolo'].tolist(),index=None,placeholder="Escolha o protocolo...")
            if protocolo_para_editar:
                dados_originais = st.session_state.denuncias_df[st.session_state.denuncias_df['protocolo'] == protocolo_para_editar].iloc[0]
                with st.form("edit_denuncia_form"):
                    st.write(f"Editando protocolo: **{protocolo_para_editar}**")
                    data_denuncia_edit = st.date_input("Data da Denúncia", value=pd.to_datetime(dados_originais['data_denuncia']))
                    motivo_denuncia_edit = st.text_input("Motivo da Denúncia", value=dados_originais['motivo_denuncia'])
                    bairro_edit = st.text_input("Bairro", value=dados_originais['bairro'])
                    logradouro_edit = st.text_input("Logradouro", value=dados_originais.get('logradouro', ''))
                    numero_edit = st.text_input("Nº", value=dados_originais['numero'])
                    cep_edit = st.text_input("CEP", value=dados_originais['cep'])
                    detalhes_denuncia_edit = st.text_area("Detalhes da Denúncia", value=dados_originais['detalhes_denuncia'])
                    if st.form_submit_button("Salvar Alterações"):
                        dados_atualizados = {'data_denuncia': data_denuncia_edit.strftime("%Y-%m-%d"),'motivo_denuncia': motivo_denuncia_edit,'bairro': bairro_edit,'logradouro': logradouro_edit,'numero': numero_edit,'cep': cep_edit,'detalhes_denuncia': detalhes_denuncia_edit}
                        ref = db.reference(f'denuncias/{protocolo_para_editar}'); ref.update(dados_atualizados)
                        st.success("Denúncia atualizada com sucesso!")
                        carregar_e_cachear_denuncias(); st.cache_data.clear(); st.rerun()
        st.divider()
        st.subheader("Denúncias Recentes")
        if 'denuncias_df' in st.session_state and not st.session_state.denuncias_df.empty:
            cols = ['protocolo', 'data_denuncia', 'motivo_denuncia', 'bairro', 'logradouro', 'numero', 'cep', 'detalhes_denuncia']
            df_display = st.session_state.denuncias_df[[c for c in cols if c in st.session_state.denuncias_df.columns]]
            df_display = df_display.rename(columns={'protocolo': 'PROTOCOLO','data_denuncia': 'DATA DA DENÚNCIA','motivo_denuncia': 'MOTIVO DA DENÚNCIA','bairro': 'BAIRRO','logradouro': 'LOGRADOURO','numero': 'Nº','cep': 'CEP','detalhes_denuncia': 'DETALHES DA DENÚNCIA'})
            st.dataframe(df_display,hide_index=True,use_container_width=True)
    with tab2:
        if 'denuncias_df' in st.session_state and not st.session_state.denuncias_df.empty:
            protocolo_selecionado = st.selectbox("Selecione o Protocolo para Gerenciar", options=st.session_state.denuncias_df['protocolo'].tolist(), index=0)
            if protocolo_selecionado:
                dados_denuncia = st.session_state.denuncias_df[st.session_state.denuncias_df['protocolo'] == protocolo_selecionado].iloc[0]
                with st.form("gerenciamento_form"):
                    st.subheader(f"Atualizando Protocolo: {protocolo_selecionado}")
                    status = st.selectbox("Status", options=["Não atendida", "Atendida", "Arquivada"], index=["Não atendida", "Atendida", "Arquivada"].index(dados_denuncia.get('status', 'Não atendida')))
                    responsavel = st.text_input("Responsável", value=dados_denuncia.get('responsavel_atendimento', ''))
                    relatorio = st.text_area("Relatório (Situação Encontrada)", value=dados_denuncia.get('relatorio_atendimento', ''), height=150)
                    conclusao = st.text_area("Conclusão do Atendimento", value=dados_denuncia.get('conclusao_atendimento', ''), height=150)
                    st.divider()
                    col1, col2 = st.columns(2)
                    with col1:
                        auto_infracao = st.selectbox("Auto de Infração?", options=["Não", "Sim"], index=["Não", "Sim"].index(dados_denuncia.get('auto_infracao', 'Não')))
                        protocolo_auto_infracao = st.text_input("Nº Auto de Infração", value=dados_denuncia.get('protocolo_auto_infracao', '')) if auto_infracao == "Sim" else ""
                    with col2:
                        auto_penalidade = st.selectbox("Auto de Penalidade?", options=["Não", "Sim"], index=["Não", "Sim"].index(dados_denuncia.get('auto_imposicao_penalidade', 'Não')))
                        protocolo_auto_penalidade = st.text_input("Nº Auto de Penalidade", value=dados_denuncia.get('protocolo_auto_imposicao_penalidade', '')) if auto_penalidade == "Sim" else ""
                    if st.form_submit_button("Salvar Gerenciamento"):
                        dados_para_atualizar = {"status": status, "responsavel_atendimento": responsavel, "relatorio_atendimento": relatorio, "conclusao_atendimento": conclusao, "auto_infracao": auto_infracao, "protocolo_auto_infracao": protocolo_auto_infracao, "auto_imposicao_penalidade": auto_penalidade, "protocolo_auto_imposicao_penalidade": protocolo_auto_penalidade}
                        ref = db.reference(f'denuncias/{protocolo_selecionado}'); ref.update(dados_para_atualizar)
                        st.success(f"Denúncia {protocolo_selecionado} atualizada!"); carregar_e_cachear_denuncias(); st.cache_data.clear(); st.rerun()
                with st.expander("🚨 Deletar Denúncia"):
                    if st.button("Eu entendo o risco, deletar denúncia", type="primary"):
                        ref = db.reference(f'denuncias/{protocolo_selecionado}'); ref.delete()
                        st.success(f"Denúncia {protocolo_selecionado} deletada!"); carregar_e_cachear_denuncias(); st.cache_data.clear(); st.rerun()
        else: st.info("Nenhuma denúncia registrada para gerenciar.")
    with tab3:
        if 'denuncias_df' in st.session_state and not st.session_state.denuncias_df.empty:
            df_resumo = st.session_state.denuncias_df.copy()
            st.subheader("Métricas Gerais"); status_counts = df_resumo['status'].value_counts()
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Denúncias Totais", len(df_resumo)); col2.metric("Atendidas", status_counts.get('Atendida', 0))
            col3.metric("Não Atendidas", status_counts.get('Não atendida', 0)); col4.metric("Arquivadas", status_counts.get('Arquivada', 0))
            st.divider()
            st.subheader("Gerar Relatório de Denúncia (.docx)")
            protocolo_relatorio = st.selectbox("Selecione um Protocolo", options=df_resumo['protocolo'].tolist(), index=None, placeholder="Escolha o protocolo...")
            if protocolo_relatorio:
                dados_relatorio = df_resumo[df_resumo['protocolo'] == protocolo_relatorio].iloc[0]
                report_bytes = create_word_report(dados_relatorio)
                st.download_button(label="📥 Baixar Relatório em Word", data=report_bytes, file_name=f"Relatorio_Inspecao_{protocolo_relatorio}.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
            st.divider()
            st.subheader("Tabela de Resumo")
            st.dataframe(df_resumo[['protocolo', 'data_denuncia', 'motivo_denuncia', 'status', 'responsavel_atendimento']].rename(columns={'protocolo': 'Protocolo', 'data_denuncia': 'Data', 'motivo_denuncia': 'Motivo', 'status': 'Status', 'responsavel_atendimento': 'Responsável'}), use_container_width=True)
            st.divider()
            st.subheader("Análise Gráfica")
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("##### Denúncias Atendidas por Mês")
                df_atendidas = df_resumo[df_resumo['status'] == 'Atendida'].copy()
                if not df_atendidas.empty:
                    df_atendidas['data_denuncia'] = pd.to_datetime(df_atendidas['data_denuncia']); df_atendidas['mes_ano'] = df_atendidas['data_denuncia'].dt.to_period('M').astype(str)
                    atendidas_por_mes = df_atendidas['mes_ano'].value_counts().sort_index()
                    fig_bar = px.bar(atendidas_por_mes, x=atendidas_por_mes.index, y=atendidas_por_mes.values, title="Contagem de Denúncias Atendidas Mensalmente", labels={'x': 'Mês/Ano', 'y': 'Quantidade de Denúncias'}, text_auto=True)
                    fig_bar.update_layout(title_x=0.5, xaxis_title="", yaxis_title=""); st.plotly_chart(fig_bar, use_container_width=True)
                else: st.info("Nenhuma denúncia foi marcada como 'Atendida' ainda.")
            with col2:
                st.markdown("##### Distribuição de Denúncias por Motivo")
                denuncias_por_motivo = df_resumo['motivo_denuncia'].value_counts()
                fig_pie = px.pie(denuncias_por_motivo, values=denuncias_por_motivo.values, names=denuncias_por_motivo.index, title="Distribuição de Denúncias por Motivo", hole=.3, color_discrete_sequence=px.colors.sequential.RdBu)
                fig_pie.update_layout(title_x=0.5); st.plotly_chart(fig_pie, use_container_width=True)
            st.divider()
            st.subheader("Geolocalização das Denúncias")
            with st.spinner("Geocodificando endereços..."):
                df_mapeado = geocode_addresses(df_resumo)
            if not df_mapeado.empty: st.map(df_mapeado, latitude='lat', longitude='lon', size=10)
            else: st.warning("Não foi possível geolocalizar nenhum endereço.")
        else: st.info("Nenhuma denúncia registrada.")

def create_boletim_word_report(data):
    document = Document()
    style = document.styles['Normal']
    font = style.font
    font.name = 'Calibri'
    font.size = Pt(11)
    titulo = document.add_heading('Boletim de Programação Diária', level=1)
    titulo.alignment = WD_ALIGN_PARAGRAPH.CENTER
    try:
        data_obj = datetime.strptime(data.get('data', ''), '%Y-%m-%d')
        data_formatada = data_obj.strftime('%d/%m/%Y')
    except (ValueError, TypeError):
        data_formatada = "Data não informada"
    p_data = document.add_paragraph(f"Data: {data_formatada}")
    p_data.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_data.paragraph_format.space_after = Pt(18)
    document.add_heading('Informações Gerais', level=2)
    p = document.add_paragraph()
    p.add_run('Bairros a serem trabalhados: ').bold = True
    p.add_run(data.get('bairros', 'N/A'))
    p = document.add_paragraph()
    p.add_run('Atividades Gerais do Dia: ').bold = True
    p.add_run(', '.join(data.get('atividades_gerais', ['N/A'])))
    p = document.add_paragraph()
    p.add_run('Motorista(s): ').bold = True
    p.add_run(', '.join(data.get('motoristas', ['N/A'])))
    p.paragraph_format.space_after = Pt(18)
    def add_turno_section(doc, turno_nome, equipes_data, faltas_data):
        doc.add_heading(f'Turno da {turno_nome}', level=2)
        equipes = equipes_data or []
        if not equipes:
            doc.add_paragraph("Nenhuma equipe programada para este turno.")
        else:
            for i, equipe in enumerate(equipes):
                membros = equipe.get('membros', [])
                atividades = equipe.get('atividades', [])
                quarteiroes = equipe.get('quarteiroes', [])
                p_equipe = doc.add_paragraph()
                p_equipe.add_run(f'Equipe {i+1}: ').bold = True
                p_equipe.add_run(', '.join(membros if membros else ['N/A']))
                p_detalhes = doc.add_paragraph(f"    Atividades: {', '.join(atividades) if atividades else 'N/A'}")
                p_detalhes.paragraph_format.space_before = Pt(0)
                p_detalhes.paragraph_format.space_after = Pt(0)
                p_quarteiroes = doc.add_paragraph(f"    Quarteirões: {', '.join(map(str, quarteiroes)) if quarteiroes else 'N/A'}")
                p_quarteiroes.paragraph_format.space_before = Pt(0)
                p_quarteiroes.paragraph_format.space_after = Pt(6)
        doc.add_paragraph().add_run('Faltas:').bold = True
        nomes_faltas = faltas_data.get('nomes', [])
        motivo_falta = faltas_data.get('motivo', '')
        if not nomes_faltas:
            doc.add_paragraph("Nenhuma falta registrada.")
        else:
            doc.add_paragraph(f"  Nomes: {', '.join(nomes_faltas)}")
            doc.add_paragraph(f"  Motivo: {motivo_falta if motivo_falta else 'Não especificado'}")
        doc.add_paragraph().paragraph_format.space_after = Pt(18)
    add_turno_section(document, "Manhã", data.get('equipes_manha', []), data.get('faltas_manha', {}))
    add_turno_section(document, "Tarde", data.get('equipes_tarde', []), data.get('faltas_tarde', {}))
    buffer = io.BytesIO()
    document.save(buffer)
    buffer.seek(0)
    return buffer.getvalue()

def modulo_boletim():
    st.title("Boletim de Programação Diária")

    df_funcionarios = carregar_dados_firebase('funcionarios')
    df_folgas = carregar_dados_firebase('folgas_ferias')
    lista_quarteiroes = carregar_quarteiroes_csv()
    df_geo_quarteiroes = carregar_geo_kml()

    if 'num_equipes_manha' not in st.session_state:
        st.session_state.num_equipes_manha = 5
    if 'num_equipes_tarde' not in st.session_state:
        st.session_state.num_equipes_tarde = 5

    tab1, tab2, tab3 = st.tabs(["🗓️ Criar Boletim", "🔍 Visualizar/Editar Boletim", "🗺️ Mapa de Atividades"])

    with tab1:
        st.subheader("Novo Boletim de Programação")
        data_boletim = st.date_input("Data do Trabalho", date.today())
        
        if isinstance(df_funcionarios, pd.DataFrame) and not df_funcionarios.empty:
            funcionarios_disponiveis_full = df_funcionarios.copy()
            if not df_folgas.empty and 'data_inicio' in df_folgas.columns and 'data_fim' in df_folgas.columns:
                try:
                    datas_validas_folgas = df_folgas.dropna(subset=['data_inicio', 'data_fim'])
                    ausentes_ids = datas_validas_folgas[
                        (pd.to_datetime(datas_validas_folgas['data_inicio']).dt.date <= data_boletim) & 
                        (pd.to_datetime(datas_validas_folgas['data_fim']).dt.date >= data_boletim)
                    ]['id_funcionario'].tolist()
                    if ausentes_ids:
                        funcionarios_disponiveis_full = df_funcionarios[~df_funcionarios['id'].isin(ausentes_ids)]
                except Exception as e:
                    st.warning(f"Não foi possível filtrar funcionários ausentes: {e}")

            lista_nomes_disponiveis_full = sorted(funcionarios_disponiveis_full['nome'].tolist())
        else:
            lista_nomes_disponiveis_full = []
            st.warning("Não há funcionários cadastrados para criar um boletim.")

        atividades_gerais_options = ["Controle de criadouros", "Visita a Imóveis", "ADL", "Nebulização"]
        bairros = st.text_area("Bairros a serem trabalhados")
        atividades_gerais = st.multiselect("Atividades Gerais do Dia", atividades_gerais_options)
        motoristas = st.multiselect("Motorista(s)", options=lista_nomes_disponiveis_full)
        st.divider()
        
        st.markdown("**Turno da Manhã**")
        funcionarios_manha_disponiveis = lista_nomes_disponiveis_full[:]
        equipes_manha = []
        
        for i in range(st.session_state.num_equipes_manha):
            st.markdown(f"--- *Equipe {i+1}* ---")
            cols = st.columns([2, 2, 3])
            with cols[0]:
                membros = st.multiselect(f"Membros da Equipe {i+1}", options=funcionarios_manha_disponiveis, key=f"manha_membros_{i}")
            with cols[1]:
                atividades = st.multiselect("Atividades", options=atividades_gerais_options, key=f"manha_atividades_{i}")
            with cols[2]:
                quarteiroes = st.multiselect("Quarteirões", options=lista_quarteiroes, key=f"manha_quarteiroes_{i}")
            if membros:
                equipes_manha.append({"membros": membros, "atividades": atividades, "quarteiroes": quarteiroes})
                for membro in membros:
                    if membro in funcionarios_manha_disponiveis:
                        funcionarios_manha_disponiveis.remove(membro)

        if st.button("➕ Adicionar Equipe (Manhã)"):
            st.session_state.num_equipes_manha += 1
            st.rerun()

        st.markdown("**Faltas - Manhã**")
        faltas_manha_nomes = st.multiselect("Funcionários Ausentes", options=sorted(df_funcionarios['nome'].tolist()) if isinstance(df_funcionarios, pd.DataFrame) else [], key="falta_manha_nomes")
        motivo_falta_manha = st.text_input("Motivo(s)", key="falta_manha_motivo")
        st.divider()

        st.markdown("**Turno da Tarde**")
        funcionarios_tarde_disponiveis = lista_nomes_disponiveis_full[:]
        equipes_tarde = []

        for i in range(st.session_state.num_equipes_tarde):
            st.markdown(f"--- *Equipe {i+1}* ---")
            cols = st.columns([2, 2, 3])
            with cols[0]:
                membros = st.multiselect(f"Membros da Equipe {i+1}", options=funcionarios_tarde_disponiveis, key=f"tarde_membros_{i}")
            with cols[1]:
                atividades = st.multiselect("Atividades ", options=atividades_gerais_options, key=f"tarde_atividades_{i}")
            with cols[2]:
                quarteiroes = st.multiselect("Quarteirões ", options=lista_quarteiroes, key=f"tarde_quarteiroes_{i}")
            if membros:
                equipes_tarde.append({"membros": membros, "atividades": atividades, "quarteiroes": quarteiroes})
                for membro in membros:
                    if membro in funcionarios_tarde_disponiveis:
                        funcionarios_tarde_disponiveis.remove(membro)

        if st.button("➕ Adicionar Equipe (Tarde)"):
            st.session_state.num_equipes_tarde += 1
            st.rerun()

        st.markdown("**Faltas - Tarde**")
        faltas_tarde_nomes = st.multiselect("Funcionários Ausentes ", options=sorted(df_funcionarios['nome'].tolist()) if isinstance(df_funcionarios, pd.DataFrame) else [], key="falta_tarde_nomes")
        motivo_falta_tarde = st.text_input("Motivo(s) ", key="falta_tarde_motivo")
        
        if st.button("Salvar Boletim", use_container_width=True, type="primary"):
            boletim_id = data_boletim.strftime("%Y-%m-%d")
            boletim_data = {"data": boletim_id, "bairros": bairros, "atividades_gerais": atividades_gerais, "motoristas": motoristas, "equipes_manha": equipes_manha, "equipes_tarde": equipes_tarde, "faltas_manha": {"nomes": faltas_manha_nomes, "motivo": motivo_falta_manha}, "faltas_tarde": {"nomes": faltas_tarde_nomes, "motivo": motivo_falta_tarde}}
            try:
                ref = db.reference(f'boletins/{boletim_id}'); ref.set(boletim_data)
                st.success(f"Boletim para o dia {data_boletim.strftime('%d/%m/%Y')} salvo com sucesso!")
                st.session_state.num_equipes_manha = 5
                st.session_state.num_equipes_tarde = 5
            except Exception as e:
                st.error(f"Erro ao salvar o boletim: {e}")

    with tab2:
        st.subheader("Visualizar e Editar Boletim Diário")
        data_para_ver = st.date_input("Selecione a data do boletim que deseja ver", date.today(), key="edit_date")
        
        if st.button("Buscar Boletim", key="search_edit"):
            boletim_id = data_para_ver.strftime("%Y-%m-%d")
            ref = db.reference(f'boletins/{boletim_id}')
            boletim_data = ref.get()
            st.session_state.boletim_encontrado = boletim_data
            if not boletim_data:
                st.warning(f"Nenhum boletim encontrado para a data {data_para_ver.strftime('%d/%m/%Y')}.")

        if 'boletim_encontrado' not in st.session_state:
            st.session_state.boletim_encontrado = None

        if st.session_state.boletim_encontrado:
            boletim_data = st.session_state.boletim_encontrado
            st.success(f"Boletim de {pd.to_datetime(boletim_data['data']).strftime('%d/%m/%Y')} carregado.")
            boletim_doc_bytes = create_boletim_word_report(boletim_data)
            st.download_button(label="📥 Exportar Boletim em .docx", data=boletim_doc_bytes, file_name=f"Boletim_Diario_{boletim_data['data']}.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
            
            with st.expander("Ver/Editar Boletim", expanded=True):
                with st.form("edit_boletim_form"):
                    boletim_id = boletim_data['data']
                    bairros_edit = st.text_area("Bairros", value=boletim_data.get('bairros', ''))
                    atividades_gerais_edit = st.multiselect("Atividades Gerais", atividades_gerais_options, default=boletim_data.get('atividades_gerais', []))
                    motoristas_edit = st.multiselect("Motoristas", options=sorted(df_funcionarios['nome'].tolist()) if isinstance(df_funcionarios, pd.DataFrame) else [], default=boletim_data.get('motoristas', []))
                    st.divider()
                    
                    equipes_manha_edit_data = []
                    st.markdown("**Equipes - Manhã**")
                    saved_teams_manha = boletim_data.get('equipes_manha', [])
                    num_equipes_manha_edit = len(saved_teams_manha) if saved_teams_manha else 1
                    for i in range(num_equipes_manha_edit):
                        st.markdown(f"--- *Equipe {i+1}* ---")
                        default_membros = saved_teams_manha[i]['membros'] if i < len(saved_teams_manha) else []
                        default_atividades = saved_teams_manha[i]['atividades'] if i < len(saved_teams_manha) else []
                        default_quarteiroes = saved_teams_manha[i]['quarteiroes'] if i < len(saved_teams_manha) else []
                        cols = st.columns([2, 2, 3])
                        with cols[0]:
                            membros = st.multiselect("Membros", options=sorted(df_funcionarios['nome'].tolist()) if isinstance(df_funcionarios, pd.DataFrame) else [], default=default_membros, key=f"edit_manha_membros_{i}")
                        with cols[1]:
                            atividades = st.multiselect("Atividades ", options=atividades_gerais_options, default=default_atividades, key=f"edit_manha_atividades_{i}")
                        with cols[2]:
                            quarteiroes = st.multiselect("Quarteirões", options=lista_quarteiroes, default=default_quarteiroes, key=f"edit_manha_quarteiroes_{i}")
                        if membros:
                            equipes_manha_edit_data.append({"membros": membros, "atividades": atividades, "quarteiroes": quarteiroes})
                    
                    st.markdown("**Faltas - Manhã**")
                    faltas_manha_nomes_edit = st.multiselect("Ausentes", options=sorted(df_funcionarios['nome'].tolist()) if isinstance(df_funcionarios, pd.DataFrame) else [], default=boletim_data.get('faltas_manha', {}).get('nomes', []), key="edit_falta_manha_nomes")
                    motivo_falta_manha_edit = st.text_input("Motivo", value=boletim_data.get('faltas_manha', {}).get('motivo', ''), key="edit_falta_manha_motivo")
                    st.divider()

                    equipes_tarde_edit_data = []
                    st.markdown("**Equipes - Tarde**")
                    saved_teams_tarde = boletim_data.get('equipes_tarde', [])
                    num_equipes_tarde_edit = len(saved_teams_tarde) if saved_teams_tarde else 1
                    for i in range(num_equipes_tarde_edit):
                        st.markdown(f"--- *Equipe {i+1}* ---")
                        default_membros = saved_teams_tarde[i]['membros'] if i < len(saved_teams_tarde) else []
                        default_atividades = saved_teams_tarde[i]['atividades'] if i < len(saved_teams_tarde) else []
                        default_quarteiroes = saved_teams_tarde[i]['quarteiroes'] if i < len(saved_teams_tarde) else []
                        cols = st.columns([2, 2, 3])
                        with cols[0]:
                            membros = st.multiselect("Membros ", options=sorted(df_funcionarios['nome'].tolist()) if isinstance(df_funcionarios, pd.DataFrame) else [], default=default_membros, key=f"edit_tarde_membros_{i}")
                        with cols[1]:
                            atividades = st.multiselect("Atividades  ", options=atividades_gerais_options, default=default_atividades, key=f"edit_tarde_atividades_{i}")
                        with cols[2]:
                            quarteiroes = st.multiselect("Quarteirões ", options=lista_quarteiroes, default=default_quarteiroes, key=f"edit_tarde_quarteiroes_{i}")
                        if membros:
                            equipes_tarde_edit_data.append({"membros": membros, "atividades": atividades, "quarteiroes": quarteiroes})

                    st.markdown("**Faltas - Tarde**")
                    faltas_tarde_nomes_edit = st.multiselect("Ausentes ", options=sorted(df_funcionarios['nome'].tolist()) if isinstance(df_funcionarios, pd.DataFrame) else [], default=boletim_data.get('faltas_tarde', {}).get('nomes', []), key="edit_falta_tarde_nomes")
                    motivo_falta_tarde_edit = st.text_input("Motivo ", value=boletim_data.get('faltas_tarde', {}).get('motivo', ''), key="edit_falta_tarde_motivo")
                    
                    if st.form_submit_button("Salvar Alterações no Boletim"):
                        boletim_atualizado = {"data": boletim_id, "bairros": bairros_edit, "atividades_gerais": atividades_gerais_edit, "motoristas": motoristas_edit, "equipes_manha": equipes_manha_edit_data, "equipes_tarde": equipes_tarde_edit_data, "faltas_manha": {"nomes": faltas_manha_nomes_edit, "motivo": motivo_falta_manha_edit}, "faltas_tarde": {"nomes": faltas_tarde_nomes_edit, "motivo": motivo_falta_tarde_edit}}
                        ref = db.reference(f'boletins/{boletim_id}')
                        ref.set(boletim_atualizado)
                        st.success("Boletim atualizado com sucesso!")
                        st.session_state.boletim_encontrado = boletim_atualizado

    with tab3:
        st.subheader("Mapa de Atividades por Dia")
        data_mapa = st.date_input("Selecione a data para visualizar o mapa", date.today(), key="mapa_data")

        if st.button("Visualizar Mapa"):
            if df_geo_quarteiroes.empty:
                st.error("Os dados de geolocalização não puderam ser carregados. Verifique o arquivo e o link no código.")
            else:
                boletim_id_mapa = data_mapa.strftime("%Y-%m-%d")
                ref_mapa = db.reference(f'boletins/{boletim_id_mapa}')
                boletim_mapa_data = ref_mapa.get()

                if not boletim_mapa_data:
                    st.warning(f"Nenhum boletim encontrado para o dia {data_mapa.strftime('%d/%m/%Y')}.")
                else:
                    pontos_para_mapa = []
                    
                    equipes_manha = boletim_mapa_data.get('equipes_manha') or []
                    for i, equipe in enumerate(equipes_manha):
                        membros_str = ", ".join(equipe.get('membros', ['N/A']))
                        equipe_label = f"Equipe {i+1} (Manhã)"
                        for q in equipe.get('quarteiroes', []):
                            geo_info = df_geo_quarteiroes[df_geo_quarteiroes['quadra'] == str(q)]
                            if not geo_info.empty:
                                ponto = geo_info.iloc[0]
                                pontos_para_mapa.append({'lat': ponto['lat'],'lon': ponto['lon'],'equipe': equipe_label,'membros': membros_str,'quarteirao': str(q)})
                    
                    equipes_tarde = boletim_mapa_data.get('equipes_tarde') or []
                    for i, equipe in enumerate(equipes_tarde):
                        membros_str = ", ".join(equipe.get('membros', ['N/A']))
                        equipe_label = f"Equipe {i+1} (Tarde)"
                        for q in equipe.get('quarteiroes', []):
                            geo_info = df_geo_quarteiroes[df_geo_quarteiroes['quadra'] == str(q)]
                            if not geo_info.empty:
                                ponto = geo_info.iloc[0]
                                pontos_para_mapa.append({'lat': ponto['lat'],'lon': ponto['lon'],'equipe': equipe_label,'membros': membros_str,'quarteirao': str(q)})
                    
                    if not pontos_para_mapa:
                        st.info("Nenhum quarteirão designado para este dia foi encontrado nos dados geográficos.")
                    else:
                        df_mapa = pd.DataFrame(pontos_para_mapa)
                        st.success(f"Exibindo a localização de {len(df_mapa)} quarteirões designados.")
                        
                        fig = px.scatter_mapbox(df_mapa,lat="lat",lon="lon",hover_name="equipe",hover_data={"membros": True,"quarteirao": True,"lat": False,"lon": False},color="equipe",zoom=12,mapbox_style="open-street-map",title="Localização das Equipes")
                        fig.update_layout(mapbox_center={"lat": df_mapa['lat'].mean(), "lon": df_mapa['lon'].mean()})
                        fig.update_layout(margin={"r":0,"t":40,"l":0,"b":0})
                        
                        fig.update_traces(marker={'size': 15})
                        
                        st.plotly_chart(fig, use_container_width=True)

def login_screen():
    st.title("Sistema Integrado de Gestão")
    with st.form("login_form"):
        st.header("Login do Sistema")
        username = st.text_input("Usuário", key="login_username")
        password = st.text_input("Senha", type="password", key="login_password")
        submit_button = st.form_submit_button("Entrar")
        if submit_button:
            if username in USERS and USERS[username] == password:
                st.session_state['logged_in'] = True
                st.session_state['username'] = username
                st.rerun()
            else:
                st.error("Usuário ou senha inválidos.")

def main_app():
    if 'module_choice' not in st.session_state:
        st.session_state['module_choice'] = None
    if st.session_state['module_choice'] is None:
        st.title("Painel de Controle")
        st.header(f"Bem-vindo(a), {st.session_state['username']}!")
        st.write("Selecione o módulo que deseja acessar:")
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("🚨 Denúncias", use_container_width=True):
                st.session_state['module_choice'] = "Denúncias"
                st.rerun()
        with col2:
            if st.button("👥 Recursos Humanos", use_container_width=True):
                st.session_state['module_choice'] = "Recursos Humanos"
                st.rerun()
        with col3:
            if st.button("🗓️ Boletim Diário", use_container_width=True):
                st.session_state['module_choice'] = "Boletim"
                st.rerun()
        st.divider()
        if st.button("Logout"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
    else:
        with st.sidebar:
            st.title("Navegação")
            st.write(f"Usuário: **{st.session_state['username']}**")
            st.divider()
            if st.button("⬅️ Voltar ao Menu Principal"):
                st.session_state['module_choice'] = None
                st.rerun()
            st.divider()
            if st.button("Logout"):
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.rerun()
        if st.session_state['module_choice'] == "Denúncias":
            modulo_denuncias()
        elif st.session_state['module_choice'] == "Recursos Humanos":
            modulo_rh()
        elif st.session_state['module_choice'] == "Boletim":
            modulo_boletim()

if __name__ == "__main__":
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False
    if st.session_state['logged_in']:
        main_app()
    else:
        login_screen()
