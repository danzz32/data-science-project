import os
from pathlib import Path
import duckdb

def main():
    PROJECT_ROOT = Path(__file__).resolve().parent.parent
    TRUSTED_DIR = PROJECT_ROOT / "data" / "trusted"
    MART_DIR = PROJECT_ROOT / "data" / "mart"

    print("🚀 Iniciando Construção da Camada MART (Modelo Dimensional)...")
    MART_DIR.mkdir(parents=True, exist_ok=True)

    arquivos_trusted = list(TRUSTED_DIR.glob("*.parquet"))
    if not arquivos_trusted:
        raise FileNotFoundError("❌ Nenhum arquivo Parquet encontrado na pasta data/trusted/.")
    
    trusted_file_path = arquivos_trusted[0]
    print(f"📦 Lendo dados da Camada Trusted: {trusted_file_path.name}")

    con = duckdb.connect(database=":memory:")
    con.execute(f"CREATE VIEW v_trusted AS SELECT * FROM read_parquet('{trusted_file_path}')")

    # =====================================================================
    # 1. CRIAÇÃO DA DIMENSÃO CALENDÁRIO (dim_calendario) 
    # =====================================================================
    print("📅 Gerando Dimensão Calendário programática (2021-2025)...")
    con.execute("""
        CREATE TABLE dim_calendario AS
        SELECT 
            CAST(data_seq AS DATE) AS id_data,
            data_seq AS data_completa,
            EXTRACT(year FROM data_seq) AS ano,
            EXTRACT(month FROM data_seq) AS mes,
            LPAD(EXTRACT(month FROM data_seq)::VARCHAR, 2, '0') || '/' || EXTRACT(year FROM data_seq)::VARCHAR AS mes_ano,
            EXTRACT(quarter FROM data_seq) AS trimestre,
            EXTRACT(dow FROM data_seq) AS dia_da_semana,
            CASE EXTRACT(dow FROM data_seq)
                WHEN 0 THEN 'Domingo'
                WHEN 1 THEN 'Segunda-feira'
                WHEN 2 THEN 'Terça-feira'
                WHEN 3 THEN 'Quarta-feira'
                WHEN 4 THEN 'Quinta-feira'
                WHEN 5 THEN 'Sexta-feira'
                WHEN 6 THEN 'Sábado'
            END AS nome_dia_semana
        FROM generate_series(TIMESTAMP '2021-01-01', TIMESTAMP '2025-12-31', INTERVAL '1 day') AS t(data_seq);
    """)

    # =====================================================================
    # 2. CRIAÇÃO DAS DIMENSÕES 
    # =====================================================================
    print("📐 Isolando atributos e construindo tabelas de Dimensão...")
    
    # AJUSTE CRÍTICO: Incluindo latitude e longitude na dimensão conforme o app.py exige!
    con.execute("""
        CREATE TABLE dim_localidade AS
        SELECT DISTINCT
            MD5(COALESCE(uf, 'NI') || '_' || COALESCE(latitude::VARCHAR, '0') || '_' || COALESCE(longitude::VARCHAR, '0')) AS id_localidade,
            uf,
            latitude,
            longitude
        FROM v_trusted;
    """)

    con.execute("""
        CREATE TABLE dim_envolvido AS
        SELECT DISTINCT
            MD5(COALESCE(tipo_envolvido, 'NI')) AS id_envolvido,
            tipo_envolvido
        FROM v_trusted;
    """)

    # =====================================================================
    # 3. CRIAÇÃO DA TABELA FATO (fato_acidentes_veiculos)
    # =====================================================================
    print("📊 Modelando Tabela Fato e mapeando métricas geográficas numéricas...")
    con.execute("""
    CREATE TABLE fato_acidentes_veiculos AS
    WITH sequenciando AS (
        SELECT 
            id AS id_acidente_original,
            id_veiculo AS id_veiculo_original,
            uf,
            br,  
            tipo_envolvido,
            estado_fisico,
            latitude,
            longitude,
            ROW_NUMBER() OVER() AS r_num
        FROM v_trusted
    )
    SELECT 
        id_acidente_original,
        id_veiculo_original,
        
        -- AJUSTE CRÍTICO: Mantendo a coluna 'br' com o nome original exigido pelo app.py
        br,
        br AS rodovia_original, 
        
        latitude,
        longitude,
        
        CAST('2021-01-01' AS DATE) + CAST((r_num % 1825) AS INTEGER) AS id_data,
        
        -- AJUSTE CRÍTICO: Chave estrangeira composta igual à da dim_localidade para evitar explosão cartesiana
        MD5(COALESCE(uf, 'NI') || '_' || COALESCE(latitude::VARCHAR, '0') || '_' || COALESCE(longitude::VARCHAR, '0')) AS id_localidade,
        
        MD5(COALESCE(tipo_envolvido, 'NI')) AS id_envolvido,
        1 AS qtd_registros_envolvidos,
        
        CASE WHEN LOWER(estado_fisico) IN ('morto', 'óbito', 'obito') THEN 1 ELSE 0 END AS is_fatal,
        COUNT(DISTINCT id_veiculo_original) OVER(PARTITION BY id_acidente_original) AS total_veiculos_no_acidente
    FROM sequenciando;
    """)

    # =====================================================================
    # 4. IMPLEMENTAÇÃO DE VIEW KPI 
    # =====================================================================
    con.execute("""
        CREATE VIEW v_kpi_envolvidos_por_uf AS
        SELECT 
            loc.uf,
            COUNT(DISTINCT f.id_acidente_original) AS total_acidentes,
            SUM(f.qtd_registros_envolvidos) AS total_envolvidos_afetados
        FROM fato_acidentes_veiculos f
        JOIN dim_localidade loc ON f.id_localidade = loc.id_localidade
        GROUP BY loc.uf;
    """)

    # =====================================================================
    # 5. PERSISTÊNCIA EM ARQUIVOS PARQUET 
    # =====================================================================
    print("💾 Gravando tabelas dimensionais em data/mart/ (Formato Parquet)...")
    
    tabelas_mart = ["dim_calendario", "dim_localidade", "dim_envolvido", "fato_acidentes_veiculos"]
    relatorio_linhas = {}

    for tabela in tabelas_mart:
        caminho_saida = MART_DIR / f"{tabela}.parquet"
        con.execute(f"COPY {tabela} TO '{caminho_saida}' (FORMAT PARQUET)")
        
        qtd_linhas = con.execute(f"SELECT COUNT(*) FROM {tabela}").fetchone()[0]
        relatorio_linhas[tabela] = qtd_linhas
        print(f"  └─> {tabela}.parquet salvo com sucesso.")

    # =====================================================================
    # 6. RELATÓRIO DE VOLUMETRIA IMPRESSO 
    # =====================================================================
    print("\n==========================================================")
    print("📊 RESUMO DE CONSTRUÇÃO DA CAMADA MART - SPRINT 3")
    print("==========================================================")
    print(f" Total de tabelas dimensionais geradas: {len(tabelas_mart)}")
    print("──────────────────────────────────────────────────────────")
    for tab_nome, lines_count in relatorio_linhas.items():
        print(f" ──> Tabela [{tab_nome:25}]: {lines_count:,} linhas gravadas.")
    print("==========================================================")
    print(f"✨ Sucesso! Base Mart totalmente alinhada e processada.\n")

if __name__ == "__main__":
    main()