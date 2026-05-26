import pandas as pd
import pandera.pandas as pa
from pandera import Column, Check
from pathlib import Path
import logging
from datetime import datetime

# Configuração de log
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# CONTRATO DE DADOS (PANDERA) - Versão Tolerante e Flexível
# CONTRATO DE DADOS (PANDERA) - Personalizado para o Projeto
trusted_contract = pa.DataFrameSchema({
    # Identificador Único (Garante que não há ID repetido e nem nulo)
    "id": Column(pd.Int64Dtype(), unique=True, nullable=False, coerce=True),
    
    # Informações Temporais e Geográficas (Sem nulos)
    "data_inversa": Column(pd.Timestamp, nullable=False),
    "uf": Column(str, Check.isin([
        'ac', 'al', 'am', 'ap', 'ba', 'ce', 'df', 'es', 'go', 'ma', 
        'mg', 'ms', 'mt', 'pa', 'pb', 'pe', 'pi', 'pr', 'rj', 'rn', 
        'ro', 'rr', 'rs', 'sc', 'se', 'sp', 'to'
    ]), nullable=False),
    "br": Column(str, nullable=False), # Tratado como string/texto para evitar problemas com BRs tipo '010'
    "latitude": Column(str, nullable=False),
    "longitude": Column(str, nullable=False),

    # Características do Acidente (Sem nulos)
    "causa_acidente": Column(str, nullable=False),
    "classificacao_acidente": Column(str, nullable=False),
    "condicao_metereologica": Column(str, nullable=False),

    # Métricas Estatísticas e Contagens (Sem nulos - Inteiros Maiores ou Iguais a Zero)
    "mortos": Column(int, Check.ge(0), coerce=True, nullable=False),
    "feridos": Column(int, Check.ge(0), coerce=True, nullable=False),
    "feridos_leves": Column(int, Check.ge(0), coerce=True, nullable=False),
    "feridos_graves": Column(int, Check.ge(0), coerce=True, nullable=False),
    "veiculos": Column(int, Check.ge(0), coerce=True, nullable=False)
})

def get_latest_raw_file(raw_dir: Path) -> Path:
    arquivos = list(raw_dir.glob("prf_191_*.csv"))
    if not arquivos:
        raise FileNotFoundError("Nenhum ficheiro bruto encontrado na pasta data/raw/")
    return max(arquivos, key=lambda p: p.stat().st_mtime)

