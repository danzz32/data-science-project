import os
import duckdb
import pandas as pd
import pandera.pandas as pa
from pandera import Column, Check
from pathlib import Path
import logging
from datetime import datetime

# Configuração de log profissional
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# =====================================================================
# CONTRATO DE DADOS (PANDERA) - Camada Trusted Granular Corrigida
# =====================================================================
trusted_contract = pa.DataFrameSchema({
    # Chaves e Identificadores Originais da Base Granular (Por Indivíduo)
    "id": Column(pd.Int64Dtype(), nullable=False, coerce=True),
    "id_veiculo": Column(str, nullable=False),
    "pesid": Column(str, nullable=False),

    # Informações Temporais e Geográficas
    "data_inversa": Column(pd.Timestamp, nullable=False),
    "uf": Column(str, Check.isin([
        'ac', 'al', 'am', 'ap', 'ba', 'ce', 'df', 'es', 'go', 'ma',
        'mg', 'ms', 'mt', 'pa', 'pb', 'pe', 'pi', 'pr', 'rj', 'rn',
        'ro', 'rr', 'rs', 'sc', 'se', 'sp', 'to'
    ]), nullable=False),
    "br": Column(str, nullable=False), 
    
    # 🔥 CORREÇÃO: Contrato atualizado para exigir float/double numérico
    "latitude": Column(float, coerce=True, nullable=True),
    "longitude": Column(float, coerce=True, nullable=True),

    # Características da Ocorrência e Perfil do Indivíduo
    "causa_acidente": Column(str, nullable=False),
    "classificacao_acidente": Column(str, nullable=False),
    "condicao_meteorologica": Column(str, nullable=False), 
    "fase_dia": Column(str, nullable=False),
    "sexo": Column(str, nullable=False),
    "estado_fisico": Column(str, nullable=False),
    "tipo_envolvido": Column(str, nullable=False),

    # Métricas Estatísticas do Indivíduo (Higienizadas para Inteiros >= 0)
    "idade": Column(int, Check.ge(0), coerce=True, nullable=False),
    "mortos": Column(int, Check.ge(0), coerce=True, nullable=False),
    "feridos_leves": Column(int, Check.ge(0), coerce=True, nullable=False),
    "feridos_graves": Column(int, Check.ge(0), coerce=True, nullable=False),
    "ilesos": Column(int, Check.ge(0), coerce=True, nullable=False),
    "ignorados": Column(int, Check.ge(0), coerce=True, nullable=False)
})

def get_latest_raw_file(raw_dir: Path) -> Path:
    """Busca o arquivo bruto mais recente gerado pela etapa de ingestão."""
    arquivos = list(raw_dir.glob("prf_191_*.csv"))
    if not arquivos:
        raise FileNotFoundError("Nenhum arquivo bruto ('prf_191_*.csv') localizado na pasta data/raw/")
    return max(arquivos, key=lambda p: p.stat().st_mtime)

