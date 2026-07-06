import streamlit as st
import duckdb
import pandas as pd
import plotly.express as px
from pathlib import Path

# Configuração da página do Streamlit
st.set_page_config(
    page_title="Dashboard Analítico - PRF Ocorrências",
    page_icon="📊",
    layout="wide"
)

# 1. FUNÇÃO DE CARREGAMENTO COM CACHE (Isolamento da camada Mart)
@st.cache_data
def carregar_dados_mart():
    base_dir = Path(__file__).resolve().parent
    mart_dir = base_dir / "data" / "mart"
    
    con = duckdb.connect(database=":memory:")
    
    con.execute(f"CREATE TABLE dim_calendario AS SELECT * FROM read_parquet('{mart_dir / 'dim_calendario.parquet'}')")
    con.execute(f"CREATE TABLE dim_localidade AS SELECT * FROM read_parquet('{mart_dir / 'dim_localidade.parquet'}')")
    con.execute(f"CREATE TABLE dim_envolvido AS SELECT * FROM read_parquet('{mart_dir / 'dim_envolvido.parquet'}')")
    con.execute(f"CREATE TABLE fato_acidentes_veiculos AS SELECT * FROM read_parquet('{mart_dir / 'fato_acidentes_veiculos.parquet'}')")
    
    df_calendario = con.execute("SELECT * FROM dim_calendario").df()
    df_localidade = con.execute("SELECT * FROM dim_localidade").df()
    
    con.close()
    return df_calendario, df_localidade

try:
    df_cal, df_loc = carregar_dados_mart()
    dados_carregados = True
except Exception as e:
    st.error(f"❌ Erro ao ler a camada Mart em data/mart/: {e}")
    dados_carregados = False

