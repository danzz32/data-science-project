import pandas as pd
import pandera.pandas as pa
from pandera import Column, Check
from pathlib import Path
import logging
from datetime import datetime

# Configuração de log
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# ---------------------------------------------------------
# DEFINIÇÃO DO CONTRATO DE DADOS (PANDERA)
# ---------------------------------------------------------
trusted_contract = pa.DataFrameSchema({
    "data_inversa": Column(pd.Timestamp, Check(lambda s: s <= pd.Timestamp.now()), nullable=False),
    "uf": Column(str, Check.isin([
        'ac', 'al', 'am', 'ap', 'ba', 'ce', 'df', 'es', 'go', 'ma', 
        'mg', 'ms', 'mt', 'pa', 'pb', 'pe', 'pi', 'pr', 'rj', 'rn', 
        'ro', 'rr', 'rs', 'sc', 'se', 'sp', 'to'
    ]), nullable=False),
    "municipio": Column(str, nullable=False),
    "mortos": Column(int, Check.ge(0), coerce=True, nullable=False)
    # Coluna 'veiculos' removida pois não existe neste dataset específico da PRF
})
# ---------------------------------------------------------

def get_latest_raw_file(raw_dir: Path) -> Path:
    arquivos = list(raw_dir.glob("prf_191_*.csv"))
    if not arquivos:
        raise FileNotFoundError("Nenhum ficheiro bruto encontrado na pasta data/raw/")
    return max(arquivos, key=lambda p: p.stat().st_mtime)