def process_with_duckdb(raw_file_path: Path) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Processa e higieniza a volumetria massiva do dataset via DuckDB de forma vetorizada."""
    logging.info("Iniciando motor em memória do DuckDB para processamento vetorizado...")
    con = duckdb.connect(database=':memory:')
    
    con.execute(f"""
        CREATE OR REPLACE VIEW v_raw_mestre AS 
        SELECT * FROM read_csv_auto('{raw_file_path}', delim=';', encoding='latin-1', all_varchar=True);
    """)
    
    cols_base = [col[0] for col in con.execute("DESCRIBE v_raw_mestre;").fetchall()]
    
    col_meteo = 'condicao_meteorologica'
    if 'condicao_metereologica' in cols_base:
        col_meteo = 'condicao_metereologica'
    elif 'condicao_meteorologica' in cols_base:
        col_meteo = 'condicao_meteorologica'

    def sql_cast_int(col):
        if col in cols_base:
            return f"COALESCE(TRY_CAST(NULLIF(NULLIF(TRIM(v_raw_mestre.{col}), 'NA'), '') AS INTEGER), 0)"
        return "0"

    # Query de Higienização corrigida com mapeamento geográfico robusto
    query_transform = f"""
        SELECT 
            -- Chaves e Identificadores
            TRY_CAST(v_raw_mestre.id AS BIGINT) as id,
            COALESCE(NULLIF(NULLIF(TRIM(v_raw_mestre.id_veiculo), 'NA'), ''), '0') as id_veiculo,
            COALESCE(NULLIF(NULLIF(TRIM(v_raw_mestre.pesid), 'NA'), ''), '0') as pesid,
            
            -- Temporalidade (Trata formatos ISO YYYY-MM-DD e BR DD/MM/YYYY dinamicamente)
            COALESCE(TRY_CAST(v_raw_mestre.data_inversa AS DATE), strptime(v_raw_mestre.data_inversa, '%d/%m/%Y')::DATE) as data_inversa,
            
            -- Georreferenciamento e Unidades da Federação
            LOWER(TRIM(v_raw_mestre.uf)) as uf,
            COALESCE(TRY_CAST(TRY_CAST(v_raw_mestre.br AS DOUBLE) AS INTEGER)::VARCHAR, '0') as br,
            
            -- 🔥 CORREÇÃO: Tratando a vírgula decimal e tipando nativamente como DOUBLE/FLOAT
            TRY_CAST(REPLACE(NULLIF(NULLIF(TRIM(v_raw_mestre.latitude), 'NA'), ''), ',', '.') AS DOUBLE) as latitude,
            TRY_CAST(REPLACE(NULLIF(NULLIF(TRIM(v_raw_mestre.longitude), 'NA'), ''), ',', '.') AS DOUBLE) as longitude,
            
            -- Normalização de Variáveis Categóricas e Textuais
            LOWER(TRIM(COALESCE(NULLIF(NULLIF(v_raw_mestre.causa_acidente, 'NA'), ''), 'nao_informado'))) as causa_acidente,
            LOWER(TRIM(COALESCE(NULLIF(NULLIF(v_raw_mestre.classificacao_acidente, 'NA'), ''), 'nao_informado'))) as classificacao_acidente,
            LOWER(TRIM(COALESCE(NULLIF(NULLIF(v_raw_mestre.{col_meteo}, 'NA'), ''), 'nao_informado'))) as condicao_meteorologica,
            LOWER(TRIM(COALESCE(NULLIF(NULLIF(v_raw_mestre.fase_dia, 'NA'), ''), 'nao_informado'))) as fase_dia,
            LOWER(TRIM(COALESCE(NULLIF(NULLIF(v_raw_mestre.sexo, 'NA'), ''), 'nao_informado'))) as sexo,
            LOWER(TRIM(COALESCE(NULLIF(NULLIF(v_raw_mestre.estado_fisico, 'NA'), ''), 'nao_informado'))) as estado_fisico,
            LOWER(TRIM(COALESCE(NULLIF(NULLIF(v_raw_mestre.tipo_envolvido, 'NA'), ''), 'nao_informado'))) as tipo_envolvido,
            
            -- Contadores Estatísticos do Indivíduo
            {sql_cast_int('idade')} as idade,
            {sql_cast_int('mortos')} as mortos,
            {sql_cast_int('feridos_leves')} as feridos_leves,
            {sql_cast_int('feridos_graves')} as feridos_graves,
            {sql_cast_int('ilesos')} as ilesos,
            {sql_cast_int('ignorados')} as ignorados
        FROM v_raw_mestre;
    """
    
    df_transformed = con.execute(query_transform).df()
    
    # Separação seletiva para a quarentena
    df_aprovados = df_transformed[df_transformed['data_inversa'].notna() & df_transformed['id'].notna()].copy()
    df_quarentena = df_transformed[df_transformed['data_inversa'].isna() | df_transformed['id'].isna()].copy()
    
    if not df_quarentena.empty:
        df_quarentena['motivo_quarentena'] = 'Falha critica de parsing: ID ou Data ausentes/corrompidos'

    stats = {
        "total_lidos": len(df_transformed),
        "total_aprovados": len(df_aprovados),
        "total_quarentena": len(df_quarentena),
        "quarentena_temporalidade": len(df_quarentena)
    }
    
    return df_aprovados, df_quarentena, stats

def gerar_relatorio(stats: dict, report_dir: Path, volumetria: dict):
    report_path = report_dir / "quality_report.md"
    conteudo = f"""# Relatório de Qualidade de Dados - Camada Trusted (DuckDB Motor)
