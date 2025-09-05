# --- MÓDULO DO BOLETIM (LAYOUT CORRIGIDO) ---
def modulo_boletim():
    """Renderiza a página do módulo de Boletim de Programação Diária com um layout melhorado."""
    st.title("Boletim de Programação Diária")

    # Injeta CSS personalizado para o layout de cartões
    st.markdown("""
        <style>
            .card-layout {
                background-color: white;
                border-radius: 12px;
                padding: 24px;
                box-shadow: 0 4px 8px rgba(0, 0, 0, 0.05);
                margin-bottom: 24px;
            }
            .card-header {
                font-size: 1.5rem;
                font-weight: 600;
                margin-bottom: 16px;
                color: #333;
            }
            .stTabs [data-baseweb="tab-list"] {
                gap: 24px;
            }
            .stTabs [data-baseweb="tab"] {
                border-radius: 100px;
                padding: 10px 20px;
                background-color: #f0f2f6;
            }
            .stTabs [aria-selected="true"] {
                background-color: #007bff;
                color: white;
            }
            /* Style for the sidebar to match the layout */
            [data-testid="stSidebar"] {
                background-color: #f0f2f6;
            }
            .css-1d391kg {
                padding-top: 2rem;
                padding-right: 1rem;
                padding-bottom: 1.5rem;
                padding-left: 1rem;
            }
            hr {
                margin-top: 1rem;
                margin-bottom: 1rem;
                border-top: 1px solid rgba(0, 0, 0, 0.1);
            }
        </style>
    """, unsafe_allow_html=True)


    # Carregamento dos dados necessários
    df_funcionarios = carregar_dados_firebase('funcionarios')
    df_boletins = carregar_dados_firebase('boletins')
    lista_quarteiroes = carregar_quarteiroes_csv()
    df_geo_quarteiroes = carregar_geo_kml()

    # Controle do estado para equipes dinâmicas
    if 'num_equipes_manha' not in st.session_state:
        st.session_state.num_equipes_manha = 1
    if 'num_equipes_tarde' not in st.session_state:
        st.session_state.num_equipes_tarde = 1

    tab1, tab2, tab3, tab4 = st.tabs(["🗓️ Criar Boletim", "🔍 Visualizar/Editar Boletim", "🗺️ Mapa de Atividades", "📊 Dashboard"])

    with tab1:
        st.header("Novo Boletim de Programação")

        col1, col2 = st.columns(2)

        with col1:
            # Card: Dados do Boletim
            st.markdown("<div class='card-layout'>", unsafe_allow_html=True)
            st.markdown("<div class='card-header'>Dados do Boletim</div>", unsafe_allow_html=True)

            data_boletim = st.date_input("Data do Trabalho", date.today())
            bairros = st.text_area("Bairros a serem trabalhados")
            atividades_gerais_options = ["Controle de criadouros", "Visita a Imóveis", "ADL", "Nebulização"]
            atividades_gerais = st.multiselect("Atividades Gerais do Dia", atividades_gerais_options)

            if isinstance(df_funcionarios, pd.DataFrame) and not df_funcionarios.empty:
                nome_map = {formatar_nome(nome): nome for nome in df_funcionarios['nome']}
                lista_nomes_curtos_full = sorted(list(nome_map.keys()))
            else:
                nome_map = {}
                lista_nomes_curtos_full = []
                st.warning("Não há funcionários cadastrados para criar um boletim.")

            motoristas_curtos = st.multiselect("Motorista(s)", options=lista_nomes_curtos_full)
            st.markdown("</div>", unsafe_allow_html=True) # Fim do card

            # Card: Equipes
            st.markdown("<div class='card-layout'>", unsafe_allow_html=True)
            st.markdown("<div class='card-header'>Equipes</div>", unsafe_allow_html=True)
            
            col_equipe_manhã, col_equipe_tarde = st.columns(2)
            
            with col_equipe_manhã:
                st.markdown("#### Manhã")
                equipes_manha = []
                membros_selecionados_manha = []
                nomes_disponiveis_manha = [nome for nome in lista_nomes_curtos_full]
                
                # Removendo ausentes e motoristas da lista
                if 'faltas_manha_curtos' in st.session_state and st.session_state.faltas_manha_curtos is not None:
                    nomes_disponiveis_manha = [nome for nome in nomes_disponiveis_manha if nome not in st.session_state.faltas_manha_curtos]
                if motoristas_curtos:
                    nomes_disponiveis_manha = [nome for nome in nomes_disponiveis_manha if nome not in motoristas_curtos]

                for i in range(st.session_state.num_equipes_manha):
                    # ### CORREÇÃO AQUI ###
                    if i > 0:
                        st.markdown("<hr>", unsafe_allow_html=True)
                        
                    st.markdown(f"**Equipe {i+1}**")
                    opcoes_equipe_manha = [nome for nome in nomes_disponiveis_manha if nome not in membros_selecionados_manha]
                    
                    membros_curtos = st.multiselect("Membros", options=opcoes_equipe_manha, key=f"manha_membros_{i}")
                    atividades = st.multiselect("Atividades", options=atividades_gerais_options, key=f"manha_atividades_{i}")
                    quarteiroes = st.multiselect("Quarteirões", options=lista_quarteiroes, key=f"manha_quarteiroes_{i}")
                    
                    if membros_curtos:
                        membros_completos = [nome_map[nome] for nome in membros_curtos]
                        equipes_manha.append({"membros": membros_completos, "atividades": atividades, "quarteiroes": quarteiroes})
                        membros_selecionados_manha.extend(membros_curtos)

                if st.button("➕ Adicionar Equipe (Manhã)", key="add_equipe_manha_button"):
                    st.session_state.num_equipes_manha += 1
                    st.rerun()

            with col_equipe_tarde:
                st.markdown("#### Tarde")
                equipes_tarde = []
                membros_selecionados_tarde = []
                nomes_disponiveis_tarde = [nome for nome in lista_nomes_curtos_full]
                
                # Removendo ausentes e motoristas da lista
                if 'faltas_tarde_curtos' in st.session_state and st.session_state.faltas_tarde_curtos is not None:
                    nomes_disponiveis_tarde = [nome for nome in nomes_disponiveis_tarde if nome not in st.session_state.faltas_tarde_curtos]
                if motoristas_curtos:
                    nomes_disponiveis_tarde = [nome for nome in nomes_disponiveis_tarde if nome not in motoristas_curtos]

                for i in range(st.session_state.num_equipes_tarde):
                    # ### CORREÇÃO AQUI ###
                    if i > 0:
                        st.markdown("<hr>", unsafe_allow_html=True)

                    st.markdown(f"**Equipe {i+1}**")
                    opcoes_equipe_tarde = [nome for nome in nomes_disponiveis_tarde if nome not in membros_selecionados_tarde]

                    membros_curtos = st.multiselect("Membros ", options=opcoes_equipe_tarde, key=f"tarde_membros_{i}")
                    atividades = st.multiselect("Atividades ", options=atividades_gerais_options, key=f"tarde_atividades_{i}")
                    quarteiroes = st.multiselect("Quarteirões ", options=lista_quarteiroes, key=f"tarde_quarteiroes_{i}")
                    
                    if membros_curtos:
                        membros_completos = [nome_map[nome] for nome in membros_curtos]
                        equipes_tarde.append({"membros": membros_completos, "atividades": atividades, "quarteiroes": quarteiroes})
                        membros_selecionados_tarde.extend(membros_curtos)

                if st.button("➕ Adicionar Equipe (Tarde)", key="add_equipe_tarde_button"):
                    st.session_state.num_equipes_tarde += 1
                    st.rerun()

            st.markdown("</div>", unsafe_allow_html=True) # Fim do card

        with col2:
            # Card: Ausências do Dia
            st.markdown("<div class='card-layout'>", unsafe_allow_html=True)
            st.markdown("<div class='card-header'>Ausências do Dia</div>", unsafe_allow_html=True)
            
            ausencias_col1, ausencias_col2 = st.columns(2)
            with ausencias_col1:
                st.subheader("Manhã")
                faltas_manha_curtos = st.multiselect("Ausentes", options=lista_nomes_curtos_full, key="faltas_manha_curtos")
                motivo_falta_manha = st.text_input("Motivo", key="motivo_falta_manha")
            with ausencias_col2:
                st.subheader("Tarde")
                faltas_tarde_curtos = st.multiselect("Ausentes", options=lista_nomes_curtos_full, key="faltas_tarde_curtos")
                motivo_falta_tarde = st.text_input("Motivo", key="motivo_falta_tarde")
            
            st.markdown("</div>", unsafe_allow_html=True) # Fim do card
            
        # Botão de salvar no final
        if st.button("Salvar Boletim", use_container_width=True, type="primary", key="save_boletim_button"):
            motoristas_completos = [nome_map[nome] for nome in motoristas_curtos]
            faltas_manha_completos = [nome_map[nome] for nome in faltas_manha_curtos]
            faltas_tarde_completos = [nome_map[nome] for nome in faltas_tarde_curtos]
            
            boletim_id = data_boletim.strftime("%Y-%m-%d")
            boletim_data = {
                "data": boletim_id,
                "bairros": bairros,
                "atividades_gerais": atividades_gerais,
                "motoristas": motoristas_completos,
                "equipes_manha": equipes_manha,
                "equipes_tarde": equipes_tarde,
                "faltas_manha": {"nomes": faltas_manha_completos, "motivo": motivo_falta_manha},
                "faltas_tarde": {"nomes": faltas_tarde_completos, "motivo": motivo_falta_tarde}
            }
            try:
                ref = db.reference(f'boletins/{boletim_id}'); ref.set(boletim_data)
                
                log_atividade(st.session_state.get('username'), "Criou novo boletim", f"Data: {boletim_id}, Bairros: {bairros}")

                st.success(f"Boletim para o dia {data_boletim.strftime('%d/%m/%Y')} salvo com sucesso!")
                st.cache_data.clear()
                time.sleep(1)
                st.rerun()
            except Exception as e:
                st.error(f"Erro ao salvar o boletim: {e}")


    with tab2:
        st.subheader("Visualizar e Editar Boletim")
        if df_boletins.empty:
            st.info("Nenhum boletim encontrado para visualização.")
        else:
            lista_boletins = sorted(df_boletins['id'].tolist(), reverse=True)
            boletim_id_selecionado = st.selectbox(
                "Selecione a data do boletim", 
                options=lista_boletins,
                format_func=lambda x: pd.to_datetime(x).strftime('%d/%m/%Y')
            )

            if boletim_id_selecionado:
                dados_boletim = df_boletins.loc[boletim_id_selecionado]
                st.markdown(f"#### Detalhes do dia: {pd.to_datetime(dados_boletim['data']).strftime('%d/%m/%Y')}")

                st.markdown(f"**Bairros trabalhados:** {dados_boletim.get('bairros', 'Não informado')}")
                st.markdown(f"**Atividades gerais:** {', '.join(dados_boletim.get('atividades_gerais', []))}")
                st.markdown(f"**Motorista(s):** {', '.join(map(formatar_nome, dados_boletim.get('motoristas', [])))}")
                st.markdown(f"**Ausentes (Manhã):** {', '.join(map(formatar_nome, dados_boletim.get('faltas_manha', {}).get('nomes', [])))} - *Motivo: {dados_boletim.get('faltas_manha', {}).get('motivo', '')}*")
                st.markdown(f"**Ausentes (Tarde):** {', '.join(map(formatar_nome, dados_boletim.get('faltas_tarde', {}).get('nomes', [])))} - *Motivo: {dados_boletim.get('faltas_tarde', {}).get('motivo', '')}*")
                
                st.divider()
                
                report_bytes = create_boletim_word_report(dados_boletim)
                st.download_button(
                    label="📥 Baixar Boletim (.docx)",
                    data=report_bytes,
                    file_name=f"Boletim_Diario_{boletim_id_selecionado}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )
                
                st.divider()

                col_manha, col_tarde = st.columns(2)
                with col_manha:
                    st.markdown("**Equipes da Manhã**")
                    equipes_manha = dados_boletim.get('equipes_manha', [])
                    if equipes_manha and isinstance(equipes_manha, list):
                        for i, equipe in enumerate(equipes_manha):
                            with st.expander(f"Equipe {i+1} (Manhã)"):
                                st.write(f"**Membros:** {', '.join(map(formatar_nome, equipe.get('membros', [])))}")
                                st.write(f"**Atividades:** {', '.join(equipe.get('atividades', []))}")
                                st.write(f"**Quarteirões:** {', '.join(equipe.get('quarteiroes', []))}")
                    else:
                        st.write("Nenhuma equipe registrada para a manhã.")

                with col_tarde:
                    st.markdown("**Equipes da Tarde**")
                    equipes_tarde = dados_boletim.get('equipes_tarde', [])
                    if equipes_tarde and isinstance(equipes_tarde, list):
                        for i, equipe in enumerate(equipes_tarde):
                            with st.expander(f"Equipe {i+1} (Tarde)"):
                                st.write(f"**Membros:** {', '.join(map(formatar_nome, equipe.get('membros', [])))}")
                                st.write(f"**Atividades:** {', '.join(equipe.get('atividades', []))}")
                                st.write(f"**Quarteirões:** {', '.join(equipe.get('quarteiroes', []))}")
                    else:
                        st.write("Nenhuma equipe registrada para a tarde.")
                
                st.divider()

                with st.expander("✏️ Editar este Boletim"):
                    with st.form(key="edit_boletim_form"):
                        st.warning("A edição de equipes ainda não é suportada. Em breve!")

                        bairros_edit = st.text_area("Bairros a serem trabalhados", value=dados_boletim.get('bairros', ''))
                        atividades_gerais_edit = st.multiselect("Atividades Gerais do Dia", options=["Controle de criadouros", "Visita a Imóveis", "ADL", "Nebulização"], default=dados_boletim.get('atividades_gerais', []))
                        
                        nome_map_full = {formatar_nome(nome): nome for nome in df_funcionarios['nome']}
                        lista_nomes_curtos_full_edit = sorted(list(nome_map_full.keys()))

                        motoristas_edit_curtos = st.multiselect("Motorista(s)", options=lista_nomes_curtos_full_edit, default=[formatar_nome(nome) for nome in dados_boletim.get('motoristas', [])])
                        
                        st.markdown("**Editar Faltas**")
                        faltas_manha_edit_curtos = st.multiselect("Ausentes (Manhã)", options=lista_nomes_curtos_full_edit, default=[formatar_nome(nome) for nome in dados_boletim.get('faltas_manha', {}).get('nomes', [])])
                        motivo_manha_edit = st.text_input("Motivo (Manhã)", value=dados_boletim.get('faltas_manha', {}).get('motivo', ''))
                        faltas_tarde_edit_curtos = st.multiselect("Ausentes (Tarde)", options=lista_nomes_curtos_full_edit, default=[formatar_nome(nome) for nome in dados_boletim.get('faltas_tarde', {}).get('nomes', [])])
                        motivo_tarde_edit = st.text_input("Motivo (Tarde)", value=dados_boletim.get('faltas_tarde', {}).get('motivo', ''))

                        submit_button = st.form_submit_button(label='Salvar Alterações')

                        if submit_button:
                            motoristas_completos_edit = [nome_map_full[nome] for nome in motoristas_edit_curtos]
                            faltas_manha_completos_edit = [nome_map_full[nome] for nome in faltas_manha_edit_curtos]
                            faltas_tarde_completos_edit = [nome_map_full[nome] for nome in faltas_tarde_edit_curtos]

                            dados_atualizados = {
                                "bairros": bairros_edit,
                                "atividades_gerais": atividades_gerais_edit,
                                "motoristas": motoristas_completos_edit,
                                "faltas_manha": {"nomes": faltas_manha_completos_edit, "motivo": motivo_manha_edit},
                                "faltas_tarde": {"nomes": faltas_tarde_completos_edit, "motivo": motivo_tarde_edit},
                            }
                            try:
                                ref = db.reference(f'boletins/{boletim_id_selecionado}')
                                ref.update(dados_atualizados)

                                log_atividade(st.session_state.get('username'), "Editou boletim", f"Boletim: {boletim_id_selecionado}")

                                st.success("Boletim atualizado com sucesso!")
                                st.cache_data.clear()
                                st.rerun()
                            except Exception as e:
                                st.error(f"Erro ao atualizar o boletim: {e}")

    with tab3:
        st.subheader("Mapa de Atividades por Dia")
        if df_boletins.empty or df_geo_quarteiroes.empty:
            st.warning("Dados de boletins ou geolocalização de quarteirões não estão disponíveis.")
        else:
            data_mapa = st.date_input("Selecione a data para visualizar no mapa", date.today(), key="mapa_data_plotly")
            boletim_id_mapa = data_mapa.strftime("%Y-%m-%d")

            if boletim_id_mapa in df_boletins.index:
                dados_boletim_mapa = df_boletins.loc[boletim_id_mapa]
                
                atividades_locs = []
                for turno in ['equipes_manha', 'equipes_tarde']:
                    if turno in dados_boletim_mapa and dados_boletim_mapa[turno] and isinstance(dados_boletim_mapa[turno], list):
                        for equipe in dados_boletim_mapa[turno]:
                            membros_nomes = ", ".join(map(formatar_nome, equipe.get('membros', [])))
                            for quarteirao in equipe.get('quarteiroes', []):
                                for atividade in equipe.get('atividades', ["Não especificada"]):
                                    atividades_locs.append({
                                        "quarteirao": quarteirao,
                                        "atividade": atividade,
                                        "equipe": membros_nomes
                                    })
                
                if not atividades_locs:
                    st.info(f"Nenhuma atividade de campo registrada para o dia {data_mapa.strftime('%d/%m/%Y')}.")
                else:
                    df_atividades_mapa = pd.DataFrame(atividades_locs)
                    df_mapa_final = pd.merge(df_atividades_mapa, df_geo_quarteiroes, left_on='quarteirao', right_on='quadra', how='inner')

                    if df_mapa_final.empty:
                        st.warning("Não foi possível encontrar as coordenadas para os quarteirões trabalhados.")
                    else:
                        st.info(f"Exibindo {len(df_mapa_final)} atividades no mapa para {data_mapa.strftime('%d/%m/%Y')}.")

                        fig = px.scatter_mapbox(
                            df_mapa_final,
                            lat="lat",
                            lon="lon",
                            color="atividade",
                            hover_name="quarteirao",
                            hover_data={"equipe": True, "atividade": True, "lat": False, "lon": False},
                            zoom=13,
                            height=600,
                            title="Distribuição de Atividades por Quarteirão"
                        )
                        
                        fig.update_layout(
                            mapbox_style="open-street-map",
                            margin={"r":0, "t":40, "l":0, "b":0},
                            legend_title_text='Atividades'
                        )
                        
                        st.plotly_chart(fig, use_container_width=True)
            else:
                st.info(f"Nenhum boletim encontrado para o dia {data_mapa.strftime('%d/%m/%Y')}.")

    with tab4:
        st.subheader("Dashboard de Produtividade")
        if df_boletins.empty:
            st.info("Nenhum dado de boletim para gerar o dashboard.")
        else:
            hoje = date.today()
            inicio_padrao = hoje - timedelta(days=30)
            data_inicio_dash, data_fim_dash = st.date_input(
                "Selecione o período de análise",
                [inicio_padrao, hoje],
                max_value=hoje,
                key="dash_date_range"
            )

            if data_inicio_dash and data_fim_dash and data_inicio_dash <= data_fim_dash:
                df_boletins['data_dt'] = pd.to_datetime(df_boletins['data']).dt.date
                df_boletins_filtrado = df_boletins[
                    (df_boletins['data_dt'] >= data_inicio_dash) &
                    (df_boletins['data_dt'] <= data_fim_dash)
                ]

                if df_boletins_filtrado.empty:
                    st.warning("Nenhum boletim encontrado no período selecionado.")
                else:
                    dados_analise = []
                    for _, boletim in df_boletins_filtrado.iterrows():
                        data = boletim['data']
                        for turno in ['equipes_manha', 'equipes_tarde']:
                            if turno in boletim and boletim[turno] and isinstance(boletim[turno], list):
                                for equipe in boletim[turno]:
                                    membros = equipe.get('membros', [])
                                    atividades = equipe.get('atividades', [])
                                    quarteiroes = equipe.get('quarteiroes', [])
                                    for membro in membros:
                                        dados_analise.append({'data': data, 'membro': formatar_nome(membro)})
                                    for atividade in atividades:
                                        dados_analise.append({'data': data, 'atividade': atividade})
                                    for quarteirao in quarteiroes:
                                        dados_analise.append({'data': data, 'quarteirao': quarteirao})

                    if not dados_analise:
                        st.info("Nenhuma atividade registrada no período para análise.")
                    else:
                        df_analise = pd.DataFrame(dados_analise)

                        st.divider()
                        st.markdown("#### Análise Gráfica do Período")
                        col1, col2 = st.columns(2)

                        with col1:
                            st.markdown("**Quarteirões Mais Trabalhados**")
                            if 'quarteirao' in df_analise.columns and not df_analise['quarteirao'].dropna().empty:
                                top_quarteiroes = df_analise['quarteirao'].value_counts().nlargest(15)
                                fig = px.bar(top_quarteiroes, x=top_quarteiroes.index, y=top_quarteiroes.values,
                                             labels={'y': 'Nº de Vezes Trabalhado', 'x': 'Quarteirão'}, text_auto=True)
                                fig.update_layout(title_x=0.5, xaxis_title="", yaxis_title="")
                                st.plotly_chart(fig, use_container_width=True)
                            else:
                                st.info("Nenhum dado de quarteirão no período.")
                        
                        with col2:
                            st.markdown("**Atividades Mais Executadas**")
                            if 'atividade' in df_analise.columns and not df_analise['atividade'].dropna().empty:
                                top_atividades = df_analise['atividade'].value_counts()
                                fig_pie = px.pie(top_atividades, values=top_atividades.values, names=top_atividades.index, 
                                                 hole=.3, color_discrete_sequence=px.colors.sequential.RdBu)
                                fig_pie.update_layout(title_x=0.5)
                                st.plotly_chart(fig_pie, use_container_width=True)
                            else:
                                st.info("Nenhum dado de atividade no período.")
                        
                        st.divider()
                        st.markdown("**Participação dos Funcionários (por turnos trabalhados)**")
                        if 'membro' in df_analise.columns and not df_analise['membro'].dropna().empty:
                            participacao = df_analise['membro'].value_counts()
                            fig_part = px.bar(participacao, x=participacao.index, y=participacao.values,
                                             labels={'y': 'Nº de Turnos', 'x': 'Funcionário'}, text_auto=True)
                            fig_part.update_layout(title_x=0.5, xaxis_title="", yaxis_title="")
                            st.plotly_chart(fig_part, use_container_width=True)
                        else:
                            st.info("Nenhum dado de participação no período.")

# ### NOVO MÓDULO DE LOGS ###
def modulo_logs():
    """Renderiza a página para visualizar os logs de atividade."""
    st.title("Logs de Atividade")

    df_logs = carregar_dados_firebase('logs_de_atividade')

    if not df_logs.empty:
        df_logs['timestamp_dt'] = pd.to_datetime(df_logs['timestamp'])
        df_logs_display = df_logs.sort_values(by='timestamp_dt', ascending=False).copy()
        
        # Opcional: Filtros para facilitar a busca
        st.sidebar.markdown("---")
        st.sidebar.subheader("Filtrar Logs")
        usuarios_logados = sorted(df_logs_display['usuario'].unique().tolist())
        filtro_usuario = st.sidebar.selectbox("Filtrar por Usuário", options=["Todos"] + usuarios_logados)

        acoes_disponiveis = sorted(df_logs_display['acao'].unique().tolist())
        filtro_acao = st.sidebar.multiselect("Filtrar por Ação", options=acoes_disponiveis)

        if filtro_usuario != "Todos":
            df_logs_display = df_logs_display[df_logs_display['usuario'] == filtro_usuario]

        if filtro_acao:
            df_logs_display = df_logs_display[df_logs_display['acao'].isin(filtro_acao)]

        # Exibe os dados filtrados
        cols_to_display = ['timestamp', 'usuario', 'acao', 'detalhes']
        st.dataframe(
            df_logs_display[cols_to_display].rename(
                columns={'timestamp': 'Data/Hora', 'usuario': 'Usuário', 'acao': 'Ação', 'detalhes': 'Detalhes'}
            ),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("Nenhum log de atividade encontrado.")


# --- ESTRUTURA PRINCIPAL DA APLICAÇÃO (LOGIN E NAVEGAÇÃO) ---

def login_screen():
    """Renderiza a tela de login."""
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
    """Controla a navegação e a exibição dos módulos após o login."""
    if 'evento_para_editar_id' not in st.session_state:
        st.session_state.evento_para_editar_id = None

    if st.session_state.get('module_choice'):
        with st.sidebar:
            st.title("Navegação")
            st.write(f"Usuário: **{st.session_state['username']}**")
            st.divider()
            if st.button("⬅️ Voltar ao Painel de Controle"):
                st.session_state.evento_para_editar_id = None
                st.session_state['module_choice'] = None
                st.rerun()
            st.divider()
            if st.button("Logout"):
                log_atividade(st.session_state.get('username'), "Logout", "Usuário encerrou a sessão.")
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.rerun()

        if st.session_state['module_choice'] == "Denúncias":
            modulo_denuncias()
        elif st.session_state['module_choice'] == "Recursos Humanos":
            modulo_rh()
        elif st.session_state['module_choice'] == "Boletim":
            modulo_boletim()
        elif st.session_state['module_choice'] == "Logs":
            modulo_logs()

    else:
        st.title("Painel de Controle")
        st.header(f"Bem-vindo(a), {st.session_state['username']}!")
        
        st.write("Selecione o módulo que deseja acessar:")
        col1, col2, col3, col4 = st.columns(4)
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
        with col4:
            if st.button("📄 Logs de Atividade", use_container_width=True):
                st.session_state['module_choice'] = "Logs"
                st.rerun()
        st.divider()

        col_form, col_cal = st.columns([1, 1.5])

        with col_form:
            df_funcionarios = carregar_dados_firebase('funcionarios')
            if not df_funcionarios.empty:
                lista_nomes_curtos = sorted([formatar_nome(nome) for nome in df_funcionarios['nome']])
            else:
                lista_nomes_curtos = []

            if st.session_state.evento_para_editar_id:
                st.subheader("✏️ Editando Evento")
                df_avisos_all = carregar_dados_firebase('avisos')
                dados_evento = df_avisos_all.loc[st.session_state.evento_para_editar_id]

                with st.form("form_avisos_edit"):
                    titulo_edit = st.text_input("Título do Evento", value=dados_evento.get('titulo', ''))
                    
                    tipos_de_evento = ["Aviso", "Compromisso", "Reunião", "Curso", "Educativa"]
                    tipo_idx = tipos_de_evento.index(dados_evento.get('tipo_aviso')) if dados_evento.get('tipo_aviso') in tipos_de_evento else 0
                    tipo_edit = st.selectbox("Tipo", tipos_de_evento, index=tipo_idx, key='tipo_evento_edit')

                    data_val = pd.to_datetime(dados_evento.get('data')).date() if pd.notna(dados_evento.get('data')) else date.today()
                    data_edit = st.date_input("Data", value=data_val)

                    participantes_edit = []
                    if tipo_edit in ["Reunião", "Curso", "Educativa"]:
                        participantes_edit = st.multiselect("Participantes", options=lista_nomes_curtos, default=dados_evento.get('participantes', []))
                    
                    descricao_edit = st.text_area("Descrição (Opcional)", value=dados_evento.get('descricao', ''))

                    col_save, col_cancel = st.columns(2)
                    with col_save:
                        if st.form_submit_button("Salvar Alterações", use_container_width=True):
                            dados_atualizados = {
                                'titulo': titulo_edit,
                                'data': data_edit.strftime("%Y-%m-%d"),
                                'tipo_aviso': tipo_edit,
                                'descricao': descricao_edit,
                                'participantes': participantes_edit
                            }
                            db.reference(f'avisos/{st.session_state.evento_para_editar_id}').update(dados_atualizados)
                            
                            log_atividade(st.session_state.get('username'), "Editou aviso no mural", f"Título: {titulo_edit}")

                            st.success("Evento atualizado com sucesso!")
                            st.session_state.evento_para_editar_id = None
                            st.cache_data.clear()
                            st.rerun()

                    with col_cancel:
                        if st.form_submit_button("Cancelar", type="secondary", use_container_width=True):
                            st.session_state.evento_para_editar_id = None
                            st.rerun()
                st.divider()


            st.subheader("📝 Adicionar no Mural")
            
            tipos_de_evento_add = ["Aviso", "Compromisso", "Reunião", "Curso", "Educativa"]
            aviso_tipo_add = st.selectbox("Tipo de Evento", tipos_de_evento_add, key='tipo_evento_selecionado')
            
            with st.form("form_avisos_add", clear_on_submit=True):
                aviso_titulo = st.text_input("Título do Evento")
                aviso_data = st.date_input("Data")
                
                participantes = []
                if st.session_state.tipo_evento_selecionado in ["Reunião", "Curso", "Educativa"]:
                    participantes = st.multiselect("Participantes", options=lista_nomes_curtos)

                aviso_descricao = st.text_area("Descrição (Opcional)")
                
                submitted = st.form_submit_button("Salvar no Mural")
                if submitted:
                    if aviso_titulo and aviso_data:
                        try:
                            aviso_id = str(int(time.time() * 1000))
                            ref = db.reference(f'avisos/{aviso_id}')
                            ref.set({
                                'titulo': aviso_titulo,
                                'data': aviso_data.strftime("%Y-%m-%d"),
                                'tipo_aviso': st.session_state.tipo_evento_selecionado,
                                'descricao': aviso_descricao,
                                'participantes': participantes 
                            })
                            
                            log_atividade(st.session_state.get('username'), "Adicionou aviso no mural", f"Título: {aviso_titulo}")

                            st.success("Evento salvo no mural com sucesso!")
                            st.cache_data.clear()
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erro ao salvar o aviso: {e}")
                    else:
                        st.warning("Por favor, preencha o Título e a Data.")

            st.divider()
            st.subheader("🗓️ Eventos Agendados")
            df_avisos = carregar_dados_firebase('avisos')

            filtro_data = st.date_input("Filtrar eventos por dia", value=date.today())

            if not df_avisos.empty:
                df_avisos['data_dt'] = pd.to_datetime(df_avisos['data']).dt.date
                avisos_filtrados = df_avisos[df_avisos['data_dt'] == filtro_data].sort_values(by='titulo')

                if avisos_filtrados.empty:
                    st.info(f"Nenhum evento agendado para {filtro_data.strftime('%d/%m/%Y')}.")
                else:
                    for id, aviso in avisos_filtrados.iterrows():
                        with st.expander(f"{aviso.get('tipo_aviso', 'Evento')}: **{aviso.get('titulo', 'Sem título')}**"):
                            if aviso.get('descricao'):
                                st.markdown(f"**Descrição:** {aviso.get('descricao')}")
                            
                            lista_participantes = aviso.get('participantes', [])
                            if lista_participantes and isinstance(lista_participantes, list):
                                participantes_validos = [str(p) for p in lista_participantes if p]
                                if participantes_validos:
                                    st.markdown(f"**Participantes:** {', '.join(participantes_validos)}")
                            
                            st.markdown("---")
                            col_b1, col_b2, _ = st.columns([1, 1, 3])
                            with col_b1:
                                if st.button("✏️ Editar", key=f"edit_{id}", use_container_width=True):
                                    st.session_state.evento_para_editar_id = id
                                    st.rerun()
                            with col_b2:
                                if st.button("🗑️ Deletar", key=f"del_{id}", type="primary", use_container_width=True):
                                    db.reference(f'avisos/{id}').delete()
                                    
                                    log_atividade(st.session_state.get('username'), "Deletou aviso no mural", f"Título: {aviso.get('titulo')}")

                                    st.success(f"Evento '{aviso.get('titulo')}' deletado.")
                                    st.cache_data.clear()
                                    st.rerun()
            else:
                st.info("Nenhum evento no mural para exibir.")


        with col_cal:
            st.subheader("📅 Calendário Geral de Eventos e Ausências")
            
            df_folgas = carregar_dados_firebase('folgas_ferias')
            df_avisos_cal = carregar_dados_firebase('avisos')
            
            calendar_events = []

            if not df_folgas.empty:
                for _, row in df_folgas.iterrows():
                    calendar_events.append({
                        "title": f"AUSÊNCIA: {formatar_nome(row['nome_funcionario'])} ({row['tipo']})",
                        "start": row['data_inicio'],
                        "end": (pd.to_datetime(row['data_fim']) + timedelta(days=1)).strftime("%Y-%m-%d"),
                        "color": "#FF4B4B" if row['tipo'] == "Férias" else "#FFA07A",
                    })
            
            if not df_avisos_cal.empty:
                event_colors = {
                    "Aviso": "#ffc107",
                    "Compromisso": "#28a745",
                    "Reunião": "#007bff",
                    "Curso": "#6f42c1",
                    "Educativa": "#fd7e14"
                }
                for _, row in df_avisos_cal.iterrows():
                    event_type = row.get('tipo_aviso', 'Aviso')
                    calendar_events.append({
                        "title": f"{event_type.upper()}: {row['titulo']}",
                        "start": row['data'],
                        "end": (pd.to_datetime(row['data']) + timedelta(days=1)).strftime("%Y-%m-%d"),
                        "color": event_colors.get(event_type, "#6c757d"),
                    })

            calendar_options = {
                "initialView": "dayGridMonth",
                "height": "800px",
                "locale": "pt-br",
                "headerToolbar": {
                    "left": "prev,next today",
                    "center": "title",
                    "right": "dayGridMonth,timeGridWeek"
                },
                "eventTimeFormat": {
                    "hour": '2-digit',
                    "minute": '2-digit',
                    "meridiem": False
                }
            }
            
            if calendar_events:
                calendar(events=calendar_events, options=calendar_options, key="calendario_mural_atualizado")
            else:
                st.info("Nenhum evento no mural ou ausência registrada para exibir no calendário.")

if __name__ == "__main__":
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False
    if st.session_state['logged_in']:
        main_app()
    else:
        login_screen()