def clean_data(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Aplica as regras de qualidade, corrige formatos e isola apenas erros críticos irremediáveis."""
    df_clean = df.copy()
    stats = {
        "total_lidos": len(df),
        "quarentena_duplicatas": 0,
        "quarentena_temporalidade": 0,
        "quarentena_acuracia": 0,
        "quarentena_consistencia": 0,
        "quarentena_completude": 0,
        "correcoes_formato_data": 0,
        "correcoes_consistencia_vitimas": 0
    }
    lista_quarentena = []

    # Mapeia as colunas de texto logo no início para evitar erros de escopo (NameError)
    cols_str = df_clean.select_dtypes(include=['object', 'string']).columns

    # 1. TEMPORALIDADE (Conversão Direta e Sem Descarte)
    logging.info("A converter formato de datas e validando integridade...")
    if 'data_inversa' in df_clean.columns:
        # Tenta ler como formato brasileiro (DD/MM/AAAA)
        data_br = pd.to_datetime(df_clean['data_inversa'], format='%d/%m/%Y', errors='coerce')
        
        # Tenta ler como formato invertido (AAAA-MM-DD)
        data_inv = pd.to_datetime(df_clean['data_inversa'], format='%Y-%m-%d', errors='coerce')
        
        # Combina os dois formatos
        df_clean['data_inversa'] = data_br.fillna(data_inv)
        
        # Remove horas/minutos deixando apenas a data pura
        df_clean['data_inversa'] = df_clean['data_inversa'].dt.normalize()
        
        # Contabiliza quantos registros foram salvos do formato invertido
        stats["correcoes_formato_data"] = int(data_br.isna().sum() - df_clean['data_inversa'].isna().sum())
        
        # QUARENTENA ULTRA-RESTRITA: Só descarta se o texto for completamente ilegível
        mask_temp_critico = df_clean['data_inversa'].isna()
        
        if mask_temp_critico.any():
            df_bad = df_clean[mask_temp_critico].copy()
            df_bad['motivo_quarentena'] = 'Temporalidade: Texto inválido impossível de converter para data'
            lista_quarentena.append(df_bad)
            df_clean = df_clean[~mask_temp_critico]
            
        stats["quarentena_temporalidade"] = int(mask_temp_critico.sum())

    # TRATAMENTO DA RODOVIA (BR): Garante que vire texto limpo sem decimais (.0)
    if 'br' in df_clean.columns:
        logging.info("A padronizar coluna 'br' para o formato de texto do contrato...")
        # Converte para numérico limpando erros, preenche nulos com 0, vira inteiro e depois string limpa
        df_clean['br'] = pd.to_numeric(df_clean['br'], errors='coerce').fillna(0).astype(int).astype(str)
        # Opcional: Se quiser padronizar com 3 dígitos (ex: BR-040, vira '040'), descomente a linha abaixo:
        # df_clean['br'] = df_clean['br'].str.zfill(3)

    # PREPARAÇÃO RESTANTE: Limpar espaços e padronizar textos das demais colunas
    for col in cols_str:
        if col != 'data_inversa' and col != 'br':  # Evita re-transformar colunas já tratadas
            df_clean[col] = df_clean[col].astype(str).str.strip().str.lower()

    # 0. DUPLICATAS
    logging.info("A isolar duplicatas exatas...")
    mask_dup = df_clean.duplicated(keep='first')
    if mask_dup.any():
        df_bad = df_clean[mask_dup].copy()
        df_bad['motivo_quarentena'] = 'Duplicata Exata'
        lista_quarentena.append(df_bad)
        df_clean = df_clean[~mask_dup]
    stats["quarentena_duplicatas"] = int(mask_dup.sum())
        
    # 2. ACURÁCIA
    logging.info("A aplicar regras de Acurácia...")
    if 'uf' in df_clean.columns:
        ufs_validas = ['ac', 'al', 'am', 'ap', 'ba', 'ce', 'df', 'es', 'go', 'ma', 'mg', 'ms', 'mt', 'pa', 'pb', 'pe', 'pi', 'pr', 'rj', 'rn', 'ro', 'rr', 'rs', 'sc', 'se', 'sp', 'to']
        df_clean['uf'] = df_clean['uf'].astype(str).str.strip().str.lower()
        mask_uf = ~df_clean['uf'].isin(ufs_validas)
        if mask_uf.any():
            df_bad = df_clean[mask_uf].copy()
            df_bad['motivo_quarentena'] = 'Acuracia: UF Invalida'
            lista_quarentena.append(df_bad)
            df_clean = df_clean[~mask_uf]
        stats["quarentena_acuracia"] = int(mask_uf.sum())

    # 3. CONSISTÊNCIA (Com Correção Lógica Automática)
    logging.info("A aplicar regras de Consistência com Correção Automática...")
    colunas_vitimas = ['mortos', 'feridos', 'feridos_leves', 'feridos_graves', 'ilesos', 'veiculos']
    for col in colunas_vitimas:
        if col in df_clean.columns:
            df_clean[col] = pd.to_numeric(df_clean[col], errors='coerce').fillna(0).astype(int).abs()
            
    if all(c in df_clean.columns for c in ['mortos', 'ilesos']):
        mask_cons = (df_clean['mortos'] > 0) & (df_clean['ilesos'] > 0)
        if mask_cons.any():
            df_clean.loc[mask_cons, 'ilesos'] = 0
            stats["correcoes_consistencia_vitimas"] = int(mask_cons.sum())

    # 4. COMPLETUDE
    logging.info("A aplicar regras de Completude...")
    if 'municipio' in df_clean.columns:
        df_clean['municipio'] = df_clean['municipio'].astype(str).str.strip().str.lower()
        mask_mun = df_clean['municipio'].isna() | df_clean['municipio'].isin(['nan', 'none', '', 'null'])
        if mask_mun.any():
            df_bad = df_clean[mask_mun].copy()
            df_bad['motivo_quarentena'] = 'Completude: Municipio ausente'
            lista_quarentena.append(df_bad)
            df_clean = df_clean[~mask_mun]
        stats["quarentena_completude"] = int(mask_mun.sum())
        
    if len(cols_str) > 0:
        for col in cols_str:
            if col != 'data_inversa' and col != 'br':
                df_clean[col] = df_clean[col].replace(['nan', 'none', '', 'null'], 'nao_informado')
                df_clean[col] = df_clean[col].fillna('nao_informado')

    if lista_quarentena:
        df_quarentena = pd.concat(lista_quarentena, ignore_index=True)
    else:
        df_quarentena = pd.DataFrame(columns=df_clean.columns.tolist() + ['motivo_quarentena'])

    return df_clean, df_quarentena, stats

def gerar_relatorio(stats: dict, total_aprovados: int, total_quarentena: int, report_dir: Path, volumetria: dict):
    """Gera o ficheiro Markdown com o relatório detalhado de qualidade."""
    report_path = report_dir / "quality_report.md"
    
    conteudo = f"""# Relatório de Qualidade de Dados - Camada Trusted
**Data de Execução:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Estratégia Adotada:** Quarentena Seletiva + Correção Automática de Formatos

## Resumo da Execução (Linhas)
* **Total de Registos Lidos (Raw):** {stats['total_lidos']}
* **Total Aprovados na Validação:** {total_aprovados}
* **Total Enviados para Quarentena:** {total_quarentena}

## Correções Automáticas Aplicadas (Dados Salvos do Descarte) ✔️
* **Formatos de Data Corrigidos (Invertidos para Padrão):** {stats['correcoes_formato_data']} registos salvos
* **Contradições Vitimológicas Ajustadas (Morto & Ileso):** {stats['correcoes_consistencia_vitimas']} registos salvos

## Eficiência de Armazenamento (CSV vs Parquet)
* **Tamanho do Ficheiro Original (CSV):** {volumetria['csv_size_mb']:.2f} MB
* **Tamanho do Ficheiro Destino (Parquet Trusted):** {volumetria['parquet_size_mb']:.2f} MB
* **Percentual de Redução de Espaço:** **{volumetria['reducao_pct']:.2f}%** de economia em disco 📉

## Motivos de Quarentena por Categoria (Erros Críticos)
* **Duplicatas Exatas:** {stats['quarentena_duplicatas']} registos
* **Temporalidade (Datas totalmente corrompidas/ilegíveis):** {stats['quarentena_temporalidade']} registos
* **Acurácia (UF inválida):** {stats['quarentena_acuracia']} registos
* **Consistência (Dados contraditórios irrecuperáveis):** {stats['quarentena_consistencia']} registos
* **Completude (Município nulo):** {stats['quarentena_completude']} registos
"""
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(conteudo)
    logging.info(f"📄 Relatório de Qualidade gerado com sucesso em: {report_path}")

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
        
        csv_size_bytes = raw_file.stat().st_size
        csv_size_mb = csv_size_bytes / (1024 * 1024)
        
        # Lê o arquivo tratando a data inicialmente como string
        df_raw = pd.read_csv(raw_file, sep=';', encoding='latin-1', low_memory=False, dtype={'data_inversa': str})
        
        df_processed, df_quarentena, estatisticas = clean_data(df_raw)
        
        if not df_quarentena.empty:
            quarantine_path = QUARANTINE_DIR / "prf_acidentes_quarentena.parquet"
            df_quarentena.to_parquet(quarantine_path, index=False)
            logging.info(f"⚠️ {len(df_quarentena)} registos isolados em Quarentena: {quarantine_path}")
        else:
            quarantine_path = QUARANTINE_DIR / "prf_acidentes_quarentena.parquet"
            if quarantine_path.exists():
                quarantine_path.unlink()
            
        logging.info("A validar dados aprovados contra o Contrato (Pandera)...")
        df_validated = trusted_contract.validate(df_processed)
        logging.info("✅ Contrato validado com sucesso! Camada Trusted garantida.")
        
        total_aprovados = len(df_validated)
        total_quarentenados = len(df_quarentena)
        
        output_path = TRUSTED_DIR / "prf_acidentes_trusted.parquet"
        df_validated.to_parquet(output_path, index=False)
        logging.info(f"✅ Dados aprovados guardados em PARQUET em: {output_path}")
        
        # Cálculos de Volumetria e Eficiência
        parquet_size_bytes = output_path.stat().st_size
        parquet_size_mb = parquet_size_bytes / (1024 * 1024)
        reducao_pct = ((csv_size_bytes - parquet_size_bytes) / csv_size_bytes) * 100
        
        # 📊 NOVO: Feedback visual imediato no terminal
        logging.info(f"📉 Eficiência de Armazenamento:")
        logging.info(f"   - Tamanho Original (CSV): {csv_size_mb:.2f} MB")
        logging.info(f"   - Tamanho Destino (Parquet): {parquet_size_mb:.2f} MB")
        logging.info(f"   - Redução de Espaço em Disco: {reducao_pct:.2f}% economizados!")
        
        volumetria = {
            "csv_size_mb": csv_size_mb,
            "parquet_size_mb": parquet_size_mb,
            "reducao_pct": reducao_pct
        }
        
        gerar_relatorio(estatisticas, total_aprovados, total_quarentenados, REPORTS_DIR, volumetria)
        
    except pa.errors.SchemaError as e:
        logging.error(f"❌ Falha crítica de Contrato:\n{e}")
    except Exception as e:
        logging.error(f"❌ Erro durante a execução: {e}")
        
if __name__ == "__main__":
    main()