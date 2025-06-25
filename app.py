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
from docx.shared import Pt, Inches
from dateutil.relativedelta import relativedelta # Para cálculos de data

# --- INTERFACE PRINCIPAL ---
st.set_page_config(layout="wide")

# --- USUÁRIOS PARA LOGIN (Exemplo) ---
# Adicione novos usuários aqui. O formato é "nome_de_usuario": "senha"
USERS = {
    "admin": "admin123",
    "taylan": "taylan123",
    "danilo": "danilo123",
    "eduardo": "eduardo123",
    "joseane": "joseane123",
    "glaucia": "galucia123" # Novo usuário adicionado
}

# --- CONFIGURAÇÃO DO FIREBASE ---
try:
    if not firebase_admin._apps:
        # Tenta usar as credenciais do Streamlit Secrets (para ambiente online)
        if 'firebase_credentials' in st.secrets:
            cred_dict = dict(st.secrets["firebase_credentials"])
            cred = credentials.Certificate(cred_dict)
        else:
            # Se não encontrar, usa o arquivo local (para desenvolvimento)
            cred = credentials.Certificate("denuncias-48660-firebase-adminsdk-fbsvc-9f27fef1c8.json")

        firebase_admin.initialize_app(cred, {
            'databaseURL': 'https://denuncias-48660-default-rtdb.firebaseio.com/'
        })
except Exception as e:
    st.error(f"Erro ao inicializar o Firebase: {e}. Verifique as suas credenciais.")

# --- FUNÇÕES GLOBAIS DE DADOS ---
@st.cache_data
def carregar_dados_firebase(node):
    """Carrega dados de um nó específico do Firebase."""
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

# ==============================================================================
# ======================== MÓDULO DE RECURSOS HUMANOS ==========================
# ==============================================================================

def calcular_status_ferias_saldo(employee_row, all_folgas_df):
    """
    Calcula o período aquisitivo de referência, o saldo de férias e o status.
    """
    try:
        today = date.today()
        if 'data_admissao' not in employee_row or pd.isna(employee_row['data_admissao']):
            return "Admissão Inválida", "Erro"
            
        data_admissao = pd.to_datetime(employee_row['data_admissao']).date()
        
        ferias_do_funcionario = pd.DataFrame()
        if not all_folgas_df.empty and 'id_funcionario' in all_folgas_df.columns:
            ferias_do_funcionario = all_folgas_df[
                (all_folgas_df['id_funcionario'] == str(employee_row['id'])) &
                (all_folgas_df['tipo'] == 'Férias')
            ].copy()
            if not ferias_do_funcionario.empty:
                ferias_do_funcionario['data_inicio'] = pd.to_datetime(ferias_do_funcionario['data_inicio']).dt.date
                ferias_do_funcionario['data_fim'] = pd.to_datetime(ferias_do_funcionario['data_fim']).dt.date

        periodo_aquisitivo_inicio = data_admissao

        while True:
            periodo_aquisitivo_fim = periodo_aquisitivo_inicio + relativedelta(years=1) - relativedelta(days=1)
            periodo_concessivo_fim = periodo_aquisitivo_fim + relativedelta(years=1)

            if today <= periodo_aquisitivo_fim:
                return f"{periodo_aquisitivo_inicio.strftime('%d/%m/%Y')} a {periodo_aquisitivo_fim.strftime('%d/%m/%Y')}", "Em Aquisição"
            
            ferias_neste_periodo = pd.DataFrame()
            dias_gozados = 0
            if not ferias_do_funcionario.empty:
                ferias_neste_periodo = ferias_do_funcionario[
                    (ferias_do_funcionario['data_inicio'] > periodo_aquisitivo_fim) &
                    (ferias_do_funcionario['data_inicio'] <= periodo_concessivo_fim)
                ]
            
            if not ferias_neste_periodo.empty:
                dias_gozados = sum((fim - inicio).days + 1 for inicio, fim in zip(ferias_neste_periodo['data_inicio'], ferias_neste_periodo['data_fim']))

            if dias_gozados < 30:
                status = f"Parcialmente Agendada ({dias_gozados}/30 dias)" if dias_gozados > 0 else "PENDENTE DE AGENDAMENTO"
                return f"{periodo_aquisitivo_inicio.strftime('%d/%m/%Y')} a {periodo_aquisitivo_fim.strftime('%d/%m/%Y')}", status
            
            periodo_aquisitivo_inicio += relativedelta(years=1)

            if periodo_aquisitivo_inicio.year > today.year + 5:
                return "N/A", "Limite de cálculo atingido"

    except Exception as e:
        return "Erro de Cálculo", f"Erro: {e}"


