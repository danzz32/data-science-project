import streamlit as st
import streamlit_shadcn_ui as ui
import duckdb
import pandas as pd
import plotly.express as px
from pathlib import Path

# ===================================================================================
# 1. CONFIGURAÇÃO DA PÁGINA E CONSTANTES VISUAIS (mesma paleta do Observatório PRF)
# ===================================================================================
PRF_ICON      = "https://upload.wikimedia.org/wikipedia/commons/1/1b/PRF_new.png"
PRF_NAVY      = "#0B1F3A"
PRF_NAVY_2    = "#142E52"
PRF_BLUE      = "#1E88E5"
PRF_BLUE_DARK = "#0D47A1"
PRF_YELLOW    = "#FFC400"
PRF_RED       = "#E53935"
PRF_GRAY_BG   = "#F1F3F6"
PRF_GRAY_TXT  = "#6B7280"

st.set_page_config(
    page_title="PRF | Dashboard Analítico de Ocorrências",
    page_icon=PRF_ICON,
    layout="wide",
)

st.markdown(
    f"""
    <style>
    .stApp {{ background-color: {PRF_GRAY_BG}; }}
    #MainMenu, footer {{ visibility: hidden; }}

    .header-banner {{
        background: linear-gradient(90deg, {PRF_NAVY} 0%, {PRF_NAVY_2} 100%);
        padding: 16px 26px;
        border-radius: 10px;
        display: flex;
        align-items: center;
        margin-bottom: 18px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.18);
    }}
    .header-banner img {{ height: 46px; margin-right: 16px; }}
    .header-title {{ color: #FFFFFF; margin: 0; font-family: 'Segoe UI', Arial, sans-serif;
                      font-size: 23px; font-weight: 700; letter-spacing: .3px; }}
    .header-subtitle {{ color: #AEB8C4; font-size: 12px; margin-left: auto;
                         text-transform: uppercase; letter-spacing: 1.5px; text-align: right; }}

    .section-subtitle {{
        color: {PRF_NAVY}; font-size: 15px; font-weight: 700; margin: 4px 0 10px 0;
        border-left: 4px solid {PRF_BLUE}; padding-left: 9px;
    }}
    
    .section-title {{
        color: {PRF_NAVY}; font-size: 20px; font-weight: 700; margin: 4px 0 10px 0;
        border-left: 4px solid {PRF_BLUE}; padding-left: 9px;
    }}
    
    .filter-caption {{ font-size: 11px; color: {PRF_GRAY_TXT}; font-weight: 700;
                        text-transform: uppercase; letter-spacing: .5px; margin-bottom: 2px; }}
    </style>
    """,
    unsafe_allow_html=True,
)