**Data de Execução:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Estratégia Computacional:** Arquitetura Vetorizada de Alta Performance com DuckDB

## Resumo da Execução (Linhas)
* **Total de Registros Lidos (Layer Raw):** {stats['total_lidos']:}
* **Total Aprovados pelo Pipeline:** {stats['total_aprovados']:}
* **Total Isolados na Quarentena:** {stats['total_quarentena']:}

## Eficiência de Armazenamento e Compressão 📉
* **Tamanho do Arquivo Bruto (CSV):** {volumetria['csv_size_mb']:.2f} MB
* **Tamanho do Arquivo Otimizado (Parquet Trusted):** {volumetria['parquet_size_mb']:.2f} MB
* **Ganho de Economia em Disco:** **{volumetria['reducao_pct']:.2f}%** reduzidos com codificação Parquet e Compressão Snappy

## Detalhamento de Erros de Quarentena
* **Falhas Críticas de Parsing (ID ou Data Nula):** {stats['quarentena_temporalidade']} registros
"""
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(conteudo)
    logging.info(f"📄 Relatório de Governança atualizado com sucesso em: {report_path}")

def main():
    SCRIPT_DIR = Path(__file__).resolve().parent if '__file__' in locals() else Path(os.getcwd())
    ROOT_DIR = SCRIPT_DIR.parent if SCRIPT_DIR.name in ['src', 'notebooks'] else SCRIPT_DIR
    
    RAW_DIR = ROOT_DIR / "data" / "raw"
    TRUSTED_DIR = ROOT_DIR / "data" / "trusted"
    QUARANTINE_DIR = ROOT_DIR / "data" / "quarantine"
    REPORTS_DIR = ROOT_DIR / "reports"

    for folder in [TRUSTED_DIR, QUARANTINE_DIR, REPORTS_DIR]:
        folder.mkdir(parents=True, exist_ok=True)

    try:
        raw_file = get_latest_raw_file(RAW_DIR)
        logging.info(f"Arquivo alvo localizado para transformação: {raw_file.name}")

        csv_size_bytes = raw_file.stat().st_size
        csv_size_mb = csv_size_bytes / (1024 * 1024)

        df_aprovados, df_quarentena, estatisticas = process_with_duckdb(raw_file)

        quarantine_path = QUARANTINE_DIR / "prf_acidentes_quarentena.parquet"
        if not df_quarentena.empty:
            df_quarentena.to_parquet(quarantine_path, index=False)
            logging.info(f"⚠️ {len(df_quarentena)} registros críticos isolados em Quarentena.")
        elif quarantine_path.exists():
            quarantine_path.unlink()

        logging.info("Submetendo DataFrame higienizado ao crivo do Pandera Contract...")
        df_validated = trusted_contract.validate(df_aprovados)
        logging.info("✅ Sucesso! Dados aderentes ao Contrato de Dados da Camada Trusted.")

        output_path = TRUSTED_DIR / "prf_acidentes_trusted.parquet"
        df_validated.to_parquet(output_path, index=False, compression="snappy")
        logging.info(f"💾 Camada Trusted salva com sucesso em: {output_path}")

        parquet_size_bytes = output_path.stat().st_size
        parquet_size_mb = parquet_size_bytes / (1024 * 1024)
        reducao_pct = ((csv_size_bytes - parquet_size_bytes) / csv_size_bytes) * 100

        logging.info(f"📉 Indicadores de Otimização Volumétrica:")
        logging.info(f"   - CSV Bruto:    {csv_size_mb:.2f} MB")
        logging.info(f"   - Parquet Tech: {parquet_size_mb:.2f} MB")
        logging.info(f"   - Redução de Armazenamento: {reducao_pct:.2f}% salvos!")

        volumetria = {
            "csv_size_mb": csv_size_mb,
            "parquet_size_mb": parquet_size_mb,
            "reducao_pct": reducao_pct
        }

        gerar_relatorio(estatisticas, REPORTS_DIR, volumetria)
        logging.info("🏁 Pipeline de Transformação concluído com sucesso total!")

    except pa.errors.SchemaError as schema_err:
        logging.error(f"❌ Violação detectada pelo Contrato do Pandera:\n{schema_err}")
    except Exception as general_err:
        logging.error(f"❌ Falha crítica no pipeline de execução: {general_err}")

if __name__ == "__main__":
    main()