if dados_carregados:
    st.title("📊 Monitoramento Analítico de Acidentes e Veículos")
    st.markdown("Interface executiva para exploração de indicadores geográficos, sazonais e de perfil de risco baseada na camada Mart.")
    st.markdown("---")
    
    # 2. PAINEL DE CONTROLE UNIFICADO (BARRA LATERAL PRF)
    st.sidebar.header("🎯 Painel de Filtros Integrados")
    
    # Filtro 1: Sazonalidade (Anos)
    lista_anos = sorted(df_cal['ano'].unique())
    anos_selecionados = st.sidebar.multiselect(
        "1. Selecione os Anos:",
        options=lista_anos,
        default=lista_anos
    )
    
    st.sidebar.markdown("---")
    
    # Filtro 2: Macrorregiões
    mapeamento_regioes = {
        "Norte": ["ac", "am", "pa", "ro", "rr", "to"],
        "Nordeste": ["al", "ba", "ce", "ma", "pb", "pe", "pi", "rn", "se"],
        "Centro-Oeste": ["df", "go", "mt", "ms"],
        "Sudeste": ["es", "mg", "rj", "sp"],
        "Sul": ["pr", "rs", "sc"]
    }
    
    regioes_selecionadas = st.sidebar.multiselect(
        "2. Selecione as Regiões:",
        options=list(mapeamento_regioes.keys()),
        default=list(mapeamento_regioes.keys())
    )
    
    # Resolução estática para evitar listas nulas no primeiro carregamento
    ufs_permitidas = []
    for r in regioes_selecionadas:
        ufs_permitidas.extend(mapeamento_regioes[r])
    if not ufs_permitidas:
        ufs_permitidas = df_loc['uf'].unique().tolist()

    # Filtro 3: Estados (UFs)
    lista_ufs_disponiveis = sorted([uf for uf in df_loc['uf'].unique() if uf in ufs_permitidas])
    ufs_selecionadas = st.sidebar.multiselect(
        "3. Refine por Estado (UF):",
        options=lista_ufs_disponiveis,
        default=lista_ufs_disponiveis
    )
    
    st.sidebar.markdown("---")
    
    # Filtro 4: Seletor de Impacto de Rodovias
    st.sidebar.subheader("🛣️ Foco em Rodovias (Top 5)")
    criterio_rodovia = st.sidebar.radio(
        "Escolha o critério de análise:",
        options=["Maior índice de acidentes", "Menor índice de acidentes"]
    )

    # Conexão interna DuckDB para queries analíticas
    mart_path = str(Path(__file__).resolve().parent / "data" / "mart")
    con_query = duckdb.connect(database=":memory:")
    con_query.execute(f"CREATE TABLE dim_calendario AS SELECT * FROM read_parquet('{mart_path}/dim_calendario.parquet')")
    con_query.execute(f"CREATE TABLE dim_localidade AS SELECT * FROM read_parquet('{mart_path}/dim_localidade.parquet')")
    con_query.execute(f"CREATE TABLE dim_envolvido AS SELECT * FROM read_parquet('{mart_path}/dim_envolvido.parquet')")
    con_query.execute(f"CREATE TABLE fato_acidentes_veiculos AS SELECT * FROM read_parquet('{mart_path}/fato_acidentes_veiculos.parquet')")

    # VALIDAÇÃO DE SEGURANÇA ANTES DE INICIAR AS QUERIES
    ufs_para_query = ufs_selecionadas if ufs_selecionadas else ufs_permitidas
    
    if not anos_selecionados:
        st.warning("⚠️ Selecione pelo menos um Ano na barra lateral para carregar as análises.")
    elif not ufs_para_query:
        st.warning("⚠️ Selecione pelo menos uma Região ou Estado para carregar as análises.")
    else:
        # Formatação das variáveis para strings SQL
        str_anos = ", ".join([str(int(a)) for a in anos_selecionados])
        str_ufs_finais = ", ".join([f"'{u}'" for u in ufs_para_query])

        # =====================================================================
        # CRIAÇÃO DAS ABAS GLOBAIS DO DASHBOARD
        # =====================================================================
        tab_pergunta1, tab_pergunta2, tab_pergunta3 = st.tabs([
            "📍 1. Análise Geográfica & Rodovias",
            "🪖 2. Perfil de Risco & Severidade",
            "📅 3. Sazonalidade Temporal"
        ])

        # =====================================================================
        # ABA 1: PERGUNTA 1 (Geografia com Gráfico de Barras + Mapa de Calor)
        # =====================================================================
        with tab_pergunta1:
            st.header("📍 1. Concentração Geográfica Avançada e Mapeamento de Ocorrências")
            
            # Query Original 1a: Para alimentar o gráfico de barras por UF
            query_p1 = f"""
                WITH total_filtrado AS (
                    SELECT SUM(f.qtd_registros_envolvidos) AS total_geral
                    FROM fato_acidentes_veiculos f
                    JOIN dim_localidade loc ON f.id_localidade = loc.id_localidade
                    JOIN dim_calendario cal ON f.id_data = cal.id_data
                    WHERE loc.uf IN ({str_ufs_finais}) AND cal.ano IN ({str_anos})
                )
                SELECT 
                    UPPER(loc.uf) AS uf,
                    SUM(f.qtd_registros_envolvidos) AS total_envolvidos,
                    ROUND((SUM(f.qtd_registros_envolvidos) * 100.0) / COALESCE(FIRST(tf.total_geral), 1), 2) AS share_percentual
                FROM fato_acidentes_veiculos f
                JOIN dim_localidade loc ON f.id_localidade = loc.id_localidade
                JOIN dim_calendario cal ON f.id_data = cal.id_data
                CROSS JOIN total_filtrado tf
                WHERE loc.uf IN ({str_ufs_finais}) AND cal.ano IN ({str_anos})
                GROUP BY loc.uf
                ORDER BY total_envolvidos DESC
            """
            
            # Nova Query 1b: Agrupamento geográfico por coordenadas para plotar o Mapa de Pontos
            query_mapa = f"""
                SELECT 
                    CAST(loc.latitude AS DOUBLE) AS latitude,
                    CAST(loc.longitude AS DOUBLE) AS longitude,
                    UPPER(loc.uf) AS estado,
                    'BR-' || LPAD(CAST(f.rodovia_original AS VARCHAR), 3, '0') AS rodovia,
                    COUNT(DISTINCT f.id_acidente_original) AS numero_acidentes
                FROM fato_acidentes_veiculos f
                JOIN dim_localidade loc ON f.id_localidade = loc.id_localidade
                JOIN dim_calendario cal ON f.id_data = cal.id_data
                WHERE loc.uf IN ({str_ufs_finais}) AND cal.ano IN ({str_anos})
                  AND loc.latitude IS NOT NULL 
                  AND loc.longitude IS NOT NULL
                  AND CAST(loc.latitude AS VARCHAR) != '0'
                  AND CAST(loc.longitude AS VARCHAR) != '0'
                GROUP BY loc.latitude, loc.longitude, loc.uf, f.rodovia_original
            """
            
            df_p1 = con_query.execute(query_p1).df()
            df_mapa = con_query.execute(query_mapa).df()
            
            if not df_p1.empty:
                col1, col2 = st.columns([2, 3])
                
                with col1:
                    fig_p1 = px.bar(
                        df_p1, x='uf', y='total_envolvidos', text='share_percentual',
                        labels={'uf': 'Estado (UF)', 'total_envolvidos': 'Total de Envolvidos'},
                        title="Volumetria de Envolvidos por UF (%)",
                        color='total_envolvidos', color_continuous_scale='Reds'
                    )
                    fig_p1.update_traces(texttemplate='%{text}%', textposition='outside')
                    st.plotly_chart(fig_p1, use_container_width=True)
                
                with col2:
                    if not df_mapa.empty:
                        fig_map = px.scatter_mapbox(
                            df_mapa,
                            lat="latitude",
                            lon="longitude",
                            size="numero_acidentes",
                            color="numero_acidentes",
                            color_continuous_scale="YlOrRd", 
                            opacity=0.8,
                            zoom=3.5,
                            mapbox_style="carto-positron", 
                            title="Distribuição Espacial de Acidentes (Alto Contraste)",
                            labels={'numero_acidentes': 'Nº de Acidentes', 'estado': 'Estado', 'rodovia': 'Rodovia'},
                            hover_name="rodovia",
                            hover_data={
                                "estado": True,
                                "rodovia": False,
                                "numero_acidentes": True,
                                "latitude": False,
                                "longitude": False
                            }
                        )
                        fig_map.update_layout(
                            margin={"r":0, "t":40, "l":0, "b":0},
                            paper_bgcolor="rgba(0,0,0,0)",
                            plot_bgcolor="rgba(0,0,0,0)"
                        )
                        st.plotly_chart(fig_map, use_container_width=True)
                    else:
                        st.info("ℹ️ Coordenadas geográficas ausentes para renderização do mapa.")
            else:
                st.info("ℹ️ Nenhuma ocorrência encontrada para os filtros selecionados.")

            st.markdown("---")
            
            # Ranking de Rodovias (Top 5)
            st.subheader(f"🛣️ Top 5 Rodovias Federais - {criterio_rodovia}")
            
            coluna_metrica = "COUNT(DISTINCT f.id_acidente_original)"
            label_eixo_y = "Total de Acidentes"
            ordenacao_sql = "DESC" if criterio_rodovia == "Maior índice de acidentes" else "ASC"
            cor_grafico = "Oranges" if ordenacao_sql == "DESC" else "Blues"
            titulo_grafico = f"As 5 Rodovias do Escopo Selecionado com {criterio_rodovia}"
            
            query_rodovias = f"""
                SELECT 
                    'BR-' || LPAD(CAST(f.rodovia_original AS VARCHAR), 3, '0') AS rodovia,
                    STRING_AGG(DISTINCT UPPER(loc.uf), ', ') AS estados,
                    {coluna_metrica} AS valor_indicador
                FROM fato_acidentes_veiculos f
                JOIN dim_localidade loc ON f.id_localidade = loc.id_localidade
                JOIN dim_calendario cal ON f.id_data = cal.id_data
                WHERE loc.uf IN ({str_ufs_finais}) 
                  AND cal.ano IN ({str_anos})
                  AND f.rodovia_original IS NOT NULL 
                  AND CAST(f.rodovia_original AS VARCHAR) != '' 
                  AND CAST(f.rodovia_original AS VARCHAR) != '0'
                GROUP BY f.rodovia_original
                ORDER BY valor_indicador {ordenacao_sql}
                LIMIT 5
            """
            
            df_rodovias = con_query.execute(query_rodovias).df()
            
            if not df_rodovias.empty:
                col_r1, col_r2 = st.columns([3, 2])
                with col_r1:
                    fig_rodovias = px.bar(
                        df_rodovias, x='rodovia', y='valor_indicador', text='valor_indicador',
                        labels={'rodovia': 'Rodovia Federal', 'valor_indicador': label_eixo_y},
                        title=titulo_grafico,
                        color='valor_indicador', color_continuous_scale=cor_grafico
                    )
                    fig_rodovias.update_traces(textposition='outside')
                    st.plotly_chart(fig_rodovias, use_container_width=True)
                with col_r2:
                    st.markdown("<br>", unsafe_allow_html=True)
                    st.dataframe(
                        df_rodovias.rename(columns={
                            'rodovia': 'Rodovia (BR)', 
                            'estados': 'Estado(s)', 
                            'valor_indicador': label_eixo_y
                        }),
                        use_container_width=True, hide_index=True
                    )
            else:
                st.info("ℹ️ Não foram encontrados registros de rodovias válidas.")

        # =====================================================================
        # ABA 2: PERGUNTA 2 (Perfil de Risco & Severidade Atualizado)
        # =====================================================================
        with tab_pergunta2:
            st.header("🪖 2. Distribuição de Severidade por Papel do Envolvido")
            
            # Query utilizando Window Function para calcular a porcentagem por linha/categoria
            query_p2 = f"""
                WITH total_por_papel AS (
                    SELECT 
                        CONCAT(UPPER(SUBSTR(env.tipo_envolvido, 1, 1)), LOWER(SUBSTR(env.tipo_envolvido, 2))) AS papel_envolvido,
                        CASE 
                            WHEN f.is_fatal = 1 THEN 'Fatal (Óbito)' 
                            ELSE 'Não Fatal (Ferido/Ileso)' 
                        END AS severidade,
                        SUM(f.qtd_registros_envolvidos) AS total_pessoas
                    FROM fato_acidentes_veiculos f
                    JOIN dim_envolvido env ON f.id_envolvido = env.id_envolvido
                    JOIN dim_localidade loc ON f.id_localidade = loc.id_localidade
                    JOIN dim_calendario cal ON f.id_data = cal.id_data
                    WHERE loc.uf IN ({str_ufs_finais}) 
                      AND cal.ano IN ({str_anos})
                      AND env.tipo_envolvido IS NOT NULL 
                      AND env.tipo_envolvido != 'nao_informado'
                    GROUP BY papel_envolvido, severidade
                )
                SELECT 
                    papel_envolvido,
                    severidade,
                    total_pessoas,
                    ROUND((total_pessoas * 100.0) / SUM(total_pessoas) OVER(PARTITION BY papel_envolvido), 1) AS percentual_papel
                FROM total_por_papel
                ORDER BY total_pessoas DESC;
            """
            
            df_p2 = con_query.execute(query_p2).df()
            
            if not df_p2.empty:
                # Criando o gráfico mantendo o tamanho real (volumetria bruta)
                fig_p2 = px.bar(
                    df_p2,
                    x="total_pessoas",
                    y="papel_envolvido",
                    color="severidade",
                    text="percentual_papel", 
                    orientation="h",
                    title="🔥 Perfil de Severidade e Volumetria por Papel do Envolvido",
                    labels={
                        "total_pessoas": "Total de Pessoas Afetadas",
                        "papel_envolvido": "Papel do Envolvido",
                        "severidade": "Classificação do Caso"
                    },
                    color_discrete_map={
                        "Fatal (Óbito)": "#D32F2F",
                        "Não Fatal (Ferido/Ileso)": "#1976D2"
                    },
                    barmode="stack" 
                )
                
                fig_p2.update_traces(
                    texttemplate='%{text}%', 
                    textposition='inside',
                    insidetextanchor='middle'
                )
                
                fig_p2.update_layout(
                    yaxis={'categoryorder': 'total ascending'},
                    margin={"r": 20, "t": 50, "l": 0, "b": 40},
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                )
                st.plotly_chart(fig_p2, use_container_width=True)
            else:
                st.info("ℹ️ Sem dados para os envolvidos neste escopo.")

            # -----------------------------------------------------------------
            # MAPA DE ACIDENTES FATAIS & TABELA TOP 5 BRs
            # -----------------------------------------------------------------
            st.markdown("---")
            st.subheader("📍 Análise Geográfica de Ocorrências Fatais")
            
            # Criando duas colunas na tela (Proporção 2 para o Mapa, 1 para a Tabela)
            col_mapa, col_tabela = st.columns([2, 1])
            
            with col_mapa:
                # 1. Query para o Mapa de Calor
                query_mapa_fatal = f"""
                    SELECT 
                        loc.latitude,
                        loc.longitude,
                        loc.uf,
                        COUNT(*) AS total_acidentes
                    FROM fato_acidentes_veiculos f
                    JOIN dim_localidade loc ON f.id_localidade = loc.id_localidade
                    JOIN dim_calendario cal ON f.id_data = cal.id_data
                    WHERE loc.uf IN ({str_ufs_finais}) 
                      AND cal.ano IN ({str_anos})
                      AND f.is_fatal = 1  
                      AND loc.latitude IS NOT NULL 
                      AND loc.longitude IS NOT NULL
                    GROUP BY loc.latitude, loc.longitude, loc.uf;
                """
                
                df_mapa_fatal = con_query.execute(query_mapa_fatal).df()
                
                if not df_mapa_fatal.empty:
                    fig_mapa_fatal = px.density_mapbox(
                        df_mapa_fatal,
                        lat="latitude",     
                        lon="longitude",    
                        z="total_acidentes",
                        radius=12,
                        center=dict(lat=-15.78, lon=-47.93),
                        zoom=3,
                        mapbox_style="open-street-map", 
                        color_continuous_scale="Reds",  # 🎯 Escala em tons de vermelho ativada
                        title="🔥 Concentração de Ocorrências Fatais",
                        labels={"total_acidentes": "Nº de Acidentes Fatais", "uf": "Estado"},
                        hover_data={"uf": True, "total_acidentes": True}
                    )
                    
                    fig_mapa_fatal.update_layout(
                        margin={"r": 0, "t": 40, "l": 0, "b": 0},
                        height=500
                    )
                    
                    st.plotly_chart(fig_mapa_fatal, use_container_width=True)
                else:
                    st.warning("⚠️ Sem dados georreferenciados para o mapa neste escopo.")
            
            with col_tabela:
                st.markdown("<br><br>", unsafe_allow_html=True) # Alinhamento vertical simples
                st.markdown("### 🏆 Top 5 Rodovias Críticas")
                
                # 2. Query corrigida: buscando a coluna 'br' diretamente da tabela fato (f) 🎯
                query_top_brs = f"""
                    SELECT 
                        COALESCE(f.br, 'Não Informada') AS "Rodovia",
                        COUNT(*) AS "Acidentes Fatais"
                    FROM fato_acidentes_veiculos f
                    JOIN dim_localidade loc ON f.id_localidade = loc.id_localidade
                    JOIN dim_calendario cal ON f.id_data = cal.id_data
                    WHERE loc.uf IN ({str_ufs_finais}) 
                      AND cal.ano IN ({str_anos})
                      AND f.is_fatal = 1
                    GROUP BY f.br
                    ORDER BY COUNT(*) DESC
                    LIMIT 5;
                """
                
                try:
                    df_top_brs = con_query.execute(query_top_brs).df()
                    
                    if not df_top_brs.empty:
                        # Exibe uma tabela limpa e elegante nativa do Streamlit
                        st.dataframe(
                            df_top_brs, 
                            use_container_width=True, 
                            hide_index=True
                        )
                    else:
                        st.info("ℹ️ Nenhuma ocorrência fatal registrada.")
                except Exception as e:
                    # Caso o nome do campo na fato seja ligeiramente diferente (ex: f.rodovia), exibe o erro técnico para sabermos o nome exato
                    st.error(f"⚠️ Erro ao carregar os dados das BRs: {e}")
                
        # =====================================================================
        # ABA 3: PERGUNTA 3 (Sazonalidade Temporal Sobreposta)
        # =====================================================================
        with tab_pergunta3:
            st.header("📅 3. Comportamento e Sazonalidade Temporal por Ano")
            
            query_p3 = f"""
                SELECT 
                    CAST(cal.ano AS VARCHAR) AS ano,
                    cal.mes,
                    CASE cal.mes
                        WHEN 1 THEN 'Jan' WHEN 2 THEN 'Fev' WHEN 3 THEN 'Mar'
                        WHEN 4 THEN 'Abr' WHEN 5 THEN 'Mai' WHEN 6 THEN 'Jun'
                        WHEN 7 THEN 'Jul' WHEN 8 THEN 'Ago' WHEN 9 THEN 'Set'
                        WHEN 10 THEN 'Out' WHEN 11 THEN 'Nov' WHEN 12 THEN 'Dez'
                    END AS nome_mes,
                    COUNT(DISTINCT f.id_acidente_original) AS total_acidentes
                FROM fato_acidentes_veiculos f
                JOIN dim_localidade loc ON f.id_localidade = loc.id_localidade
                JOIN dim_calendario cal ON f.id_data = cal.id_data
                WHERE loc.uf IN ({str_ufs_finais}) AND cal.ano IN ({str_anos})
                GROUP BY cal.ano, cal.mes, nome_mes
                ORDER BY cal.ano ASC, cal.mes ASC
            """
            
            df_p3 = con_query.execute(query_p3).df()
            anos_retornados = sorted(df_p3['ano'].unique()) if not df_p3.empty else []
            ordem_meses = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
            
            if len(anos_retornados) > 0:
                lista_titulos_abas = [f"Ano {ano}" for ano in anos_retornados] + ["📈 Todos (Comparativo)"]
                abas_anos = st.tabs(lista_titulos_abas)
                
                for i, ano in enumerate(anos_retornados):
                    with abas_anos[i]:
                        df_ano = df_p3[df_p3['ano'] == ano]
                        fig_p3_ano = px.line(
                            df_ano, x='nome_mes', y='total_acidentes',
                            labels={'nome_mes': 'Mês', 'total_acidentes': 'Quantidade de Ocorrências'},
                            title=f"Evolução Mensal de Ocorrências - Histórico {ano}",
                            markers=True
                        )
                        fig_p3_ano.update_layout(xaxis={'categoryorder': 'array', 'categoryarray': ordem_meses})
                        st.plotly_chart(fig_p3_ano, use_container_width=True)
                
                with abas_anos[-1]:
                    st.subheader("📊 Comparativo Sazonal Sobreposto (Ano contra Ano)")
                    fig_comparativo = px.line(
                        df_p3, x='nome_mes', y='total_acidentes', color='ano',
                        labels={'nome_mes': 'Mês', 'total_acidentes': 'Quantidade de Ocorrências', 'ano': 'Ano de Análise'},
                        title="Análise Cruzada de Sazonalidade: Históricos Sobrepostos",
                        markers=True,
                        color_discrete_sequence=px.colors.qualitative.Bold
                    )
                    fig_comparativo.update_layout(xaxis={'categoryorder': 'array', 'categoryarray': ordem_meses})
                    st.plotly_chart(fig_comparativo, use_container_width=True)
            else:
                st.info("ℹ️ Dados temporais indisponíveis para os filtros aplicados.")