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
    add_black_run(document.add_paragraph(), "Refere-se à:      1ª (   )      2ª (   )    3ª (  ) do Primeiro Semestre de: ____________")
    add_black_run(document.add_paragraph(), "                 \t\t 1ª (   )      2ª (   )    3ª (  ) do Segundo Semestre de: ____________")
    p_visto = document.add_paragraph("     ___________________________________________");
    p_visto_label = document.add_paragraph("                                      (visto do funcionário da seção de pessoal)")
    p_abone = document.add_paragraph("                         Abone-se: _____/_____/______")
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
            return "Admissão Inválida", "Erro"
        data_admissao = pd.to_datetime(employee_row['data_admissao']).date()
        ferias_do_funcionario = pd.DataFrame()
        if not all_folgas_df.empty and 'id_funcionario' in all_folgas_df.columns:
            ferias_do_funcionario = all_folgas_df[(all_folgas_df['id_funcionario'] == str(employee_row['id'])) & (all_folgas_df['tipo'] == 'Férias')].copy()
            if not ferias_do_funcionario.empty:
                ferias_do_funcionario['data_inicio'] = pd.to_datetime(ferias_do_funcionario['data_inicio']).dt.date
                ferias_do_funcionario['data_fim'] = pd.to_datetime(ferias_do_funcionario['data_fim']).dt.date
        periodo_aquisitivo_inicio = data_admissao
        while True:
            periodo_aquisitivo_fim = periodo_aquisitivo_inicio + relativedelta(years=1) - relativedelta(days=1)
            periodo_concessivo_fim = periodo_aquisitivo_fim + relativedelta(years=1)
            if today <= periodo_aquisitivo_fim:
                return f"{periodo_aquisitivo_inicio.strftime('%d/%m/%Y')} a {periodo_aquisitivo_fim.strftime('%d/%m/%Y')}", "Em Aquisição"
            dias_gozados = 0
            if not ferias_do_funcionario.empty:
                ferias_neste_periodo = ferias_do_funcionario[(ferias_do_funcionario['data_inicio'] > periodo_aquisitivo_fim) & (ferias_do_funcionario['data_inicio'] <= periodo_concessivo_fim)]
                if not ferias_neste_periodo.empty:
                    dias_gozados = sum((fim - inicio).days + 1 for inicio, fim in zip(ferias_neste_periodo['data_inicio'], ferias_neste_periodo['data_fim']))
            if dias_gozados < 30:
                status = f"Parcialmente Agendada ({dias_gozados}/30 dias)" if dias_gozados > 0 else "PENDENTE DE AGENDAMENTO"
                return f"{periodo_aquisitivo_inicio.strftime('%d/%m/%Y')} a {periodo_aquisitivo_fim.strftime('%d/%m/%Y')}", status
            periodo_aquisitivo_inicio += relativedelta(years=1)
            if periodo_aquisitivo_inicio.year > today.year + 5: return "N/A", "Limite de cálculo atingido"
    except Exception as e:
        return "Erro de Cálculo", f"Erro: {e}"