# ===================================================================================
# 2. CABEÇALHO
# ===================================================================================
st.markdown(
    f"""
    <div class="header-banner">
        <img src="{PRF_ICON}">
        <h1 class="header-title" style="color:#fff">MONITORAMENTO ANALÍTICO DE ACIDENTES E VEÍCULOS</h1>
        <div class="header-subtitle">Camada Mart &middot; PRF</div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ===================================================================================
# 3. CARREGAMENTO DE DADOS (mantido: leitura da camada Mart via DuckDB/Parquet)
# ===================================================================================
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


def fmt_num(n: float) -> str:
    """Formata número no padrão brasileiro (ponto como separador de milhar)."""
    return f"{n:,.0f}".replace(",", ".")


def _safe_int(x) -> int:
    return int(x) if pd.notna(x) else 0


try:
    df_cal, df_loc = carregar_dados_mart()
    dados_carregados = True
except Exception as e:
    st.error(f"❌ Erro ao ler a camada Mart em data/mart/: {e}")
    dados_carregados = False

if dados_carregados:

    # ===============================================================================
    # 4. FILTROS (Ajustados: Remoção do st.radio irrelevante)
    # ===============================================================================
    st.markdown('<div class="filter-caption">FILTROS</div>', unsafe_allow_html=True)

    mapeamento_regioes = {
        "Norte": ["ac", "am", "pa", "ro", "rr", "to"],
        "Nordeste": ["al", "ba", "ce", "ma", "pb", "pe", "pi", "rn", "se"],
        "Centro-Oeste": ["df", "go", "mt", "ms"],
        "Sudeste": ["es", "mg", "rj", "sp"],
        "Sul": ["pr", "rs", "sc"],
    }

    f1, f2, f3 = st.columns([1, 1.5, 2.5])

    with f1:
        lista_anos = sorted(df_cal["ano"].unique())
        anos_selecionados = st.multiselect("Ano", options=lista_anos, default=lista_anos)

    with f2:
        regioes_selecionadas = st.multiselect(
            "Região", options=list(mapeamento_regioes.keys()), default=list(mapeamento_regioes.keys())
        )

    # Resolução estática para evitar listas nulas no primeiro carregamento
    ufs_permitidas = []
    for r in regioes_selecionadas:
        ufs_permitidas.extend(mapeamento_regioes[r])
    if not ufs_permitidas:
        ufs_permitidas = df_loc["uf"].unique().tolist()

    with f3:
        lista_ufs_disponiveis = sorted([uf for uf in df_loc["uf"].unique() if uf in ufs_permitidas])
        ufs_selecionadas = st.multiselect("UF", options=lista_ufs_disponiveis, default=lista_ufs_disponiveis)

    st.markdown("<br>", unsafe_allow_html=True)

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
        st.warning("⚠️ Selecione pelo menos um Ano nos filtros para carregar as análises.")
    elif not ufs_para_query:
        st.warning("⚠️ Selecione pelo menos uma Região ou Estado para carregar as análises.")
    else:
        str_anos = ", ".join([str(int(a)) for a in anos_selecionados])
        str_ufs_finais = ", ".join([f"'{u}'" for u in ufs_para_query])

        # ===========================================================================
        # 5. KPIs GLOBAIS
        # ===========================================================================
        query_kpis = f"""
            SELECT
                COUNT(DISTINCT f.id_acidente_original) AS total_acidentes,
                COUNT(DISTINCT CASE WHEN f.is_fatal = 1 THEN f.id_acidente_original END) AS acidentes_fatais,
                SUM(f.qtd_registros_envolvidos) AS total_envolvidos,
                COUNT(*) AS registros_veiculo
            FROM fato_acidentes_veiculos f
            JOIN dim_localidade loc ON f.id_localidade = loc.id_localidade
            JOIN dim_calendario cal ON f.id_data = cal.id_data
            WHERE loc.uf IN ({str_ufs_finais}) AND cal.ano IN ({str_anos})
        """
        kpis = con_query.execute(query_kpis).df().iloc[0]
        total_acidentes    = _safe_int(kpis["total_acidentes"])
        acidentes_fatais   = _safe_int(kpis["acidentes_fatais"])
        total_envolvidos   = _safe_int(kpis["total_envolvidos"])
        registros_veiculo  = _safe_int(kpis["registros_veiculo"])
        letalidade = (acidentes_fatais / total_acidentes * 100) if total_acidentes else 0

        k1, k2, k3, k4, k5 = st.columns(5)
        with k1:
            ui.metric_card(title="", content=fmt_num(total_acidentes), description="ACIDENTES", key="kpi1")
        with k2:
            ui.metric_card(title="", content=fmt_num(acidentes_fatais), description="ACIDENTES FATAIS", key="kpi2")
        with k3:
            ui.metric_card(title="", content=fmt_num(total_envolvidos), description="ENVOLVIDOS", key="kpi3")
        with k4:
            ui.metric_card(title="", content=f"{letalidade:.1f}%", description="ÍNDICE DE LETALIDADE", key="kpi4")
        with k5:
            ui.metric_card(title="", content=fmt_num(registros_veiculo), description="REGISTROS VEÍCULO-ENVOLVIDO", key="kpi5")

        st.markdown("<br>", unsafe_allow_html=True)

        # ===========================================================================
        # 6. ABAS
        # ===========================================================================
        tab_pergunta1, tab_pergunta2, tab_pergunta3 = st.tabs([
            "📍 Análise Geográfica & Rodovias",
            "🪖 Perfil de Risco & Severidade",
            "📅 Sazonalidade Temporal",
        ])

        # =====================================================================
        # ABA 1: GEOGRAFIA (Gráfico de Barras + Mapa + Ranking de Rodovias)
        # =====================================================================
        with tab_pergunta1:
            st.markdown(
                '<div class="section-title">Concentração Geográfica Avançada e Mapeamento de Ocorrências</div>',
                unsafe_allow_html=True,
            )

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
                LIMIT 10
            """

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
                # 🎯 Alterado de [2, 3] para [1, 1] para equilibrar o layout meio a meio na tela
                col1, col2 = st.columns([1, 1])

                with col1:
                    st.markdown('<div class="section-subtitle">Volumetria de Envolvidos por UF</div>', unsafe_allow_html=True)
                    fig_p1 = px.bar(
                        df_p1.sort_values("total_envolvidos"), x="total_envolvidos", y="uf", orientation="h",
                        text="share_percentual", color_discrete_sequence=[PRF_BLUE],
                        labels={"uf": "Estado (UF)", "total_envolvidos": "Total de Envolvidos"},
                    )
                    fig_p1.update_traces(texttemplate="%{text}%", textposition="outside")
                    fig_p1.update_layout(
                        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                        margin={"r": 30, "t": 5, "l": 5, "b": 5}, height=400, # 🎯 Ajustado para 400px
                        xaxis_title=None, yaxis_title=None,
                    )
                    st.plotly_chart(fig_p1, use_container_width=True)

                with col2:
                    st.markdown('<div class="section-subtitle">Distribuição Espacial de Acidentes</div>', unsafe_allow_html=True)
                    if not df_mapa.empty:
                        fig_map = px.scatter_mapbox(
                            df_mapa, lat="latitude", lon="longitude",
                            size="numero_acidentes", color="numero_acidentes",
                            zoom=3.2, mapbox_style="carto-positron", height=400, opacity=0.85, # 🎯 Ajustado para 400px
                            color_continuous_scale=[PRF_BLUE, PRF_YELLOW, PRF_RED],
                            hover_name="rodovia",
                            hover_data={
                                "estado": True, "rodovia": False, "numero_acidentes": True,
                                "latitude": False, "longitude": False,
                            },
                        )
                        fig_map.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0}, coloraxis_showscale=False)
                        st.plotly_chart(fig_map, use_container_width=True)
                    else:
                        st.info("ℹ️ Coordenadas geográficas ausentes para renderização do mapa.")
            else:
                st.info("ℹ️ Nenhuma ocorrência encontrada para os filtros selecionados.")

            st.markdown("<br>", unsafe_allow_html=True)

            # Ajustado para fixar a exibição no Top 5 de maior índice de acidentes de forma padrão
            st.markdown(
                '<div class="section-subtitle">🛣️ Top 5 Rodovias Federais — Maior índice de acidentes</div>',
                unsafe_allow_html=True,
            )

            query_rodovias = f"""
                SELECT
                    'BR-' || LPAD(CAST(f.rodovia_original AS VARCHAR), 3, '0') AS rodovia,
                    STRING_AGG(DISTINCT UPPER(loc.uf), ', ') AS estados,
                    COUNT(DISTINCT f.id_acidente_original) AS valor_indicador
                FROM fato_acidentes_veiculos f
                JOIN dim_localidade loc ON f.id_localidade = loc.id_localidade
                JOIN dim_calendario cal ON f.id_data = cal.id_data
                WHERE loc.uf IN ({str_ufs_finais})
                  AND cal.ano IN ({str_anos})
                  AND f.rodovia_original IS NOT NULL
                  AND CAST(f.rodovia_original AS VARCHAR) != ''
                  AND CAST(f.rodovia_original AS VARCHAR) != '0'
                GROUP BY f.rodovia_original
                ORDER BY valor_indicador DESC
                LIMIT 5
            """

            df_rodovias = con_query.execute(query_rodovias).df()

            if not df_rodovias.empty:
                col_r1, col_r2 = st.columns([1, 1]) # 🎯 Se quiser equilibrar o ranking de baixo também
                with col_r1:
                    fig_rodovias = px.bar(
                        df_rodovias.sort_values("valor_indicador"), x="valor_indicador", y="rodovia", orientation="h",
                        text="valor_indicador", color_discrete_sequence=[PRF_BLUE],
                        labels={"rodovia": "Rodovia Federal", "valor_indicador": "Total de Acidentes"},
                    )
                    fig_rodovias.update_traces(texttemplate="%{text:,}", textposition="outside")
                    fig_rodovias.update_layout(
                        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                        margin={"r": 30, "t": 5, "l": 5, "b": 5}, height=320,
                        xaxis_title=None, yaxis_title=None,
                    )
                    st.plotly_chart(fig_rodovias, use_container_width=True)
                with col_r2:
                    st.markdown("<br>", unsafe_allow_html=True)
                    st.dataframe(
                        df_rodovias.rename(columns={
                            "rodovia": "Rodovia (BR)",
                            "estados": "Estado(s)",
                            "valor_indicador": "Total de Acidentes",
                        }),
                        use_container_width=True, hide_index=True,
                    )
            else:
                st.info("ℹ️ Não foram encontrados registros de rodovias válidas.")
        # =====================================================================
        # ABA 2: PERFIL DE RISCO & SEVERIDADE
        # =====================================================================
        with tab_pergunta2:
            st.markdown(
                '<div class="section-subtitle">Distribuição de Severidade por Papel do Envolvido</div>',
                unsafe_allow_html=True,
            )

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
                fig_p2 = px.bar(
                    df_p2,
                    x="total_pessoas",
                    y="papel_envolvido",
                    color="severidade",
                    text="percentual_papel",
                    orientation="h",
                    labels={
                        "total_pessoas": "Total de Pessoas Afetadas",
                        "papel_envolvido": "Papel do Envolvido",
                        "severidade": "Classificação do Caso",
                    },
                    color_discrete_map={
                        "Fatal (Óbito)": PRF_RED,
                        "Não Fatal (Ferido/Ileso)": PRF_BLUE,
                    },
                    barmode="stack",
                )
                fig_p2.update_traces(texttemplate="%{text}%", textposition="inside", insidetextanchor="middle")
                fig_p2.update_layout(
                    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                    yaxis={"categoryorder": "total ascending"},
                    margin={"r": 20, "t": 10, "l": 0, "b": 40}, height=340,
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                )
                st.plotly_chart(fig_p2, use_container_width=True)
            else:
                st.info("ℹ️ Sem dados para os envolvidos neste escopo.")

            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown(
                '<div class="section-subtitle">📍 Análise Geográfica de Ocorrências Fatais</div>',
                unsafe_allow_html=True,
            )

            # 🎯 Alterado de [2, 1] para [1, 1] para garantir o layout meio a meio na tela
            col_mapa, col_tabela = st.columns([1, 1])

            with col_mapa:
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
                        mapbox_style="carto-positron",
                        color_continuous_scale="Reds",  # 🎯 Ajustado para a escala de tons vermelhos
                        labels={"total_acidentes": "Nº de Acidentes Fatais", "uf": "Estado"},
                        hover_data={"uf": True, "total_acidentes": True},
                    )
                    fig_mapa_fatal.update_layout(
                        margin={"r": 0, "t": 0, "l": 0, "b": 0}, height=420, coloraxis_showscale=False, # 🎯 Altura padronizada
                    )
                    st.plotly_chart(fig_mapa_fatal, use_container_width=True)
                else:
                    st.warning("⚠️ Sem dados georreferenciados para o mapa neste escopo.")

            with col_tabela:
                st.markdown('<div class="section-subtitle">🏆 Top 5 Rodovias Críticas</div>', unsafe_allow_html=True)

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
                        # 🎯 Adicionado um pequeno espaçamento para alinhar com o topo do mapa ao lado
                        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
                        st.dataframe(df_top_brs, use_container_width=True, hide_index=True)
                    else:
                        st.info("ℹ️ Nenhuma ocorrência fatal registrada.")
                except Exception as e:
                    st.error(f"⚠️ Erro ao carregar os dados das BRs: {e}")

            st.markdown("<br>", unsafe_allow_html=True)

            # -----------------------------------------------------------------
            # BLOCO: Ranking e Mapa de Letalidade por Estado (UF)
            # -----------------------------------------------------------------
            st.markdown(
                '<div class="section-subtitle">📊 Letalidade por Estado: % de Acidentes Fatais</div>',
                unsafe_allow_html=True,
            )

            query_letalidade = f"""
                WITH total_por_uf AS (
                    SELECT
                        loc.uf,
                        AVG(loc.latitude) AS latitude,
                        AVG(loc.longitude) AS longitude,
                        COUNT(CASE WHEN f.is_fatal = 1 THEN 1 END) AS acidentes_fatais,
                        COUNT(*) AS total_acidentes
                    FROM fato_acidentes_veiculos f
                    JOIN dim_localidade loc ON f.id_localidade = loc.id_localidade
                    JOIN dim_calendario cal ON f.id_data = cal.id_data
                    WHERE loc.uf IN ({str_ufs_finais})
                      AND cal.ano IN ({str_anos})
                    GROUP BY loc.uf
                )
                SELECT
                    uf AS "Estado",
                    latitude,
                    longitude,
                    acidentes_fatais AS "Acidentes Fatais",
                    total_acidentes AS "Total de Acidentes",
                    ROUND((acidentes_fatais * 100.0) / total_acidentes, 2) AS "Percentual Fatal (%)"
                FROM total_por_uf
                WHERE total_acidentes > 0
                ORDER BY "Percentual Fatal (%)" DESC;
            """

            try:
                df_letalidade = con_query.execute(query_letalidade).df()

                if not df_letalidade.empty:
                    col_rank, col_mapa_let = st.columns([1, 1])

                    with col_rank:
                        fig_letalidade = px.bar(
                            df_letalidade,
                            x="Percentual Fatal (%)",
                            y="Estado",
                            orientation="h",
                            text="Percentual Fatal (%)",
                            labels={
                                "Percentual Fatal (%)": "Casos Fatais (%)",
                                "Estado": "UF"
                            },
                            color="Percentual Fatal (%)",
                            color_continuous_scale=[PRF_BLUE, PRF_YELLOW, PRF_RED],
                        )
                        
                        fig_letalidade.update_traces(
                            texttemplate="%{text}%", 
                            textposition="outside"
                        )
                        
                        fig_letalidade.update_layout(
                            plot_bgcolor="rgba(0,0,0,0)", 
                            paper_bgcolor="rgba(0,0,0,0)",
                            yaxis={"categoryorder": "total ascending"},
                            margin={"r": 40, "t": 10, "l": 0, "b": 10}, 
                            height=380,
                            coloraxis_showscale=False,
                        )
                        st.plotly_chart(fig_letalidade, use_container_width=True)

                    with col_mapa_let:
                        fig_mapa_let = px.scatter_mapbox(
                            df_letalidade,
                            lat="latitude",
                            lon="longitude",
                            size="Percentual Fatal (%)",
                            zoom=3,
                            center=dict(lat=-15.78, lon=-47.93),
                            mapbox_style="carto-positron",
                            size_max=22,
                            labels={"Percentual Fatal (%)": "Letalidade (%)", "Estado": "Estado"},
                            hover_data={
                                "Estado": True, 
                                "Percentual Fatal (%)": ":.2f%", 
                                "Total de Acidentes": True,
                                "latitude": False,
                                "longitude": False
                            }
                        )
                        
                        fig_mapa_let.update_traces(
                            marker=dict(color=PRF_RED)
                        )
                        
                        fig_mapa_let.update_layout(
                            margin={"r": 0, "t": 10, "l": 0, "b": 10}, 
                            height=380, 
                            coloraxis_showscale=False
                        )
                        st.plotly_chart(fig_mapa_let, use_container_width=True)
                else:
                    st.info("ℹ️ Sem dados suficientes para calcular o ranking e o mapa de letalidade.")
            except Exception as e:
                st.error(f"⚠️ Erro ao carregar a análise de letalidade: {e}")

            st.markdown("<br>", unsafe_allow_html=True)
            
            # -----------------------------------------------------------------
            # EXIBIÇÃO DA TAXA DE FATALIDADE BRASIL (ESCOPO SELECIONADO)
            # -----------------------------------------------------------------
            if not df_letalidade.empty:
                total_fatais_br = df_letalidade["Acidentes Fatais"].sum()
                total_acidentes_br = df_letalidade["Total de Acidentes"].sum()
                
                if total_acidentes_br > 0:
                    taxa_fatalidade_br = round((total_fatais_br * 100.0) / total_acidentes_br, 2)
                else:
                    taxa_fatalidade_br = 0.0

                st.markdown(
                    f"""
                    <div style="background-color: rgba(255, 0, 0, 0.05); padding: 15px; border-left: 5px solid {PRF_RED}; border-radius: 4px; margin-top: 10px;">
                        <span style="font-weight: bold; font-size: 16px;">
                            A taxa de fatalidade por acidente para o período selecionado no Brasil é: 
                            <span style="color: {PRF_RED}; font-size: 18px;">{taxa_fatalidade_br}%</span>
                        </span>
                    </div>
                    """, 
                    unsafe_allow_html=True
                )
        # =====================================================================
        # ABA 3: SAZONALIDADE TEMPORAL
        # =====================================================================
        with tab_pergunta3:
            st.markdown(
                '<div class="section-title">Comportamento e Sazonalidade Temporal por Ano</div>',
                unsafe_allow_html=True,
            )

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
            anos_retornados = sorted(df_p3["ano"].unique()) if not df_p3.empty else []
            ordem_meses = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]

            if len(anos_retornados) > 0:
                lista_titulos_abas = [f"Ano {ano}" for ano in anos_retornados] + ["📈 Todos (Comparativo)"]
                abas_anos = st.tabs(lista_titulos_abas)

                for i, ano in enumerate(anos_retornados):
                    with abas_anos[i]:
                        st.markdown(
                            f'<div class="section-subtitle">Evolução Mensal de Ocorrências — {ano}</div>',
                            unsafe_allow_html=True,
                        )
                        df_ano = df_p3[df_p3["ano"] == ano]
                        fig_p3_ano = px.line(
                            df_ano, x="nome_mes", y="total_acidentes", markers=True, text="total_acidentes",
                            labels={"nome_mes": "Mês", "total_acidentes": "Quantidade de Ocorrências"},
                        )
                        fig_p3_ano.update_traces(
                            line_color=PRF_BLUE, textposition="top center",
                            texttemplate="%{text:,}", textfont_size=11, cliponaxis=False,
                        )
                        fig_p3_ano.update_layout(
                            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                            xaxis={"categoryorder": "array", "categoryarray": ordem_meses},
                            margin={"r": 10, "t": 30, "l": 10, "b": 10}, height=320,
                        )
                        st.plotly_chart(fig_p3_ano, use_container_width=True)

                with abas_anos[-1]:
                    st.markdown(
                        '<div class="section-title">📊 Comparativo Sazonal Sobreposto (Ano contra Ano)</div>',
                        unsafe_allow_html=True,
                    )
                    fig_comparativo = px.line(
                        df_p3, x="nome_mes", y="total_acidentes", color="ano", markers=True, text="total_acidentes",
                        labels={
                            "nome_mes": "Mês", "total_acidentes": "Quantidade de Ocorrências", "ano": "Ano de Análise",
                        },
                        color_discrete_sequence=[PRF_NAVY, PRF_BLUE, PRF_YELLOW, PRF_RED, PRF_BLUE_DARK, PRF_GRAY_TXT],
                    )
                    fig_comparativo.update_traces(
                        textposition="top center", texttemplate="%{text:,}",
                        textfont_size=9, cliponaxis=False,
                    )
                    fig_comparativo.update_layout(
                        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                        xaxis={"categoryorder": "array", "categoryarray": ordem_meses},
                        margin={"r": 10, "t": 30, "l": 10, "b": 10}, height=340,
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                    )
                    st.plotly_chart(fig_comparativo, use_container_width=True)
            else:
                st.info("ℹ️ Dados temporais indisponíveis para os filtros aplicados.")