def clean_data(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Aplica as regras de qualidade, isola falhas e retorna o df limpo, df quarentena e estatísticas."""
    df_clean = df.copy()
    stats = {"total_lidos": len(df)}
    lista_quarentena = []

    # PREPARAÇÃO: Limpar espaços e padronizar textos ANTES das regras para evitar quarentena injusta
    cols_str = df_clean.select_dtypes(include=['object', 'string']).columns
    for col in cols_str:
        df_clean[col] = df_clean[col].astype(str).str.strip().str.lower()

    # 0. DUPLICATAS
    logging.info("A isolar duplicatas exatas...")
    mask_dup = df_clean.duplicated(keep='first')
    if mask_dup.any():
        df_bad = df_clean[mask_dup].copy()
        df_bad['motivo_quarentena'] = 'Duplicata Exata'
        lista_quarentena.append(df_bad)
        df_clean = df_clean[~mask_dup]
    stats["quarentena_duplicatas"] = mask_dup.sum()

    # 1. TEMPORALIDADE
    logging.info("A aplicar regras de Temporalidade...")
    if 'data_inversa' in df_clean.columns:
        df_clean['data_inversa'] = pd.to_datetime(df_clean['data_inversa'], errors='coerce', dayfirst=True)
        mask_temp = df_clean['data_inversa'].isna() | (df_clean['data_inversa'] > pd.Timestamp.now())
        if mask_temp.any():
            df_bad = df_clean[mask_temp].copy()
            df_bad['motivo_quarentena'] = 'Temporalidade: Data Invalida ou Futura'
            lista_quarentena.append(df_bad)
            df_clean = df_clean[~mask_temp]
        stats["quarentena_temporalidade"] = mask_temp.sum()
        
    # 2. ACURÁCIA
    logging.info("A aplicar regras de Acurácia...")
    if 'uf' in df_clean.columns:
        ufs_validas = [
            'ac', 'al', 'am', 'ap', 'ba', 'ce', 'df', 'es', 'go', 'ma',
            'mg', 'ms', 'mt', 'pa', 'pb', 'pe', 'pi', 'pr', 'rj', 'rn',
            'ro', 'rr', 'rs', 'sc', 'se', 'sp', 'to'
        ]
        mask_uf = ~df_clean['uf'].isin(ufs_validas)
        if mask_uf.any():
            df_bad = df_clean[mask_uf].copy()
            df_bad['motivo_quarentena'] = 'Acuracia: UF Invalida'
            lista_quarentena.append(df_bad)
            df_clean = df_clean[~mask_uf]
        stats["quarentena_acuracia"] = mask_uf.sum()

    # 3. CONSISTÊNCIA
    logging.info("A aplicar regras de Consistência...")
    stats["quarentena_consistencia"] = 0
    
    colunas_vitimas = ['mortos', 'feridos_leves', 'feridos_graves', 'ilesos']
    for col in colunas_vitimas:
        if col in df_clean.columns:
            df_clean[col] = pd.to_numeric(df_clean[col], errors='coerce').fillna(0).astype(int).abs()
            
    # Nova Regra: É impossível o mesmo registo apontar Mortos > 0 e Ilesos > 0
    if all(c in df_clean.columns for c in ['mortos', 'ilesos']):
        mask_cons = (df_clean['mortos'] > 0) & (df_clean['ilesos'] > 0)
        if mask_cons.any():
            df_bad = df_clean[mask_cons].copy()
            df_bad['motivo_quarentena'] = 'Consistencia: Vitima com status contraditorio (Morto e Ileso)'
            lista_quarentena.append(df_bad)
            df_clean = df_clean[~mask_cons]
        stats["quarentena_consistencia"] = mask_cons.sum()

    # 4. COMPLETUDE
    logging.info("A aplicar regras de Completude...")
    stats["quarentena_completude"] = 0
    if 'municipio' in df_clean.columns:
        mask_mun = df_clean['municipio'].isna() | df_clean['municipio'].isin(['nan', 'none', '', 'null'])
        if mask_mun.any():
            df_bad = df_clean[mask_mun].copy()
            df_bad['motivo_quarentena'] = 'Completude: Municipio ausente'
            lista_quarentena.append(df_bad)
            df_clean = df_clean[~mask_mun]
        stats["quarentena_completude"] = mask_mun.sum()
        
    # Imputação em outras colunas menos críticas
    if len(cols_str) > 0:
        df_clean[cols_str] = df_clean[cols_str].replace(['nan', 'none', '', 'null'], 'nao_informado')
        df_clean[cols_str] = df_clean[cols_str].fillna('nao_informado')

    # Compilar a Quarentena
    if lista_quarentena:
        df_quarentena = pd.concat(lista_quarentena, ignore_index=True)
    else:
        df_quarentena = pd.DataFrame(columns=df_clean.columns.tolist() + ['motivo_quarentena'])

    return df_clean, df_quarentena, stats

def gerar_relatorio(stats: dict, total_aprovados: int, total_quarentena: int, report_dir: Path):
    """Gera o ficheiro Markdown com o relatório de qualidade."""
    report_path = report_dir / "quality_report.md"
    
    conteudo = f"""# Relatório de Qualidade de Dados - Camada Trusted
**Data de Execução:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Estratégia Adotada:** Quarentena (Isolamento de registos inválidos)

## Resumo da Execução
* **Total de Registos Lidos (Raw):** {stats['total_lidos']}
* **Total Aprovados na Validação:** {total_aprovados}
* **Total Enviados para Quarentena:** {total_quarentena}

## Motivos de Quarentena por Categoria
* **Duplicatas Exatas:** {stats['quarentena_duplicatas']} registos
* **Temporalidade (Datas inválidas ou no futuro):** {stats['quarentena_temporalidade']} registos
* **Acurácia (UF inválida):** {stats['quarentena_acuracia']} registos
* **Consistência (Dados vitimológicos contraditórios):** {stats['quarentena_consistencia']} registos
* **Completude (Município nulo):** {stats['quarentena_completude']} registos

*Nota: Os registos quarentenados foram isolados no ficheiro `prf_acidentes_quarentena.parquet` na camada `data/quarantine/` para futura auditoria.*
"""
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(conteudo)
    logging.info(f"📄 Relatório de Qualidade gerado em: {report_path}")

def main():
    ROOT_DIR = Path(__file__).resolve().parent.parent
    RAW_DIR = ROOT_DIR / "data" / "raw"
    TRUSTED_DIR = ROOT_DIR / "data" / "trusted"
    QUARANTINE_DIR = ROOT_DIR / "data" / "quarantine"
    REPORTS_DIR = ROOT_DIR / "reports"
    
    TRUSTED_DIR.mkdir(parents=True, exist_ok=True)
    QUARANTINE_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    
    try:
        raw_file = get_latest_raw_file(RAW_DIR)
        logging.info(f"A iniciar processamento: {raw_file.name}")
        
        df_raw = pd.read_csv(raw_file, sep=';', encoding='latin-1', low_memory=False)
        
        df_processed, df_quarentena, estatisticas = clean_data(df_raw)
        
        if not df_quarentena.empty:
            quarantine_path = QUARANTINE_DIR / "prf_acidentes_quarentena.parquet"
            df_quarentena.to_parquet(quarantine_path, index=False)
            logging.info(f"⚠️ {len(df_quarentena)} registos isolados em Quarentena: {quarantine_path}")
            
        logging.info("A validar dados aprovados contra o Contrato (Pandera)...")
        df_validated = trusted_contract.validate(df_processed)
        logging.info("✅ Contrato validado com sucesso! Camada Trusted garantida.")
        
        total_aprovados = len(df_validated)
        total_quarentenados = len(df_quarentena)
        
        output_path = TRUSTED_DIR / "prf_acidentes_trusted.parquet"
        df_validated.to_parquet(output_path, index=False)
        logging.info(f"✅ Dados aprovados guardados em PARQUET em: {output_path}")
        
        gerar_relatorio(estatisticas, total_aprovados, total_quarentenados, REPORTS_DIR)
        
    except pa.errors.SchemaError as e:
        logging.error(f"❌ Falha crítica de Contrato. A limpeza não capturou todos os erros:\n{e}")
    except Exception as e:
        logging.error(f"❌ Erro durante a execução: {e}")

if __name__ == "__main__":
    main()