def get_abonadas_ano(employee_id, all_folgas_df):
    try:
        current_year = date.today().year
        if all_folgas_df.empty or 'id_funcionario' not in all_folgas_df.columns:
            return 0
        abonadas_funcionario = all_folgas_df[(all_folgas_df['id_funcionario'] == str(employee_id)) & (all_folgas_df['tipo'] == 'Abonada') & (pd.to_datetime(all_folgas_df['data_inicio']).dt.year == current_year)]
        return len(abonadas_funcionario)
    except Exception:
        return 0

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
                            ref.set({'id_funcionario': id_funcionario, 'nome_funcionario': funcionario_selecionado, 'tipo': tipo_evento, 'data_inicio': data_inicio.strftime("%Y-%m-%d"), 'data_fim': data_fim.strftime("%Y-%m-%d")})
                            st.success(f"{tipo_evento} para {funcionario_selecionado} registrado com sucesso!")
                            if tipo_evento == "Abonada":
                                dados_func = df_funcionarios[df_funcionarios['id'] == id_funcionario].iloc[0]
                                doc_data = {'nome': dados_func.get('nome', ''),'funcao': dados_func.get('funcao', ''),'unidade': dados_func.get('unidade_trabalho', ''),'data_abonada': data_inicio.strftime('%d-%m-%Y'),}
                                st.session_state.doc_data = doc_data
                            else:
                                st.session_state.doc_data = None
                            st.cache_data.clear()
                        except Exception as e:
                            st.error(f"Erro ao registrar evento: {e}")
            if st.session_state.doc_data:
                word_bytes = create_abonada_word_report(st.session_state.doc_data)
                st.download_button(label="📥 Baixar Requerimento de Abonada (.docx)",data=word_bytes,file_name=f"Abonada_{st.session_state.doc_data['nome']}_{st.session_state.doc_data['data_abonada']}.docx",mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        else:
            st.info("Nenhum funcionário cadastrado.")
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
                ferias_info = [calcular_status_ferias_saldo(func, df_folgas) for _, func in df_funcionarios.iterrows()]
                abonadas_info = [get_abonadas_ano(func_id, df_folgas) for func_id in df_funcionarios['id']]
                df_display = df_funcionarios.copy()
                df_display['Período Aquisitivo de Referência'] = [info[0] for info in ferias_info]
                df_display['Status Agendamento'] = [info[1] for info in ferias_info]
                df_display['Abonadas no Ano'] = abonadas_info
                def style_status(val):
                    if "PENDENTE" in val: return 'background-color: #ffc44b;'
                    if "Parcialmente" in val: return 'background-color: #a9d1f7;'
                    return ''
                st.dataframe(df_display[['nome', 'funcao', 'data_admissao', 'Período Aquisitivo de Referência', 'Status Agendamento', 'Abonadas no Ano']].rename(columns={'nome': 'Nome', 'funcao': 'Função', 'data_admissao': 'Data de Admissão'}).style.apply(lambda row: [style_status(row['Status Agendamento'])]*len(row), axis=1),use_container_width=True,hide_index=True)
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
                    st.divider()
                    st.markdown("**Informações Adicionais:**")
                    abonadas_ano = get_abonadas_ano(dados_func.get('id'), df_folgas)
                    ultimas_ferias = get_ultimas_ferias(dados_func.get('id'), df_folgas)
                    st.markdown(f"- **Abonadas no ano:** {abonadas_ano}")
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
    # ... (código do módulo de Denúncias)
def create_boletim_word_report(data):
    # ... (código da função de gerar Word)

def modulo_boletim():
    st.title("Boletim de Programação Diária")

    df_funcionarios = carregar_dados_firebase('funcionarios')
    df_folgas = carregar_dados_firebase('folgas_ferias')
    lista_quarteiroes = carregar_quarteiroes_csv() 
    df_geo_quarteiroes = carregar_geo_kml() 

    # --- LÓGICA DOS BOTÕES DINÂMICOS ---
    # Inicializa os contadores de equipe no estado da sessão se não existirem
    if 'num_equipes_manha' not in st.session_state:
        st.session_state.num_equipes_manha = 1
    if 'num_equipes_tarde' not in st.session_state:
        st.session_state.num_equipes_tarde = 1

    tab1, tab2, tab3 = st.tabs(["🗓️ Criar Boletim", "🔍 Visualizar/Editar Boletim", "🗺️ Mapa de Atividades"])

    with tab1:
        st.subheader("Novo Boletim de Programação")
        data_boletim = st.date_input("Data do Trabalho", date.today())
        
        if isinstance(df_funcionarios, pd.DataFrame) and not df_funcionarios.empty:
            funcionarios_disponiveis_full = df_funcionarios.copy()
            if not df_folgas.empty:
                ausentes_ids = df_folgas[(pd.to_datetime(df_folgas['data_inicio']).dt.date <= data_boletim) & (pd.to_datetime(df_folgas['data_fim']).dt.date >= data_boletim)]['id_funcionario'].tolist()
                if ausentes_ids:
                     funcionarios_disponiveis_full = df_funcionarios[~df_funcionarios['id'].isin(ausentes_ids)]
            lista_nomes_disponiveis_full = sorted(funcionarios_disponiveis_full['nome'].tolist())
        else:
            lista_nomes_disponiveis_full = []
            st.warning("Não há funcionários cadastrados para criar um boletim.")

        atividades_gerais_options = ["Controle de criadouros", "Visita a Imóveis", "ADL", "Nebulização"]
        
        with st.form("boletim_form"):
            bairros = st.text_area("Bairros a serem trabalhados")
            atividades_gerais = st.multiselect("Atividades Gerais do Dia", atividades_gerais_options)
            motoristas = st.multiselect("Motorista(s)", options=lista_nomes_disponiveis_full)
            st.divider()
            
            # --- TURNO DA MANHÃ DINÂMICO ---
            st.markdown("**Turno da Manhã**")
            equipes_manha = []
            funcionarios_manha_disponiveis = lista_nomes_disponiveis_full.copy()
            for i in range(st.session_state.num_equipes_manha):
                st.markdown(f"--- *Equipe {i+1} (Manhã)* ---")
                cols = st.columns([2, 2, 3]) 
                with cols[0]:
                    membros = st.multiselect("Membros", options=funcionarios_manha_disponiveis, max_selections=2, key=f"manha_membros_{i}")
                with cols[1]:
                    atividades = st.multiselect("Atividades", options=atividades_gerais_options, key=f"manha_atividades_{i}")
                with cols[2]:
                    quarteiroes = st.multiselect("Quarteirões", options=lista_quarteiroes, key=f"manha_quarteiroes_{i}")
                
                if membros:
                    equipes_manha.append({"membros": membros, "atividades": atividades, "quarteiroes": quarteiroes})
                    for membro in membros:
                        if membro in funcionarios_manha_disponiveis:
                           funcionarios_manha_disponiveis.remove(membro)

            st.markdown("**Faltas - Manhã**")
            faltas_manha_nomes = st.multiselect("Funcionários Ausentes (Manhã)", options=sorted(df_funcionarios['nome'].tolist()) if isinstance(df_funcionarios, pd.DataFrame) else [], key="falta_manha_nomes")
            motivo_falta_manha = st.text_input("Motivo(s) (Manhã)", key="falta_manha_motivo")
            st.divider()

            # --- TURNO DA TARDE DINÂMICO ---
            st.markdown("**Turno da Tarde**")
            equipes_tarde = []
            funcionarios_tarde_disponiveis = lista_nomes_disponiveis_full.copy()
            for i in range(st.session_state.num_equipes_tarde):
                st.markdown(f"--- *Equipe {i+1} (Tarde)* ---")
                cols = st.columns([2, 2, 3]) 
                with cols[0]:
                    membros = st.multiselect("Membros", options=funcionarios_tarde_disponiveis, max_selections=2, key=f"tarde_membros_{i}")
                with cols[1]:
                    atividades = st.multiselect("Atividades", options=atividades_gerais_options, key=f"tarde_atividades_{i}")
                with cols[2]:
                    quarteiroes = st.multiselect("Quarteirões", options=lista_quarteiroes, key=f"tarde_quarteiroes_{i}")
                if membros:
                    equipes_tarde.append({"membros": membros, "atividades": atividades, "quarteiroes": quarteiroes})
                    for membro in membros:
                        if membro in funcionarios_tarde_disponiveis:
                            funcionarios_tarde_disponiveis.remove(membro)

            st.markdown("**Faltas - Tarde**")
            faltas_tarde_nomes = st.multiselect("Funcionários Ausentes (Tarde)", options=sorted(df_funcionarios['nome'].tolist()) if isinstance(df_funcionarios, pd.DataFrame) else [], key="falta_tarde_nomes")
            motivo_falta_tarde = st.text_input("Motivo(s) (Tarde)", key="falta_tarde_motivo")
            
            # Botão de salvar dentro do formulário
            submitted = st.form_submit_button("Salvar Boletim")
            if submitted:
                boletim_id = data_boletim.strftime("%Y-%m-%d")
                boletim_data = {"data": boletim_id, "bairros": bairros, "atividades_gerais": atividades_gerais, "motoristas": motoristas, "equipes_manha": equipes_manha, "equipes_tarde": equipes_tarde, "faltas_manha": {"nomes": faltas_manha_nomes, "motivo": motivo_falta_manha}, "faltas_tarde": {"nomes": faltas_tarde_nomes, "motivo": motivo_falta_tarde}}
                try:
                    ref = db.reference(f'boletins/{boletim_id}'); ref.set(boletim_data)
                    st.success(f"Boletim para o dia {data_boletim.strftime('%d/%m/%Y')} salvo com sucesso!")
                    # Reseta os contadores após salvar
                    st.session_state.num_equipes_manha = 1
                    st.session_state.num_equipes_tarde = 1
                except Exception as e:
                    st.error(f"Erro ao salvar o boletim: {e}")
        
        # Botões para adicionar/remover equipes FORA do formulário
        st.divider()
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("##### Turno da Manhã")
            if st.button("➕ Adicionar Equipe (Manhã)"):
                st.session_state.num_equipes_manha += 1
                st.rerun()
            if st.button("➖ Remover Última Equipe (Manhã)"):
                if st.session_state.num_equipes_manha > 1:
                    st.session_state.num_equipes_manha -= 1
                    st.rerun()
        with col2:
            st.markdown("##### Turno da Tarde")
            if st.button("➕ Adicionar Equipe (Tarde)"):
                st.session_state.num_equipes_tarde += 1
                st.rerun()
            if st.button("➖ Remover Última Equipe (Tarde)"):
                if st.session_state.num_equipes_tarde > 1:
                    st.session_state.num_equipes_tarde -= 1
                    st.rerun()

    with tab2:
        # Conteúdo da Aba 2 (Visualizar/Editar) totalmente restaurado
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
            st.download_button(label="📥 Exportar Boletim em .docx",data=boletim_doc_bytes,file_name=f"Boletim_Diario_{boletim_data['data']}.docx",mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
            
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
                    # Loop baseado no número de equipes salvas
                    for i in range(len(saved_teams_manha)):
                        st.markdown(f"--- *Equipe {i+1}* ---")
                        cols = st.columns([2, 2, 3])
                        with cols[0]:
                            membros = st.multiselect("Membros", options=sorted(df_funcionarios['nome'].tolist()) if isinstance(df_funcionarios, pd.DataFrame) else [], max_selections=2, default=saved_teams_manha[i].get('membros',[]), key=f"edit_manha_membros_{i}")
                        with cols[1]:
                            atividades = st.multiselect("Atividades ", options=atividades_gerais_options, default=saved_teams_manha[i].get('atividades',[]), key=f"edit_manha_atividades_{i}")
                        with cols[2]:
                            quarteiroes = st.multiselect("Quarteirões", options=lista_quarteiroes, default=saved_teams_manha[i].get('quarteiroes',[]), key=f"edit_manha_quarteiroes_{i}")
                        if membros:
                            equipes_manha_edit_data.append({"membros": membros, "atividades": atividades, "quarteiroes": quarteiroes})
                    
                    st.markdown("**Faltas - Manhã**")
                    faltas_manha_nomes_edit = st.multiselect("Ausentes", options=sorted(df_funcionarios['nome'].tolist()) if isinstance(df_funcionarios, pd.DataFrame) else [], default=boletim_data.get('faltas_manha', {}).get('nomes', []), key="edit_falta_manha_nomes")
                    motivo_falta_manha_edit = st.text_input("Motivo", value=boletim_data.get('faltas_manha', {}).get('motivo', ''), key="edit_falta_manha_motivo")
                    st.divider()
                    
                    equipes_tarde_edit_data = []
                    st.markdown("**Equipes - Tarde**")
                    saved_teams_tarde = boletim_data.get('equipes_tarde', [])
                    # Loop baseado no número de equipes salvas
                    for i in range(len(saved_teams_tarde)):
                        st.markdown(f"--- *Equipe {i+1}* ---")
                        cols = st.columns([2, 2, 3])
                        with cols[0]:
                            membros = st.multiselect("Membros ", options=sorted(df_funcionarios['nome'].tolist()) if isinstance(df_funcionarios, pd.DataFrame) else [], max_selections=2, default=saved_teams_tarde[i].get('membros',[]), key=f"edit_tarde_membros_{i}")
                        with cols[1]:
                            atividades = st.multiselect("Atividades  ", options=atividades_gerais_options, default=saved_teams_tarde[i].get('atividades',[]), key=f"edit_tarde_atividades_{i}")
                        with cols[2]:
                             quarteiroes = st.multiselect("Quarteirões ", options=lista_quarteiroes, default=saved_teams_tarde[i].get('quarteiroes',[]), key=f"edit_tarde_quarteiroes_{i}")
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
        # (O código desta aba permanece o mesmo)
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
    # ... (código do login)
def main_app():
    # ... (código da app principal)

if __name__ == "__main__":
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False
    if st.session_state['logged_in']:
        main_app()
    else:
        login_screen()