def modulo_rh():
    st.title("Recursos Humanos")

    df_funcionarios = carregar_dados_firebase('funcionarios')
    df_folgas = carregar_dados_firebase('folgas_ferias')

    tab_rh1, tab_rh2, tab_rh3 = st.tabs(["👨‍💼 Cadastrar Funcionário", "✈️ Gerenciar Ausências", "👥 Visualizar Equipe"])

    with tab_rh1:
        st.subheader("Cadastro de Novo Funcionário")
        with st.form("novo_funcionario_form", clear_on_submit=True):
            nome = st.text_input("Nome Completo")
            cargo = st.text_input("Cargo")
            data_admissao = st.date_input("Data de Admissão", datetime.now())
            submit_funcionario = st.form_submit_button("Cadastrar Funcionário")

            if submit_funcionario and nome and cargo:
                try:
                    novo_id = str(int(time.time() * 1000))
                    ref = db.reference(f'funcionarios/{novo_id}')
                    ref.set({'nome': nome, 'cargo': cargo, 'data_admissao': data_admissao.strftime("%Y-%m-%d"), 'id': novo_id})
                    st.success(f"Funcionário {nome} cadastrado com sucesso!")
                    st.cache_data.clear()
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao cadastrar funcionário: {e}")

    with tab_rh2:
        st.subheader("Registro de Férias e Abonadas")
        if not df_funcionarios.empty and 'nome' in df_funcionarios.columns:
            lista_funcionarios = sorted(df_funcionarios['nome'].tolist())
            funcionario_selecionado = st.selectbox("Selecione o Funcionário", lista_funcionarios)
            
            with st.form("folgas_ferias_form", clear_on_submit=True):
                tipo_evento = st.selectbox("Tipo de Evento", ["Férias", "Abonada"])
                
                if tipo_evento == "Férias":
                    col1, col2 = st.columns(2)
                    with col1:
                        data_inicio = st.date_input("Data de Início")
                    with col2:
                        data_fim = st.date_input("Data de Fim")
                else: 
                    data_inicio = st.date_input("Data da Abonada")
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
                            st.cache_data.clear()
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erro ao registrar evento: {e}")
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
            st.dataframe(
                df_folgas_filtrado[cols_to_display].rename(columns={'nome_funcionario': 'Funcionário', 'tipo': 'Tipo', 'data_inicio': 'Início', 'data_fim': 'Fim'}), 
                use_container_width=True,
                hide_index=True
            )
        else:
            st.write("Nenhum registro de ausência encontrado.")

    with tab_rh3:
        st.subheader("Equipe e Status de Férias")
        if not df_funcionarios.empty and 'id' in df_funcionarios.columns:
            ferias_info = [calcular_status_ferias_saldo(func, df_folgas) for _, func in df_funcionarios.iterrows()]
            
            df_display = df_funcionarios.copy()
            df_display['Período Aquisitivo de Referência'] = [info[0] for info in ferias_info]
            df_display['Status Agendamento'] = [info[1] for info in ferias_info]
            
            def style_status(val):
                if "PENDENTE" in val:
                    return 'background-color: #ffc44b;' # Amarelo
                if "Parcialmente" in val:
                    return 'background-color: #a9d1f7;' # Azul claro
                return ''

            st.dataframe(
                df_display[['nome', 'cargo', 'data_admissao', 'Período Aquisitivo de Referência', 'Status Agendamento']]
                .rename(columns={'nome': 'Nome', 'cargo': 'Cargo', 'data_admissao': 'Data de Admissão'})
                .style.apply(lambda row: [style_status(row['Status Agendamento'])]*len(row), axis=1),
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("Nenhum funcionário cadastrado.")

# ==============================================================================
# ========================== MÓDULO DE DENÚNCIAS ===============================
# ==============================================================================
def modulo_denuncias():
    # O código deste módulo permanece o mesmo
    st.title("Denúncias")

    # --- Funções específicas do módulo de denúncias ---
    @st.cache_data
    def geocode_addresses(df):
        geolocator = Nominatim(user_agent=f"streamlit_app_{time.time()}")
        latitudes, longitudes = [], []
        df_copy = df.copy()
        for col in ['rua', 'numero', 'bairro', 'cep']:
            if col not in df_copy.columns: df_copy[col] = ''
        for index, row in df_copy.iterrows():
            address = f"{row.get('rua', '')}, {row.get('numero', '')}, {row.get('bairro', '')}, Guaratinguetá, SP, Brasil"
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
        endereco_completo = f"{data.get('rua', '')}, {data.get('numero', '')} - {data.get('bairro', '')}"
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
                    dados['protocolo'] = protocolo; dados.setdefault('conclusao_atendimento', ''); dados.setdefault('cep', ''); dados.setdefault('status', 'Não atendida'); dados.setdefault('auto_infracao', 'Não');
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
        with st.form("nova_denuncia_form", clear_on_submit=True):
            st.subheader("Formulário de Nova Denúncia")
            data_denuncia = st.date_input("Data da Denúncia", datetime.now()); motivo_denuncia = st.text_input("Motivo da Denúncia")
            bairro = st.text_input("Bairro"); rua = st.text_input("Rua"); numero = st.text_input("Nº"); cep = st.text_input("CEP (Opcional)")
            detalhes_denuncia = st.text_area("Detalhes da Denúncia"); submit_button = st.form_submit_button("Registrar Denúncia")
        if submit_button:
            if motivo_denuncia and bairro and rua:
                ano_atual = datetime.now().year; ref_contador = db.reference(f'contadores/{ano_atual}')
                def incrementar(valor_atual):
                    if valor_atual is None: return 1
                    return valor_atual + 1
                protocolo_gerado = f"{ref_contador.transaction(incrementar):04d}{ano_atual}"
                if protocolo_gerado:
                    nova_denuncia = { "data_denuncia": data_denuncia.strftime("%Y-%m-%d"), "motivo_denuncia": motivo_denuncia, "bairro": bairro, "rua": rua, "numero": numero, "cep": cep, "detalhes_denuncia": detalhes_denuncia, "status": "Não atendida", "auto_infracao": "Não", "protocolo_auto_infracao": "", "auto_imposicao_penalidade": "Não", "protocolo_auto_imposicao_penalidade": "", "responsavel_atendimento": "", "relatorio_atendimento": "", "conclusao_atendimento": ""}
                    ref = db.reference(f'denuncias/{protocolo_gerado}'); ref.set(nova_denuncia)
                    st.success(f"Denúncia registrada com sucesso! Protocolo: {protocolo_gerado}")
                    carregar_e_cachear_denuncias(); st.cache_data.clear(); st.rerun()
            else: st.warning("Por favor, preencha os campos obrigatórios (Motivo, Bairro, Rua).")
        st.subheader("Denúncias Recentes")
        if 'denuncias_df' in st.session_state and not st.session_state.denuncias_df.empty:
            st.dataframe(st.session_state.denuncias_df[['protocolo', 'data_denuncia', 'motivo_denuncia', 'bairro', 'rua', 'numero', 'cep', 'detalhes_denuncia']])

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

# --- SISTEMA DE LOGIN E NAVEGAÇÃO ---
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
    with st.sidebar:
        st.title("Navegação")
        st.write(f"Bem-vindo(a), **{st.session_state['username']}**!")
        
        # CSS para estilizar o st.radio como botões
        st.markdown("""
            <style>
                /* Oculta o título do st.radio */
                div[data-testid="stRadio"] > label[data-testid="stWidgetLabel"] {
                    display: none;
                }
                /* Estiliza o container dos botões */
                div[data-testid="stRadio"] {
                    display: flex;
                    flex-direction: column;
                }
                /* Estiliza cada opção (label) como um botão */
                div[data-testid="stRadio"] > div {
                    margin-bottom: 8px;
                }
                div[data-testid="stRadio"] label {
                    display: flex; /* Para centralizar o conteúdo interno */
                    align-items: center;
                    justify-content: center;
                    padding: 8px 12px;
                    background-color: #262730;
                    color: #FAFAFA;
                    border-radius: 4px; /* Cantos mais quadrados */
                    border: 1px solid #4A4A4A;
                    transition: background-color 0.2s, border-color 0.2s;
                    cursor: pointer;
                    text-align: center;
                }
                /* Esconde o ponto do rádio e o círculo residual */
                div[data-testid="stRadio"] input, .st-emotion-cache-1y4p8pa {
                    display: none;
                }
                /* Estilo do botão selecionado */
                div[data-testid="stRadio"] > div:has(input:checked) > label {
                    background-color: #262730;
                    color: #00A65A; /* Cor verde para o texto */
                    border: 1px solid #00A65A; /* Borda verde */
                    font-weight: 600;
                }
                /* Efeito hover para botões não selecionados */
                div[data-testid="stRadio"] > div:not(:has(input:checked)) > label:hover {
                    background-color: #3e3e42;
                    border-color: #FAFAFA;
                }
            </style>
        """, unsafe_allow_html=True)
    
        escolha_modulo = st.radio(
            "Módulos:",
            ("Denúncias", "Recursos Humanos"),
            label_visibility="collapsed"
        )

        st.divider()
        if st.button("Logout"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
    
    if escolha_modulo == "Denúncias":
        modulo_denuncias()
    elif escolha_modulo == "Recursos Humanos":
        modulo_rh()

if __name__ == "__main__":
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False

    if st.session_state['logged_in']:
        main_app()
    else:
        login_screen()

